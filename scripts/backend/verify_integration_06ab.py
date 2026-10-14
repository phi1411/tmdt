"""06AB checkpoint: current-source HTTP integration, contracts and DB integrity."""
import copy
import hashlib
import hmac
import json
import re
import secrets
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timedelta, timezone
from importlib.metadata import version
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen
from uuid import uuid4
from bson import ObjectId
from bson.int64 import Int64

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app import create_app
from app.auth.passwords import hash_password
from app.auth.tokens import create_access_token
from app.services.vnpay_provider import provider_time
from verify_auth_users import fingerprint, NAMES
from verify_integration_05ab import Listener, source_manifest, shared_audit

FIXTURE_SECRET = 'checkpoint-only-not-live-vnpay-secret'


def route_contract_audit(app):
    routes = [{'method': method, 'path': rule.rule, 'endpoint': rule.endpoint}
              for rule in app.url_map.iter_rules() for method in sorted(rule.methods - {'HEAD', 'OPTIONS'})]
    pairs = [(r['method'], re.sub(r'<[^>]+>', ':param', r['path'])) for r in routes]
    assert len(routes) == 52 and len(app.blueprints) == 13
    assert len({id(b) for b in app.blueprints.values()}) == 13
    assert all(n == 1 for n in Counter(pairs).values()) and all(p.startswith('/api/v1/') for _, p in pairs)
    endpoints = [rule.endpoint for rule in app.url_map.iter_rules()]
    assert len(endpoints) == len(set(endpoints))
    # Concrete matching detects static/dynamic shadows as well as duplicate patterns.
    adapter = app.url_map.bind('localhost')
    for r in routes:
        concrete = re.sub(r'<([^>]+)>', lambda m: 'audit-slug' if 'slug' in m[1] else '0' * 24, r['path'])
        endpoint, _ = adapter.match(concrete, method=r['method'])
        assert endpoint == r['endpoint'], (r, endpoint)
    text = (ROOT / 'docs/api-contract.md').read_text(encoding='utf-8')
    groups = [
        ('Auth/User/Admin User IMPLEMENTED', 13, ('auth', 'users', 'admin-users')),
        ('Catalog IMPLEMENTED — PHASE 05B', 14, ('categories', 'products', 'admin-products')),
        ('Commerce IMPLEMENTED — PHASE 05C', 10, ('cart', 'checkout', 'orders')),
        ('Payment IMPLEMENTED — PHASE 06A', 3, ('payment',)),
        ('Admin Orders và Dashboard IMPLEMENTED — PHASE 06B', 11, ('admin-orders', 'admin-dashboard')),
    ]
    documented, sections = {('GET', '/api/v1/health')}, {}
    for heading, count, features in groups:
        body = text.split('## ' + heading + '\n', 1)[1].split('\n## ', 1)[0]
        rows = {(m, re.sub(r':\w+', ':param', p)) for m, p in re.findall(r'^\| (GET|POST|PATCH|DELETE) (/[^ |]+)', body, re.M)}
        assert len(rows) == count, heading
        feature_rows = set()
        for name in features:
            feature = (ROOT / f'docs/features/{name}.md').read_text(encoding='utf-8')
            feature_rows.update((m, re.sub(r':\w+', ':param', p)) for m, p in re.findall(r'^\| (GET|POST|PATCH|DELETE) (/[^ |]+)', feature, re.M))
        if heading.startswith('Payment'):
            feature_rows.discard(('GET', '/orders/:param'))  # Existing owner poll, not a fourth Payment route.
        assert rows == feature_rows, (heading, rows ^ feature_rows)
        documented.update((m, '/api/v1' + p) for m, p in rows)
        sections[heading] = {'methodPaths': count, 'sha256': hashlib.sha256(body.encode()).hexdigest()}
    assert documented == set(pairs)
    assert '**VNPAY IMPLEMENTED — PHASE06A:**' in text and 'disabled trả503 PAYMENT_UNAVAILABLE trước hold/write' in text
    return {'blueprints': list(app.blueprints), 'blueprintCount': 13, 'methodPathCount': 52,
            'routes': routes, 'collisions': [], 'shadows': [], 'contractSections': sections, 'contractMatchesRoutesAndFeatures': True}


