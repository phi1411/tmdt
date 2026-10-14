"""07C local fixtures via existing APIs; no seed edits/reset/schema/application change."""
import argparse
import hashlib
import json
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4
from bson import ObjectId, json_util
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'backend'), str(ROOT / 'scripts/backend')]
from app import create_app
from verify_auth_users import NAMES, fingerprint

LOCAL = ROOT / '.local/phase07c'
STATE = LOCAL / 'fixture.json'
EVIDENCE = ROOT / 'database/evidence'
BASE = 'http://127.0.0.1:5001/api/v1'
EMAIL = 'defense07c@example.test'
PRODUCTS = [
    {'sku': 'DEFENSE-07C-ELE', 'name': 'Điện thoại bảo vệ 07C', 'slug': 'defense-07c-dien-thoai',
     'productType': 'ELECTRONICS', 'price': 10000000, 'attributes': {'ram': '8GB', 'storage': '256GB', 'chip': 'Demo CPU 07C'},
     'images': ['https://cdn.dummyjson.com/product-images/smartphones/iphone-5s/1.webp', 'https://cdn.dummyjson.com/product-images/smartphones/iphone-5s/2.webp']},
    {'sku': 'DEFENSE-07C-FAS', 'name': 'Áo thun bảo vệ 07C', 'slug': 'defense-07c-ao-thun',
     'productType': 'FASHION', 'price': 200000, 'attributes': {'sizes': ['M', 'L'], 'colors': ['Black'], 'material': 'Cotton'},
     'images': ['https://cdn.dummyjson.com/product-images/mens-shirts/gigabyte-aorus-men-tshirt/1.webp', 'https://cdn.dummyjson.com/product-images/mens-shirts/gigabyte-aorus-men-tshirt/2.webp']},
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['prepare', 'rehearse', 'restore', 'check'])
    args = parser.parse_args()
    app = create_app()
    db = app.extensions['mongo'].database
    checks = []
    LOCAL.mkdir(parents=True, exist_ok=True)
    state = json.loads(STATE.read_text(encoding='utf-8')) if STATE.exists() else None

    def save():
        STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding='utf-8')

    def http(label, method, path, payload=None, token=None, key=None):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        if key:
            headers['Idempotency-Key'] = key
        raw = json.dumps(payload).encode() if payload is not None else None
        try:
            response = urlopen(Request(BASE + path, data=raw, headers=headers, method=method), timeout=15)
        except HTTPError as error:
            response = error
        with response:
            body = json.loads(response.read()) if response.status != 204 else None
            if response.status >= 400:
                raise RuntimeError(label + ': HTTP ' + str(response.status) + ' ' + body.get('error', {}).get('code', 'ERROR'))
            checks.append({'label': label, 'status': response.status})
            return body['data'] if body else None

    def login(email, password):
        return http('login ' + email, 'POST', '/auth/login', {'email': email, 'password': password})['accessToken']

    def original_digest():
        ids = {'users': [ObjectId(state['userId'])] if state.get('userId') else [],
               'categories': [ObjectId(v) for v in state['categories'].values()],
               'products': [ObjectId(v['id']) for v in state['products']]}
        snapshot = {'counts': {}, 'documents': {}, 'collections': list(db.list_collections()),
                    'indexes': {n: list(db[n].list_indexes()) for n in NAMES}}
        for name in NAMES:
            query = {'_id': {'$nin': ids[name]}} if name in ids else (
                {'userId': {'$ne': ObjectId(state['userId'])}} if state.get('userId') else {})
            docs = list(db[name].find(query).sort('_id', 1))
            snapshot['documents'][name] = docs
            snapshot['counts'][name] = len(docs)
        return hashlib.sha256(json_util.dumps(snapshot, json_options=json_util.CANONICAL_JSON_OPTIONS,
                                               sort_keys=True).encode()).hexdigest()

    def verify_owned():
        assert state['project'] == str(ROOT) and state['database'] == db.name
        user = db.users.find_one({'_id': ObjectId(state['userId']), 'email': EMAIL, 'role': 'CUSTOMER'})
        assert user and user['status'] == 'ACTIVE', 'Fixture Customer missing/changed'
        for kind, category_id in state['categories'].items():
            assert db.categories.find_one({'_id': ObjectId(category_id), 'productType': kind, 'status': 'ACTIVE'}), 'Fixture Category unavailable'
        for p in state['products']:
            current = db.products.find_one({'_id': ObjectId(p['id']), 'sku': p['sku'],
                'categoryId': ObjectId(state['categories'][p['productType']])})
            assert current and current['status'] == 'ACTIVE', 'Fixture Product missing/changed'

    try:
        hello = db.client.admin.command('hello')
        assert db.name == 'ecommerce_dev' and hello.get('setName') == 'rs0' and hello['isWritablePrimary']
        assert db.client.address == ('localhost', 27017), 'Unexpected database endpoint'
        http('backend health', 'GET', '/health')
        seed_password = dotenv_values(ROOT / '.env', interpolate=False).get('SEED_DEMO_PASSWORD')
        assert seed_password, 'Private seed demo password missing; do not reseed live data'
        admin = login('admin@example.test', seed_password)
        if args.mode == 'prepare':
            if state is None:
                assert db.users.find_one({'email': EMAIL}) is None, 'Unowned demo email exists'
                assert not db.products.count_documents({'sku': {'$in': [p['sku'] for p in PRODUCTS]}})
                state = {'project': str(ROOT), 'database': db.name, 'before': fingerprint(db),
                         'customerPassword': secrets.token_urlsafe(24), 'categories': {}, 'products': [], 'rehearsalOrders': []}
                save()
            if not state.get('userId'):
                registered = http('register dedicated Customer', 'POST', '/auth/register', {
                    'name': 'Khách bảo vệ 07C', 'email': EMAIL, 'password': state['customerPassword']})['user']
                state['userId'] = registered['id']
                save()
            customer = login(EMAIL, state['customerPassword'])
            profile = http('fixture profile', 'GET', '/users/me', token=customer)
            if not profile.get('phone'):
                profile = http('fixture phone', 'PATCH', '/users/me', {'phone': '0901234567', 'expectedVersion': profile['version']}, customer)
            if not profile['addresses']:
                address = http('fixture address', 'POST', '/users/me/addresses', {
                    'receiverName': 'Khách bảo vệ 07C', 'phone': '0901234567', 'addressLine': '123 Đường Demo',
                    'province': 'Hồ Chí Minh', 'expectedVersion': profile['version']}, customer)
                state['addressId'] = address['address']['id']
            else:
                state['addressId'] = profile['addresses'][0]['id']
            save()
            for spec in PRODUCTS:
                kind = spec['productType']
                if kind not in state['categories']:
                    category = http('create isolated category', 'POST', '/admin/categories', {
                        'name': 'Demo bảo vệ 07C ' + ('Điện tử' if kind == 'ELECTRONICS' else 'Thời trang'),
                        'slug': 'defense-07c-' + kind.lower().replace('_', '-'), 'productType': kind,
                        'description': 'Fixture riêng cho bảo vệ; không thuộc seed180'}, admin)
                    state['categories'][kind] = category['id']
                    save()
                if not any(p['sku'] == spec['sku'] for p in state['products']):
                    created = http('create isolated product', 'POST', '/admin/products', {
                        **spec, 'categoryId': state['categories'][kind], 'brand': 'NovaMart Demo',
                        'description': 'Fixture bảo vệ; giá/spec mô phỏng, không giao dịch tiền thật.',
                        'stock': 20, 'images': spec.get('images', []), 'status': 'ACTIVE'}, admin)
                    state['products'].append({**spec, 'id': created['id']})
                    save()
            (LOCAL / 'demo-credentials.md').write_text('# Chỉ local development; không commit/chia sẻ màn hình\n\n'
                + f'Customer: {EMAIL}\nPassword: `{state["customerPassword"]}`\n\n'
                + f'Admin: admin@example.test\nPassword: `{seed_password}`\n', encoding='utf-8')
        assert state and state.get('userId') and len(state['products']) == 2, 'Run prepare first'
        verify_owned()
        customer = login(EMAIL, state['customerPassword'])
        if args.mode == 'check':
            user = db.users.find_one({'_id': ObjectId(state['userId'])})
            assert user.get('phone') and any(str(a['_id']) == state['addressId'] for a in user['addresses'])
            for p in state['products']:
                current = db.products.find_one({'_id': ObjectId(p['id'])})
                assert current['price'] == p['price'] and current['stock'] >= 1, 'Restore fixture price/check stock before demo'
            cart = db.carts.find_one({'userId': ObjectId(state['userId'])})
            assert not cart or not cart['items'], 'Clear only the owned demo Cart before readiness check'

        def restore():
            for order in db.orders.find({'userId': ObjectId(state['userId']), 'paymentMethod': 'COD',
                                         'orderStatus': {'$in': ['PENDING', 'CONFIRMED']}}):
                http('cancel owned unpaid demo order', 'POST', '/orders/' + str(order['_id']) + '/cancel',
                     {'expectedVersion': order['version']}, customer)
            for p in state['products']:
                current = http('read fixture price/version', 'GET', '/admin/products/' + p['id'], token=admin)
                allowed = {p['price'], 12000000} if p['productType'] == 'ELECTRONICS' else {p['price']}
                assert current['price'] in allowed, 'Unexpected fixture price; refusing overwrite'
                if current['price'] != p['price']:
                    http('restore only fixture price', 'PATCH', '/admin/products/' + p['id'],
                         {'price': p['price'], 'expectedVersion': current['version']}, admin)
            cart = http('fixture Cart', 'GET', '/cart', token=customer)
            if cart['items']:
                http('clear own demo Cart', 'DELETE', '/cart', {'cartVersion': cart['version']}, customer)

        if args.mode == 'rehearse':
            restore()
            stock_before = {p['id']: db.products.find_one({'_id': ObjectId(p['id'])})['stock'] for p in state['products']}
            cart = http('empty Cart', 'GET', '/cart', token=customer)
            for p in state['products']:
                cart = http('add private item', 'POST', '/cart/items', {
                    'productId': p['id'], 'quantity': 1, 'cartVersion': cart['version'],
                    'selectedAttributes': {'size': 'M', 'color': 'Black'} if p['productType'] == 'FASHION' else {}}, customer)
            quote = http('COD quote', 'GET', '/checkout/quote?' + urlencode({
                'addressId': state['addressId'], 'paymentMethod': 'COD'}), token=customer)
            intent = {'cartVersion': quote['cartVersion'], 'addressId': state['addressId'],
                      'paymentMethod': 'COD', 'quoteToken': quote['quoteToken']}
            key = uuid4().hex
            order = http('real COD checkout', 'POST', '/orders', intent, customer, key)['order']
            state['rehearsalOrders'].append({'id': order['id'], 'orderCode': order['orderCode']})
            save()
            replay = http('COD replay', 'POST', '/orders', intent, customer, key)['order']
            assert replay['id'] == order['id'] and len(order['items']) == 2
            p = state['products'][0]
            current = http('read private Product', 'GET', '/admin/products/' + p['id'], token=admin)
            changed = http('price A to B', 'PATCH', '/admin/products/' + p['id'],
                           {'price': 12000000, 'expectedVersion': current['version']}, admin)
            old = http('read snapshot after price change', 'GET', '/orders/' + order['id'], token=customer)
            stored = db.orders.find_one({'_id': ObjectId(order['id'])})
            assert old['items'] == order['items'] and old['customerSnapshot'] == order['customerSnapshot']
            item_before = next(i for i in order['items'] if i['productId'] == p['id'])
            item_after = next(i for i in old['items'] if i['productId'] == p['id'])
            stored_item = next(i for i in stored['items'] if i['productId'] == ObjectId(p['id']))
            assert old['shippingAddress'] == order['shippingAddress'] and stored_item['priceAtPurchase'] == 10000000
            state['snapshotProof'] = {'orderId': order['id'], 'orderCode': order['orderCode'], 'priceA': 10000000,
                'priceB': changed['price'], 'snapshotPriceAfterChange': item_after['priceAtPurchase'],
                'subtotal': order['subtotal'], 'shippingFee': order['shippingFee'], 'total': order['total'],
                'items': order['items'], 'transport': 'REAL_HTTP_API_NOT_BROWSER', 'snapshotUnchanged': True}
            restore()
            assert db.products.find_one({'_id': ObjectId(p['id'])})['price'] == 10000000
            assert all(db.products.find_one({'_id': ObjectId(p['id'])})['stock'] == stock_before[p['id']] for p in state['products'])
            save()
        elif args.mode == 'restore':
            restore()

        assert original_digest() == state['before']['digest'], 'Original documents/schema/indexes changed; inspect concurrent writes, do not reset'
        home = db.products.find_one({'sku': 'DEMO-HOM-019'}, {'passwordHash': 0})
        assert home and all(k in home['attributes'] for k in ('power', 'capacity', 'voltage'))
        result = {'phase': '07C', 'mode': args.mode, 'timestampUtc': datetime.now(timezone.utc).isoformat(),
            'replicaSet': 'rs0', 'primary': True, 'database': db.name, 'apiChecks': checks,
            'before': state['before'], 'after': fingerprint(db), 'originalDigestAfterExcludingOwnedFixtures': original_digest(),
            'originalDataUnchanged': True, 'ownedFixture': {'customerEmail': EMAIL, 'userId': state['userId'],
                'categories': state['categories'], 'products': state['products'], 'addressId': state['addressId']},
            'snapshotProof': state.get('snapshotProof'), 'liveSandbox': 'BLOCKED',
            'frontendBrowserRehearsed': False, 'compassGuiRehearsed': False}
        EVIDENCE.mkdir(parents=True, exist_ok=True)
        (EVIDENCE / ('phase07c-' + args.mode + '.json')).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
        print(json.dumps({'phase': '07C', 'mode': args.mode, 'apiChecks': len(checks), 'originalDataUnchanged': True,
                          'counts': result['after']['counts'], 'fixtureReady': True, 'snapshotProof': bool(state.get('snapshotProof'))}))
    finally:
        app.extensions['mongo'].close()


if __name__ == '__main__':
    main()
