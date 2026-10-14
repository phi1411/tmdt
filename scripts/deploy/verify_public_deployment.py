"""Owned public Render smoke with exact Atlas cleanup; never resets or seeds."""
import argparse
import copy
import json
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from bson import ObjectId, json_util
from dotenv import dotenv_values
from pymongo import MongoClient
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts/backend'), str(ROOT / 'backend')]
from verify_auth_users import NAMES, fingerprint
from cleanup_phase06ab_database import snapshot, canonical_schema_check, orphan_check


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--backend-url', required=True)
    parser.add_argument('--frontend-url', required=True)
    args = parser.parse_args()
    for value in (args.backend_url, args.frontend_url):
        u = urlsplit(value)
        assert u.scheme == 'https' and u.hostname.endswith('.onrender.com') and not u.path and not u.query and not u.username
    private = json.loads((ROOT / '.local/atlas-upload/connection.json').read_text(encoding='utf-8'))
    assert private['database'] == 'novamart_demo' and urlsplit(private['uri']).hostname == 'cluster0.asxeso0.mongodb.net'
    client = MongoClient(private['uri'], serverSelectionTimeoutMS=15000, tz_aware=True)
    db = client[private['database']]
    before = fingerprint(db)
    schema = canonical_schema_check(snapshot(db))
    run = 'deploy-' + secrets.token_hex(6)
    email, sku = run + '@example.test', run.upper()
    password = secrets.token_urlsafe(24)
    local = ROOT / '.local/render-deployment' / run
    local.mkdir(parents=True, exist_ok=False)
    journal = {'database': db.name, 'run': run, 'email': email, 'sku': sku, 'before': before}
    (local / 'ownership.json').write_text(json.dumps(journal), encoding='utf-8')
    checks, results = [], {}
    owner = category = product = None
    cleanup = False

    def http(method, path, expected=200, payload=None, token=None, key=None, origin=None):
        headers = {'Content-Type': 'application/json', 'Origin': origin or args.frontend_url}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        if key:
            headers['Idempotency-Key'] = key
        req = Request(args.backend_url + '/api/v1' + path, method=method, headers=headers,
                      data=json.dumps(payload).encode() if payload is not None else None)
        try:
            response = urlopen(req, timeout=60)
        except HTTPError as error:
            response = error
        with response:
            body = json.loads(response.read()) if response.status != 204 else None
            assert response.status == expected, (method, path, response.status, body.get('error', {}).get('code') if body else None)
            assert response.headers.get('Access-Control-Allow-Origin') == args.frontend_url if origin is None else response.headers.get('Access-Control-Allow-Origin') is None
            if body:
                assert body['meta']['requestId'] == response.headers['X-Request-ID']
            checks.append({'method': method, 'path': path, 'status': response.status})
            return body['data'] if body and 'data' in body else body

    def create_order(customer, address):
        cart = http('GET', '/cart', token=customer)
        cart = http('POST', '/cart/items', payload={'productId': product['id'], 'quantity': 1, 'cartVersion': cart['version']}, token=customer)
        quote = http('GET', '/checkout/quote?' + urlencode({'addressId': address, 'paymentMethod': 'COD'}), token=customer)
        intent = {'cartVersion': cart['version'], 'addressId': address, 'paymentMethod': 'COD', 'quoteToken': quote['quoteToken']}
        http('POST', '/orders', expected=422, payload={**intent, 'total': 1}, token=customer, key=run + '-tamper')
        key = run + '-' + secrets.token_hex(4)
        order = http('POST', '/orders', expected=201, payload=intent, token=customer, key=key)['order']
        replay = http('POST', '/orders', payload=intent, token=customer, key=key)['order']
        assert replay['id'] == order['id']
        return order

    try:
        results['health'] = http('GET', '/health')
        http('GET', '/health', origin='https://untrusted.example.test')
        http('GET', '/categories')
        for kind in ('ELECTRONICS', 'FASHION', 'HOME_APPLIANCE'):
            listing = http('GET', '/products?' + urlencode({'productType': kind, 'pageSize': 1}))
            assert listing and http('GET', '/products/' + listing[0]['slug'])['attributes']
        http('GET', '/products?q=07C')
        http('GET', '/admin/users', expected=401)
        http('GET', '/auth/me', expected=401, token='invalid.jwt.token')
        secret = dotenv_values(ROOT / '.env', interpolate=False)['SEED_DEMO_PASSWORD']
        admin = http('POST', '/auth/login', payload={'email': 'admin@example.test', 'password': secret})['accessToken']
        assert db.users.count_documents({'email': email}) == 0 and db.categories.count_documents({'slug': run}) == 0 and db.products.count_documents({'sku': sku}) == 0
        user = http('POST', '/auth/register', expected=201, payload={'name': 'Kiểm tra deploy', 'email': email, 'password': password, 'phone': '0901234567'})['user']
        owner = ObjectId(user['id'])
        customer = http('POST', '/auth/login', payload={'email': email, 'password': password})['accessToken']
        user = http('GET', '/auth/me', token=customer)
        http('GET', '/admin/users', expected=403, token=customer)
        profile = http('GET', '/users/me', token=customer)
        address = http('POST', '/users/me/addresses', expected=201, payload={'expectedVersion': profile['version'], 'receiverName': 'Deploy Test', 'phone': '0901234567', 'addressLine': 'Địa chỉ kiểm thử', 'province': 'Hồ Chí Minh'}, token=customer)['address']['id']
        category = http('POST', '/admin/categories', expected=201, payload={'name': 'Kiểm tra deploy ' + run, 'slug': run, 'productType': 'ELECTRONICS'}, token=admin)
        product = http('POST', '/admin/products', expected=201, payload={'sku': sku, 'name': 'Kiểm tra deploy ' + run, 'slug': run, 'categoryId': category['id'], 'productType': 'ELECTRONICS', 'brand': '', 'description': 'Temporary owned deployment verification', 'price': 100000, 'stock': 5, 'images': [], 'attributes': {'ram': '8GB', 'storage': '128GB'}, 'status': 'ACTIVE'}, token=admin)
        first = create_order(customer, address)
        snapshot_fields = ('items', 'customerSnapshot', 'shippingAddress', 'subtotal', 'shippingFee', 'total')
        historical = {k: copy.deepcopy(first[k]) for k in snapshot_fields}
        current = http('GET', '/admin/products/' + product['id'], token=admin)
        http('PATCH', '/admin/products/' + product['id'], payload={'expectedVersion': current['version'], 'name': 'Tên mới ' + run, 'price': 120000}, token=admin)
        unchanged = http('GET', '/orders/' + first['id'], token=customer)
        assert {k: unchanged[k] for k in snapshot_fields} == historical
        fixture = json.loads((ROOT / '.local/phase07c/fixture.json').read_text(encoding='utf-8'))
        other = http('POST', '/auth/login', payload={'email': 'defense07c@example.test', 'password': fixture['customerPassword']})['accessToken']
        http('GET', '/orders/' + first['id'], expected=404, token=other)
        cancelled = http('POST', '/orders/' + first['id'] + '/cancel', payload={'expectedVersion': first['version']}, token=customer)
        assert cancelled['orderStatus'] == 'CANCELLED'
        http('POST', '/orders/' + first['id'] + '/cancel', payload={'expectedVersion': first['version']}, token=customer)
        assert http('GET', '/admin/products/' + product['id'], token=admin)['stock'] == 5
        window = urlencode({'from': (datetime.now(timezone.utc)-timedelta(days=1)).isoformat(), 'to': (datetime.now(timezone.utc)+timedelta(days=1)).isoformat()})
        summary_before = http('GET', '/admin/dashboard/summary?' + window, token=admin)
        second = create_order(customer, address)
        for action in ('confirm', 'ship', 'complete'):
            second = http('POST', '/admin/orders/' + second['id'] + '/' + action, payload={'expectedVersion': second['version']}, token=admin)
        assert second['orderStatus'] == 'COMPLETED' and second['paymentStatus'] == 'PAID'
        summary_after = http('GET', '/admin/dashboard/summary?' + window, token=admin)
        assert summary_after['totalRevenue'] - summary_before['totalRevenue'] == 120000
        for report in ('revenue', 'top-products', 'category-revenue', 'order-status'):
            http('GET', '/admin/dashboard/' + report + '?' + window, token=admin)
        results.update(customerCod='PASS', idempotency='PASS', snapshot='PASS', adminLifecycle='PASS', revenueDelta=120000, shippingExcluded=True, ownership='PASS', payloadTampering='PASS')
    finally:
        # Recover exact IDs even if an HTTP response was lost after committing.
        found = db.users.find_one({'email': email})
        if found:
            owner = found['_id']
        found_category = db.categories.find_one({'slug': run})
        found_product = db.products.find_one({'sku': sku})
        product_ids = [found_product['_id']] if found_product else []
        if product_ids:
            assert db.orders.count_documents({'userId': {'$ne': owner}, 'items.productId': {'$in': product_ids}}) == 0
            assert db.carts.count_documents({'userId': {'$ne': owner}, 'items.productId': {'$in': product_ids}}) == 0
        with client.start_session() as session:
            with session.start_transaction(read_concern=ReadConcern('snapshot'), write_concern=WriteConcern('majority')):
                removed = {}
                if owner:
                    assert db.users.count_documents({'_id': owner, 'email': email}, session=session) == 1
                    for n in ('payment_attempts', 'orders', 'carts'):
                        removed[n] = db[n].delete_many({'userId': owner}, session=session).deleted_count
                    removed['users'] = db.users.delete_one({'_id': owner, 'email': email}, session=session).deleted_count
                if found_product:
                    removed['products'] = db.products.delete_one({'_id': found_product['_id'], 'sku': sku}, session=session).deleted_count
                if found_category:
                    assert db.products.count_documents({'categoryId': found_category['_id']}, session=session) == 0
                    removed['categories'] = db.categories.delete_one({'_id': found_category['_id'], 'slug': run}, session=session).deleted_count
        after = fingerprint(db)
        canonical_schema_check(snapshot(db))
        orphan_check(snapshot(db))
        cleanup = after == before
        receipt = {'recordedAtUtc': datetime.now(timezone.utc).isoformat(), 'backendUrl': args.backend_url, 'frontendUrl': args.frontend_url,
            'checks': checks, 'results': results, 'schema': schema, 'before': before, 'after': after,
            'exactCleanup': cleanup, 'removedOwnedDocuments': removed, 'resetReseed': False, 'vnpayLiveSandbox': 'NOT_TESTED_DISABLED'}
        (ROOT / 'backend/evidence/render-public-smoke.json').write_text(json_util.dumps(receipt, indent=2, ensure_ascii=False), encoding='utf-8')
        client.close()
        assert cleanup, 'Atlas baseline changed; inspect evidence and do not reset unrelated data'
    assert results.get('customerCod') == 'PASS'
    print(json.dumps({'status': 'PUBLIC_HTTP_COMMERCE_SMOKE_PASS', 'httpChecks': len(checks), 'exactCleanup': cleanup}))


if __name__ == '__main__':
    main()
