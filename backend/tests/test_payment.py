"""PHASE06A: deterministic provider fixtures and real MongoDB rs0 payment flow."""
import copy
import hashlib
import hmac
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier, local
from urllib.parse import parse_qs, urlencode, urlsplit
from uuid import uuid4
import pytest
from bson import ObjectId
from bson.int64 import Int64
from pymongo.errors import PyMongoError, OperationFailure
from werkzeug.datastructures import MultiDict
from tests.test_commerce import commerce
from app.config import load_config, ConfigurationError
from app.errors import ServiceUnavailableError
from app.repositories.order_repository import OrderRepository
from app.repositories.payment_attempt_repository import PaymentAttemptRepository
from app.repositories.product_repository import ProductRepository
from app.services.payment_service import PaymentService
from app.services.vnpay_provider import canonical_parameters, sign_parameters, provider_time

PREFIX = '/api/v1'
pytestmark = pytest.mark.integration
TEST_SECRET = 'fixture-only-deterministic-merchant-key-not-a-live-credential'


@pytest.fixture
def settings(settings):
    return {**settings, 'VNPAY_ENABLED': True, 'VNP_TMN_CODE': 'TEST0001', 'VNP_HASH_SECRET': TEST_SECRET,
            'VNP_PAYMENT_URL': 'https://sandbox.vnpayment.vn/paymentv2/vpcpay.html',
            'VNP_RETURN_URL': 'http://127.0.0.1:5001/api/v1/payments/vnpay/return',
            'VNP_IPN_URL': 'http://127.0.0.1:5001/api/v1/payments/vnpay/ipn'}


def signed(values):
    # Reference fixture signing independent of production adapter entry points.
    body = urlencode(sorted((k, str(v)) for k, v in values.items() if k not in {'vnp_SecureHash', 'vnp_SecureHashType'}))
    return {**values, 'vnp_SecureHash': hmac.new(TEST_SECRET.encode(), body.encode(), hashlib.sha512).hexdigest()}


@pytest.fixture
def payment(commerce, client, database):
    c = commerce
    p = c['product']()

    def checkout(product=p, quantity=1):
        c['add'](product, quantity)
        q = c['quote'](method='VNPAY').json['data']
        intent = {'cartVersion': q['cartVersion'], 'addressId': str(c['users'][0]['addresses'][0]['_id']),
                  'paymentMethod': 'VNPAY', 'quoteToken': q['quoteToken']}
        key = uuid4().hex
        response = c['checkout'](intent, key).json['data']
        order_id = ObjectId(response['order']['id'])
        attempt = database.payment_attempts.find_one({'orderId': order_id, 'status': 'PENDING'})
        assert attempt
        return {'result': response, 'orderId': order_id, 'attempt': attempt, 'intent': intent, 'key': key}

    initial = checkout()

    def callback(attempt=None, **changes):
        attempt = attempt or initial['attempt']
        values = {'vnp_TmnCode': 'TEST0001', 'vnp_Amount': str(int(attempt['amount']) * 100),
                  'vnp_TxnRef': attempt['txnRef'], 'vnp_OrderInfo': attempt['paymentRequest']['orderInfo'],
                  'vnp_ResponseCode': '00', 'vnp_TransactionStatus': '00', 'vnp_BankCode': 'NCB',
                  'vnp_TransactionNo': str(uuid4().int % 99999999999999 + 1),
                  'vnp_PayDate': provider_time(datetime.now(timezone.utc)), **changes}
        values = {k: v for k, v in values.items() if v is not None}
        return signed(values)

    def ipn(query, expected='00', test_client=client):
        response = test_client.get(PREFIX + '/payments/vnpay/ipn', query_string=query)
        assert response.status_code == 200 and response.json['RspCode'] == expected, response.json
        assert set(response.json) == {'RspCode', 'Message'} and response.headers['X-Request-ID']
        assert TEST_SECRET not in response.text
        return response

    def attempt(payload=None, key=None, expected=201, who='a', order_id=None, test_client=None):
        oid = order_id or initial['orderId']
        order = database.orders.find_one({'_id': oid})
        return c['call']('post', '/orders/' + str(oid) + '/payment-attempts',
            payload or {'expectedVersion': order['version']}, who, expected,
            {'Idempotency-Key': key or uuid4().hex}, test_client=test_client)

    def age(deadline=None):
        deadline = deadline or datetime.now(timezone.utc) - timedelta(seconds=2)
        created = deadline - timedelta(minutes=15)
        database.orders.update_one({'_id': initial['orderId']}, {'$set': {'paymentExpiresAt': deadline, 'createdAt': created}})
        database.payment_attempts.update_many({'orderId': initial['orderId']}, {'$set': {
            'expiresAt': deadline, 'createdAt': created, 'paymentRequest.createdAt': created, 'paymentRequest.expiresAt': deadline}})
        return deadline

    return {**initial, 'c': c, 'product': p, 'checkout': checkout, 'callback': callback, 'ipn': ipn, 'create_attempt': attempt, 'age': age}


