"""07D guarded rehearsal: dev/benchmark read-only, exact owned test clone and cleanup."""
import argparse
import copy
import hashlib
import json
import os
import secrets
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from bson import ObjectId, json_util
from dotenv import dotenv_values
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern
from werkzeug.serving import make_server

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'backend'), str(ROOT / 'scripts/backend')]
from app import create_app
from verify_auth_users import NAMES, fingerprint
from cleanup_phase06ab_database import snapshot, canonical_schema_check, orphan_check

RUN_TAG = os.environ.get('REHEARSAL_TAG', 'phase07d-images')
assert RUN_TAG.startswith('phase07d-') and all(c.isalnum() or c == '-' for c in RUN_TAG)
LOCAL = ROOT / '.local' / RUN_TAG
OUT = ROOT / 'database/evidence'
JOURNAL = LOCAL / 'journal.json'


def write(name, value):
    (OUT / name.replace('phase07d-fix', RUN_TAG)).write_text(json_util.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')


def hashes():
    paths = []
    for directory in ('backend/app', 'frontend/src', 'database/validators', 'database/aggregations', 'database/indexes', 'docs/evidence/performance'):
        paths.extend(p for p in (ROOT / directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    paths.extend((ROOT / 'database/evidence').glob('phase07c-*'))
    paths.extend([ROOT / 'docs/api-contract.md', ROOT / 'frontend/package.json', ROOT / 'frontend/vite.config.ts'])
    return {str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def http(method, path, payload=None, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    with urlopen(Request('http://127.0.0.1:5001/api/v1' + path, method=method, headers=headers,
                         data=json.dumps(payload).encode() if payload is not None else None), timeout=15) as response:
        assert response.status in (200, 201)
        return json.loads(response.read())['data']


def fixture_state(db):
    state = json.loads((ROOT / '.local/phase07c/fixture.json').read_text(encoding='utf-8'))
    assert state['project'] == str(ROOT) and state['database'] == db.name
    user = db.users.find_one({'_id': ObjectId(state['userId']), 'email': 'defense07c@example.test'})
    assert user and user['status'] == 'ACTIVE' and user['phone'] and user['addresses']
    products = []
    for spec in state['products']:
        p = db.products.find_one({'_id': ObjectId(spec['id']), 'sku': spec['sku']})
        assert p and p['status'] == 'ACTIVE' and p['price'] == spec['price'] and p['stock'] == 20
        assert isinstance(p['images'], list) and len(p['images']) <= 8
        assert db.categories.find_one({'_id': p['categoryId'], 'status': 'ACTIVE', 'productType': p['productType']})
        products.append({k: p[k] for k in ('_id', 'sku', 'slug', 'price', 'stock', 'images', 'attributes', 'version')})
    cart = db.carts.find_one({'userId': user['_id']})
    assert cart and cart['items'] == []
    return {'userId': str(user['_id']), 'products': products, 'cartEmpty': True, 'phoneAddressReady': True}


def plans(db, command):
    result, rows = {}, {}
    for name, hint in [('natural', {'$natural': 1}), ('indexed', 'ix_products_category_price'), ('planner', None)]:
        cmd = {**command, **({'hint': hint} if hint is not None else {})}
        raw = db.command('explain', cmd, verbosity='executionStats')
        cursor = db.products.find(command['filter'], command.get('projection')).sort(list(command['sort'].items())).limit(command['limit'])
        if hint is not None:
            cursor = cursor.hint(hint)
        rows[name] = [str(p['_id']) for p in cursor]
        result[name] = {'stats': raw['executionStats'], 'plan': raw['queryPlanner']['winningPlan']}
    assert rows['natural'] == rows['indexed'] == rows['planner']
    return {'database': db.name, 'command': command, 'plans': result, 'sameOrderedIds': rows['indexed'], 'equalResults': True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['prepare', 'serve', 'browser', 'charts', 'cleanup'])
    args = parser.parse_args()
    LOCAL.mkdir(parents=True, exist_ok=True)
    if args.mode in ('browser', 'charts'):
        env = dict(os.environ)
        env['E2E_SEED_PASSWORD'] = dotenv_values(ROOT / '.env', interpolate=False)['SEED_DEMO_PASSWORD']
        env['E2E_BASE_URL'] = 'http://127.0.0.1:5174'
        env['REHEARSAL_TAG'] = RUN_TAG
        script = 'phase07d-fix-rehearsal.mjs' if args.mode == 'browser' else 'phase07d-fix-chart-visual.mjs'
        result = subprocess.run(['node', 'tests/' + script], cwd=ROOT / 'frontend', env=env)
        raise SystemExit(result.returncode)
    if args.mode == 'serve':
        app = create_app(json.loads((LOCAL / 'settings.json').read_text(encoding='utf-8')))
        assert app.extensions['mongo'].database.name == 'ecommerce_test'
        with make_server('127.0.0.1', 5002, app, threaded=True) as server:
            print('07D isolated same-source test API ready', flush=True)
            server.serve_forever()
        return
    app = create_app()
    db = app.extensions['mongo'].database
    client, test = db.client, db.client.ecommerce_test
    try:
        hello = client.admin.command('hello')
        assert db.name == 'ecommerce_dev' and hello['setName'] == 'rs0' and hello['isWritablePrimary']
        assert client.address == ('localhost', 27017)
        marker = json.loads((ROOT / '.local/ecommerce_test.ownership.json').read_text(encoding='utf-8'))
        assert marker == {'project': str(ROOT), 'database': 'ecommerce_test', 'endpoint': 'localhost:27017/rs0'}
        if args.mode == 'prepare':
            assert not JOURNAL.exists(), '07D journal exists: inspect/reuse cleanup, never overwrite ownership'
            assert all(test[n].count_documents({}) == 0 for n in NAMES), 'Owned test DB must be empty; never reset'
            current = snapshot(db)
            schema = canonical_schema_check(current)
            canonical_schema_check(snapshot(test))
            fixture = fixture_state(db)
            baseline = {'project': str(ROOT), 'dev': fingerprint(db), 'benchmark': fingerprint(client.ecommerce_benchmark),
                'protectedHashes': hashes(), 'ownedIds': {n: [str(d['_id']) for d in current['documents'][n]] for n in NAMES},
                'owner': fixture['userId']}
            # Persist exact ownership before any insert; private journal contains no passwords.
            JOURNAL.write_text(json.dumps(baseline, indent=2), encoding='utf-8')
            seed_password = dotenv_values(ROOT / '.env', interpolate=False)['SEED_DEMO_PASSWORD']
            private = json.loads((ROOT / '.local/phase07c/fixture.json').read_text(encoding='utf-8'))
            admin = http('POST', '/auth/login', {'email': 'admin@example.test', 'password': seed_password})['accessToken']
            customer = http('POST', '/auth/login', {'email': 'defense07c@example.test', 'password': private['customerPassword']})['accessToken']
            live = {'health': http('GET', '/health'), 'products': http('GET', '/products?q=bao%20ve%2007c'),
                'cart': http('GET', '/cart', token=customer), 'orders': http('GET', '/orders', token=customer)}
            reports = {}
            window = {'from': '2026-10-01T00:00:00Z', 'to': '2026-11-01T00:00:00Z'}
            for endpoint in ('summary', 'revenue', 'top-products', 'category-revenue', 'order-status'):
                reports[endpoint] = http('GET', '/admin/dashboard/' + endpoint + '?' + urlencode(window), token=admin)
            pipelines, outputs = {}, {}
            for name in ('top-products', 'revenue-day', 'revenue-month', 'sales-summary'):
                pipeline = json_util.loads((ROOT / f'database/aggregations/{name}.json').read_text(encoding='utf-8'))
                pipeline[0]['$match']['completedAt'] = {'$gte': datetime(2026, 7, 3, tzinfo=timezone.utc), '$lt': datetime(2026, 10, 1, tzinfo=timezone.utc)}
                pipelines[name], outputs[name] = pipeline, list(db.orders.aggregate(pipeline, maxTimeMS=10000))
            assert outputs['sales-summary'][0]['totalRevenue'] == 10103259022 and outputs['sales-summary'][0]['totalProductsSold'] == 434
            dev_command = json_util.loads((ROOT / 'database/evidence/phase07c-query-verification.json').read_text(encoding='utf-8'))
            dev_plan = plans(db, {'find': 'products', 'filter': dev_command['indexQuery'], 'sort': dev_command['indexSort'], 'limit': 10})
            command = json_util.loads((ROOT / 'docs/evidence/performance/before-index.json').read_text(encoding='utf-8'))['queries']['products-category-price']['command']
            benchmark_plan = plans(client.ecommerce_benchmark, command)
            assert benchmark_plan['plans']['natural']['stats']['totalDocsExamined'] == 30000
            assert benchmark_plan['plans']['indexed']['stats']['totalDocsExamined'] == 20
            settings = {k: app.config[k] for k in ('MONGODB_URI', 'JWT_ISSUER', 'JWT_AUDIENCE')}
            settings.update(APP_ENV='testing', MONGODB_DB='ecommerce_dev', MONGODB_TEST_DB='ecommerce_test', JWT_SECRET=secrets.token_urlsafe(48),
                FRONTEND_ORIGIN='http://127.0.0.1:5174', VNPAY_ENABLED=False, LOG_LEVEL='ERROR')
            (LOCAL / 'settings.json').write_text(json.dumps(settings), encoding='utf-8')
            with client.start_session() as session:
                with session.start_transaction(read_concern=ReadConcern('snapshot'), write_concern=WriteConcern('majority')):
                    for n in NAMES:
                        if current['documents'][n]:
                            test[n].insert_many(copy.deepcopy(current['documents'][n]), session=session)
            assert fingerprint(db) == baseline['dev'] and fingerprint(client.ecommerce_benchmark) == baseline['benchmark']
            write('phase07d-fix-environment.json', {'phase': '07D-FIX', 'recordedAtUtc': datetime.now(timezone.utc),
                'version': client.server_info()['version'], 'replicaSet': hello['setName'], 'primary': hello['isWritablePrimary'],
                'devBaseline': baseline['dev'], 'benchmarkBaseline': baseline['benchmark'], 'fixture': fixture, 'schema': schema,
                'orphans': orphan_check(current), 'liveApi': live, 'dashboardWindow': window, 'liveDashboard': reports,
                'testCloneCounts': {n: test[n].count_documents({}) for n in NAMES}, 'mutationsTarget': 'ecommerce_test_only',
                'vnpayEnabled': app.config['VNPAY_ENABLED'], 'protectedHashes': baseline['protectedHashes']})
            write('phase07d-fix-queries.json', {'phase': '07D-FIX', 'recordedAtUtc': datetime.now(timezone.utc), 'mode': 'READ_ONLY',
                'pipelines': pipelines, 'outputs': outputs, 'devExplain': dev_plan, 'benchmarkExplainReplay': benchmark_plan,
                'newLatencyBenchmark': False, 'compassGuiEvidence': False})
            print(json.dumps({'phase': '07D-FIX', 'prepared': True, 'fixtureBaseline': True, 'devWrites': 0, 'queryEquality': True,
                'devCounts': baseline['dev']['counts'], 'schema': schema}))
        else:
            baseline = json.loads(JOURNAL.read_text(encoding='utf-8'))
            assert baseline['project'] == str(ROOT)
            test_snapshot = snapshot(test)
            write('phase07d-fix-test-outcomes.json', {'phase': '07D-FIX', 'recordedAtUtc': datetime.now(timezone.utc),
                'database': 'ecommerce_test', 'schema': canonical_schema_check(test_snapshot), 'orphans': orphan_check(test_snapshot),
                'ownedRehearsalOrders': [{k: d[k] for k in ('_id', 'orderCode', 'orderStatus', 'paymentStatus', 'subtotal', 'shippingFee', 'total', 'items')}
                    for d in test.orders.find({'userId': ObjectId(baseline['owner']), '_id': {'$nin': [ObjectId(i) for i in baseline['ownedIds']['orders']]}})],
                'fixtureStocksBeforeExactCleanup': [{k:p[k] for k in ('sku', 'price', 'stock', 'images')} for p in test.products.find({'sku': {'$in': ['DEFENSE-07C-ELE', 'DEFENSE-07C-FAS']}})]})
            allowed = {n: {ObjectId(i) for i in ids} for n, ids in baseline['ownedIds'].items()}
            for n in NAMES:
                for d in test[n].find({}):
                    assert d['_id'] in allowed[n] or (n in ('orders', 'carts', 'payment_attempts') and str(d['userId']) == baseline['owner']), 'Unknown test fixture; refuse cleanup'
                    allowed[n].add(d['_id'])
            with client.start_session() as session:
                with session.start_transaction(read_concern=ReadConcern('snapshot'), write_concern=WriteConcern('majority')):
                    removed = {n: test[n].delete_many({'_id': {'$in': sorted(allowed[n])}}, session=session).deleted_count for n in NAMES}
                    assert all(test[n].count_documents({}, session=session) == 0 for n in NAMES)
            current_hashes = hashes()
            changed = [p for p, h in baseline['protectedHashes'].items() if current_hashes.get(p) != h]
            after_dev, after_bench = fingerprint(db), fingerprint(client.ecommerce_benchmark)
            result = {'phase': '07D-FIX', 'recordedAtUtc': datetime.now(timezone.utc), 'devBefore': baseline['dev'], 'devAfter': after_dev,
                'benchmarkBefore': baseline['benchmark'], 'benchmarkAfter': after_bench,
                'devExactUnchanged': after_dev == baseline['dev'], 'benchmarkExactUnchanged': after_bench == baseline['benchmark'],
                'fixtureBaseline': fixture_state(db), 'schema': canonical_schema_check(snapshot(db)), 'orphans': orphan_check(snapshot(db)),
                'changedProtectedFiles': changed, 'cleanupExactCounts': removed, 'testEmpty': all(test[n].count_documents({}) == 0 for n in NAMES),
                'testSchema': canonical_schema_check(snapshot(test)), 'resetOrReseed': False}
            write('phase07d-fix-integrity.json', result)
            assert result['devExactUnchanged'] and result['benchmarkExactUnchanged'] and not changed
            print(json.dumps({k: result[k] for k in ('phase', 'devExactUnchanged', 'benchmarkExactUnchanged', 'changedProtectedFiles', 'testEmpty')}))
    finally:
        app.extensions['mongo'].close()


if __name__ == '__main__':
    main()
