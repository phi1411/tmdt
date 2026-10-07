"""Read-only HTTP/explain/fingerprint evidence for PHASE05B; no DB mutations."""
import hashlib
import json
import sys
import threading
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from bson import json_util
from werkzeug.serving import make_server

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app import create_app
from app.auth.tokens import create_access_token
from app.repositories.product_repository import ProductRepository


def http(base, method, path, token=None):
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    try:
        response = urlopen(Request(base + path, method=method, headers=headers), timeout=10)
    except HTTPError as error:
        response = error
    with response:
        body = json.loads(response.read())
        assert response.headers['X-Request-ID'] == body['meta']['requestId']
        return {'status': response.status, 'body': body}


def explain_summary(database, pipeline, hint=None):
    command = {'aggregate': 'products', 'pipeline': pipeline, 'cursor': {}}
    if hint:
        command['hint'] = hint
    result = database.command('explain', command, verbosity='executionStats')
    cursor = next((s['$cursor'] for s in result.get('stages', []) if '$cursor' in s), result)
    stats = cursor.get('executionStats', {})
    plan = cursor.get('queryPlanner', {}).get('winningPlan', {})
    return {'hint': hint, 'winningPlan': plan,
            **{key: stats.get(key) for key in ('nReturned', 'totalDocsExamined', 'totalKeysExamined', 'executionTimeMillis')},
            'lookupIndexes': [s.get('indexesUsed', []) for s in result.get('stages', []) if '$lookup' in s]}


if __name__ == '__main__':
    app = create_app()
    mongo = app.extensions['mongo']
    server = None
    try:
        db = mongo.database
        names = ('users', 'categories', 'products', 'carts', 'orders', 'payment_attempts')
        snapshot = {'counts': {n: db[n].count_documents({}) for n in names},
                    'documents': {n: list(db[n].find({}).sort('_id', 1)) for n in names},
                    'collections': list(db.list_collections()),
                    'indexes': {n: list(db[n].list_indexes()) for n in names}}
        digest = hashlib.sha256(json_util.dumps(snapshot, json_options=json_util.CANONICAL_JSON_OPTIONS, sort_keys=True).encode()).hexdigest()
        baseline = json_util.loads((ROOT / '.local/phase04-db-before.json').read_text(encoding='utf-8'))
        assert baseline['digest'] == digest, 'Dev documents/validators/indexes changed'
        suite = ET.parse(ROOT / 'backend/evidence/phase05b-pytest.xml').getroot().find('testsuite')
        assert suite is not None and suite.attrib['failures'] == suite.attrib['errors'] == suite.attrib['skipped'] == '0'
        assert mongo.client.ecommerce_test.categories.count_documents({}) == 0
        assert mongo.client.ecommerce_test.products.count_documents({}) == 0
        with app.app_context():
            admin = db.users.find_one({'role': 'ADMIN', 'status': 'ACTIVE'})
            customer = db.users.find_one({'role': 'CUSTOMER', 'status': 'ACTIVE'})
            admin_token, customer_token = create_access_token(admin), create_access_token(customer)
            repository = ProductRepository()
            active = next(db.products.aggregate(repository.pipeline({'status': 'ACTIVE'}, public=True) + [{'$limit': 1}]))
            public_total = next(db.products.aggregate(repository.pipeline({'status': 'ACTIVE'}, public=True) + [{'$count': 'total'}]))['total']
            explain = {}
            index_names = {item['name'] for item in db.products.list_indexes()}
            for label, field, index in [('categoryPrice', 'categoryId', 'ix_products_category_price'), ('typePrice', 'productType', 'ix_products_type_price')]:
                pipeline = repository.pipeline({'status': 'ACTIVE', field: active[field], 'price': {'$gte': 1}}, [('price', 1), ('_id', 1)], public=True)
                explain[label] = {'planner': explain_summary(db, pipeline),
                    'candidate': explain_summary(db, pipeline, index) if index in index_names else {'name': index, 'status': 'DECLARED_NOT_APPLIED'}}
        # A real localhost HTTP listener using current source, separate from any shared running process.
        server = make_server('127.0.0.1', 0, app)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}/api/v1'
        health = http(base, 'GET', '/health')
        categories = http(base, 'GET', '/categories')
        products = http(base, 'GET', '/products')
        detail = http(base, 'GET', '/products/' + active['slug'])
        admin_list = http(base, 'GET', '/admin/products', admin_token)
        admin_category = http(base, 'GET', '/admin/categories/' + str(active['categoryId']), admin_token)
        admin_detail = http(base, 'GET', '/admin/products/' + str(active['_id']), admin_token)
        guest = http(base, 'POST', '/admin/products')
        forbidden = http(base, 'DELETE', '/admin/products/' + str(active['_id']), customer_token)
        assert all(r['status'] == 200 for r in (health, categories, products, detail, admin_list, admin_category, admin_detail))
        assert products['body']['meta']['total'] == public_total
        assert len(products['body']['data']) <= 20 and admin_list['body']['meta']['total'] == snapshot['counts']['products']
        assert guest['status'] == 401 and forbidden['status'] == 403
        persistent_base = f"http://{app.config['API_HOST']}:{app.config['API_PORT']}/api/v1"
        try:
            live_list = http(persistent_base, 'GET', '/products?pageSize=1')
            live_query = http(persistent_base, 'GET', '/products/missing?status=ACTIVE')
            assert live_list['status'] == 200 and live_list['body']['meta']['total'] == public_total
            assert live_query['status'] == 422
            persistent = {'status': 'PASS', 'baseUrl': persistent_base, 'productList': 200, 'unknownDetailQuery': 422}
        except (URLError, TimeoutError):
            persistent = {'status': 'NOT_RUNNING', 'baseUrl': persistent_base}
        checks = {label: result['status'] for label, result in [('health', health), ('publicCategories', categories), ('publicProducts', products),
            ('publicDetail', detail), ('adminProducts', admin_list), ('adminCategoryDetail', admin_category), ('adminProductDetail', admin_detail),
            ('guestWrite', guest), ('customerWrite', forbidden)]}
        report = {'status': 'PHASE05B_CATALOG_PASS', 'http': checks, 'httpListener': 'temporary localhost WSGI server, current source',
            'persistentServerSmoke': persistent,
            'pytest': dict(suite.attrib), 'databaseCounts': snapshot['counts'], 'publicProductTotal': public_total,
            'databaseFingerprintBefore': baseline['digest'], 'databaseFingerprintAfter': digest,
            'devDocumentsValidatorsIndexesUnchanged': True, 'catalogTestFixturesCleaned': True,
            'explain': explain, 'fullBenchmarkPerformed': False,
            'catalogRoutes': [rule.rule for rule in app.url_map.iter_rules() if rule.endpoint.split('.')[0] in {'categories', 'products', 'admin_products'}]}
        (ROOT / 'backend/evidence/phase05b-runtime.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'status': report['status'], 'tests': suite.attrib['tests'], 'http': checks, 'devUnchanged': True}))
    finally:
        if server:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        mongo.close()