def order(database, payment):
    return database.orders.find_one({'_id': payment['orderId']})


def stored_attempt(database, payment):
    return database.payment_attempts.find_one({'_id': payment['attempt']['_id']})


def test_canonical_encoding_known_hmac_vector():
    values = {'vnp_TxnRef': 'ABC123', 'vnp_ReturnUrl': 'https://example.test/payment/return?a=1&b=x y',
              'vnp_OrderInfo': 'Thanh toan A+B Đồ test', 'vnp_Amount': '10000000'}
    expected = 'vnp_Amount=10000000&vnp_OrderInfo=Thanh+toan+A%2BB+%C4%90%E1%BB%93+test&vnp_ReturnUrl=https%3A%2F%2Fexample.test%2Fpayment%2Freturn%3Fa%3D1%26b%3Dx+y&vnp_TxnRef=ABC123'
    assert canonical_parameters(values) == expected
    assert sign_parameters(values, 'deterministic-vector-key') == '3217ed433c233e5f0bf611f8e12a1e632f404f5dacba7e1af33066e7ad2c6dae1effc69e8589a846206dfe64313cd5fefe3ae7242e19221b5b720615782a61bb'

    assert sign_parameters({**values, 'vnp_SecureHash': 'ignored', 'vnp_SecureHashType': 'ignored'}, 'deterministic-vector-key') == sign_parameters(values, 'deterministic-vector-key')


def test_expiry_cutover_preserves_historical_fixture_and_releases_new_hold_once(app, payment, database):
    p=payment
    now=datetime.now(timezone.utc)
    cutoff=now-timedelta(hours=1)
    p['age'](cutoff-timedelta(minutes=5))
    recent=p['checkout']()
    created,deadline=now-timedelta(minutes=20),now-timedelta(minutes=5)
    database.orders.update_one({'_id':recent['orderId']},{'$set':{'createdAt':created,'paymentExpiresAt':deadline}})
    database.payment_attempts.update_many({'orderId':recent['orderId']},{'$set':{
        'createdAt':created,'expiresAt':deadline,'paymentRequest.createdAt':created,'paymentRequest.expiresAt':deadline}})
    with app.app_context():
        first=PaymentService().expire_due(created_after=cutoff)
        second=PaymentService().expire_due(created_after=cutoff)
    assert first=={'scanned':1,'expired':1,'failed':0} and second['scanned']==0
    assert order(database,p)['orderStatus']=='PENDING'
    assert stored_attempt(database,p)['status']=='PENDING'
    assert database.orders.find_one({'_id':recent['orderId']})['orderStatus']=='EXPIRED'
    assert database.products.find_one({'_id':p['product']['_id']})['stock']==9


def test_initial_checkout_atomic_metadata_url_and_replay(payment, database):
    p = payment
    o, a = order(database, p), stored_attempt(database, p)
    assert o['paymentMethod'] == 'VNPAY' and o['paymentStatus'] == 'PENDING' and o['orderStatus'] == 'PENDING'
    assert o['paymentExpiresAt'] - o['createdAt'] == timedelta(minutes=15)
    assert a['orderId'] == o['_id'] and a['userId'] == o['userId'] and a['expiresAt'] == o['paymentExpiresAt']
    assert a['amount'] == o['total'] and isinstance(a['amount'], Int64) and isinstance(a['paymentRequest']['amountScaled'], Int64)
    assert a['paymentRequest']['amountScaled'] == int(o['total']) * 100
    assert not {'card', 'hashSecret', 'paymentUrl', 'rawQuery'} & a.keys()
    result = p['result']['payment']
    url = urlsplit(result['paymentUrl'])
    assert url.scheme == 'https' and url.hostname == 'sandbox.vnpayment.vn'
    fields = {k: v[0] for k, v in parse_qs(url.query).items()}
    assert fields['vnp_Amount'] == str(int(o['total']) * 100) and fields['vnp_TxnRef'] == a['txnRef']
    assert fields['vnp_CreateDate'] == provider_time(a['createdAt']) and fields['vnp_ExpireDate'] == provider_time(a['expiresAt'])
    assert fields['vnp_Version'] == '2.1.0' and fields['vnp_Command'] == 'pay'
    assert signed(fields)['vnp_SecureHash'] == fields['vnp_SecureHash']
    assert 'vnp_IpnUrl' not in fields and TEST_SECRET not in result['paymentUrl']
    replay = p['c']['checkout'](p['intent'], p['key'], expected=200).json['data']
    assert replay == p['result']
    assert database.orders.count_documents({'userId': o['userId']}) == 1
    assert database.payment_attempts.count_documents({'orderId': o['_id']}) == 1
    assert database.products.find_one({'_id': p['product']['_id']})['stock'] == 9


