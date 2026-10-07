"""Checkpoint only: current-source HTTP, routes/contracts, unchanged dev DB."""
import ast
import copy
import hashlib
import json
import re
import secrets
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from importlib.metadata import version
from pathlib import Path
from threading import Thread
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4
from bson import ObjectId
from werkzeug.serving import make_server

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app import create_app
from app.auth.passwords import hash_password
from verify_auth_users import fingerprint, NAMES


def source_manifest():
    paths = [p for base in ('backend/app', 'backend/tests') for p in (ROOT / base).rglob('*.py')]
    paths.append(ROOT / 'docs/api-contract.md')
    return {str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def route_audit(app):
    routes, pairs, endpoints = [], [], []
    for rule in app.url_map.iter_rules():
        assert rule.rule.startswith('/api/v1/'), rule.rule
        assert rule.endpoint.split('.')[0] in app.blueprints
        endpoints.append(rule.endpoint)
        for method in sorted(rule.methods - {'HEAD', 'OPTIONS'}):
            routes.append({'method': method, 'path': rule.rule, 'endpoint': rule.endpoint})
            pairs.append((method, re.sub(r'<[^>]+>', ':param', rule.rule)))
    assert not [pair for pair, count in Counter(pairs).items() if count > 1], 'Route collision'
    assert len(endpoints) == len(set(endpoints)), 'Duplicate endpoint registration'
    assert len(app.blueprints) == len({id(value) for value in app.blueprints.values()}) == 7
    assert len(routes) == 28
    assert not any('/cart' in r['path'] or '/orders' in r['path'] or '/checkout' in r['path'] for r in routes)
    return {'blueprints': list(app.blueprints), 'blueprintCount': 7, 'methodPathCount': len(routes),
            'ruleCount': len(endpoints), 'routeConflicts': [], 'endpointConflicts': [], 'routes': routes}


def contract_audit(routes):
    text = (ROOT / 'docs/api-contract.md').read_text(encoding='utf-8')
    sections = {}
    for heading, section in [('authUser', 'Auth/User/Admin User IMPLEMENTED'), ('catalog', 'Catalog IMPLEMENTED — PHASE 05B')]:
        body = text.split('## ' + section + '\n', 1)[1].split('\n## ', 1)[0]
        rows = re.findall(r'^\| (GET|POST|PATCH|DELETE) (/[^ |]+)', body, re.M)
        sections[heading] = {'methodPathCount': len(rows), 'sectionSha256': hashlib.sha256(body.encode()).hexdigest()}
        expected = 13 if heading == 'authUser' else 14
        assert len(rows) == expected, (heading, rows)
        actual = {(r['method'], re.sub(r'<[^>]+>', ':param', r['path'].removeprefix('/api/v1'))) for r in routes}
        documented = {(method, re.sub(r':\w+', ':param', path)) for method, path in rows}
        assert len(documented) == expected
        groups = ('/auth/', '/users/', '/admin/users') if heading == 'authUser' else ('/categories', '/products', '/admin/categories', '/admin/products')
        assert documented == {row for row in actual if row[1].startswith(groups)}
        feature_names = ('auth', 'users', 'admin-users') if heading == 'authUser' else ('categories', 'products', 'admin-products')
        feature_rows = set()
        for name in feature_names:
            feature = (ROOT / f'docs/features/{name}.md').read_text(encoding='utf-8')
            for method, path in re.findall(r'^\| (GET|POST|PATCH|DELETE) (/[^ |]+)', feature, re.M):
                feature_rows.add((method, re.sub(r':\w+', ':param', path)))
        assert documented == feature_rows, (heading, documented ^ feature_rows)
        sections[heading]['matchesFeatureDocsAndRegisteredRoutes'] = True
    assert '## API nghiệp vụ PLANNED' in text and 'Cart |' in text and 'Checkout |' in text and 'Orders |' in text
    return {'status': 'PASS', 'sections': sections, 'implementedBusinessMethodPaths': 27,
            'commerceStillPlanned': True, 'contractFileUnchanged': True}


def shared_audit():
    names = {'register_error_handlers', 'decode_access_token', 'create_access_token', 'get_current_user',
             'require_auth', 'require_roles', 'validate_payload', 'parse_json_body', 'single_query_values',
             'parse_object_id', 'to_api', 'Pagination', 'load_config', 'init_mongo', 'get_db', 'MongoConnection'}
    definitions = defaultdict(list)
    for file in (ROOT / 'backend/app').rglob('*.py'):
        tree = ast.parse(file.read_text(encoding='utf-8'))
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names:
                definitions[node.name].append(str(file.relative_to(ROOT)).replace('\\', '/'))
    assert set(definitions) == names
    assert all(len(paths) == 1 for paths in definitions.values()), 'Competing foundation definitions'
    return {'status': 'PASS', 'competingImplementations': [], 'canonicalDefinitions': dict(definitions)}


class Listener:
    def __init__(self, app):
        self.server = make_server('127.0.0.1', 0, app, threaded=True)
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}/api/v1'

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


