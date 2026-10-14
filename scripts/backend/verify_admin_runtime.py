"""PHASE06B HTTP, aggregation/explain and immutable database evidence."""
import argparse
import copy
import json
import re
import secrets
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timedelta, timezone
from importlib.metadata import version
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4
from bson import ObjectId, json_util

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app import create_app
from verify_auth_users import fingerprint, NAMES
from verify_integration_05ab import Listener, source_manifest
from app.auth.passwords import hash_password
from app.repositories.dashboard_repository import DashboardRepository
from app.schemas.dashboard_schema import ReportWindow

BASELINE = ROOT / '.local/phase06b-before.json'


def capture():
    app = create_app()
    try:
        snapshot = fingerprint(app.extensions['mongo'].database)
        previous = json.loads((ROOT / '.local/phase05c-before.json').read_text())['database']
        assert snapshot == previous, 'Development DB differs from approved Commerce baseline'
        with BASELINE.open('x', encoding='utf-8') as file:
            json.dump(snapshot, file, indent=2)
        print('Saved PHASE06B read-only baseline')
    finally:
        app.extensions['mongo'].close()


def explain_summary(explain):
    cursor = next((stage['$cursor'] for stage in explain.get('stages', []) if '$cursor' in stage), explain)
    stats, planner = cursor['executionStats'], cursor['queryPlanner']
    plan = planner['winningPlan']
    def indexes(value):
        if isinstance(value, dict):
            return ([value['indexName']] if 'indexName' in value else []) + [name for child in value.values() for name in indexes(child)]
        if isinstance(value, list):
            return [name for child in value for name in indexes(child)]
        return []
    return {'winningPlan': plan, 'indexes': sorted(set(indexes(plan))),
            **{key: stats[key] for key in ('nReturned', 'totalDocsExamined', 'totalKeysExamined', 'executionTimeMillis')}}