def test_success_duplicate_failure_after_success_and_read_only_return(payment, client, database):
    p = payment
    cb = p['callback']()
    before = copy.deepcopy(order(database, p))
    response = client.get(PREFIX + '/payments/vnpay/return', query_string=cb)
    assert response.json['data']['result'] == 'PENDING' and response.json['data']['providerResult'] == 'SUCCESS'
    assert response.json['data']['confirmed'] is False and order(database, p) == before
    p['ipn'](cb)
    paid = order(database, p)
    assert paid['paymentStatus'] == 'PAID' and paid['orderStatus'] == 'CONFIRMED' and paid['version'] == 2
    assert 'paidAt' in paid and not paid['paymentReviewRequired']
    assert stored_attempt(database, p)['status'] == 'SUCCEEDED'
    for query in (cb, p['callback'](vnp_ResponseCode='24', vnp_TransactionStatus='02', vnp_TransactionNo='0')):
        p['ipn'](query, '02')
        assert order(database, p) == paid
    result = client.get(PREFIX + '/payments/vnpay/return', query_string=cb).json['data']
    assert result['result'] == 'SUCCESS' and result['confirmed'] and not result['authoritative']
    assert not {'customerSnapshot', 'shippingAddress', 'userId', 'items', 'paymentRequest'} & result.keys()
    assert database.products.find_one({'_id': p['product']['_id']})['stock'] == 9
    p['c']['call']('post', '/orders/' + str(p['orderId']) + '/cancel', {'expectedVersion': 2}, expected=409)


@pytest.mark.parametrize('codes', [('24', '02'), ('00', '01'), ('01', '00')])
def test_failure_requires_both_success_codes_and_no_stock_restore(payment, client, database, codes):
    p = payment
    cb = p['callback'](vnp_ResponseCode=codes[0], vnp_TransactionStatus=codes[1], vnp_TransactionNo='0')
    initial = copy.deepcopy(order(database, p))
    assert client.get(PREFIX + '/payments/vnpay/return', query_string=cb).json['data']['result'] == 'FAILED'
    assert order(database, p) == initial
    p['ipn'](cb)
    o, a = order(database, p), stored_attempt(database, p)
    assert o['orderStatus'] == 'PENDING' and o['paymentStatus'] == 'FAILED' and 'paidAt' not in o
    assert a['status'] == 'FAILED' and 'providerTransactionNo' not in a and 'verifiedAt' in a
    p['ipn'](cb, '02')
    assert order(database, p) == o and stored_attempt(database, p) == a
    assert database.products.find_one({'_id': p['product']['_id']})['stock'] == 9


@pytest.mark.parametrize('field', ['vnp_TmnCode', 'vnp_Amount', 'vnp_TxnRef', 'vnp_OrderInfo', 'vnp_ResponseCode',
                                   'vnp_TransactionStatus', 'vnp_BankCode', 'vnp_TransactionNo', 'vnp_SecureHash'])
def test_missing_signature_parameters_rejected_without_writes(payment, database, field):
    before = copy.deepcopy(order(database, payment))
    cb = payment['callback']()
    cb.pop(field)
    payment['ipn'](cb, '97')
    assert order(database, payment) == before and stored_attempt(database, payment)['status'] == 'PENDING'


@pytest.mark.parametrize('field,value', [('vnp_Amount', '1'), ('vnp_TxnRef', 'tampered'), ('vnp_TmnCode', 'WRONG001'), ('vnp_SecureHash', '0' * 128)])
def test_unsigned_tampering_invalid_signature(payment, client, database, field, value):
    cb = payment['callback']()
    cb[field] = value
    payment['ipn'](cb, '97')
    result = client.get(PREFIX + '/payments/vnpay/return', query_string=cb).json['data']
    assert result == {'result': 'INVALID_SIGNATURE', 'verified': False, 'confirmed': False, 'authoritative': False}
    assert order(database, payment)['paymentStatus'] == 'PENDING'


@pytest.mark.parametrize('field', ['vnp_Amount', 'vnp_TxnRef', 'vnp_SecureHash', 'vnp_TmnCode'])
def test_duplicate_query_keys_rejected(payment, database, field):
    cb = MultiDict(payment['callback']())
    cb.add(field, cb[field])
    payment['ipn'](cb, '97')
    assert stored_attempt(database, payment)['status'] == 'PENDING'


@pytest.mark.parametrize('changes,code', [
    ({'vnp_Amount': '100'}, '04'), ({'vnp_TxnRef': 'UNKNOWNREFERENCE'}, '01'),
    ({'vnp_TmnCode': 'WRONG001'}, '97'), ({'vnp_Amount': '-1'}, '99'),
    ({'vnp_Amount': '1.5'}, '99'), ({'vnp_ResponseCode': '000'}, '99'),
    ({'vnp_TransactionNo': '0'}, '99'), ({'vnp_PayDate': '20260230000000'}, '99'),
    ({'vnp_PayDate': '2026011'}, '99'), ({'vnp_BankCode': 'X'}, '99'),
    ({'extra': 'unsupported'}, '97'), ({'vnp_Amount[$ne]': '0'}, '97'),
])
def test_signed_invalid_callbacks_and_protocol_codes(payment, database, changes, code):
    before = copy.deepcopy(order(database, payment))
    payment['ipn'](payment['callback'](**changes), code)
    assert order(database, payment) == before