def main():
    baseline = json.loads((ROOT / '.local/phase05ab-before.json').read_text(encoding='utf-8'))
    assert source_manifest() == baseline['source'], 'Source changed since checkpoint baseline'
    suite = ET.parse(ROOT / 'backend/evidence/phase05ab-pytest.xml').getroot().find('testsuite')
    assert suite is not None and all(suite.attrib[k] == '0' for k in ('failures', 'errors', 'skipped'))
    dev = create_app()
    listeners, test, emails, category_ids, product_ids, checks = [], None, [], [], [], []
    try:
        mongo = dev.extensions['mongo']
        assert fingerprint(mongo.database) == baseline['database']
        routes = route_audit(dev)
        contract = contract_audit(routes['routes'])
        shared = shared_audit()

        def http(base, label, method, path, status, payload=None, token=None, error_code=None):
            headers = {'Content-Type': 'application/json'}
            if token:
                headers['Authorization'] = f'Bearer {token}'
            data = json.dumps(payload).encode() if payload is not None else None
            try:
                response = urlopen(Request(base + path, data=data, headers=headers, method=method), timeout=10)
            except HTTPError as error:
                response = error
            with response:
                raw = response.read()
                assert response.status == status, (label, response.status, status)
                body = json.loads(raw) if raw else None
                if body:
                    assert response.headers['X-Request-ID'] == body['meta']['requestId']
                    assert all(key not in raw.decode() for key in ('passwordHash', 'tokenVersion', '$oid', '$date'))
                    assert ('error' in body) if status >= 400 else ('data' in body)
                    if error_code:
                        assert body['error']['code'] == error_code
                checks.append({'label': label, 'method': method, 'path': re.sub(r'/[a-f0-9]{24}(?=/|$)', '/:id', path),
                               'status': status, 'errorCode': error_code,
                               'listener': 'dev' if base == dev_listener.base else ('persistent' if base == persistent_base else 'test')})
                return body['data'] if body and 'data' in body else body

        persistent_base = f"http://{dev.config['API_HOST']}:{dev.config['API_PORT']}/api/v1"
        dev_listener = Listener(dev)
        listeners.append(dev_listener)
        health = http(dev_listener.base, 'dev startup/health', 'GET', '/health', 200)
        assert health['checks'] == {'backend': 'ok', 'database': 'ok', 'replicaSet': 'ok'}
        http(dev_listener.base, 'dev Auth route exists', 'GET', '/auth/me', 401, error_code='UNAUTHENTICATED')
        products = http(dev_listener.base, 'dev Catalog route exists', 'GET', '/products?pageSize=1', 200)
        assert len(products) == 1
        http(persistent_base, 'persistent health', 'GET', '/health', 200)
        http(persistent_base, 'persistent Auth route', 'GET', '/auth/me', 401, error_code='UNAUTHENTICATED')
        http(persistent_base, 'persistent Catalog route', 'GET', '/products?pageSize=1', 200)

        config = {k: dev.config[k] for k in ('MONGODB_URI', 'JWT_ISSUER', 'JWT_AUDIENCE')}
        config.update(APP_ENV='testing', MONGODB_DB='ecommerce_dev', MONGODB_TEST_DB='ecommerce_test',
                      JWT_SECRET=secrets.token_urlsafe(48), LOG_LEVEL='ERROR')
        test = create_app(config)
        db = test.extensions['mongo'].database
        marker = json.loads((ROOT / '.local/ecommerce_test.ownership.json').read_text(encoding='utf-8'))
        assert marker == {'project': str(ROOT), 'database': 'ecommerce_test', 'endpoint': 'localhost:27017/rs0'}
        assert db.name == 'ecommerce_test' and set(db.list_collection_names()) == set(NAMES)
        assert all(db[n].count_documents({}) == 0 for n in NAMES), 'Existing test data: refusing mutation'
        assert test.extensions['mongo'].health()['replicaSet'] == 'ok'
        listener = Listener(test)
        listeners.append(listener)
        base = listener.base
        password = secrets.token_urlsafe(24)
        email = f'checkpoint05ab-{uuid4().hex}@example.test'
        emails.append(email)
        user = http(base, 'register Customer', 'POST', '/auth/register', 201,
                    {'name': 'Checkpoint Customer', 'email': email, 'password': password})['user']
        customer_token = http(base, 'login Customer', 'POST', '/auth/login', 200,
                              {'email': email, 'password': password})['accessToken']
        assert http(base, 'Customer auth me', 'GET', '/auth/me', 200, token=customer_token)['role'] == 'CUSTOMER'
        http(base, 'Customer profile permitted', 'GET', '/users/me', 200, token=customer_token)
        http(base, 'Customer Admin User denied', 'GET', '/admin/users', 403, token=customer_token, error_code='FORBIDDEN')
        http(base, 'Customer Admin Catalog denied', 'GET', '/admin/products', 403, token=customer_token, error_code='FORBIDDEN')
        http(base, 'Guest Admin Catalog denied', 'GET', '/admin/products', 401, error_code='UNAUTHENTICATED')
        admin = copy.deepcopy(mongo.database.users.find_one({'role': 'ADMIN', 'status': 'ACTIVE'}))
        assert admin
        admin.update(_id=ObjectId(), email=f'checkpoint05ab-{uuid4().hex}@example.test', passwordHash=hash_password(password))
        emails.append(admin['email'])
        db.users.insert_one(admin)
        admin_token = http(base, 'login Admin', 'POST', '/auth/login', 200,
                           {'email': admin['email'], 'password': password})['accessToken']
        assert http(base, 'Admin auth me', 'GET', '/auth/me', 200, token=admin_token)['role'] == 'ADMIN'
        http(base, 'Admin User permitted', 'GET', '/admin/users?pageSize=1', 200, token=admin_token)
        http(base, 'Admin Customer profile denied', 'GET', '/users/me', 403, token=admin_token, error_code='FORBIDDEN')
        slug = 'checkpoint-' + uuid4().hex
        category = http(base, 'Admin create Category', 'POST', '/admin/categories', 201,
                        {'name': 'Checkpoint điện tử', 'slug': slug, 'productType': 'ELECTRONICS'}, admin_token)
        category_ids.append(ObjectId(category['id']))
        assert re.fullmatch(r'[a-f0-9]{24}', category['id']) and category['createdAt'].endswith('Z')
        http(base, 'categories list', 'GET', '/categories', 200)
        http(base, 'category detail', 'GET', '/categories/' + slug, 200)
        payload = {'sku': 'CHECKPOINT_' + uuid4().hex.upper(), 'name': 'Điện thoại Checkpoint 05AB',
                   'slug': slug + '-product', 'categoryId': category['id'], 'productType': 'ELECTRONICS',
                   'brand': 'Checkpoint', 'description': 'Integration fixture', 'price': 12000000, 'stock': 5,
                   'images': [], 'attributes': {'ram': '8GB', 'storage': '256GB'}, 'status': 'ACTIVE'}
        product = http(base, 'Admin create Product with login JWT', 'POST', '/admin/products', 201, payload, admin_token)
        product_ids.append(ObjectId(product['id']))
        public = http(base, 'product detail', 'GET', '/products/' + payload['slug'], 200)
        assert public['price'] == 12000000 and type(public['price']) is int and 'status' not in public
        assert public['attributes'] == payload['attributes'] and public['category']['id'] == category['id']
        http(base, 'products list', 'GET', '/products?pageSize=1', 200)
        query = urlencode({'q': 'dien thoai checkpoint', 'categoryId': category['id'], 'productType': 'ELECTRONICS',
                           'brand': 'CHECKPOINT', 'minPrice': 10000000, 'maxPrice': 13000000,
                           'ram': '8GB', 'sort': 'price_asc', 'page': 1, 'pageSize': 1})
        filtered = http(base, 'Vietnamese search/filter/sort/pagination', 'GET', '/products?' + query, 200)
        assert len(filtered) == 1 and filtered[0]['id'] == product['id']
        http(base, 'Admin Catalog permitted', 'GET', '/admin/products?pageSize=1', 200, token=admin_token)
        http(base, 'Auth strict validation', 'POST', '/auth/register', 422,
             {'name': 'Bad role', 'email': email, 'password': password, 'role': 'ADMIN'}, error_code='VALIDATION_ERROR')
        http(base, 'Catalog strict validation', 'PATCH', '/admin/products/' + product['id'], 422,
             {'price': True, 'expectedVersion': product['version']}, admin_token, 'VALIDATION_ERROR')
        http(base, 'Catalog ObjectId error', 'GET', '/admin/products/bad-id', 400, token=admin_token, error_code='BAD_REQUEST')
        http(base, 'Auth pagination maximum', 'GET', '/admin/users?pageSize=101', 422, token=admin_token, error_code='VALIDATION_ERROR')
        http(base, 'Catalog pagination maximum', 'GET', '/products?pageSize=101', 422, error_code='VALIDATION_ERROR')
        updated = http(base, 'Admin Product patch', 'PATCH', '/admin/products/' + product['id'], 200,
                       {'price': 12500000, 'expectedVersion': product['version']}, admin_token)
        assert updated['stock'] == product['stock'] and updated['version'] == product['version'] + 1
        http(base, 'Catalog stale version conflict', 'PATCH', '/admin/products/' + product['id'], 409,
             {'price': 13000000, 'expectedVersion': product['version']}, admin_token, 'PRODUCT_CHANGED')
        http(base, 'Admin block Customer', 'PATCH', '/admin/users/' + user['id'] + '/status', 200,
             {'status': 'BLOCKED', 'expectedVersion': user['version']}, admin_token)
        http(base, 'Auth live revocation', 'GET', '/auth/me', 401, token=customer_token, error_code='UNAUTHENTICATED')
        http(base, 'Catalog same live revocation guard', 'GET', '/admin/products', 401, token=customer_token, error_code='UNAUTHENTICATED')
    finally:
        for listener in reversed(listeners):
            listener.close()
        if test:
            db = test.extensions['mongo'].database
            if product_ids:
                db.products.delete_many({'_id': {'$in': product_ids}})
            if category_ids:
                db.categories.delete_many({'_id': {'$in': category_ids}})
            if emails:
                db.users.delete_many({'email': {'$in': emails}})
            test.extensions['mongo'].close()
        dev.extensions['mongo'].close()
    verification = create_app()
    try:
        after = fingerprint(verification.extensions['mongo'].database)
        assert after == baseline['database']
        assert source_manifest() == baseline['source']
        assert all(verification.extensions['mongo'].client.ecommerce_test[n].count_documents({}) == 0 for n in NAMES)
        total = int(suite.attrib['tests'])
        breakdown = Counter(case.attrib['classname'] for case in suite.findall('testcase'))
        report = {'status': 'PHASE 05AB INTEGRATION PASS', 'readyForCommerceBackend': True,
                  'gitHead': None, 'sourceManifest': source_manifest(), 'sourceUnchangedDuringCheckpoint': True,
                  'tests': {'total': total, 'passed': total, 'failed': 0, 'errors': 0, 'skipped': 0,
                            'seconds': float(suite.attrib['time']), 'modules': dict(breakdown)},
                  'runtime': {'python': sys.version.split()[0],
                              **{name: version(name) for name in ('Flask', 'pymongo', 'pytest', 'PyJWT', 'argon2-cffi')},
                              'mongodb': verification.extensions['mongo'].client.admin.command('buildInfo')['version'],
                              'replicaSet': verification.extensions['mongo'].client.admin.command('hello')['setName']},
                  'httpSmoke': checks, 'httpCheckCount': len(checks), 'routes': routes,
                  'apiContract': contract, 'sharedFoundation': shared, 'databaseBefore': baseline['database'],
                  'databaseAfter': after, 'historicalBaselineMatched': baseline['historicalBaselineMatched'],
                  'testDatabaseEmptyAfterCleanup': True, 'implementationFixes': [], 'commerceBlockers': [],
                  'newFeaturesImplemented': False, 'frontendWorkPerformed': False}
        destination = ROOT / 'backend/evidence/phase05ab-integration.json'
        destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'status': report['status'], 'tests': report['tests'], 'httpChecks': len(checks),
                          'routes': routes['methodPathCount'], 'devDatabaseUnchanged': True}))
    finally:
        verification.extensions['mongo'].close()


if __name__ == '__main__':
    main()
