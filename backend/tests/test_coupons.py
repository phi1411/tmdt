"""Campaign boundaries and real rs0 discounted checkout/payment/reporting."""
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlsplit, urlencode
from uuid import uuid4
import pytest
from bson import ObjectId
from bson.int64 import Int64
from pymongo.errors import WriteError
from tests.test_commerce import commerce
from app.services.coupon_service import allocate_discount, coupon_pricing
from app.repositories.dashboard_repository import DashboardRepository
from app.schemas.dashboard_schema import ReportWindow
from tests.test_payment import TEST_SECRET, signed
from app.services.vnpay_provider import provider_time


@pytest.fixture
def settings(settings):
    return {**settings, 'VNPAY_ENABLED': True, 'VNP_TMN_CODE': 'TEST0001', 'VNP_HASH_SECRET': TEST_SECRET,
            'VNP_PAYMENT_URL': 'https://sandbox.vnpayment.vn/paymentv2/vpcpay.html',
            'VNP_RETURN_URL': 'http://127.0.0.1:5001/api/v1/payments/vnpay/return',
            'VNP_IPN_URL': 'http://127.0.0.1:5001/api/v1/payments/vnpay/ipn'}


def apply(c, code='NOVA25', **kwargs):
    return c['call']('patch', '/cart/coupon', {'code': code, 'cartVersion': c['cart']()['version']}, **kwargs)


@pytest.mark.parametrize('subtotal,discount', [(0, 0), (499999, 0), (500000, 50000),
                                               (500001, 50000), (1000000000, 50000)])
def test_boundaries(subtotal, discount):
    pricing = coupon_pricing('NOVA25', subtotal)
    assert pricing['discount'] == discount
    assert bool(pricing['couponIssue']) == (subtotal < 500000)
    assert subtotal - discount >= 0


@pytest.mark.parametrize('code,subtotal,discount,eligible', [
    ('DEMO10',99999,0,False), ('DEMO10',100000,10000,True), ('DEMO10',160000,16000,True),
    ('DEMO10',999999,20000,True), ('DEMO15',299999,0,False), ('DEMO15',300000,40000,True),
    ('DEMO15',999999,40000,True),
])
def test_demo_code_thresholds_and_caps(code, subtotal, discount, eligible):
    result = coupon_pricing(code.lower(), subtotal)
    assert result['discount'] == discount
    assert (result['couponIssue'] is None) == eligible
    assert result['coupon']['code'] == code


@pytest.mark.parametrize('code,price,discount', [('DEMO10',160000,16000), ('DEMO15',420000,40000)])
def test_demo_codes_persist_snapshot_and_survive_cancel(commerce, database, code, price, discount):
    c=commerce; c['add'](c['product'](price=price)); apply(c,code)
    order=c['checkout']().json['data']['order']
    assert order['coupon']['code']==code and order['discount']==discount
    assert order['total']==price-discount+30000
    assert sum(i['discountAllocated'] for i in order['items'])==discount
    c['call']('post','/orders/'+order['id']+'/cancel',{'expectedVersion':order['version']})
    saved=database.orders.find_one({'_id':ObjectId(order['id'])})
    assert saved['coupon']['code']==code and saved['discount']==discount and saved['orderStatus']=='CANCELLED'


@pytest.mark.parametrize('values,discount', [([1, 1, 1], 2), ([250001, 249999], 50000),
                                          ([7, 11, 13], 30), ([1, 1, 1], 3)])
def test_allocation_exact_integer(values, discount):
    items = [{'lineTotal': Int64(value)} for value in values]
    allocate_discount(items, discount)
    assert sum(i['discountAllocated'] for i in items) == discount
    assert all(type(i['discountAllocated']) is Int64 and 0 <= i['discountAllocated'] <= i['lineTotal'] for i in items)


@pytest.mark.integration
def test_cart_eligibility_cas_removal_and_clear(commerce):
    c = commerce
    apply(c, expected=409)
    p = c['product'](price=250000)
    c['add'](p)
    apply(c, expected=422)
    apply(c, 'INVALID', expected=422)
    c['add'](p)
    old_version = c['cart']()['version']
    cart = apply(c, ' nova25 ').json['data']
    assert cart['discount'] == 50000 and cart['coupon']['code'] == 'NOVA25'
    c['call']('patch', '/cart/coupon', {'code': '', 'cartVersion': old_version}, expected=409)
    c['call']('patch', '/cart/items/' + cart['items'][0]['lineId'], {'quantity': 1, 'cartVersion': cart['version']})
    cart = c['cart']()
    assert cart['couponIssue'] and cart['discount'] == 0 and not cart['checkoutAllowed']
    c['quote'](expected=422)
    assert apply(c, '').json['data']['coupon'] is None
    c['add'](p)
    apply(c)
    c['call']('delete', '/cart', {'cartVersion': c['cart']()['version']}, expected=204)
    assert c['cart']()['coupon'] is None


@pytest.mark.parametrize('who,status', [('guest', 401), ('admin', 403), ('blocked', 401)])
def test_coupon_permissions(commerce, who, status):
    commerce['call']('patch', '/cart/coupon', {'code': 'NOVA25', 'cartVersion': 0}, who=who, expected=status)


@pytest.mark.parametrize('extra', [{'discount': 1000000}, {'percent': 100}, {'userId': 'x'},
                                  {'code': {'$ne': ''}}, {'code': 'NOVA25' * 10}, {'code': None}])