def test_callback_checks_order_total_and_attempt_amount(payment, database):
    p = payment
    callback = p['callback']()
    total = order(database, p)['total']
    # Valid long shape but corrupted business invariant must not be silently trusted.
    database.orders.update_one({'_id': p['orderId']}, {'$set': {'total': Int64(total + 1)}})
    p['ipn'](callback, '04')
    database.orders.update_one({'_id': p['orderId']}, {'$set': {'total': total}})
    database.payment_attempts.update_one({'_id': p['attempt']['_id']}, {'$set': {'amount': Int64(total + 1)}})
    p['ipn'](callback, '04')
    assert order(database, p)['paymentStatus'] == 'PENDING'


def test_missing_optional_pay_date_uses_verified_at(payment, database):
    p = payment
    p['ipn'](p['callback'](vnp_PayDate=None))
    a, o = stored_attempt(database, p), order(database, p)
    assert 'providerPaidAt' not in a and o['paidAt'] == a['verifiedAt']


def test_retry_creation_replay_pending_guard_and_fixed_deadline(payment, database):
    p = payment
    p['create_attempt'](expected=409)
    p['ipn'](p['callback'](vnp_ResponseCode='24', vnp_TransactionStatus='02', vnp_TransactionNo='0'))
    expired_at = order(database, p)['paymentExpiresAt']
    key, payload = uuid4().hex, {'expectedVersion': 2}
    result = p['create_attempt'](payload, key).json['data']
    assert result['orderVersion'] == 3 and result['attemptStatus'] == 'PENDING' and result['expiresAt']
    assert p['create_attempt'](payload, key, expected=200).json['data'] == result
    p['create_attempt']({'expectedVersion': 3}, key, expected=409)
    p['create_attempt']({'expectedVersion': 2}, expected=409)
    assert order(database, p)['paymentExpiresAt'] == expired_at
    assert database.payment_attempts.count_documents({'orderId': p['orderId']}) == 2
    assert database.products.find_one({'_id': p['product']['_id']})['stock'] == 9


@pytest.mark.parametrize('who,status', [('b', 404), ('admin', 403), ('guest', 401), ('blocked', 401)])
def test_attempt_owner_role_guards(payment, who, status):
    payment['create_attempt'](who=who, expected=status)


@pytest.mark.parametrize('changes', [{'amount': 1}, {'total': 1}, {'userId': 'x'}, {'paymentUrl': 'https://evil.test'},
                                    {'VNP_HASH_SECRET': 'browser'}, {'expectedVersion': True}, {'expectedVersion': 1.5}, {'expectedVersion': 0}])
def test_attempt_payload_tampering(payment, changes):
    payment['create_attempt']({'expectedVersion': 1, **changes}, expected=422)


@pytest.mark.parametrize('state', ['PAID', 'CANCELLED', 'EXPIRED', 'COD'])
def test_cannot_create_new_payment_for_invalid_order(payment, database, state):
    p = payment
    if state == 'PAID':
        p['ipn'](p['callback']())
    elif state == 'CANCELLED':
        p['c']['call']('post', '/orders/' + str(p['orderId']) + '/cancel', {'expectedVersion': 1})
    elif state == 'EXPIRED':
        p['age']()
    else:
        p['c']['add'](p['product'])
        cod = p['c']['checkout']().json['data']['order']
        p['create_attempt'](order_id=ObjectId(cod['id']), expected=409)
        return
    p['create_attempt'](expected=409)


@pytest.mark.parametrize('mode', ['cancelled', 'late_no_worker', 'late_worker', 'late_provider_date'])
def test_late_success_reviews_without_reviving_or_double_restoring(payment, app, client, database, mode):
    p = payment
    if mode == 'cancelled':
        p['c']['call']('post', '/orders/' + str(p['orderId']) + '/cancel', {'expectedVersion': 1})
        callback = p['callback']()
    elif mode == 'late_provider_date':
        callback = p['callback'](vnp_PayDate=provider_time(order(database, p)['paymentExpiresAt'] + timedelta(seconds=1)))
    else:
        deadline = p['age']()
        callback = p['callback'](vnp_PayDate=provider_time(deadline - timedelta(seconds=1)))
        if mode == 'late_worker':
            with app.app_context():
                assert PaymentService().expire_due()['expired'] == 1
    p['ipn'](callback)
    o = order(database, p)
    assert o['orderStatus'] == ('CANCELLED' if mode == 'cancelled' else 'EXPIRED')
    assert o['paymentStatus'] == 'REVIEW_REQUIRED' and o['paymentReviewRequired'] and 'paidAt' in o
    assert stored_attempt(database, p)['status'] == 'REVIEW_REQUIRED'
    assert database.products.find_one({'_id': p['product']['_id']})['stock'] == 10
    p['ipn'](callback, '02')
    with app.app_context():
        PaymentService().expire_due()
    assert order(database, p) == o
    assert client.get(PREFIX + '/payments/vnpay/return', query_string=callback).json['data']['result'] == 'PENDING'


