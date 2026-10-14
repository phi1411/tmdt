"""PHASE06A real HTTP on owned test rs0; read-only full dev fingerprint."""
import copy
import hashlib
import hmac
import json
import re
import secrets
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timedelta, timezone
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
from app.services.payment_service import PaymentService
from app.services.vnpay_provider import provider_time
from verify_auth_users import fingerprint, NAMES
from verify_integration_05ab import Listener, source_manifest

FIXTURE_SECRET = 'http-fixture-only-not-a-live-vnpay-credential'


def main():
    manifest = json.loads((ROOT / '.local/phase06a-source-before-tests.json').read_text(encoding='utf-8'))
    assert source_manifest() == manifest, 'Backend source/API contract changed since test baseline'
    suites = {}
    for label, file in [('payment', 'phase06a-payment-pytest.xml'), ('full', 'phase06a-pytest.xml')]:
        suite = ET.parse(ROOT / 'backend/evidence' / file).getroot().find('testsuite')
        counts = {k: int(suite.attrib[k]) for k in ('tests', 'failures', 'errors', 'skipped')}
        assert not counts['failures'] and not counts['errors'] and not counts['skipped'], (label, counts)
        suites[label] = counts
    dev = create_app()
    test, listener = None, None
    owned, products, categories, checks = [], [], [], []
    try:
        before = fingerprint(dev.extensions['mongo'].database)
        expected = json.loads((ROOT / '.local/phase05c-before.json').read_text(encoding='utf-8'))['database']
        assert before == expected, 'Dev fingerprint differs from immutable Commerce baseline'
        routes = [{'method': method, 'path': rule.rule, 'endpoint': rule.endpoint}
                  for rule in dev.url_map.iter_rules() for method in sorted(rule.methods - {'HEAD', 'OPTIONS'})]
        pairs = [(r['method'], re.sub(r'<[^>]+>', ':id', r['path'])) for r in routes]
        assert not [p for p, count in Counter(pairs).items() if count > 1], 'Route collision'
        assert len(dev.blueprints) == len({id(b) for b in dev.blueprints.values()})
        actual = {(r['method'], re.sub(r'<[^>]+>', ':id', r['path'].removeprefix('/api/v1')))
                  for r in routes if r['endpoint'].startswith('payments.')}
        contract = (ROOT / 'docs/api-contract.md').read_text(encoding='utf-8')
        section = contract.split('## Payment IMPLEMENTED — PHASE 06A\n', 1)[1].split('\n## ', 1)[0]
        documented = set(re.findall(r'^\| (GET|POST) (/[^ |]+)', section, re.M))
        assert actual == documented and len(actual) == 3, (actual, documented)
        feature = (ROOT / 'docs/features/payment.md').read_text(encoding='utf-8')
        assert actual <= set(re.findall(r'^\| (GET|POST) (/[^ |]+)', feature, re.M))
        config = {k: dev.config[k] for k in ('MONGODB_URI', 'JWT_ISSUER', 'JWT_AUDIENCE')}
        config.update(APP_ENV='testing', MONGODB_TEST_DB='ecommerce_test', JWT_SECRET=secrets.token_urlsafe(48),
            LOG_LEVEL='ERROR', VNPAY_ENABLED=True, VNP_TMN_CODE='TEST0001', VNP_HASH_SECRET=FIXTURE_SECRET,
            VNP_PAYMENT_URL='https://sandbox.vnpayment.vn/paymentv2/vpcpay.html',
            VNP_RETURN_URL='http://127.0.0.1:5001/api/v1/payments/vnpay/return',
            VNP_IPN_URL='http://127.0.0.1:5001/api/v1/payments/vnpay/ipn')
        test = create_app(config)
        db = test.extensions['mongo'].database
        marker = json.loads((ROOT / '.local/ecommerce_test.ownership.json').read_text(encoding='utf-8'))
        assert marker == {'project': str(ROOT), 'database': 'ecommerce_test', 'endpoint': 'localhost:27017/rs0'}
        assert db.name == 'ecommerce_test' and set(db.list_collection_names()) == set(NAMES)
        assert all(db[n].count_documents({}) == 0 for n in NAMES), 'Test data exists; refusing mutation'
        assert test.extensions['mongo'].health()['replicaSet'] == 'ok'
        listener = Listener(test)

        def http(label, method, path, status=200, payload=None, token=None, key=None, provider_code=None):
            headers = {'Content-Type': 'application/json'}
            if token:
                headers['Authorization'] = 'Bearer ' + token
            if key:
                headers['Idempotency-Key'] = key
            data = json.dumps(payload).encode() if payload is not None else None
            try:
                response = urlopen(Request(listener.base + path, data=data, headers=headers, method=method), timeout=10)
            except HTTPError as error:
                response = error
            with response:
                raw = response.read()
                assert response.status == status, (label, response.status, status)
                body = json.loads(raw) if raw else None
                assert response.headers['X-Request-ID'] and response.headers['X-Content-Type-Options'] == 'nosniff'
                if provider_code:
                    assert set(body) == {'RspCode', 'Message'} and body['RspCode'] == provider_code, (label, body)
                elif body:
                    assert body['meta']['requestId'] == response.headers['X-Request-ID']
                assert FIXTURE_SECRET.encode() not in raw and b'passwordHash' not in raw and b'tokenVersion' not in raw
                checks.append({'label': label, 'method': method,
                    'path': re.sub(r'/[a-f0-9]{24}(?=/|$)', '/:id', path.split('?', 1)[0]),
                    'status': status, 'providerCode': provider_code})
                return body.get('data', body) if body else None

        original = dev.extensions['mongo'].database.users.find_one({'role': 'CUSTOMER', 'status': 'ACTIVE'})
        password = secrets.token_urlsafe(24)
        tokens, users = {}, {}
        for label, role in [('owner', 'CUSTOMER'), ('other', 'CUSTOMER'), ('admin', 'ADMIN')]:
            user = copy.deepcopy(original)
            user.update(_id=ObjectId(), email=uuid4().hex + '@example.test', role=role,
                        phone='0901234567', passwordHash=hash_password(password), tokenVersion=0)
            user['addresses'] = [{'_id': ObjectId(), 'receiverName': 'Payment HTTP', 'phone': '0901234567',
                'addressLine': '123 Test', 'province': 'Hồ Chí Minh'}]
            user['defaultAddressId'] = user['addresses'][0]['_id']
            owned.append(user['_id'])
            db.users.insert_one(user)
            users[label] = user
            tokens[label] = http(label + ' actual login', 'POST', '/auth/login', payload={
                'email': user['email'], 'password': password})['accessToken']
        token = tokens['owner']
        http('real listener health/rs0', 'GET', '/health')
        category = copy.deepcopy(dev.extensions['mongo'].database.categories.find_one({'status': 'ACTIVE'}))
        category.update(_id=ObjectId(), slug='payment-http-' + uuid4().hex, version=1)
        categories.append(category['_id'])
        db.categories.insert_one(category)
        product = copy.deepcopy(dev.extensions['mongo'].database.products.find_one({'productType': category['productType'], 'status': 'ACTIVE'}))
        product.update(_id=ObjectId(), sku='HTTP_' + uuid4().hex.upper(), slug='payment-http-' + uuid4().hex,
                       categoryId=category['_id'], version=1, stock=20, price=Int64(120000), status='ACTIVE')
        # Use a non-Fashion selection-free fixture with canonical flexible attributes.
        if product['productType'] == 'FASHION':
            product['attributes'] = {'material': 'Test'}
        products.append(product['_id'])
        db.products.insert_one(product)
        http('Catalog remains available', 'GET', '/products/' + product['slug'])

        def checkout(method='VNPAY'):
            cart = http('read Cart', 'GET', '/cart', token=token)
            cart = http('add item', 'POST', '/cart/items', payload={'productId': str(product['_id']),
                'quantity': 1, 'selectedAttributes': {}, 'cartVersion': cart['version']}, token=token)
            quote = http(method + ' quote', 'GET', '/checkout/quote?' + urlencode({
                'addressId': str(users['owner']['addresses'][0]['_id']), 'paymentMethod': method}), token=token)
            payload = {'cartVersion': cart['version'], 'addressId': str(users['owner']['addresses'][0]['_id']),
                       'paymentMethod': method, 'quoteToken': quote['quoteToken']}
            key = uuid4().hex
            result = http(method + ' atomic checkout', 'POST', '/orders', 201, payload, token, key)
            assert http(method + ' checkout replay', 'POST', '/orders', 200, payload, token, key)['order']['id'] == result['order']['id']
            oid = ObjectId(result['order']['id'])
            attempt = db.payment_attempts.find_one({'orderId': oid})
            if method == 'VNPAY':
                parsed = urlsplit(result['payment']['paymentUrl'])
                assert parsed.hostname == 'sandbox.vnpayment.vn'
                params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
                signature = params.pop('vnp_SecureHash')
                expected = hmac.new(FIXTURE_SECRET.encode(), urlencode(sorted(params.items())).encode(), hashlib.sha512).hexdigest()
                assert hmac.compare_digest(signature, expected)
                assert int(params['vnp_Amount']) == result['order']['total'] * 100
                assert db.payment_attempts.count_documents({'orderId': oid}) == 1
            else:
                assert attempt is None and result['payment'] == {'method': 'COD'}
            return oid, attempt, result

        def callback(attempt, **changes):
            values = {'vnp_TmnCode': 'TEST0001', 'vnp_Amount': str(int(attempt['amount']) * 100),
                'vnp_TxnRef': attempt['txnRef'], 'vnp_OrderInfo': attempt['paymentRequest']['orderInfo'],
                'vnp_ResponseCode': '00', 'vnp_TransactionStatus': '00', 'vnp_BankCode': 'NCB',
                'vnp_TransactionNo': str(uuid4().int % 99999999999999 + 1),
                'vnp_PayDate': provider_time(datetime.now(timezone.utc)), **changes}
            values['vnp_SecureHash'] = hmac.new(FIXTURE_SECRET.encode(), urlencode(sorted(values.items())).encode(), hashlib.sha512).hexdigest()
            return values

        def ipn(label, query, code):
            return http(label, 'GET', '/payments/vnpay/ipn?' + urlencode(query), provider_code=code)

        oid, attempt, result = checkout()
        path = '/orders/' + str(oid)
        query = callback(attempt)
        unchanged = fingerprint(db)
        returned = http('Return before IPN read-only', 'GET', '/payments/vnpay/return?' + urlencode(query))
        assert returned['result'] == 'PENDING' and not returned['authoritative'] and fingerprint(db) == unchanged
        ipn('tampered signature', {**query, 'vnp_Amount': '1'}, '97')
        invalid_return = http('Return invalid signature', 'GET', '/payments/vnpay/return?' + urlencode({**query, 'vnp_Amount': '1'}))
        assert invalid_return['result'] == 'INVALID_SIGNATURE' and not invalid_return['verified']
        ipn('signed wrong amount', callback(attempt, vnp_Amount='1'), '04')
        ipn('unknown reference', callback(attempt, vnp_TxnRef='UNKNOWNREF'), '01')
        http('Guest create denied', 'POST', path + '/payment-attempts', 401, {'expectedVersion': 1}, key=uuid4().hex)
        http('Admin create denied', 'POST', path + '/payment-attempts', 403, {'expectedVersion': 1}, tokens['admin'], uuid4().hex)
        http('other owner create denied', 'POST', path + '/payment-attempts', 404, {'expectedVersion': 1}, tokens['other'], uuid4().hex)
        http('client amount rejected', 'POST', path + '/payment-attempts', 422, {'expectedVersion': 1, 'amount': 1}, token, uuid4().hex)
        ipn('authoritative success committed', query, '00')
        unchanged = fingerprint(db)
        ipn('duplicate receipt no write', query, '02')
        assert fingerprint(db) == unchanged
        assert http('owner paid status', 'GET', path, token=token)['paymentStatus'] == 'PAID'
        assert http('Return after IPN success', 'GET', '/payments/vnpay/return?' + urlencode(query))['result'] == 'SUCCESS'
        http('paid cannot create', 'POST', path + '/payment-attempts', 409, {'expectedVersion': 2}, token, uuid4().hex)
        http('paid cannot cancel', 'POST', path + '/cancel', 409, {'expectedVersion': 2}, token)

        retry_oid, first, _ = checkout()
        failure_query = callback(first, vnp_ResponseCode='24', vnp_TransactionStatus='02')
        ipn('failure receipt', failure_query, '00')
        assert http('Return failed receipt', 'GET', '/payments/vnpay/return?' + urlencode(failure_query))['result'] == 'FAILED'
        failed = http('failed owner status', 'GET', '/orders/' + str(retry_oid), token=token)
        retry_path, retry_key = '/orders/' + str(retry_oid) + '/payment-attempts', uuid4().hex
        retry_body = {'expectedVersion': failed['version']}
        retry = http('create retry attempt', 'POST', retry_path, 201, retry_body, token, retry_key)
        assert http('retry replay', 'POST', retry_path, 200, retry_body, token, retry_key)['attemptId'] == retry['attemptId']
        second = db.payment_attempts.find_one({'_id': ObjectId(retry['attemptId'])})
        assert second['expiresAt'] == first['expiresAt']
        ipn('retry success', callback(second), '00')

        late_oid, late_attempt, _ = checkout()
        deadline = datetime.now(timezone.utc) - timedelta(seconds=2)
        created = deadline - timedelta(minutes=15)
        db.orders.update_one({'_id': late_oid}, {'$set': {'createdAt': created, 'paymentExpiresAt': deadline}})
        db.payment_attempts.update_one({'_id': late_attempt['_id']}, {'$set': {'createdAt': created,
            'expiresAt': deadline, 'paymentRequest.createdAt': created, 'paymentRequest.expiresAt': deadline}})
        late_query = callback(late_attempt)
        unchanged = fingerprint(db)
        http('Return due hold remains read-only', 'GET', '/payments/vnpay/return?' + urlencode(late_query))
        assert fingerprint(db) == unchanged
        with test.app_context():
            assert PaymentService().expire_due()['expired'] == 1
            assert PaymentService().expire_due()['scanned'] == 0
        ipn('late receipt requires review', late_query, '00')
        late = http('late terminal status', 'GET', '/orders/' + str(late_oid), token=token)
        assert late['orderStatus'] == 'EXPIRED' and late['paymentStatus'] == 'REVIEW_REQUIRED'
        cod_oid, _, cod = checkout('COD')
        canceled = http('COD cancel still works', 'POST', '/orders/' + str(cod_oid) + '/cancel', payload={
            'expectedVersion': cod['order']['version']}, token=token)
        assert canceled['orderStatus'] == 'CANCELLED' and canceled['paymentStatus'] == 'UNPAID'
        assert db.products.find_one({'_id': product['_id']})['stock'] == 18
        evidence = {'phase': '06A', 'status': 'PASS_BACKEND', 'testSuites': suites,
            'httpCheckCount': len(checks), 'httpChecks': checks, 'fixtureCredentialsOnly': True,
            'routes': {'blueprintCount': len(dev.blueprints), 'methodPathCount': len(routes), 'conflicts': [], 'paymentMethodPaths': 3},
            'contractAudit': 'PASS', 'fullSourceManifest': manifest,
            'liveSandbox': {'status': 'BLOCKED LIVE SANDBOX' if not dev.config['VNP_HASH_SECRET'] else 'CONFIG_PRESENT_REHEARSAL_NOT_RUN',
                            'enabled': dev.config['VNPAY_ENABLED'], 'redirectVerified': False, 'providerIpnVerified': False},
            'devBefore': before, 'devAfter': fingerprint(dev.extensions['mongo'].database)}
        assert evidence['devAfter'] == before
    finally:
        if listener:
            listener.close()
        if test:
            db = test.extensions['mongo'].database
            for name in ('payment_attempts', 'orders', 'carts'):
                db[name].delete_many({'userId': {'$in': owned}})
            db.products.delete_many({'_id': {'$in': products}})
            db.categories.delete_many({'_id': {'$in': categories}})
            db.users.delete_many({'_id': {'$in': owned}})
            empty = {n: db[n].count_documents({}) for n in NAMES}
            test.extensions['mongo'].close()
        dev.extensions['mongo'].close()
    assert all(value == 0 for value in empty.values()), 'Owned fixture cleanup incomplete'
    assert source_manifest() == manifest, 'Backend source/API contract changed during HTTP verification'
    evidence['testCollectionsAfterCleanup'] = empty
    (ROOT / 'backend/evidence/phase06a-runtime.json').write_text(json.dumps(evidence, indent=2, ensure_ascii=True), encoding='utf-8')
    print(json.dumps({'status': evidence['status'], 'httpChecks': len(checks), 'devUnchanged': True,
                      'testCollectionsEmpty': True, 'liveSandbox': evidence['liveSandbox']['status']}))


if __name__ == '__main__':
    main()
