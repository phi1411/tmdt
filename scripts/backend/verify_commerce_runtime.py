"""PHASE05C current-source HTTP flow on owned test rs0 and immutable dev fingerprint."""
import copy
import hashlib
import json
import platform
import re
import secrets
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from importlib.metadata import version
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4
from bson import ObjectId

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app import create_app
from app.auth.passwords import hash_password
from verify_auth_users import fingerprint, NAMES
from verify_integration_05ab import Listener, source_manifest


def main():
    before = json.loads((ROOT / '.local/phase05c-before.json').read_text())['database']
    suites = {}
    for label, filename in [('commerce', 'phase05c-commerce-pytest.xml'), ('full', 'phase05c-pytest.xml')]:
        suite = ET.parse(ROOT / 'backend/evidence' / filename).getroot().find('testsuite')
        assert suite is not None and all(suite.attrib[k] == '0' for k in ('failures', 'errors', 'skipped'))
        suites[label] = {**suite.attrib, 'pass': int(suite.attrib['tests'])}
    dev = create_app()
    test, listener, dev_listener = None, None, None
    checks, emails, cats, products, user_ids = [], [], [], [], []
    original_manifest = source_manifest()
    assert original_manifest == json.loads((ROOT / '.local/phase05c-source-before-tests.json').read_text()), 'Source changed since final pytest run'
    try:
        assert fingerprint(dev.extensions['mongo'].database) == before
        mongo_version = dev.extensions['mongo'].client.server_info()['version']
        replica_set = dev.extensions['mongo'].client.admin.command('hello')['setName']
        config = {k: dev.config[k] for k in ('MONGODB_URI', 'JWT_ISSUER', 'JWT_AUDIENCE')}
        config.update(APP_ENV='testing', MONGODB_DB='ecommerce_dev', MONGODB_TEST_DB='ecommerce_test',
                      JWT_SECRET=secrets.token_urlsafe(48), LOG_LEVEL='ERROR')
        test = create_app(config)
        db = test.extensions['mongo'].database
        marker = json.loads((ROOT / '.local/ecommerce_test.ownership.json').read_text())
        assert marker == {'project': str(ROOT), 'database': 'ecommerce_test', 'endpoint': 'localhost:27017/rs0'}
        assert db.name == 'ecommerce_test' and set(db.list_collection_names()) == set(NAMES)
        assert all(db[n].count_documents({}) == 0 for n in NAMES), 'Refusing mutation of existing test data'
        routes = [{'method': method, 'path': rule.rule} for rule in test.url_map.iter_rules()
                  for method in sorted(rule.methods - {'HEAD', 'OPTIONS'})]
        pairs = [(r['method'], re.sub(r'<[^>]+>', ':param', r['path'])) for r in routes]
        assert len(test.blueprints) == 10 and len(routes) == 38 and all(n == 1 for n in Counter(pairs).values())
        contract = (ROOT / 'docs/api-contract.md').read_text(encoding='utf-8')
        body = contract.split('## Commerce IMPLEMENTED — PHASE 05C\n', 1)[1].split('\n## ', 1)[0]
        documented = {(m, re.sub(r':\w+', ':param', p)) for m, p in re.findall(r'^\| (GET|POST|PATCH|DELETE) (/[^ |]+)', body, re.M)}
        actual = {(m, p.removeprefix('/api/v1')) for m, p in pairs if p.startswith(('/api/v1/cart', '/api/v1/checkout', '/api/v1/orders'))}
        assert len(documented) == 10 and documented == actual
        features = set()
        for name in ('cart', 'checkout', 'orders'):
            text = (ROOT / f'docs/features/{name}.md').read_text(encoding='utf-8')
            features.update((m, re.sub(r':\w+', ':param', p)) for m, p in re.findall(r'^\| (GET|POST|PATCH|DELETE) (/[^ |]+)', text, re.M))
        assert features == documented
        listener, dev_listener = Listener(test), Listener(dev)

        def http(label, method, path, status=200, payload=None, token=None, key=None, base=None, code=None):
            headers = {'Content-Type': 'application/json'}
            if token:
                headers['Authorization'] = 'Bearer ' + token
            if key:
                headers['Idempotency-Key'] = key
            data = json.dumps(payload).encode() if payload is not None else None
            try:
                response = urlopen(Request((base or listener.base) + path, data=data, headers=headers, method=method), timeout=10)
            except HTTPError as error:
                response = error
            with response:
                raw = response.read()
                parsed = json.loads(raw) if raw else None
                assert response.status == status, (label, response.status, status, parsed)
                if parsed:
                    assert response.headers['X-Request-ID'] == parsed['meta']['requestId']
                    assert not any(s in raw.decode() for s in ('passwordHash', 'tokenVersion', 'checkoutKey', 'checkoutRequestHash', '$oid', '$date'))
                    if code:
                        assert parsed['error']['code'] == code
                checks.append({'label': label, 'method': method, 'status': status, 'errorCode': code,
                               'path': re.sub(r'/[a-f0-9]{24}(?=/|$)', '/:id', path).split('?')[0]})
                return parsed['data'] if parsed and 'data' in parsed else parsed

        http('dev startup/health', 'GET', '/health', base=dev_listener.base)
        http('test rs0 readiness', 'GET', '/health')
        persistent_base = f"http://{dev.config['API_HOST']}:{dev.config['API_PORT']}/api/v1"
        http('persistent backend health', 'GET', '/health', base=persistent_base)
        http('persistent Cart registered/guest denied', 'GET', '/cart', 401, base=persistent_base, code='UNAUTHENTICATED')
        http('persistent Orders registered/guest denied', 'GET', '/orders', 401, base=persistent_base, code='UNAUTHENTICATED')
        http('persistent quote registered/guest denied', 'GET', '/checkout/quote', 401, base=persistent_base, code='UNAUTHENTICATED')
        assert len(http('persistent Catalog retained', 'GET', '/products?pageSize=1', base=persistent_base)) == 1
        http('guest cart denied', 'GET', '/cart', 401, code='UNAUTHENTICATED')
        http('guest order denied', 'POST', '/orders', 401, {}, code='UNAUTHENTICATED')
        password, email = secrets.token_urlsafe(24), 'commerce-http-' + uuid4().hex + '@example.test'
        emails.append(email)
        customer = http('register customer', 'POST', '/auth/register', 201,
                        {'email': email, 'password': password, 'name': 'Khách HTTP', 'phone': '0901234567'})
        user_ids.append(ObjectId(customer['user']['id']))
        token = http('login customer', 'POST', '/auth/login', payload={'email': email, 'password': password})['accessToken']
        customer = http('customer profile', 'GET', '/users/me', token=token)
        profile = http('save own address', 'POST', '/users/me/addresses', 201,
                       {'expectedVersion': customer['version'], 'receiverName': 'Khách HTTP', 'phone': '0901234567',
                        'addressLine': '123 Test', 'province': 'Hồ Chí Minh'}, token)
        address_id = profile['address']['id']
        admin = copy.deepcopy(db.users.find_one({'_id': user_ids[0]}))
        admin.update(_id=ObjectId(), email='commerce-admin-' + uuid4().hex + '@example.test', role='ADMIN',
                     passwordHash=hash_password(password), addresses=[], defaultAddressId=None)
        emails.append(admin['email'])
        user_ids.append(admin['_id'])
        db.users.insert_one(admin)
        admin_token = http('login fixture admin', 'POST', '/auth/login', payload={'email': admin['email'], 'password': password})['accessToken']
        http('admin cart denied', 'GET', '/cart', 403, token=admin_token, code='FORBIDDEN')
        category = http('admin create category', 'POST', '/admin/categories', 201,
                        {'name': 'HTTP Commerce', 'slug': 'http-cat-' + uuid4().hex, 'productType': 'ELECTRONICS'}, admin_token)
        cats.append(ObjectId(category['id']))
        product = http('admin create product', 'POST', '/admin/products', 201,
                       {'sku': 'HTTP_' + uuid4().hex.upper(), 'name': 'Sản phẩm HTTP', 'slug': 'http-prod-' + uuid4().hex,
                        'productType': 'ELECTRONICS', 'categoryId': category['id'], 'price': 10000000, 'stock': 3,
                        'brand': '', 'description': '', 'attributes': {'material': 'Original'},
                        'images': ['https://example.test/image.png'], 'status': 'ACTIVE'}, admin_token)
        products.append(ObjectId(product['id']))
        http('browse product', 'GET', '/products/' + product['slug'])
        assert http('empty cart', 'GET', '/cart', token=token)['version'] == 0
        cart = http('add product', 'POST', '/cart/items', payload={'productId': product['id'], 'quantity': 1, 'cartVersion': 0}, token=token)
        cart = http('merge product', 'POST', '/cart/items', payload={'productId': product['id'], 'quantity': 1, 'cartVersion': 1}, token=token)
        assert cart['items'][0]['quantity'] == 2
        cart = http('update quantity', 'PATCH', '/cart/items/' + cart['items'][0]['lineId'],
                    payload={'quantity': 1, 'cartVersion': 2}, token=token)
        qpath = '/checkout/quote?' + urlencode({'addressId': address_id, 'paymentMethod': 'COD'})
        quote = http('server signed quote', 'GET', qpath, token=token)
        assert quote['total'] == 10030000
        intent = {'cartVersion': cart['version'], 'addressId': address_id, 'paymentMethod': 'COD', 'quoteToken': quote['quoteToken']}
        key = uuid4().hex
        result = http('COD checkout commit', 'POST', '/orders', 201, intent, token, key)
        order = result['order']
        assert db.products.find_one({'_id': products[0]})['stock'] == 2
        assert http('cart cleared version retained', 'GET', '/cart', token=token)['version'] == 4
        assert http('idempotent checkout replay', 'POST', '/orders', 200, intent, token, key)['order']['id'] == order['id']
        http('different intent same key denied', 'POST', '/orders', 409, {**intent, 'cartVersion': 0}, token, key, code='IDEMPOTENCY_CONFLICT')
        assert len(http('my orders history', 'GET', '/orders', token=token)) == 1
        snapshot = http('my order detail', 'GET', '/orders/' + order['id'], token=token)
        http('live product price/name change', 'PATCH', '/admin/products/' + product['id'],
             payload={'price': 12000000, 'name': 'Tên mới', 'attributes': {'material': 'New'}, 'expectedVersion': 2}, token=admin_token)
        assert http('snapshot remains unchanged', 'GET', '/orders/' + order['id'], token=token) == snapshot
        cancelled = http('cancel own order', 'POST', '/orders/' + order['id'] + '/cancel', payload={'expectedVersion': 1}, token=token)
        assert cancelled['orderStatus'] == 'CANCELLED'
        http('cancel replay no double restore', 'POST', '/orders/' + order['id'] + '/cancel', payload={'expectedVersion': 1}, token=token)
        assert db.products.find_one({'_id': products[0]})['stock'] == 3
        http('VNPAY explicitly deferred', 'GET', '/checkout/quote?' + urlencode({'addressId': address_id, 'paymentMethod': 'VNPAY'}),
             503, token=token, code='PAYMENT_UNAVAILABLE')
        http('remove unknown cart item', 'DELETE', '/cart/items/' + cart['items'][0]['lineId'], 404,
             {'cartVersion': 4}, token, code='NOT_FOUND')
        cart = http('add again after checkout', 'POST', '/cart/items', payload={'productId': product['id'], 'quantity': 1, 'cartVersion': 4}, token=token)
        http('remove cart line', 'DELETE', '/cart/items/' + cart['items'][0]['lineId'], 204, {'cartVersion': 5}, token)
        http('clear retained cart', 'DELETE', '/cart', 204, {'cartVersion': 6}, token)
        assert db.orders.count_documents({'userId': user_ids[0]}) == 1
        assert db.payment_attempts.count_documents({'userId': {'$in': user_ids}}) == 0
    finally:
        if listener:
            listener.close()
        if dev_listener:
            dev_listener.close()
        if test:
            db = test.extensions['mongo'].database
            for name in ('payment_attempts', 'orders', 'carts'):
                db[name].delete_many({'userId': {'$in': user_ids}})
            db.products.delete_many({'_id': {'$in': products}})
            db.categories.delete_many({'_id': {'$in': cats}})
            db.users.delete_many({'email': {'$in': emails}})
            assert all(db[n].count_documents({}) == 0 for n in NAMES), 'Test cleanup incomplete'
            test.extensions['mongo'].close()
        after = fingerprint(dev.extensions['mongo'].database)
        dev.extensions['mongo'].close()
        assert after == before, 'Development database changed'
    assert original_manifest == source_manifest(), 'Source changed during HTTP verification'
    result = {'status': 'PASS', 'runtime': {'python': platform.python_version(), 'mongoDB': mongo_version, 'replicaSet': replica_set,
              **{p: version(p) for p in ('Flask', 'pymongo', 'pytest', 'PyJWT')}},
              'tests': suites, 'http': {'pass': len(checks), 'checks': checks},
              'routes': {'blueprints': 10, 'methodPaths': len(routes), 'collisions': 0, 'items': routes},
              'contract': {'commerceMethodPaths': 10, 'matchesRoutesAndFeatureDocs': True},
              'database': {'before': before, 'after': after, 'unchanged': True, 'testCleanup': 'empty'},
              'sourceManifest': original_manifest, 'vnpayGateway': 'DEFERRED', 'frontend': 'DEFERRED'}
    (ROOT / 'backend/evidence/phase05c-runtime.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'status': 'PASS', 'http': len(checks), 'devUnchanged': True, 'testCleanup': 'empty'}))


if __name__ == '__main__':
    main()