@pytest.mark.parametrize('winning_attempt', ['initial', 'retry'])
def test_second_distinct_success_preserves_paid_order_and_revenue_basis(payment, database, winning_attempt):
    p = payment
    p['ipn'](p['callback'](vnp_ResponseCode='24', vnp_TransactionStatus='02', vnp_TransactionNo='0'))
    retry = p['create_attempt']().json['data']
    retry_attempt = database.payment_attempts.find_one({'_id': ObjectId(retry['attemptId'])})
    first, second = (p['attempt'], retry_attempt) if winning_attempt == 'initial' else (retry_attempt, p['attempt'])
    p['ipn'](p['callback'](first))
    paid = order(database, p)
    assert paid['paymentStatus'] == 'PAID' and not paid['paymentReviewRequired']
    second_callback = p['callback'](second)
    p['ipn'](second_callback)
    current = order(database, p)
    assert current['paymentStatus'] == 'PAID' and current['orderStatus'] == paid['orderStatus'] and current['paidAt'] == paid['paidAt']
    assert current['paymentReviewRequired'] and current['total'] == paid['total'] and current['items'] == paid['items']
    assert database.payment_attempts.find_one({'_id': second['_id']})['status'] == 'REVIEW_REQUIRED'
    p['ipn'](second_callback, '02')
    assert order(database, p) == current and database.products.find_one({'_id': p['product']['_id']})['stock'] == 9


def test_expiry_detail_once_and_failed_attempt_expiry(payment, app, database):
    p = payment
    p['ipn'](p['callback'](vnp_ResponseCode='24', vnp_TransactionStatus='02', vnp_TransactionNo='0'))
    p['age']()
    result = p['c']['call']('get', '/orders/' + str(p['orderId'])).json['data']
    assert result['orderStatus'] == 'EXPIRED' and result['paymentStatus'] == 'FAILED'
    assert stored_attempt(database, p)['status'] == 'FAILED'
    version = order(database, p)['version']
    with app.app_context():
        assert PaymentService().expire_due()['scanned'] == 0
    p['c']['call']('get', '/orders/' + str(p['orderId']))
    assert order(database, p)['version'] == version and database.products.find_one({'_id': p['product']['_id']})['stock'] == 10


def test_expiry_return_is_read_only_and_wrong_amount_does_not_expire(payment, client, database):
    p = payment
    p['age']()
    before = copy.deepcopy(order(database, p))
    client.get(PREFIX + '/payments/vnpay/return', query_string=p['callback']())
    assert order(database, p) == before and database.products.find_one({'_id': p['product']['_id']})['stock'] == 9
    p['ipn'](p['callback'](vnp_Amount='100'), '04')
    assert order(database, p) == before


def test_initial_attempt_failure_rolls_back_order_cart_stock_and_category(commerce, database, monkeypatch):
    c = commerce
    p = c['product']()
    c['add'](p)
    q = c['quote'](method='VNPAY').json['data']
    payload = {'cartVersion': 1, 'addressId': str(c['users'][0]['addresses'][0]['_id']), 'paymentMethod': 'VNPAY', 'quoteToken': q['quoteToken']}
    def failure(*args, **kwargs):
        raise PyMongoError('injected private diagnostic')
    monkeypatch.setattr(PaymentAttemptRepository, 'insert', failure)
    c['checkout'](payload, expected=503)
    assert database.orders.count_documents({'userId': c['owned'][0]}) == 0
    assert database.payment_attempts.count_documents({'userId': c['owned'][0]}) == 0
    assert database.products.find_one({'_id': p['_id']})['stock'] == 10
    assert database.categories.find_one({'_id': p['categoryId']})['version'] == 1
    assert c['cart']()['version'] == 1 and len(c['cart']()['items']) == 1


def test_post_commit_url_failure_keeps_order_and_allows_same_checkout_replay(commerce, database, monkeypatch):
    from app.services.vnpay_provider import VnpayProvider
    c = commerce
    p = c['product']()
    c['add'](p)
    q = c['quote'](method='VNPAY').json['data']
    payload = {'cartVersion': 1, 'addressId': str(c['users'][0]['addresses'][0]['_id']), 'paymentMethod': 'VNPAY', 'quoteToken': q['quoteToken']}
    key = uuid4().hex
    original = VnpayProvider.payment_url
    def failure(*args, **kwargs):
        raise ServiceUnavailableError()
    monkeypatch.setattr(VnpayProvider, 'payment_url', failure)
    result = c['checkout'](payload, key).json['data']
    assert result['payment']['retryRequired'] and 'paymentUrl' not in result['payment']
    monkeypatch.setattr(VnpayProvider, 'payment_url', original)
    replay = c['checkout'](payload, key, expected=200).json['data']
    assert replay['order']['id'] == result['order']['id'] and replay['payment']['attemptId'] == result['payment']['attemptId']
    assert replay['payment']['paymentUrl'] and database.orders.count_documents({'userId': c['owned'][0]}) == 1
    assert database.products.find_one({'_id': p['_id']})['stock'] == 9