def test_coupon_payload_tampering(commerce, extra):
    commerce['call']('patch', '/cart/coupon', {'code': 'NOVA25', 'cartVersion': 0, **extra}, expected=422)


@pytest.mark.integration
def test_discounted_cod_snapshot_replay_cancel_and_validators(commerce, database):
    c = commerce
    p = c['product'](price=250001)
    p2 = c['product'](price=249999)
    c['add'](p); c['add'](p2)
    apply(c)
    payload = c['intent'](); key = uuid4().hex
    result = c['checkout'](payload, key).json['data']['order']
    assert (result['subtotal'], result['discount'], result['shippingFee'], result['total']) == (500000, 50000, 30000, 480000)
    assert [i['discountAllocated'] for i in result['items']] == [25000, 25000]
    assert c['cart']()['coupon'] is None
    assert c['checkout'](payload, key, expected=200).json['data']['order']['id'] == result['id']
    order = database.orders.find_one({'_id': ObjectId(result['id'])})
    assert type(order['discount']) is Int64 and type(order['coupon']['maxDiscount']) is Int64
    for update in ({'discount': Int64(50001)}, {'total': Int64(1)}, {'items.0.discountAllocated': Int64(1)}):
        with pytest.raises(WriteError):
            database.orders.update_one({'_id': order['_id']}, {'$set': update})
    database.products.update_one({'_id': p['_id']}, {'$set': {'price': Int64(300000)}})
    historical = c['call']('get', '/orders/' + result['id']).json['data']
    assert historical['items'][0]['priceAtPurchase'] == 250001 and historical['total'] == 480000
    c['call']('post', '/orders/' + result['id'] + '/cancel', {'expectedVersion': 1})
    assert database.products.find_one({'_id': p['_id']})['stock'] == p['stock']


@pytest.mark.integration
def test_quote_invalid_after_coupon_or_price_changes(commerce, database):
    c = commerce; p = c['product'](price=500000); c['add'](p)
    intent = c['intent'](); apply(c)
    c['checkout'](intent, expected=409)
    intent = c['intent']()
    database.products.update_one({'_id': p['_id']}, {'$set': {'price': Int64(600000)}})
    c['checkout'](intent, expected=409)
    intent = c['intent'](); apply(c, '')
    c['checkout'](intent, expected=409)


@pytest.mark.integration
def test_admin_revenue_all_reports_use_net_sales(commerce, database, app):
    c = commerce
    for price in (250001, 249999):
        c['add'](c['product'](price=price))
    apply(c)
    result = c['checkout']().json['data']['order']; oid = result['id']
    for version, action in enumerate(('confirm', 'ship', 'complete'), 1):
        c['call']('post', f'/admin/orders/{oid}/{action}', {'expectedVersion': version}, who='admin')
    now = datetime.now(timezone.utc)
    with app.app_context():
        repo = DashboardRepository()
        window = ReportWindow(now - timedelta(minutes=2), now + timedelta(minutes=2), 'day')
        reports = {}
        for name in ('sales-summary', 'revenue-day', 'revenue-month', 'top-products', 'category-revenue'):
            pipeline = repo.pipeline(name, window)
            pipeline[0]['$match']['_id'] = ObjectId(oid)
            reports[name] = list(database.orders.aggregate(pipeline))
        assert reports['sales-summary'][0]['totalRevenue'] == 450000
        for name in ('revenue-day', 'revenue-month', 'top-products', 'category-revenue'):
            assert sum(row['revenue'] for row in reports[name]) == 450000


@pytest.mark.integration
def test_vnpay_discounted_amount_and_authoritative_ipn(commerce, database, client):
    c = commerce; c['add'](c['product'](price=500000)); apply(c)
    quote = c['quote'](method='VNPAY').json['data']
    payload = {'cartVersion': quote['cartVersion'], 'addressId': str(c['users'][0]['addresses'][0]['_id']),
               'paymentMethod': 'VNPAY', 'quoteToken': quote['quoteToken']}
    result = c['checkout'](payload).json['data']
    query = parse_qs(urlsplit(result['payment']['paymentUrl']).query)
    assert query['vnp_Amount'] == ['48000000']
    attempt = database.payment_attempts.find_one({'orderId': ObjectId(result['order']['id'])})
    assert attempt['amount'] == 480000
    callback = {'vnp_TmnCode': 'TEST0001', 'vnp_Amount': '48000000', 'vnp_TxnRef': attempt['txnRef'],
                'vnp_OrderInfo': attempt['paymentRequest']['orderInfo'], 'vnp_ResponseCode': '00',
                'vnp_TransactionStatus': '00', 'vnp_BankCode': 'NCB', 'vnp_TransactionNo': '123456789',
                'vnp_PayDate': provider_time(datetime.now(timezone.utc))}
    wrong = client.get('/api/v1/payments/vnpay/ipn', query_string=signed({**callback, 'vnp_Amount': '53000000'})).json
    assert wrong['RspCode'] == '04'
    path = '/api/v1/payments/vnpay/ipn?' + urlencode(signed(callback))
    assert client.get(path).json['RspCode'] == '00'
    assert client.get(path).json['RspCode'] == '02'
    order = database.orders.find_one({'_id': attempt['orderId']})
    assert order['paymentStatus'] == 'PAID' and order['total'] == 480000 and order['discount'] == 50000