def verify():
    before = json.loads(BASELINE.read_text())
    suites = {}
    for name, file in [('worker', 'phase06b-worker-pytest.xml'), ('full', 'phase06b-pytest.xml')]:
        suite = ET.parse(ROOT / 'backend/evidence' / file).getroot().find('testsuite')
        assert suite is not None and all(suite.attrib[k] == '0' for k in ('failures', 'errors', 'skipped'))
        suites[name] = {**suite.attrib, 'pass': int(suite.attrib['tests'])}
    manifest = source_manifest()
    tested_manifest = json.loads((ROOT / '.local/phase06b-source-before-tests.json').read_text())
    # API documentation may be completed by the parallel worker while pytest runs.
    # Every backend source/test hash must match; the current contract is audited below.
    assert {key: value for key, value in manifest.items() if key.startswith('backend/')} == {
        key: value for key, value in tested_manifest.items() if key.startswith('backend/')}
    dev = create_app()
    test, listeners = None, []
    user_ids, product_ids, order_ids, checks = [], [], [], []
    try:
        dev_db = dev.extensions['mongo'].database
        assert fingerprint(dev_db) == before
        config = {key: dev.config[key] for key in ('MONGODB_URI', 'JWT_ISSUER', 'JWT_AUDIENCE')}
        config.update(APP_ENV='testing', MONGODB_DB='ecommerce_dev', MONGODB_TEST_DB='ecommerce_test',
                      JWT_SECRET=secrets.token_urlsafe(48), LOG_LEVEL='ERROR')
        test = create_app(config)
        db = test.extensions['mongo'].database
        marker = json.loads((ROOT / '.local/ecommerce_test.ownership.json').read_text())
        assert marker == {'project': str(ROOT), 'database': 'ecommerce_test', 'endpoint': 'localhost:27017/rs0'}
        assert db.name == 'ecommerce_test' and set(db.list_collection_names()) == set(NAMES)
        assert all(db[n].count_documents({}) == 0 for n in NAMES), 'Refusing to mutate existing test data'
        routes = [{'method': method, 'path': rule.rule} for rule in test.url_map.iter_rules()
                  for method in sorted(rule.methods - {'HEAD', 'OPTIONS'})]
        pairs = [(row['method'], re.sub(r'<[^>]+>', ':param', row['path'])) for row in routes]
        assert all(count == 1 for count in Counter(pairs).values())
        contract = (ROOT / 'docs/api-contract.md').read_text(encoding='utf-8')
        body = contract.split('## Admin Orders và Dashboard IMPLEMENTED — PHASE 06B\n', 1)[1].split('\n## ', 1)[0]
        documented = {(m, re.sub(r':\w+', ':param', p)) for m, p in re.findall(r'^\| (GET|POST) (/[^ |]+)', body, re.M)}
        actual = {(m, p.removeprefix('/api/v1')) for m, p in pairs if p.startswith(('/api/v1/admin/orders', '/api/v1/admin/dashboard'))}
        assert len(documented) == 11 and documented == actual
        feature_rows = set()
        for feature in ('admin-orders', 'admin-dashboard'):
            text = (ROOT / f'docs/features/{feature}.md').read_text(encoding='utf-8')
            feature_rows.update((m, re.sub(r':\w+', ':param', p)) for m, p in re.findall(r'^\| (GET|POST) (/[^ |]+)', text, re.M))
        assert feature_rows == documented
        listener, dev_listener = Listener(test), Listener(dev)
        listeners.extend([listener, dev_listener])

        def http(method, path, expected=200, payload=None, token=None, base=None):
            headers = {'Content-Type': 'application/json'}
            if token:
                headers['Authorization'] = 'Bearer '+token
            data = json.dumps(payload).encode() if payload is not None else None
            try:
                response = urlopen(Request((base or listener.base)+path, data=data, headers=headers, method=method), timeout=15)
            except HTTPError as error:
                response = error
            with response:
                raw = response.read()
                body = json.loads(raw) if raw else None
                assert response.status == expected, (method, path.split('?')[0], response.status, expected)
                if body:
                    assert body['meta']['requestId'] == response.headers['X-Request-ID']
                    assert not any(key in raw.decode() for key in ('passwordHash', 'tokenVersion', 'checkoutKey', 'checkoutRequestHash'))
                checks.append({'method': method, 'path': re.sub(r'/[a-f0-9]{24}(?=/|$)', '/:id', path).split('?')[0],
                               'status': expected, 'database': 'dev-read-only' if base == dev_listener.base else 'owned-test'})
                return body['data'] if body and 'data' in body else body

        now = datetime.now(timezone.utc)
        password = secrets.token_urlsafe(24)
        tokens = {}
        for role in ('ADMIN', 'CUSTOMER'):
            user = copy.deepcopy(dev_db.users.find_one({'role': 'CUSTOMER'}))
            user.update(_id=ObjectId(), email='phase06b-'+uuid4().hex+'@example.test', role=role,
                        status='ACTIVE', version=1, tokenVersion=0, passwordHash=hash_password(password))
            user_ids.append(user['_id'])
            db.users.insert_one(user)
            tokens[role] = http('POST', '/auth/login', payload={'email': user['email'], 'password': password})['accessToken']
        product = copy.deepcopy(dev_db.products.find_one({'productType': 'ELECTRONICS'}))
        product.update(_id=ObjectId(), sku='TEST-'+uuid4().hex.upper(), slug='test-'+uuid4().hex, version=1, stock=10)
        product_ids.append(product['_id'])
        db.products.insert_one(product)
        template = dev_db.orders.find_one({'orderStatus': 'PENDING', 'paymentMethod': 'COD'})
        orders = []
        for _ in range(2):
            order = copy.deepcopy(template)
            order.update(_id=ObjectId(), userId=user_ids[1], orderCode='TEST-'+uuid4().hex.upper(),
                         checkoutKey=uuid4().hex, version=1, createdAt=now-timedelta(hours=1), updatedAt=now-timedelta(hours=1))
            item = copy.deepcopy(order['items'][0])
            from bson.int64 import Int64
            item.update(productId=product['_id'], quantity=2, priceAtPurchase=Int64(100), lineTotal=Int64(200))
            order.update(items=[item], subtotal=Int64(200), shippingFee=Int64(30000), discount=Int64(0), total=Int64(30200))
            order_ids.append(order['_id'])
            db.orders.insert_one(order)
            orders.append(order)
        query = '?' + urlencode({'from': (now-timedelta(days=1)).isoformat(), 'to': (now+timedelta(days=1)).isoformat()})
        for method, path in sorted(actual):
            path = path.replace(':param', str(order_ids[0]))
            if '/dashboard/' in path:
                path += query
            for token, status in [(None, 401), (tokens['CUSTOMER'], 403)]:
                http(method, path, status, {'expectedVersion': 1} if method == 'POST' else None, token)
        http('GET', '/health', base=dev_listener.base)
        http('GET', '/admin/orders', token=tokens['ADMIN'])
        first = str(order_ids[0])
        http('GET', '/admin/orders/'+first, token=tokens['ADMIN'])
        empty = http('GET', '/admin/dashboard/summary'+query, token=tokens['ADMIN'])
        assert empty['totalRevenue'] == 0
        for count, action in enumerate(('confirm', 'ship', 'complete'), 1):
            completed = http('POST', f'/admin/orders/{first}/{action}', payload={'expectedVersion': count}, token=tokens['ADMIN'])
        assert completed['paymentStatus'] == 'PAID' and completed['completedAt'] == completed['paidAt']
        assert http('POST', f'/admin/orders/{first}/complete', payload={'expectedVersion': 1}, token=tokens['ADMIN']) == completed
        after = http('GET', '/admin/dashboard/summary'+query, token=tokens['ADMIN'])
        assert after['totalRevenue'] == 200 and after['totalProductsSold'] == 2 and after['totalOrders'] == 2
        for name in ('revenue', 'top-products', 'category-revenue', 'order-status'):
            http('GET', '/admin/dashboard/'+name+query, token=tokens['ADMIN'])
        http('GET', '/admin/dashboard/revenue'+query+'&interval=month', token=tokens['ADMIN'])
        second = str(order_ids[1])
        cancelled = http('POST', f'/admin/orders/{second}/cancel', payload={'expectedVersion': 1}, token=tokens['ADMIN'])
        assert http('POST', f'/admin/orders/{second}/cancel', payload={'expectedVersion': 1}, token=tokens['ADMIN']) == cancelled
        assert db.products.find_one({'_id': product['_id']})['stock'] == 12
        http('POST', f'/admin/orders/{first}/confirm', 409, {'expectedVersion': 4}, tokens['ADMIN'])

        # Read-only live seed reports: the PHASE03 deterministic oracle remains unchanged.
        seed_window = {'from': '2026-07-03T00:00:00Z', 'to': '2026-10-01T00:00:00Z'}
        seed_token = None
        # Token for the dev Admin is created only in-memory; dev accounts are never mutated.
        from app.auth.tokens import create_access_token
        with dev.app_context():
            seed_token = create_access_token(dev_db.users.find_one({'role': 'ADMIN', 'status': 'ACTIVE'}))
        for name in ('summary', 'revenue', 'top-products', 'category-revenue', 'order-status'):
            value = http('GET', '/admin/dashboard/'+name+'?'+urlencode(seed_window), token=seed_token, base=dev_listener.base)
            if name == 'summary':
                assert {key: value[key] for key in ('totalRevenue', 'totalProductsSold', 'totalOrders', 'totalCustomers')} == {
                    'totalRevenue': 10103259022, 'totalProductsSold': 434, 'totalOrders': 100, 'totalCustomers': 39}
                seed_summary = value

        explanations = {}
        window = ReportWindow(datetime(2026, 7, 3, tzinfo=timezone.utc), datetime(2026, 10, 1, tzinfo=timezone.utc))
        with dev.app_context():
            repository = DashboardRepository()
            for name in ('sales-summary', 'revenue-day', 'revenue-month', 'top-products', 'category-revenue', 'order-count', 'order-status', 'customer-count'):
                pipeline = repository.pipeline(name, window)
                collection = 'users' if name == 'customer-count' else 'orders'
                raw = dev_db.command('explain', {'aggregate': collection, 'pipeline': pipeline, 'cursor': {}}, verbosity='executionStats')
                explanations[name] = explain_summary(raw)
            pipeline = repository.pipeline('top-products', window)
            rows = []
            for label, hint in [('named-index', 'ix_orders_qualified_completed'), ('natural', {'$natural': 1})]:
                rows.append(list(dev_db.orders.aggregate(pipeline, hint=hint)))
                raw = dev_db.command('explain', {'aggregate': 'orders', 'pipeline': pipeline, 'cursor': {}, 'hint': hint}, verbosity='executionStats')
                explanations['top-products-'+label] = explain_summary(raw)
            assert rows[0] == rows[1]
            raw = dev_db.command('explain', {'find': 'orders', 'filter': {}, 'sort': {'createdAt': -1, '_id': -1}, 'limit': 20}, verbosity='executionStats')
            explanations['admin-orders-latest'] = explain_summary(raw)
        (ROOT / 'backend/evidence/phase06b-explain.json').write_text(
            json_util.dumps({'status': 'PASS', 'dataset': before['counts'], 'queries': explanations,
                             'indexedAndNaturalResultsEqual': True, 'newIndexesCreated': False}, indent=2), encoding='utf-8')
    finally:
        for listener in listeners:
            listener.close()
        if test:
            db = test.extensions['mongo'].database
            db.orders.delete_many({'_id': {'$in': order_ids}})
            db.products.delete_many({'_id': {'$in': product_ids}})
            db.users.delete_many({'_id': {'$in': user_ids}})
            test.extensions['mongo'].close()
        after = fingerprint(dev.extensions['mongo'].database)
        cleaned = all(dev.extensions['mongo'].client.ecommerce_test[n].count_documents({}) == 0 for n in NAMES)
        dev.extensions['mongo'].close()
    assert after == before and cleaned and source_manifest() == manifest
    persistent_checks = []
    for path, expected in [('/api/v1/health', 200), ('/api/v1/admin/orders', 401),
                           ('/api/v1/admin/dashboard/summary', 401)]:
        try:
            response = urlopen('http://127.0.0.1:5001'+path, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            body = json.loads(response.read())
            assert response.status == expected and body['meta']['requestId'] == response.headers['X-Request-ID']
            persistent_checks.append({'method': 'GET', 'path': path, 'status': expected})
    report = {'status': 'PHASE06B_PASS', 'pytest': suites, 'httpChecks': checks, 'seedSummary': seed_summary,
              'databaseFingerprintBefore': before['digest'], 'databaseFingerprintAfter': after['digest'], 'counts': after['counts'],
              'devDataValidatorsIndexesUnchanged': True, 'testDatabaseEmptyAfterCleanup': cleaned,
              'routes': routes, 'blueprints': list(test.blueprints), 'methodPathCount': len(routes), 'routeCollisions': [],
              'canonicalPipelinesExecuted': 8, 'sourceManifest': manifest, 'testedSourceManifest': tested_manifest,
              'backendSourceUnchangedSinceTests': True,
              'contractUpdatedSinceTests': manifest['docs/api-contract.md'] != tested_manifest['docs/api-contract.md'],
              'persistentServerSmoke': persistent_checks,
              'runtime': {name: version(name) for name in ('Flask', 'pymongo', 'pytest', 'PyJWT')},
              'frontendCreated': False, 'gatewayImplementedByThisWorker': False}
    (ROOT / 'backend/evidence/phase06b-runtime.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print({'status': report['status'], 'tests': suites['full']['tests'], 'httpChecks': len(checks), 'databaseUnchanged': True})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--capture', action='store_true')
    args = parser.parse_args()
    if args.capture:
        capture()
    else:
        verify()