def test_amount_cap_checked_before_online_hold(commerce, database):
    c = commerce
    p = c['product'](price=1000000000, stock=20)
    c['add'](p, 11)
    c['quote'](method='VNPAY', expected=422)
    c['quote'](method='COD')
    assert database.products.find_one({'_id': p['_id']})['stock'] == 20 and database.orders.count_documents({'userId': c['owned'][0]}) == 0


def test_ipn_db_failure_99_and_retry_after_real_unknown_commit(payment, database, monkeypatch):
    from pymongo.synchronous.client_session import ClientSession
    p = payment
    callback = p['callback']()
    original = ClientSession.commit_transaction
    committed = []
    def lost(session):
        if not committed:
            original(session)
            committed.append(True)
        raise OperationFailure('injected private response loss', details={'errorLabels': ['UnknownTransactionCommitResult']})
    monkeypatch.setattr(ClientSession, 'commit_transaction', lost)
    p['ipn'](callback, '99')
    assert order(database, p)['paymentStatus'] == 'PAID'
    monkeypatch.setattr(ClientSession, 'commit_transaction', original)
    p['ipn'](callback, '02')
    assert order(database, p)['version'] == 2


def test_ipn_rollback_when_order_write_fails(payment, database, monkeypatch):
    p = payment
    def failure(*args, **kwargs):
        raise PyMongoError('injected ' + TEST_SECRET)
    monkeypatch.setattr(OrderRepository, 'patch_payment', failure)
    p['ipn'](p['callback'](), '99')
    assert order(database, p)['paymentStatus'] == 'PENDING' and stored_attempt(database, p)['status'] == 'PENDING'


def test_expiry_restore_fault_rolls_back_all_writes(payment, app, database, monkeypatch):
    p = payment
    p['age']()
    def failure(*args, **kwargs):
        return 0
    monkeypatch.setattr(ProductRepository, 'restore_stock', failure)
    with app.app_context():
        result = PaymentService().expire_due()
    assert result['failed'] == 1 and result['expired'] == 0
    assert order(database, p)['orderStatus'] == 'PENDING' and 'stockReleasedAt' not in order(database, p)
    assert stored_attempt(database, p)['status'] == 'PENDING' and database.products.find_one({'_id': p['product']['_id']})['stock'] == 9


def synchronize_first_write(monkeypatch, targets):
    barrier, state = Barrier(2), local()
    for cls, method in targets:
        original = getattr(cls, method)
        def wrapper(self, *args, _original=original, **kwargs):
            if not getattr(state, 'waited', False):
                state.waited = True
                barrier.wait(timeout=10)
            return _original(self, *args, **kwargs)
        monkeypatch.setattr(cls, method, wrapper)


def test_concurrent_duplicate_ipn_once(app, payment, database, monkeypatch):
    p = payment
    callback = p['callback']()
    synchronize_first_write(monkeypatch, [(PaymentAttemptRepository, 'patch')])
    def send():
        with app.test_client() as worker:
            return worker.get(PREFIX + '/payments/vnpay/ipn', query_string=callback).json['RspCode']
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(send) for _ in range(2)]
        results = [f.result(timeout=20) for f in futures]
    assert sorted(results) == ['00', '02']
    assert order(database, p)['version'] == stored_attempt(database, p)['version'] == 2
    assert database.products.find_one({'_id': p['product']['_id']})['stock'] == 9


def test_ipn_vs_cancel_race_safe_stock_outcome(app, payment, database, monkeypatch):
    p = payment
    callback = p['callback']()
    synchronize_first_write(monkeypatch, [(OrderRepository, 'patch_payment'), (OrderRepository, 'cancel')])
    def ipn():
        with app.test_client() as worker:
            return worker.get(PREFIX + '/payments/vnpay/ipn', query_string=callback).json['RspCode']
    def cancel():
        with app.test_client() as worker:
            return worker.post(PREFIX + '/orders/' + str(p['orderId']) + '/cancel', json={'expectedVersion': 1}, headers=p['c']['headers']['a']).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = pool.submit(ipn), pool.submit(cancel)
        assert first.result(timeout=20) == '00'
        cancelled = second.result(timeout=20)
    o = order(database, p)
    if cancelled == 200:
        assert o['orderStatus'] == 'CANCELLED' and o['paymentStatus'] == 'REVIEW_REQUIRED'
        assert database.products.find_one({'_id': p['product']['_id']})['stock'] == 10
    else:
        assert cancelled == 409 and o['orderStatus'] == 'CONFIRMED' and o['paymentStatus'] == 'PAID'
        assert database.products.find_one({'_id': p['product']['_id']})['stock'] == 9


