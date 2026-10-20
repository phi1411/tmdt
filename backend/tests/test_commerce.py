"""PHASE05C: real rs0 API, atomic rollback, snapshots, owner isolation and races."""
import copy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier, Event, local
from uuid import uuid4
import pytest
from bson import ObjectId
from bson.int64 import Int64
from pymongo.errors import PyMongoError
from app.auth.tokens import create_access_token
from app.repositories.cart_repository import CartRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.services.checkout_service import read_quote, sign_quote

PREFIX = '/api/v1'
pytestmark = pytest.mark.integration


@pytest.fixture
def commerce(app, client, identities, database):
    users = [identities['customer'], copy.deepcopy(identities['customer'])]
    users[1].update(_id=ObjectId(), email=uuid4().hex + '@example.test')
    owned = [user['_id'] for user in users]
    cats, products = [], []
    try:
        for i, user in enumerate(users):
            user['phone'] = '0901234567'
            user['addresses'] = [{'_id': ObjectId(), 'receiverName': 'Khách hàng', 'phone': '0901234567',
                                  'addressLine': '123 Đường Test', 'province': 'Hồ Chí Minh'}]
            user['defaultAddressId'] = user['addresses'][0]['_id']
            if i == 0:
                database.users.replace_one({'_id': user['_id']}, user)
            else:
                database.users.insert_one(user)
        headers = {}
        with app.app_context():
            for key, user in [('a', users[0]), ('b', users[1]), ('admin', identities['admin']), ('blocked', identities['blocked'])]:
                if key == 'blocked':
                    user = {**user, 'status': 'ACTIVE'}
                headers[key] = {'Authorization': 'Bearer ' + create_access_token(user)}
        now = datetime.now(timezone.utc)

        def product(kind='ELECTRONICS', stock=10, price=10000000, attributes=None):
            category_id, product_id = ObjectId(), ObjectId()
            cats.append(category_id)
            products.append(product_id)
            database.categories.insert_one({'_id': category_id, 'schemaVersion': 1, 'version': 1,
                'createdAt': now, 'updatedAt': now, 'name': 'Danh mục test', 'slug': 'cat-' + uuid4().hex,
                'productType': kind, 'description': '', 'status': 'ACTIVE'})
            document = {'_id': product_id, 'schemaVersion': 1, 'version': 1, 'createdAt': now, 'updatedAt': now,
                'sku': 'TEST_' + uuid4().hex.upper(), 'name': 'Sản phẩm ban đầu', 'slug': 'prod-' + uuid4().hex,
                'categoryId': category_id, 'productType': kind, 'brand': '', 'description': '',
                'price': Int64(price), 'stock': stock, 'images': ['https://example.test/original.png'],
                'attributes': attributes or ({'sizes': ['S', 'M'], 'colors': ['Black', 'White']} if kind == 'FASHION' else {'material': 'Original'}),
                'nameNormalized': 'san pham ban dau', 'brandNormalized': '', 'status': 'ACTIVE'}
            database.products.insert_one(document)
            return document

        def call(method, path, payload=None, who='a', expected=200, extra=None, test_client=None):
            response = getattr(test_client or client, method)(PREFIX + path, json=payload,
                                                           headers={**headers.get(who, {}), **(extra or {})})
            assert response.status_code == expected, response.json
            if response.json:
                assert response.headers['X-Request-ID'] == response.json['meta']['requestId']
                assert not any(secret in response.get_data(as_text=True) for secret in
                               ('passwordHash', 'tokenVersion', 'checkoutKey', 'checkoutRequestHash', '$oid', '$date'))
            return response

        def cart(who='a'):
            return call('get', '/cart', who=who).json['data']

        def add(p, qty=1, selection=None, who='a', version=None, expected=200):
            version = cart(who)['version'] if version is None else version
            return call('post', '/cart/items', {'productId': str(p['_id']), 'quantity': qty,
                'selectedAttributes': selection or {}, 'cartVersion': version}, who, expected)

        def quote(who='a', method='COD', address=None, expected=200):
            address = address or str(users[0 if who == 'a' else 1]['addresses'][0]['_id'])
            return call('get', '/checkout/quote?addressId=' + address + '&paymentMethod=' + method,
                        who=who, expected=expected)

        def intent(who='a'):
            q = quote(who).json['data']
            return {'cartVersion': q['cartVersion'], 'addressId': str(users[0 if who == 'a' else 1]['addresses'][0]['_id']),
                    'paymentMethod': 'COD', 'quoteToken': q['quoteToken']}

        def checkout(payload=None, key=None, who='a', expected=201):
            return call('post', '/orders', payload or intent(who), who, expected,
                        extra={'Idempotency-Key': key or uuid4().hex})

        yield {'product': product, 'call': call, 'cart': cart, 'add': add, 'quote': quote, 'intent': intent,
               'checkout': checkout, 'users': users, 'headers': headers, 'owned': owned,
               'productIds': products, 'categoryIds': cats}
    finally:
        for collection in ('payment_attempts', 'orders', 'carts'):
            database[collection].delete_many({'userId': {'$in': owned}})
        database.products.delete_many({'_id': {'$in': products}})
        database.categories.delete_many({'_id': {'$in': cats}})
        database.users.delete_one({'_id': users[1]['_id']})