def main():
    baseline = json.loads((ROOT / '.local/phase06ab-before.json').read_text())
    runtime_baseline = json.loads((ROOT / '.local/phase06ab-runtime-before.json').read_text())
    delta = json.loads((ROOT / '.local/phase06ab-dev-delta.json').read_text())
    schema_audit = json.loads((ROOT / '.local/phase06ab-schema-index-audit.json').read_text())
    assert schema_audit['canonicalMatch']
    assert delta['additionalUserApprovedByUser'] and delta['disposition'] == 'KEEP'
    assert source_manifest() == baseline['source'], 'Backend/contract source changed since checkpoint baseline'
    suite = ET.parse(ROOT / 'backend/evidence/phase06ab-pytest.xml').getroot().find('testsuite')
    assert suite is not None and all(suite.attrib[k] == '0' for k in ('failures', 'errors', 'skipped'))
    dev = create_app()
    listeners, test, users, categories, products, checks = [], None, [], [], [], []
    revenue_checks = {}
    try:
        mongo = dev.extensions['mongo']
        assert fingerprint(mongo.database) == runtime_baseline['database']
        audit = route_contract_audit(dev)
        foundation = shared_audit()
        live_keys = ('VNP_TMN_CODE', 'VNP_HASH_SECRET', 'VNP_PAYMENT_URL', 'VNP_RETURN_URL', 'VNP_IPN_URL')
        live = {'status': 'LIVE SANDBOX BLOCKED', 'enabled': dev.config['VNPAY_ENABLED'],
                'missingEffectiveConfig': [k for k in live_keys if not dev.config.get(k)],
                'realRedirectVerified': False, 'realProviderIpnVerified': False}
        assert not dev.config['VNPAY_ENABLED'] and live['missingEffectiveConfig']
        dev_listener = Listener(dev)
        listeners.append(dev_listener)
        persistent_base = f"http://{dev.config['API_HOST']}:{dev.config['API_PORT']}/api/v1"

        def http(label, method, path, status=200, payload=None, token=None, key=None, provider_code=None, base=None):
            url_base = base or listener.base
            headers = {'Content-Type': 'application/json'}
            if token:
                headers['Authorization'] = 'Bearer ' + token
            if key:
                headers['Idempotency-Key'] = key
            raw = json.dumps(payload).encode() if payload is not None else None
            try:
                response = urlopen(Request(url_base + path, data=raw, headers=headers, method=method), timeout=15)
            except HTTPError as error:
                response = error
            with response:
                content = response.read()
                body = json.loads(content) if content else None
                assert response.status == status, (label, response.status, status)
                if body:
                    assert all(k not in content.decode() for k in ('passwordHash', 'tokenVersion', 'checkoutKey', 'checkoutRequestHash', FIXTURE_SECRET))
                    if provider_code:
                        assert body['RspCode'] == provider_code and 'data' not in body
                    else:
                        assert response.headers['X-Request-ID'] == body['meta']['requestId']
                checks.append({'label': label, 'method': method, 'path': re.sub(r'/[a-f0-9]{24}(?=/|$)', '/:id', path.split('?', 1)[0]),
                               'status': status, 'providerCode': provider_code,
                               'environment': 'development-read-only' if url_base in {dev_listener.base, persistent_base} else 'owned-test'})
                return body.get('data', body) if body else None

        assert http('development startup health', 'GET', '/health', base=dev_listener.base)['checks']['replicaSet'] == 'ok'
        http('persistent health', 'GET', '/health', base=persistent_base)
        http('persistent Catalog', 'GET', '/products?pageSize=1', base=persistent_base)
        http('persistent Admin routes', 'GET', '/admin/orders', 401, base=persistent_base)
        http('missing live config Return', 'GET', '/payments/vnpay/return', 503, base=dev_listener.base)
        http('missing live config IPN', 'GET', '/payments/vnpay/ipn', provider_code='99', base=dev_listener.base)
        config = {k: dev.config[k] for k in ('MONGODB_URI', 'JWT_ISSUER', 'JWT_AUDIENCE')}
        config.update(APP_ENV='testing', MONGODB_TEST_DB='ecommerce_test', JWT_SECRET=secrets.token_urlsafe(48),
                      LOG_LEVEL='ERROR', VNPAY_ENABLED=True, VNP_TMN_CODE='TEST0001', VNP_HASH_SECRET=FIXTURE_SECRET,
                      VNP_PAYMENT_URL='https://sandbox.vnpayment.vn/paymentv2/vpcpay.html',
                      VNP_RETURN_URL='http://127.0.0.1:5001/api/v1/payments/vnpay/return',
                      VNP_IPN_URL='http://127.0.0.1:5001/api/v1/payments/vnpay/ipn')
        test = create_app(config)
        db = test.extensions['mongo'].database
        marker = json.loads((ROOT / '.local/ecommerce_test.ownership.json').read_text())
        assert marker == {'project': str(ROOT), 'database': 'ecommerce_test', 'endpoint': 'localhost:27017/rs0'}
        assert db.name == 'ecommerce_test' and set(db.list_collection_names()) == set(NAMES)
        assert all(db[n].count_documents({}) == 0 for n in NAMES), 'Refusing mutations in nonempty test DB'
        listener = Listener(test)
        listeners.append(listener)
        template = mongo.database.users.find_one({'role': 'CUSTOMER', 'status': 'ACTIVE'})
        password = secrets.token_urlsafe(24)
        tokens, identities = {}, {}
        for label, role in [('customer', 'CUSTOMER'), ('other', 'CUSTOMER'), ('admin', 'ADMIN')]:
            user = copy.deepcopy(template)
            user.update(_id=ObjectId(), email='checkpoint06ab-' + uuid4().hex + '@example.test', role=role,
                        passwordHash=hash_password(password), tokenVersion=0, version=1, phone='0901234567')
            user['addresses'] = [{'_id': ObjectId(), 'receiverName': 'Checkpoint', 'phone': '0901234567',
                                  'addressLine': '123 Test', 'province': 'Hồ Chí Minh'}]
            user['defaultAddressId'] = user['addresses'][0]['_id']
            users.append(user['_id'])
            db.users.insert_one(user)
            identities[label] = user
            tokens[label] = http(label + ' login', 'POST', '/auth/login', payload={'email': user['email'], 'password': password})['accessToken']
        token, admin_token = tokens['customer'], tokens['admin']
        category = copy.deepcopy(mongo.database.categories.find_one({'status': 'ACTIVE', 'productType': 'ELECTRONICS'}))
        category.update(_id=ObjectId(), slug='checkpoint-' + uuid4().hex, version=1)
        categories.append(category['_id'])
        db.categories.insert_one(category)
        product = copy.deepcopy(mongo.database.products.find_one({'status': 'ACTIVE', 'productType': 'ELECTRONICS'}))
        product.update(_id=ObjectId(), sku='CHECKPOINT_' + uuid4().hex.upper(), slug='checkpoint-' + uuid4().hex,
                       categoryId=category['_id'], stock=100, price=Int64(120000), version=1)
        products.append(product['_id'])
        db.products.insert_one(product)
        http('Product detail', 'GET', '/products/' + product['slug'])
        now = datetime.now(timezone.utc)
        window = urlencode({'from': (now - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ'),
                            'to': (now + timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')})
        report_path = '/admin/dashboard/summary?' + window

        def summary(label):
            return http(label, 'GET', report_path, token=admin_token)

        def stock():
            return db.products.find_one({'_id': product['_id']})['stock']

        def checkout(method, quantity=1):
            cart = http('Cart read', 'GET', '/cart', token=token)
            cart = http('Cart add', 'POST', '/cart/items', payload={'productId': str(product['_id']), 'quantity': quantity,
                        'cartVersion': cart['version'], 'selectedAttributes': {}}, token=token)
            quote = http(method + ' quote', 'GET', '/checkout/quote?' + urlencode({
                'addressId': str(identities['customer']['defaultAddressId']), 'paymentMethod': method}), token=token)
            payload = {'cartVersion': cart['version'], 'addressId': str(identities['customer']['defaultAddressId']),
                       'paymentMethod': method, 'quoteToken': quote['quoteToken']}
            key = uuid4().hex
            result = http(method + ' checkout', 'POST', '/orders', 201, payload, token, key)
            before_replay = stock()
            replay = http(method + ' idempotency replay', 'POST', '/orders', 200, payload, token, key)
            assert replay['order']['id'] == result['order']['id'] and stock() == before_replay
            order = db.orders.find_one({'_id': ObjectId(result['order']['id'])})
            attempt = db.payment_attempts.find_one({'orderId': order['_id']})
            if method == 'VNPAY':
                parsed = urlsplit(result['payment']['paymentUrl'])
                assert parsed.hostname == 'sandbox.vnpayment.vn'
                params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
                signature = params.pop('vnp_SecureHash')
                expected = hmac.new(FIXTURE_SECRET.encode(), urlencode(sorted(params.items())).encode(), hashlib.sha512).hexdigest()
                assert hmac.compare_digest(signature, expected) and int(params['vnp_Amount']) == order['total'] * 100
                assert attempt['amount'] == order['total'] and db.payment_attempts.count_documents({'orderId': order['_id']}) == 1
            else:
                assert attempt is None and result['payment'] == {'method': 'COD'}
            return order, attempt

        def callback(attempt, failed=False):
            params = {'vnp_TmnCode': 'TEST0001', 'vnp_Amount': str(int(attempt['amount']) * 100),
                      'vnp_TxnRef': attempt['txnRef'], 'vnp_OrderInfo': attempt['paymentRequest']['orderInfo'],
                      'vnp_ResponseCode': '24' if failed else '00', 'vnp_TransactionStatus': '02' if failed else '00',
                      'vnp_BankCode': 'NCB', 'vnp_TransactionNo': str(uuid4().int % 99999999999999 + 1),
                      'vnp_PayDate': provider_time(datetime.now(timezone.utc))}
            params['vnp_SecureHash'] = hmac.new(FIXTURE_SECRET.encode(), urlencode(sorted(params.items())).encode(), hashlib.sha512).hexdigest()
            return params

        def ipn(label, query, code='00'):
            return http(label, 'GET', '/payments/vnpay/ipn?' + urlencode(query), provider_code=code)

        def admin_action(order_id, action, expected_version, status=200):
            return http('Admin ' + action, 'POST', f'/admin/orders/{order_id}/{action}', status,
                        {'expectedVersion': expected_version}, admin_token)

        assert summary('Empty revenue')['totalRevenue'] == 0
        online, attempt = checkout('VNPAY', 2)
        oid = str(online['_id'])
        assert stock() == 98
        admin_action(oid, 'confirm', 1, 409)
        admin_action(oid, 'ship', 1, 409)
        signed = callback(attempt)
        before_return = fingerprint(db)
        returned = http('Return before IPN', 'GET', '/payments/vnpay/return?' + urlencode(signed))
        assert returned['result'] == 'PENDING' and returned['authoritative'] is False and fingerprint(db) == before_return
        ipn('Authoritative VNPAY success', signed)
        paid = http('Owner Order paid poll', 'GET', '/orders/' + oid, token=token)
        assert (paid['orderStatus'], paid['paymentStatus']) == ('CONFIRMED', 'PAID') and stock() == 98
        assert summary('Paid not completed excluded')['totalRevenue'] == 0
        http('Return after IPN', 'GET', '/payments/vnpay/return?' + urlencode(signed))
        admin_action(oid, 'confirm', paid['version'], 409)
        admin_action(oid, 'cancel', paid['version'], 409)
        shipped = admin_action(oid, 'ship', paid['version'])
        completed = admin_action(oid, 'complete', shipped['version'])
        assert completed['paidAt'] == paid['paidAt'] and completed['items'] == paid['items']
        assert summary('Online completed revenue')['totalRevenue'] == 240000
        before_replay = fingerprint(db)
        admin_action(oid, 'complete', 1)
        ipn('Duplicate completed payment', signed, '02')
        assert fingerprint(db) == before_replay

        cod, _ = checkout('COD')
        cod_id = str(cod['_id'])
        assert cod['paymentStatus'] == 'UNPAID' and stock() == 97
        admin_action(cod_id, 'ship', cod['version'], 409)
        confirmed = admin_action(cod_id, 'confirm', cod['version'])
        shipped = admin_action(cod_id, 'ship', confirmed['version'])
        finished = admin_action(cod_id, 'complete', shipped['version'])
        assert finished['paymentStatus'] == 'PAID' and finished['completedAt'] == finished['paidAt']
        qualified = summary('COD plus online completed')
        assert qualified['totalRevenue'] == 360000 and qualified['totalProductsSold'] == 3
        current_product = db.products.find_one({'_id': product['_id']})
        http('Live Product price/name mutation', 'PATCH', '/admin/products/' + str(product['_id']), payload={
            'price': 130000, 'name': 'Changed live name', 'expectedVersion': current_product['version']}, token=admin_token)
        assert summary('Revenue independent of live Product')['totalRevenue'] == 360000
        assert http('Snapshot after live price change', 'GET', '/orders/' + oid, token=token)['items'] == paid['items']
        for name in ('revenue', 'top-products', 'category-revenue', 'order-status'):
            report = http('Dashboard ' + name, 'GET', '/admin/dashboard/' + name + '?' + window, token=admin_token)
            if name == 'revenue':
                assert sum(row['revenue'] for row in report['series']) == 360000
            elif name == 'top-products':
                assert len(report['items']) == 1 and report['items'][0]['quantity'] == 3 and report['items'][0]['revenue'] == 360000
            elif name == 'category-revenue':
                assert sum(row['revenue'] for row in report['items']) == 360000
        revenue_checks.update(qualifiedRevenue=360000, excludedShipping=60000, qualifiedUnits=3,
                              paidBeforeCompletionRevenue=0, liveProductMutationPreservedRevenue=True)

        retry_order, first = checkout('VNPAY')
        retry_oid = str(retry_order['_id'])
        held_stock = stock()
        path = '/orders/' + retry_oid + '/payment-attempts'
        http('Different owner attempt denied', 'POST', path, 404, {'expectedVersion': 1}, tokens['other'], uuid4().hex)
        http('Client amount rejected', 'POST', path, 422, {'expectedVersion': 1, 'amount': 1}, token, uuid4().hex)
        ipn('Payment failure keeps hold', callback(first, failed=True))
        failed = http('Failed Order poll', 'GET', '/orders/' + retry_oid, token=token)
        assert failed['orderStatus'] == 'PENDING' and failed['paymentStatus'] == 'FAILED' and stock() == held_stock
        retry_body, retry_key = {'expectedVersion': failed['version']}, uuid4().hex
        retry = http('Retry payment attempt', 'POST', path, 201, retry_body, token, retry_key)
        replay = http('Retry attempt same key replay', 'POST', path, 200, retry_body, token, retry_key)
        second = db.payment_attempts.find_one({'_id': ObjectId(retry['attemptId'])})
        assert replay['attemptId'] == retry['attemptId'] and second['amount'] == retry_order['total']
        assert second['expiresAt'] == first['expiresAt'] and stock() == held_stock
        ipn('Retry payment success', callback(second))
        assert summary('Confirmed retry not revenue')['totalRevenue'] == 360000

        cancel_order, cancel_attempt = checkout('VNPAY')
        cancelled = admin_action(str(cancel_order['_id']), 'cancel', cancel_order['version'])
        assert cancelled['orderStatus'] == 'CANCELLED' and cancelled['paymentStatus'] == 'FAILED'
        restored = stock()
        admin_action(str(cancel_order['_id']), 'cancel', 1)
        ipn('Late payment after Admin cancel', callback(cancel_attempt))
        reviewed = http('Cancelled late payment review', 'GET', '/orders/' + str(cancel_order['_id']), token=token)
        assert (reviewed['orderStatus'], reviewed['paymentStatus']) == ('CANCELLED', 'REVIEW_REQUIRED') and stock() == restored
        admin_action(str(cancel_order['_id']), 'ship', reviewed['version'], 409)
        admin_action(str(cancel_order['_id']), 'complete', reviewed['version'], 409)

        expired_order, expired_attempt = checkout('VNPAY')
        deadline = datetime.now(timezone.utc) - timedelta(seconds=2)
        created = deadline - timedelta(minutes=15)
        db.orders.update_one({'_id': expired_order['_id']}, {'$set': {'createdAt': created, 'paymentExpiresAt': deadline}})
        db.payment_attempts.update_one({'_id': expired_attempt['_id']}, {'$set': {'createdAt': created, 'expiresAt': deadline,
            'paymentRequest.createdAt': created, 'paymentRequest.expiresAt': deadline}})
        expired = http('Lazy expiry restores once', 'GET', '/orders/' + str(expired_order['_id']), token=token)
        restored = stock()
        assert (expired['orderStatus'], expired['paymentStatus']) == ('EXPIRED', 'FAILED')
        http('Repeated expiry no restore', 'GET', '/orders/' + str(expired_order['_id']), token=token)
        ipn('Late payment after expiry', callback(expired_attempt))
        for action in ('confirm', 'ship', 'complete', 'cancel'):
            latest = db.orders.find_one({'_id': expired_order['_id']})
            admin_action(str(expired_order['_id']), action, latest['version'], 409)
        assert stock() == restored
        cancelled_cod, _ = checkout('COD')
        http('COD Customer cancel', 'POST', '/orders/' + str(cancelled_cod['_id']) + '/cancel', payload={
            'expectedVersion': cancelled_cod['version']}, token=token)
        restored = stock()
        http('COD cancel replay', 'POST', '/orders/' + str(cancelled_cod['_id']) + '/cancel', payload={'expectedVersion': 1}, token=token)
        assert stock() == restored == 96
        http('Admin Orders list', 'GET', '/admin/orders?pageSize=2', token=admin_token)
        http('Admin Order detail', 'GET', '/admin/orders/' + oid, token=admin_token)
        final_summary = summary('Terminal/review/noncompleted excluded')
        assert final_summary['totalRevenue'] == 360000 and final_summary['totalOrders'] == 6
        http('Customer Dashboard denied', 'GET', report_path, 403, token=token)
        http('Customer Admin Orders denied', 'GET', '/admin/orders', 403, token=token)
        with dev.app_context():
            seed_admin = mongo.database.users.find_one({'role': 'ADMIN', 'status': 'ACTIVE'})
            seed_token = create_access_token(seed_admin)
        seed_window = urlencode({'from': '2026-07-03T00:00:00Z', 'to': '2026-10-01T00:00:00Z'})
        seed_summary = http('Development historical revenue oracle', 'GET', '/admin/dashboard/summary?' + seed_window,
                            token=seed_token, base=dev_listener.base)
        assert seed_summary['totalRevenue'] == 10103259022 and seed_summary['totalProductsSold'] == 434
        assert seed_summary['totalCustomers'] == mongo.database.users.count_documents({'role': 'CUSTOMER'})
        revenue_checks['historicalDevRevenue'] = seed_summary['totalRevenue']
    finally:
        for listener in reversed(listeners):
            listener.close()
        if test:
            db = test.extensions['mongo'].database
            if users:
                db.payment_attempts.delete_many({'userId': {'$in': users}})
                db.orders.delete_many({'userId': {'$in': users}})
                db.carts.delete_many({'userId': {'$in': users}})
                db.users.delete_many({'_id': {'$in': users}})
            if products:
                db.products.delete_many({'_id': {'$in': products}})
            if categories:
                db.categories.delete_many({'_id': {'$in': categories}})
            test.extensions['mongo'].close()
        after = fingerprint(dev.extensions['mongo'].database)
        cleaned = all(mongo.client.ecommerce_test[n].count_documents({}) == 0 for n in NAMES)
        dev.extensions['mongo'].close()
    assert after == runtime_baseline['database'] and cleaned and source_manifest() == baseline['source']
    total = int(suite.attrib['tests'])
    report = {'status': 'PHASE 06AB BACKEND INTEGRATION PASS', 'readyForFrontendAdminPayment': True,
              'gitHead': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
              'tests': {'total': total, 'passed': total, 'failed': 0, 'errors': 0, 'skipped': 0,
                        'seconds': float(suite.attrib['time']), 'modules': dict(Counter(c.attrib['classname'] for c in suite.findall('testcase')))},
              'httpCheckCount': len(checks), 'httpChecks': checks, 'routesAndContract': audit,
              'sharedFoundation': foundation, 'sourceManifest': baseline['source'], 'backendAndContractUnchanged': True,
              'initialDevBaseline': baseline['database'], 'devBefore': runtime_baseline['database'], 'devAfter': after,
              'externalDevChangeSinceInitialBaseline': runtime_baseline['externalDevChangeSinceInitialBaseline'],
              'approvedDevDelta': delta,
              'canonicalSchemaIndexAudit': schema_audit,
              'devDatabaseUnchangedDuringSmoke': after == runtime_baseline['database'],
              'devDataReview': {'status': 'PENDING_USER_CONFIRMATION',
                                'scope': 'Later additional User, Cart, Order and related stock/version changes',
                                'automaticCleanupPerformed': False},
              'testDatabaseEmptyAfterCleanup': cleaned, 'revenueVerification': revenue_checks, 'liveSandbox': live,
              'applicationFixes': [], 'frontendWorkPerformed': False, 'newFeaturesImplemented': False,
              'runtime': {'python': sys.version.split()[0], **{n: version(n) for n in ('Flask', 'pymongo', 'pytest', 'PyJWT')}}}
    (ROOT / 'backend/evidence/phase06ab-integration.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': report['status'], 'tests': report['tests'], 'httpChecks': len(checks), 'routes': 52,
                      'devDatabaseUnchangedDuringSmoke': report['devDatabaseUnchangedDuringSmoke'],
                      'devDataReview': report['devDataReview']['status'], 'liveSandbox': live['status']}))


if __name__ == '__main__':
    main()