def test_ipn_vs_expiry_race_once_restore(app, payment, database, monkeypatch):
    p = payment
    p['age']()
    callback = p['callback']()
    synchronize_first_write(monkeypatch, [(OrderRepository, 'patch_payment')])
    def ipn():
        with app.test_client() as worker:
            return worker.get(PREFIX + '/payments/vnpay/ipn', query_string=callback).json['RspCode']
    def expire():
        with app.app_context():
            return PaymentService().expire(p['orderId'])['orderStatus']
    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = pool.submit(ipn), pool.submit(expire)
        assert first.result(timeout=20) == '00' and second.result(timeout=20) == 'EXPIRED'
    assert order(database, p)['paymentStatus'] == 'REVIEW_REQUIRED'
    assert database.products.find_one({'_id': p['product']['_id']})['stock'] == 10


@pytest.mark.parametrize('same_key', [True, False])
def test_concurrent_attempt_creation_one_pending(app, payment, database, monkeypatch, same_key):
    p = payment
    p['ipn'](p['callback'](vnp_ResponseCode='24', vnp_TransactionStatus='02', vnp_TransactionNo='0'))
    synchronize_first_write(monkeypatch, [(PaymentAttemptRepository, 'insert')])
    key = uuid4().hex
    def create(value):
        with app.test_client() as worker:
            return worker.post(PREFIX + '/orders/' + str(p['orderId']) + '/payment-attempts',
                json={'expectedVersion': 2}, headers={**p['c']['headers']['a'], 'Idempotency-Key': key if same_key else key + str(value)}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(create, value) for value in range(2)]
        results = [f.result(timeout=20) for f in futures]
    assert sorted(results) == ([200, 201] if same_key else [201, 409])
    assert database.payment_attempts.count_documents({'orderId': p['orderId']}) == 2
    assert order(database, p)['version'] == 3


def test_unique_provider_transaction_number_cannot_pay_two_orders(payment, database):
    p = payment
    cb = p['callback']()
    p['ipn'](cb)
    another = p['checkout']()
    second_cb = p['callback'](another['attempt'], vnp_TransactionNo=cb['vnp_TransactionNo'])
    p['ipn'](second_cb, '99')
    assert database.orders.find_one({'_id': another['orderId']})['paymentStatus'] == 'PENDING'
    assert database.payment_attempts.find_one({'_id': another['attempt']['_id']})['status'] == 'PENDING'


def test_attempt_replay_after_paid_does_not_offer_paid_link(payment, database):
    p = payment
    p['ipn'](p['callback'](vnp_ResponseCode='24', vnp_TransactionStatus='02', vnp_TransactionNo='0'))
    key, payload = uuid4().hex, {'expectedVersion': 2}
    result = p['create_attempt'](payload, key).json['data']
    a = database.payment_attempts.find_one({'_id': ObjectId(result['attemptId'])})
    p['ipn'](p['callback'](a))
    replay = p['create_attempt'](payload, key, expected=200).json['data']
    assert replay['attemptId'] == result['attemptId'] and replay['attemptStatus'] == 'SUCCEEDED' and 'paymentUrl' not in replay


def test_no_lingering_failure_paid_date_when_success_has_no_date(payment, database):
    p = payment
    p['ipn'](p['callback'](vnp_ResponseCode='24', vnp_TransactionStatus='02', vnp_TransactionNo='0'))
    assert 'providerPaidAt' in stored_attempt(database, p)
    p['ipn'](p['callback'](vnp_PayDate=None))
    a = stored_attempt(database, p)
    assert 'providerPaidAt' not in a and order(database, p)['paidAt'] == a['verifiedAt']


def test_version_cap_callback_fails_retryably_without_partial_paid(payment, database):
    p = payment
    database.payment_attempts.update_one({'_id': p['attempt']['_id']}, {'$set': {'version': 2147483647}})
    p['ipn'](p['callback'](), '99')
    assert order(database, p)['paymentStatus'] == 'PENDING' and stored_attempt(database, p)['status'] == 'PENDING'


def test_no_credential_or_raw_payload_leak_in_error_logs(payment, client, database, monkeypatch, capsys):
    p = payment
    def failure(*args, **kwargs):
        raise PyMongoError('injected ' + TEST_SECRET)
    monkeypatch.setattr(OrderRepository, 'patch_payment', failure)
    response = p['ipn'](p['callback'](), '99')
    logs = capsys.readouterr().err
    assert TEST_SECRET not in logs and TEST_SECRET not in response.text
    assert 'vnp_SecureHash=' not in logs and 'vnp_Amount=' not in logs and 'injected' not in logs