def test_cart_lifecycle_lazy_merge_update_delete_clear(commerce, database):
    c = commerce
    assert c['cart']() == {'version': 0, 'items': [], 'subtotal': 0, 'currency': 'VND', 'issues': [],
                          'checkoutAllowed': False, 'discount': 0, 'coupon': None, 'couponIssue': None}
    assert database.carts.count_documents({'userId': c['owned'][0]}) == 0
    c['call']('delete', '/cart', {'cartVersion': 0}, expected=204)
    p = c['product']()
    data = c['add'](p, 2).json['data']
    line = data['items'][0]
    assert len(line['lineId']) == 64 and data['version'] == 1
    assert line['name'] == p['name'] and line['slug'] == p['slug'] and line['stock'] == 10
    assert line['currentPrice'] == 10000000 and line['lineTotal'] == 20000000
    data = c['add'](p, 1).json['data']
    assert len(data['items']) == 1 and data['items'][0]['quantity'] == 3
    data = c['call']('patch', '/cart/items/' + line['lineId'], {'cartVersion': 2, 'quantity': 4}).json['data']
    assert data['version'] == 3 and data['subtotal'] == 40000000
    c['call']('delete', '/cart/items/' + line['lineId'], {'cartVersion': 3}, expected=204)
    assert c['cart']()['version'] == 4 and c['cart']()['items'] == []
    c['add'](p)
    c['call']('delete', '/cart', {'cartVersion': 5}, expected=204)
    stored = database.carts.find_one({'userId': c['owned'][0]})
    assert stored['version'] == 6 and stored['items'] == []
    assert not any(key in stored for key in ('price', 'subtotal', 'total'))


@pytest.mark.parametrize('quantity', [0, -1, 100, True, 1.5, '1', None])
def test_cart_quantity_validation(commerce, quantity):
    p = commerce['product']()
    commerce['call']('post', '/cart/items', {'productId': str(p['_id']), 'quantity': quantity, 'cartVersion': 0}, expected=422)


@pytest.mark.parametrize('field,value', [('price', 1), ('lineTotal', 1), ('userId', 'x'), ('selectedAttributes', {'$set': 'x'}),
                                        ('selectedAttributes', {'size': True}), ('cartVersion', True), ('cartVersion', -1)])
def test_cart_rejects_untrusted_fields(commerce, field, value):
    p = commerce['product']()
    commerce['call']('post', '/cart/items', {'productId': str(p['_id']), 'quantity': 1, 'cartVersion': 0, field: value}, expected=422)


def test_cart_shared_stock_selections_and_line_identity(commerce, database):
    c = commerce
    p = c['product']('FASHION', stock=3)
    c['add'](p, 2, {'color': 'Black', 'size': 'S'})
    data = c['add'](p, 1, {'size': 'S', 'color': 'Black'}).json['data']
    assert len(data['items']) == 1 and data['items'][0]['quantity'] == 3
    assert c['add'](p, 1, {'size': 'M', 'color': 'White'}, expected=409).json['error']['code'] == 'STOCK_CONFLICT'
    c['call']('patch', '/cart/items/' + data['items'][0]['lineId'], {'cartVersion': 2, 'quantity': 2})
    data = c['add'](p, 1, {'size': 'M', 'color': 'White'}).json['data']
    assert len(data['items']) == 2 and data['subtotal'] == 30000000
    assert database.products.find_one({'_id': p['_id']})['stock'] == 3
    order = c['checkout']().json['data']['order']
    assert len(order['items']) == 2 and database.products.find_one({'_id': p['_id']})['stock'] == 0
    assert database.products.find_one({'_id': p['_id']})['version'] == 2
    c['call']('post', '/orders/' + order['id'] + '/cancel', {'expectedVersion': 1})
    assert database.products.find_one({'_id': p['_id']})['stock'] == 3
    assert database.products.find_one({'_id': p['_id']})['version'] == 3


@pytest.mark.parametrize('selection', [{}, {'size': 'S'}, {'size': 'XXL', 'color': 'Black'}, {'size': 'S', 'color': 'Blue'}])
def test_cart_requires_current_fashion_selection(commerce, selection):
    commerce['add'](commerce['product']('FASHION'), selection=selection, expected=422)


@pytest.mark.parametrize('change', ['missing', 'inactive', 'archived', 'category', 'stock'])
def test_cart_add_and_get_invalid_product(commerce, database, change):
    c = commerce
    p = c['product']()
    c['add'](p)
    if change == 'missing':
        database.products.delete_one({'_id': p['_id']})
    elif change == 'category':
        database.categories.update_one({'_id': p['categoryId']}, {'$set': {'status': 'ARCHIVED'}})
    elif change == 'stock':
        database.products.update_one({'_id': p['_id']}, {'$set': {'stock': 0}})
    else:
        database.products.update_one({'_id': p['_id']}, {'$set': {'status': change.upper()}})
    data = c['cart']()
    assert data['items'][0]['available'] is False and data['subtotal'] == 0 and data['issues']
    c['add'](p, expected=404 if change == 'missing' else 409)
    c['quote'](expected=409)
    # Removing an invalid line remains possible.
    c['call']('delete', '/cart/items/' + data['items'][0]['lineId'], {'cartVersion': 1}, expected=204)