def test_online_checkout_same_key_race_has_one_order_and_initial_attempt(app, commerce, database, monkeypatch):
    from app.repositories.category_repository import CategoryRepository
    c = commerce
    p = c['product']()
    c['add'](p)
    q = c['quote'](method='VNPAY').json['data']
    payload = {'cartVersion': 1, 'addressId': str(c['users'][0]['addresses'][0]['_id']), 'paymentMethod': 'VNPAY', 'quoteToken': q['quoteToken']}
    synchronize_first_write(monkeypatch, [(CategoryRepository, 'guard_active')])
    key = uuid4().hex
    def create():
        with app.test_client() as worker:
            return worker.post(PREFIX + '/orders', json=payload, headers={**c['headers']['a'], 'Idempotency-Key': key}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(create) for _ in range(2)]
        statuses = [f.result(timeout=20) for f in futures]
    assert sorted(statuses) == [200, 201]
    assert database.orders.count_documents({'userId': c['owned'][0]}) == database.payment_attempts.count_documents({'userId': c['owned'][0]}) == 1
    assert database.products.find_one({'_id': p['_id']})['stock'] == 9 and c['cart']()['version'] == 2


def test_missing_credentials_ipn_returns_protocol_99(app, client):
    app.config['VNP_HASH_SECRET'] = ''
    response = client.get(PREFIX + '/payments/vnpay/ipn')
    assert response.status_code == 200 and response.json['RspCode'] == '99'


def test_expiry_cli_once_uses_owned_test_database(payment, settings, database):
    import json
    import os
    import subprocess
    import sys
    from pathlib import Path
    p = payment
    p['age']()
    project = Path(__file__).resolve().parents[2]
    environment = {**os.environ, **{k: str(v) for k, v in settings.items()}, 'VNPAY_ENABLED': 'false'}
    result = subprocess.run([sys.executable, '-X', 'utf8', str(project / 'scripts/payment/expire_pending.py'), '--once'],
        cwd=project, env=environment, capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, 'Expiry CLI failed; no raw diagnostics exposed'
    assert json.loads(result.stdout.strip()) == {'scanned': 1, 'expired': 1, 'failed': 0}
    assert order(database, p)['orderStatus'] == 'EXPIRED' and stored_attempt(database, p)['status'] == 'EXPIRED'
    assert database.products.find_one({'_id': p['product']['_id']})['stock'] == 10


def test_expiry_cli_scan_failure_is_safe_and_nonzero(app, monkeypatch, capsys):
    import importlib.util
    import json
    import sys
    from pathlib import Path
    path = Path(__file__).resolve().parents[2] / 'scripts/payment/expire_pending.py'
    spec = importlib.util.spec_from_file_location('payment_expiry_cli', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, 'create_app', lambda: app)
    monkeypatch.setattr(sys, 'argv', ['expire_pending.py', '--once'])
    def failure(*args, **kwargs):
        raise PyMongoError('injected ' + TEST_SECRET)
    monkeypatch.setattr(OrderRepository, 'due_ids', failure)
    with pytest.raises(SystemExit) as error:
        module.main()
    assert error.value.code == 1
    captured = capsys.readouterr()
    assert json.loads(captured.out.strip())['failed'] == 1 and TEST_SECRET not in captured.err


@pytest.mark.parametrize('override', [
    {'VNP_TMN_CODE': ''}, {'VNP_TMN_CODE': 'BAD'}, {'VNP_HASH_SECRET': ''}, {'VNP_HASH_SECRET': 'REPLACE_ME'},
    {'VNP_HASH_SECRET': ' outer whitespace '}, {'VNP_IPN_URL': ''}, {'VNP_RETURN_URL': ''},
    {'VNP_PAYMENT_URL': 'https://pay.vnpay.vn/paymentv2/vpcpay.html'},
    {'VNP_PAYMENT_URL': 'http://sandbox.vnpayment.vn/paymentv2/vpcpay.html'},
    {'VNP_PAYMENT_URL': 'https://sandbox.vnpayment.vn/paymentv2/vpcpay.html?x=1'},
    {'VNP_RETURN_URL': 'javascript:alert(1)'}, {'VNP_RETURN_URL': 'http://external.test/return'},
    {'VNP_RETURN_URL': 'https://u:secret@external.test/return'}, {'VNP_IPN_URL': 'http://external.test/ipn'},
    {'VNP_IPN_URL': 'https://external.test/ipn?x=1'}, {'VNPAY_ENABLED': ''}, {'VNPAY_ENABLED': 1},
    {'PAYMENT_HOLD_MINUTES': 16}, {'PAYMENT_EXPIRY_POLL_SECONDS': 0},
])
def test_payment_config_fails_closed(settings, override):
    with pytest.raises(ConfigurationError) as error:
        load_config({**settings, **override})
    assert TEST_SECRET not in str(error.value)


def test_disabled_gate_preserves_cod_and_callback_processing(app, payment, database):
    p = payment
    app.config['VNPAY_ENABLED'] = False
    p['c']['add'](p['product'])
    p['c']['quote'](method='VNPAY', expected=503)
    p['c']['quote'](method='COD')
    assert database.products.find_one({'_id': p['product']['_id']})['stock'] == 9
    p['ipn'](p['callback']())
    assert order(database, p)['paymentStatus'] == 'PAID'