def test_cart_current_price_and_version_ownership(commerce, database):
    c = commerce
    p = c['product']()
    line = c['add'](p).json['data']['items'][0]
    assert c['cart']('b')['items'] == []
    c['call']('patch', '/cart/items/' + line['lineId'], {'cartVersion': 0, 'quantity': 2}, who='b', expected=404)
    c['call']('delete', '/cart/items/' + line['lineId'], {'cartVersion': 0}, who='b', expected=404)
    assert c['add'](p, version=0, expected=409).json['error']['code'] == 'CART_CHANGED'
    database.products.update_one({'_id': p['_id']}, {'$set': {'price': Int64(12000000)}})
    assert c['cart']()['items'][0]['currentPrice'] == 12000000
    assert c['quote']().json['data']['subtotal'] == 12000000
    stored = database.carts.find_one({'userId': c['owned'][0]})
    assert set(stored['items'][0]) == {'lineId', 'productId', 'quantity', 'selectedAttributes'}


def test_cart_limits_and_missing_lines(commerce, database):
    c = commerce
    p = c['product'](stock=1000)
    c['add'](p, 99)
    c['add'](p, expected=422)
    c['call']('patch', '/cart/items/' + 'f' * 64, {'cartVersion': 1, 'quantity': 1}, expected=404)
    # Valid 50-line fixture, unique selection identity enforced by application.
    p = c['product']('FASHION', stock=1000, attributes={'sizes': [str(i) for i in range(30)], 'colors': ['A', 'B']})
    from app.services.commerce_pricing import line_id
    lines = [{'lineId': line_id(p['_id'], {'size': str(i // 2), 'color': 'AB'[i % 2]}),
              'productId': p['_id'], 'quantity': 1, 'selectedAttributes': {'size': str(i // 2), 'color': 'AB'[i % 2]}}
             for i in range(50)]
    database.carts.update_one({'userId': c['owned'][0]}, {'$set': {'items': lines}})
    assert c['add'](p, selection={'size': '29', 'color': 'B'}, expected=409).json['error']['code'] == 'CART_LIMIT'


@pytest.mark.parametrize('method,path', [('get', '/cart'), ('post', '/cart/items'), ('patch', '/cart/items/' + 'a' * 64),
    ('delete', '/cart/items/' + 'a' * 64), ('delete', '/cart'), ('get', '/checkout/quote'), ('post', '/orders'),
    ('get', '/orders'), ('get', '/orders/' + 'a' * 24), ('post', '/orders/' + 'a' * 24 + '/cancel')])
def test_commerce_auth_matrix(commerce, method, path):
    for who, status in [('guest', 401), ('admin', 403), ('blocked', 401)]:
        commerce['call'](method, path, {}, who=who, expected=status)


def test_checkout_cod_snapshot_and_history(commerce, database):
    c = commerce
    p = c['product']()
    c['add'](p, 2)
    quote = c['quote']().json['data']
    assert quote['subtotal'] == 20000000 and quote['total'] == 20030000 and quote['shippingFee'] == 30000
    assert database.orders.count_documents({'userId': c['owned'][0]}) == 0
    response = c['checkout']()
    order = response.json['data']['order']
    assert response.headers['Location'] == PREFIX + '/orders/' + order['id']
    assert response.json['data']['payment'] == {'method': 'COD'}
    assert (order['orderStatus'], order['paymentStatus']) == ('PENDING', 'UNPAID')
    assert 'paidAt' not in order and 'paymentExpiresAt' not in order
    assert c['cart']()['version'] == 2 and c['cart']()['items'] == []
    assert database.products.find_one({'_id': p['_id']})['stock'] == 8
    assert database.categories.find_one({'_id': p['categoryId']})['version'] == 2
    assert database.payment_attempts.count_documents({'userId': c['owned'][0]}) == 0
    stored = database.orders.find_one({'_id': ObjectId(order['id'])})
    assert all(type(stored[field]) is Int64 for field in ('subtotal', 'shippingFee', 'discount', 'total'))
    assert type(stored['items'][0]['priceAtPurchase']) is Int64
    before = c['call']('get', '/orders/' + order['id']).json['data']
    database.products.update_one({'_id': p['_id']}, {'$set': {'price': Int64(12000000), 'name': 'Tên mới',
                                'attributes': {'material': 'New'}, 'images': [], 'status': 'ARCHIVED'}})
    database.categories.update_one({'_id': p['categoryId']}, {'$set': {'name': 'Danh mục mới', 'status': 'ARCHIVED'}})
    database.users.update_one({'_id': c['owned'][0]}, {'$set': {'name': 'Khách mới', 'phone': '0999999999', 'addresses': [], 'defaultAddressId': None}})
    after = c['call']('get', '/orders/' + order['id']).json['data']
    assert after == before
    assert after['items'][0]['priceAtPurchase'] == 10000000
    assert after['items'][0]['attributesSnapshot'] == {'material': 'Original'}
    assert 'id' not in after['shippingAddress'] and 'label' not in after['shippingAddress']
    assert c['call']('get', '/orders').json['meta']['total'] == 1
    assert c['call']('get', '/orders', who='b').json['data'] == []


@pytest.mark.parametrize('path', ['', '/cancel'])
def test_order_cross_owner_404(commerce, path):
    c = commerce
    c['add'](c['product']())
    order = c['checkout']().json['data']['order']
    c['call']('post' if path else 'get', '/orders/' + order['id'] + path,
              {'expectedVersion': 1} if path else None, who='b', expected=404)


def test_checkout_empty_address_and_phone_validation(commerce, database):
    c = commerce
    assert c['quote'](expected=409).json['error']['code'] == 'CART_EMPTY'
    c['add'](c['product']())
    c['quote'](address=str(ObjectId()), expected=404)
    c['quote'](address=str(c['users'][1]['addresses'][0]['_id']), expected=404)
    database.users.update_one({'_id': c['owned'][0]}, {'$set': {'phone': ''}})
    c['quote'](expected=422)


@pytest.mark.parametrize('change,code', [('price', 'PRICE_CHANGED'), ('address', 'QUOTE_CHANGED'),
    ('selection', 'PRICE_CHANGED'), ('stock', 'STOCK_CONFLICT'), ('inactive', 'PRODUCT_UNAVAILABLE'),
    ('category', 'PRODUCT_UNAVAILABLE'), ('cart', 'CART_CHANGED'), ('missing', 'PRODUCT_UNAVAILABLE')])
def test_confirmed_quote_revalidation(commerce, database, change, code):
    c = commerce
    p = c['product']('FASHION')
    c['add'](p, selection={'size': 'S', 'color': 'Black'})
    intent = c['intent']()
    if change == 'price':
        database.products.update_one({'_id': p['_id']}, {'$set': {'price': Int64(12000000)}})
    elif change == 'selection':
        database.products.update_one({'_id': p['_id']}, {'$set': {'attributes.sizes': ['M']}})
    elif change == 'address':
        database.users.update_one({'_id': c['owned'][0]}, {'$set': {'addresses.0.addressLine': 'Địa chỉ khác'}})
    elif change == 'stock':
        database.products.update_one({'_id': p['_id']}, {'$set': {'stock': 0}})
    elif change == 'inactive':
        database.products.update_one({'_id': p['_id']}, {'$set': {'status': 'INACTIVE'}})
    elif change == 'category':
        database.categories.update_one({'_id': p['categoryId']}, {'$set': {'status': 'ARCHIVED'}})
    elif change == 'missing':
        database.products.delete_one({'_id': p['_id']})
    else:
        c['add'](p, selection={'size': 'S', 'color': 'Black'})
    assert c['checkout'](intent, expected=409).json['error']['code'] == code
    assert database.orders.count_documents({'userId': c['owned'][0]}) == 0


def test_quote_fee_change_and_address_deleted(commerce, app, database):
    c = commerce
    c['add'](c['product']())
    intent = c['intent']()
    app.config['SHIPPING_FEE_VND'] = 35000
    assert c['checkout'](intent, expected=409).json['error']['code'] == 'PRICE_CHANGED'
    database.users.update_one({'_id': c['owned'][0]}, {'$set': {'addresses': [], 'defaultAddressId': None}})
    c['checkout'](intent, expected=404)


@pytest.mark.parametrize('mutation,expected', [('tamper', 422), ('expiry', 409), ('owner', 409), ('address', 409), ('version', 409)])
def test_quote_integrity_binding_and_expiry(commerce, app, mutation, expected):
    c = commerce
    c['add'](c['product']())
    intent = c['intent']()
    if mutation == 'tamper':
        intent['quoteToken'] = 'invalid'
    else:
        with app.app_context():
            claims = read_quote(intent['quoteToken'])
            if mutation == 'owner':
                claims['userId'] = str(c['owned'][1])
            elif mutation == 'address':
                claims['addressId'] = str(ObjectId())
            elif mutation == 'version':
                claims['cartVersion'] += 1
            expires = datetime.now(timezone.utc) + timedelta(seconds=-1 if mutation == 'expiry' else 300)
            intent['quoteToken'] = sign_quote(claims, expires)
    response = c['checkout'](intent, expected=expected)
    if mutation == 'expiry':
        assert response.json['error']['code'] == 'QUOTE_EXPIRED'


@pytest.mark.parametrize('field,value', [('total', 1), ('subtotal', 1), ('price', 1), ('userId', 'x'),
    ('orderStatus', 'COMPLETED'), ('paymentStatus', 'PAID'), ('shippingFee', 0), ('cartVersion', True),
    ('paymentMethod', 'CARD'), ('quoteToken', ''), ('addressId', {'$ne': None})])
def test_checkout_strict_inputs(commerce, field, value):
    c = commerce
    c['add'](c['product']())
    intent = c['intent']()
    intent[field] = value
    c['checkout'](intent, expected=422)


@pytest.mark.parametrize('key', [None, '', 'short', 'x' * 129, 'bad key value', 'khóa-12345'])
def test_checkout_idempotency_key_validation(commerce, key):
    c = commerce
    c['add'](c['product']())
    c['call']('post', '/orders', c['intent'](), extra={} if key is None else {'Idempotency-Key': key}, expected=422)


def test_idempotency_replay_before_cart_and_expiry(commerce, database, monkeypatch):
    c = commerce
    p = c['product']()
    c['add'](p)
    intent, key = c['intent'](), uuid4().hex
    first = c['checkout'](intent, key).json['data']
    def never_decode(token):
        raise AssertionError('Replay must not read quote or cart')
    monkeypatch.setattr('app.services.checkout_service.read_quote', never_decode)
    assert c['checkout'](intent, key, expected=200).json['data'] == first
    assert c['checkout']({**intent, 'cartVersion': 99}, key, expected=409).json['error']['code'] == 'IDEMPOTENCY_CONFLICT'
    assert database.orders.count_documents({'userId': c['owned'][0]}) == 1
    assert database.products.find_one({'_id': p['_id']})['stock'] == 9


def test_vnpay_deferred_without_hold_or_fake_payment(commerce, database):
    c = commerce
    p = c['product']()
    c['add'](p)
    assert c['quote'](method='VNPAY', expected=503).json['error']['code'] == 'PAYMENT_UNAVAILABLE'
    intent = c['intent']()
    intent['paymentMethod'] = 'VNPAY'
    c['checkout'](intent, expected=503)
    assert database.products.find_one({'_id': p['_id']})['stock'] == 10
    assert c['cart']()['version'] == 1
    assert database.orders.count_documents({'userId': c['owned'][0]}) == 0
    assert database.payment_attempts.count_documents({'userId': c['owned'][0]}) == 0


@pytest.mark.parametrize('failure', ['second_product', 'insert', 'cart_clear'])
def test_checkout_transaction_rollback(commerce, database, monkeypatch, failure):
    c = commerce
    ps = [c['product'](), c['product']()]
    for p in ps:
        c['add'](p)
    intent = c['intent']()
    before = {p['_id']: database.products.find_one({'_id': p['_id']}) for p in ps}
    cats = {p['categoryId']: database.categories.find_one({'_id': p['categoryId']}) for p in ps}
    cart = database.carts.find_one({'userId': c['owned'][0]})
    if failure == 'second_product':
        original = ProductRepository.decrement_stock
        calls = []
        def fail(self, p, qty, now, session):
            calls.append(p['_id'])
            return 0 if len(calls) == 2 else original(self, p, qty, now, session)
        monkeypatch.setattr(ProductRepository, 'decrement_stock', fail)
    elif failure == 'insert':
        def fail(*args, **kwargs):
            raise PyMongoError('Injected DB failure')
        monkeypatch.setattr(OrderRepository, 'insert', fail)
    else:
        monkeypatch.setattr(CartRepository, 'replace_items', lambda *a, **kw: None)
    c['checkout'](intent, expected=503 if failure == 'insert' else 409)
    assert database.orders.count_documents({'userId': c['owned'][0]}) == 0
    assert database.carts.find_one({'userId': c['owned'][0]}) == cart
    assert all(database.products.find_one({'_id': key}) == value for key, value in before.items())
    assert all(database.categories.find_one({'_id': key}) == value for key, value in cats.items())


def concurrent_requests(app, requests):
    with ThreadPoolExecutor(max_workers=len(requests)) as pool:
        def run(args):
            method, path, payload, headers = args
            with app.test_client() as client:
                return getattr(client, method)(PREFIX + path, json=payload, headers=headers)
        return list(pool.map(run, requests))


def barrier_before(monkeypatch, cls, method):
    original, barrier, state = getattr(cls, method), Barrier(2), local()
    def wrapped(*args, **kwargs):
        if not getattr(state, 'entered', False):
            state.entered = True
            barrier.wait(timeout=10)
        return original(*args, **kwargs)
    monkeypatch.setattr(cls, method, wrapped)


@pytest.mark.parametrize('existing', [False, True])
def test_concurrent_cart_cas_and_lazy_create(commerce, app, monkeypatch, database, existing):
    c = commerce
    p = c['product']()
    if existing:
        c['add'](p)
        barrier_before(monkeypatch, CartRepository, 'replace_items')
    else:
        barrier_before(monkeypatch, CartRepository, 'create')
    body = {'productId': str(p['_id']), 'quantity': 1, 'cartVersion': int(existing)}
    responses = concurrent_requests(app, [('post', '/cart/items', body, c['headers']['a'])] * 2)
    assert sorted(r.status_code for r in responses) == [200, 409]
    assert next(r for r in responses if r.status_code == 409).json['error']['code'] == 'CART_CHANGED'
    assert database.carts.count_documents({'userId': c['owned'][0]}) == 1
    assert c['cart']()['items'][0]['quantity'] == 1 + int(existing)


def test_stock_one_concurrent_checkout(commerce, app, monkeypatch, database):
    c = commerce
    p = c['product'](stock=1)
    c['add'](p, who='a')
    c['add'](p, who='b')
    intents = [c['intent'](who) for who in ('a', 'b')]
    barrier_before(monkeypatch, CategoryRepository, 'guard_active')
    responses = concurrent_requests(app, [('post', '/orders', intent,
        {**c['headers'][who], 'Idempotency-Key': uuid4().hex}) for who, intent in zip(('a', 'b'), intents)])
    assert sorted(r.status_code for r in responses) == [201, 409]
    assert next(r for r in responses if r.status_code == 409).json['error']['code'] == 'STOCK_CONFLICT'
    assert database.products.find_one({'_id': p['_id']})['stock'] == 0
    assert database.orders.count_documents({'userId': {'$in': c['owned']}}) == 1
    assert sum(len(database.carts.find_one({'userId': user_id})['items']) for user_id in c['owned']) == 1


def test_duplicate_checkout_race(commerce, app, monkeypatch, database):
    c = commerce
    p = c['product']()
    c['add'](p)
    intent, key = c['intent'](), uuid4().hex
    barrier_before(monkeypatch, CategoryRepository, 'guard_active')
    responses = concurrent_requests(app, [('post', '/orders', intent,
                                          {**c['headers']['a'], 'Idempotency-Key': key})] * 2)
    assert sorted(r.status_code for r in responses) == [200, 201]
    assert responses[0].json['data']['order']['id'] == responses[1].json['data']['order']['id']
    assert database.products.find_one({'_id': p['_id']})['stock'] == 9
    assert database.orders.count_documents({'userId': c['owned'][0]}) == 1


def test_category_archive_wins_against_checkout(commerce, app, database, monkeypatch):
    c = commerce
    p = c['product']()
    c['add'](p)
    intent = c['intent']()
    original, ready, resume, state = CategoryRepository.guard_active, Event(), Event(), local()
    def pause(*args, **kwargs):
        if not getattr(state, 'entered', False):
            state.entered = True
            ready.set()
            assert resume.wait(timeout=10)
        return original(*args, **kwargs)
    monkeypatch.setattr(CategoryRepository, 'guard_active', pause)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(concurrent_requests, app, [('post', '/orders', intent,
                              {**c['headers']['a'], 'Idempotency-Key': uuid4().hex})])
        try:
            assert ready.wait(timeout=10)
            c['call']('patch', '/admin/categories/' + str(p['categoryId']),
                      {'status': 'ARCHIVED', 'expectedVersion': 1}, who='admin')
        finally:
            resume.set()
        response = future.result(timeout=15)[0]
    assert response.status_code == 409
    assert database.products.find_one({'_id': p['_id']})['stock'] == 10
    assert database.orders.count_documents({'userId': c['owned'][0]}) == 0


def test_cancel_once_replay_stale_and_archived_product(commerce, database):
    c = commerce
    p = c['product']()
    c['add'](p, 2)
    order = c['checkout']().json['data']['order']
    path = '/orders/' + order['id'] + '/cancel'
    assert c['call']('post', path, {'expectedVersion': 2}, expected=409).json['error']['code'] == 'ORDER_CHANGED'
    database.products.update_one({'_id': p['_id']}, {'$set': {'status': 'ARCHIVED'}})
    cancelled = c['call']('post', path, {'expectedVersion': 1}).json['data']
    assert cancelled['orderStatus'] == 'CANCELLED' and cancelled['version'] == 2
    assert cancelled['cancelledAt'] == cancelled['stockReleasedAt']
    assert c['call']('post', path, {'expectedVersion': 1}).json['data'] == cancelled
    assert database.products.find_one({'_id': p['_id']})['stock'] == 10
    assert database.products.find_one({'_id': p['_id']})['version'] == 3


@pytest.mark.parametrize('state', ['SHIPPING', 'COMPLETED', 'PAID', 'REVIEW_REQUIRED', 'EXPIRED'])
def test_cancel_invalid_transition(commerce, database, state):
    c = commerce
    p = c['product']()
    c['add'](p)
    order = c['checkout']().json['data']['order']
    changes = {'orderStatus': state}
    now = datetime.now(timezone.utc)
    if state == 'COMPLETED':
        changes.update(paymentStatus='PAID', completedAt=now, paidAt=now)
    elif state in {'PAID', 'REVIEW_REQUIRED'}:
        changes = {'orderStatus': 'CONFIRMED' if state == 'PAID' else 'CANCELLED', 'paymentMethod': 'VNPAY',
                   'paymentStatus': state, 'paymentExpiresAt': now + timedelta(minutes=15), 'paidAt': now}
        if state == 'REVIEW_REQUIRED':
            changes.update(paymentReviewRequired=True, cancelledAt=now, stockReleasedAt=now)
    elif state == 'EXPIRED':
        changes.update(paymentMethod='VNPAY', paymentStatus='FAILED', paymentExpiresAt=now,
                       expiredAt=now, stockReleasedAt=now)
    database.orders.update_one({'_id': ObjectId(order['id'])}, {'$set': changes})
    c['call']('post', '/orders/' + order['id'] + '/cancel', {'expectedVersion': 1}, expected=409 if state != 'REVIEW_REQUIRED' else 200)
    assert database.products.find_one({'_id': p['_id']})['stock'] == 9


def test_cancel_concurrent_once(commerce, app, monkeypatch, database):
    c = commerce
    p = c['product']()
    c['add'](p)
    order = c['checkout']().json['data']['order']
    barrier_before(monkeypatch, OrderRepository, 'cancel')
    responses = concurrent_requests(app, [('post', '/orders/' + order['id'] + '/cancel',
                                          {'expectedVersion': 1}, c['headers']['a'])] * 2)
    assert [r.status_code for r in responses] == [200, 200]
    assert responses[0].json['data'] == responses[1].json['data']
    assert database.products.find_one({'_id': p['_id']})['stock'] == 10
    assert database.orders.find_one({'_id': ObjectId(order['id'])})['version'] == 2


def test_cancel_missing_product_rolls_back(commerce, database):
    c = commerce
    p = c['product']()
    c['add'](p)
    order = c['checkout']().json['data']['order']
    database.products.delete_one({'_id': p['_id']})
    response = c['call']('post', '/orders/' + order['id'] + '/cancel', {'expectedVersion': 1}, expected=409)
    assert response.json['error']['code'] == 'STOCK_RESTORE_FAILED'
    current = database.orders.find_one({'_id': ObjectId(order['id'])})
    assert current['orderStatus'] == 'PENDING' and 'stockReleasedAt' not in current


@pytest.mark.parametrize('query', ['status=BAD', 'from=2026-01-01', 'from=2026-01-01T00:00:00%2B07:00',
    'from=2026-02-01T00:00:00Z&to=2026-01-01T00:00:00Z', 'pageSize=101', 'userId=x', 'status=PENDING&status=SHIPPING', 'sort=price_asc'])
def test_history_filter_validation(commerce, query):
    commerce['call']('get', '/orders?' + query, expected=422)


def test_history_dates_sort_pagination(commerce, database):
    c = commerce
    p = c['product']()
    orders = []
    for _ in range(3):
        c['add'](p)
        orders.append(c['checkout']().json['data']['order'])
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for i, order in enumerate(orders):
        database.orders.update_one({'_id': ObjectId(order['id'])}, {'$set': {'createdAt': start + timedelta(days=i)}})
    data = c['call']('get', '/orders?from=2026-01-01T00:00:00Z&to=2026-01-03T00:00:00Z&pageSize=1').json
    assert data['meta']['total'] == 2 and data['meta']['totalPages'] == 2 and data['data'][0]['id'] == orders[1]['id']
    assert 'shippingAddress' not in data['data'][0]
    data = c['call']('get', '/orders?from=2026-01-01T00:00:00Z&to=2026-01-03T00:00:00Z&pageSize=1&page=2').json
    assert data['data'][0]['id'] == orders[0]['id']
    assert c['call']('get', '/orders?status=COMPLETED').json['meta']['total'] == 0


def test_snapshot_read_has_no_live_dependency(commerce, database, monkeypatch):
    c = commerce
    p = c['product']()
    c['add'](p)
    order = c['checkout']().json['data']['order']
    database.products.delete_one({'_id': p['_id']})
    database.categories.delete_one({'_id': p['categoryId']})
    def forbidden(*args, **kwargs):
        raise AssertionError('Order history must not read live Product/Category')
    monkeypatch.setattr(ProductRepository, 'find_many', forbidden)
    monkeypatch.setattr(CategoryRepository, 'find', forbidden)
    assert c['call']('get', '/orders/' + order['id']).json['data'] == order
    assert c['call']('get', '/orders').json['meta']['total'] == 1


def test_cancel_confirmed_online_invalidates_pending_attempt(commerce, database):
    c = commerce
    p = c['product']()
    c['add'](p)
    order = c['checkout']().json['data']['order']
    order_id, now = ObjectId(order['id']), datetime.now(timezone.utc)
    # Canonical online fixtures exercise cancel dependency without a fake gateway.
    database.orders.update_one({'_id': order_id}, {'$set': {'paymentMethod': 'VNPAY', 'paymentStatus': 'PENDING',
                                                          'paymentExpiresAt': now + timedelta(minutes=15)}})
    original = database.client.ecommerce_dev.payment_attempts.find_one({'status': 'PENDING'})
    attempt = copy.deepcopy(original)
    assert attempt
    attempt.update(_id=ObjectId(), orderId=order_id, userId=c['owned'][0], txnRef=uuid4().hex,
                   amount=Int64(order['total']), attemptKey=uuid4().hex, version=1)
    attempt.pop('providerTransactionNo', None)
    attempt['paymentRequest'].update(txnRef=attempt['txnRef'], amountScaled=Int64(order['total'] * 100))
    database.payment_attempts.insert_one(attempt)
    changed = c['call']('post', '/orders/' + order['id'] + '/cancel', {'expectedVersion': 1}).json['data']
    assert changed['paymentStatus'] == 'FAILED' and changed['orderStatus'] == 'CANCELLED'
    current = database.payment_attempts.find_one({'_id': attempt['_id']})
    assert current['status'] == 'EXPIRED' and 'expiredAt' in current and current['version'] == 2
    assert database.products.find_one({'_id': p['_id']})['stock'] == 10


def test_cancel_confirmed_cod_and_review_flag_guard(commerce, database):
    c = commerce
    p = c['product']()
    c['add'](p)
    order = c['checkout']().json['data']['order']
    database.orders.update_one({'_id': ObjectId(order['id'])}, {'$set': {'orderStatus': 'CONFIRMED'}})
    assert c['call']('post', '/orders/' + order['id'] + '/cancel', {'expectedVersion': 1}).json['data']['orderStatus'] == 'CANCELLED'
    c['add'](p)
    order = c['checkout']().json['data']['order']
    now = datetime.now(timezone.utc)
    database.orders.update_one({'_id': ObjectId(order['id'])}, {'$set': {
        'paymentMethod': 'VNPAY', 'orderStatus': 'CONFIRMED', 'paymentStatus': 'PAID', 'paidAt': now,
        'paymentReviewRequired': True, 'paymentExpiresAt': now + timedelta(minutes=15)}})
    assert c['call']('post', '/orders/' + order['id'] + '/cancel', {'expectedVersion': 1}, expected=409).json['error']['code'] == 'INVALID_TRANSITION'


def test_unknown_commit_response_lost_then_replay(commerce, database, monkeypatch):
    from pymongo.synchronous.client_session import ClientSession
    from pymongo.errors import OperationFailure
    c = commerce
    p = c['product']()
    c['add'](p)
    intent, key = c['intent'](), uuid4().hex
    original, committed = ClientSession.commit_transaction, []
    def lost(session):
        if not committed:
            original(session)
            committed.append(True)
        raise OperationFailure('Injected lost commit response', details={'errorLabels': ['UnknownTransactionCommitResult']})
    monkeypatch.setattr(ClientSession, 'commit_transaction', lost)
    c['checkout'](intent, key, expected=503)
    result = c['checkout'](intent, key, expected=200).json['data']['order']
    assert result['orderStatus'] == 'PENDING'
    assert database.orders.count_documents({'userId': c['owned'][0]}) == 1
    assert database.products.find_one({'_id': p['_id']})['stock'] == 9


@pytest.mark.parametrize('override', [{'SHIPPING_FEE_VND': ''}, {'SHIPPING_FEE_VND': -1},
    {'SHIPPING_FEE_VND': True}, {'SHIPPING_FEE_VND': 1000001}, {'QUOTE_TTL_SECONDS': ''},
    {'QUOTE_TTL_SECONDS': 0}, {'QUOTE_TTL_SECONDS': True}, {'VNPAY_ENABLED': 'true'}, {'VNPAY_ENABLED': ''}])
def test_commerce_config_fails_closed(settings, override):
    from app.config import load_config, ConfigurationError
    with pytest.raises(ConfigurationError):
        load_config({**settings, **override})


@pytest.mark.parametrize('price', [12000000, 8000000])
def test_cart_price_is_quote_only_new_confirmation_uses_current_price(commerce, database, price):
    c = commerce
    p = c['product']()
    c['add'](p)
    old = c['intent']()
    database.products.update_one({'_id': p['_id']}, {'$set': {'price': Int64(price)}, '$inc': {'version': 1}})
    assert c['checkout'](old, expected=409).json['error']['code'] == 'PRICE_CHANGED'
    order = c['checkout']().json['data']['order']
    assert order['items'][0]['priceAtPurchase'] == price and order['total'] == price + 30000
    c['call']('patch', '/admin/products/' + str(p['_id']), {'price': 1, 'expectedVersion': 2}, who='admin', expected=409)


@pytest.mark.parametrize('body', [{}, {'expectedVersion': True}, {'expectedVersion': 0},
                                {'expectedVersion': 1, 'paymentStatus': 'PAID'}])
def test_cancel_input_allowlist(commerce, body):
    commerce['call']('post', '/orders/' + str(ObjectId()) + '/cancel', body, expected=422)


@pytest.mark.parametrize('failure', ['second_restore', 'attempt_invalidation'])
def test_cancel_rollback_no_partial_stock_restore(commerce, database, monkeypatch, failure):
    from app.repositories.payment_attempt_repository import PaymentAttemptRepository
    c = commerce
    ps = [c['product'](), c['product']()]
    for p in ps:
        c['add'](p)
    order = c['checkout']().json['data']['order']
    if failure == 'second_restore':
        original, calls = ProductRepository.restore_stock, []
        def fail(*args, **kwargs):
            calls.append(True)
            return 0 if len(calls) == 2 else original(*args, **kwargs)
        monkeypatch.setattr(ProductRepository, 'restore_stock', fail)
    else:
        def fail(*args, **kwargs):
            raise PyMongoError('Injected invalidation failure')
        monkeypatch.setattr(PaymentAttemptRepository, 'invalidate_pending', fail)
    c['call']('post', '/orders/' + order['id'] + '/cancel', {'expectedVersion': 1}, expected=409 if failure == 'second_restore' else 503)
    assert all(database.products.find_one({'_id': p['_id']})['stock'] == 9 for p in ps)
    current = database.orders.find_one({'_id': ObjectId(order['id'])})
    assert current['orderStatus'] == 'PENDING' and current['version'] == 1 and 'stockReleasedAt' not in current


@pytest.mark.parametrize('path,expected', [('/cart?userId=x', 422), ('/checkout/quote?addressId=bad&paymentMethod=COD', 400),
    ('/checkout/quote?addressId=aaaaaaaaaaaaaaaaaaaaaaaa&paymentMethod=CARD', 422), ('/orders/bad', 400),
    ('/orders/aaaaaaaaaaaaaaaaaaaaaaaa', 404), ('/orders?from=bad', 422)])
def test_commerce_ids_and_query_allowlists(commerce, path, expected):
    commerce['call']('get', path, expected=expected)
