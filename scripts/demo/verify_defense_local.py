"""Local COD/cancel/disabled-payment smoke using only disposable owned fixtures."""
import json
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/deploy'))
import rehearse_vnpay_sandbox as transport
from migrate_sku_reviews import COLLECTIONS, fingerprint
from bson import json_util
from pymongo import MongoClient
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern


def main():
    private = ROOT / '.local/defense-final'
    marker = json.loads((private / 'local-copy-ownership.json').read_text(encoding='utf-8'))
    assert marker == {'project': str(ROOT), 'destination': 'ecommerce_defense', 'endpoint': '127.0.0.1:27017/rs0'}
    transport.API = 'http://127.0.0.1:5000/api/v1'
    transport.ORIGIN = 'http://127.0.0.1:5173'
    checks = []
    def http(method, path, payload=None, token=None, key=None, expected=200):
        value = transport.http(method, path, payload, token, key, expected)
        checks.append({'method': method, 'path': path, 'expectedStatus': expected})
        return value
    with MongoClient('mongodb://127.0.0.1:27017/?replicaSet=rs0', tz_aware=True) as client:
        db = client.ecommerce_defense
        before = fingerprint(db)
        dev_before = fingerprint(client.ecommerce_dev)
        run = 'local-defense-' + secrets.token_hex(6)
        email = run + '@example.test'
        sku = run.upper()
        creds = json.loads((private / 'admin-credentials.json').read_text(encoding='utf-8'))
        (private / 'before-local-smoke.ejson').write_text(json_util.dumps({n: list(db[n].find()) for n in COLLECTIONS}, json_options=json_util.CANONICAL_JSON_OPTIONS), encoding='utf-8')
        passed = False
        try:
            http('GET', '/health')
            http('GET', '/products/ao-demo-sku-m-xl')
            assert http('GET', '/products/ao-demo-sku-m-xl/reviews')['stats']['totalReviews'] == 1
            admin = http('POST', '/auth/login', {'email': 'admin@example.test', 'password': creds['adminPassword']})['accessToken']
            password = secrets.token_urlsafe(24)
            http('POST', '/auth/register', {'email': email, 'name': 'Kiểm thử local', 'password': password, 'phone': '0901234567'}, expected=201)
            token = http('POST', '/auth/login', {'email': email, 'password': password})['accessToken']
            profile = http('GET', '/users/me', token=token)
            address = http('POST', '/users/me/addresses', {'expectedVersion': profile['version'], 'receiverName': 'Demo local', 'phone': '0901234567', 'addressLine': 'Địa chỉ thử local', 'province': 'Hồ Chí Minh'}, token, expected=201)['address']['id']
            category = http('POST', '/admin/categories', {'name': run, 'slug': run, 'productType': 'FASHION'}, admin, expected=201)
            product = http('POST', '/admin/products', {'sku': sku, 'name': 'Kiểm thử COD local', 'slug': run, 'categoryId': category['id'], 'productType': 'FASHION', 'brand': '', 'description': 'Disposable local smoke fixture', 'attributes': {'material': 'Cotton'}, 'price': 100000, 'stock': 5, 'images': [], 'status': 'ACTIVE'}, admin, expected=201)
            cart = http('GET', '/cart', token=token)
            cart = http('POST', '/cart/items', {'cartVersion': cart['version'], 'productId': product['id'], 'quantity': 2}, token)
            http('GET', '/checkout/quote?' + urlencode({'addressId': address, 'paymentMethod': 'VNPAY'}), token=token, expected=503)
            quote = http('GET', '/checkout/quote?' + urlencode({'addressId': address, 'paymentMethod': 'COD'}), token=token)
            body = {'cartVersion': cart['version'], 'addressId': address, 'paymentMethod': 'COD', 'quoteToken': quote['quoteToken']}
            order = http('POST', '/orders', body, token, key=run, expected=201)['order']
            assert http('POST', '/orders', body, token, key=run)['order']['id'] == order['id']
            assert order['subtotal'] == 200000 and order['total'] == 230000 and order['items'][0]['priceAtPurchase'] == 100000
            assert http('GET', '/admin/products/' + product['id'], token=admin)['stock'] == 3
            for _ in range(2):
                assert http('POST', '/orders/' + order['id'] + '/cancel', {'expectedVersion': order['version']}, token)['orderStatus'] == 'CANCELLED'
            assert http('GET', '/admin/products/' + product['id'], token=admin)['stock'] == 5
            passed = True
        finally:
            user = db.users.find_one({'email': email})
            product = db.products.find_one({'sku': sku})
            category = db.categories.find_one({'slug': run})
            removed = {}
            with client.start_session() as session:
                with session.start_transaction(read_concern=ReadConcern('snapshot'), write_concern=WriteConcern('majority')):
                    if user:
                        for n in ('reviews', 'payment_attempts', 'orders', 'carts'):
                            removed[n] = db[n].delete_many({'userId': user['_id']}, session=session).deleted_count
                        removed['users'] = db.users.delete_one({'_id': user['_id'], 'email': email}, session=session).deleted_count
                    if product:
                        assert not db.orders.count_documents({'items.productId': product['_id']}, session=session)
                        assert not db.carts.count_documents({'items.productId': product['_id']}, session=session)
                        removed['products'] = db.products.delete_one({'_id': product['_id'], 'sku': sku}, session=session).deleted_count
                    if category:
                        assert not db.products.count_documents({'categoryId': category['_id']}, session=session)
                        removed['categories'] = db.categories.delete_one({'_id': category['_id'], 'slug': run}, session=session).deleted_count
            after = fingerprint(db)
            report = {'recordedAtUtc': datetime.now(timezone.utc).isoformat(), 'passed': passed, 'checks': checks,
                'httpChecks': len(checks), 'codIdempotencyCancelStockOnce': passed, 'vnpayDisabled503': passed,
                'beforeFingerprint': before, 'afterFingerprint': after, 'exactCleanup': before == after,
                'removedOwnedDocuments': removed, 'localDevUnchanged': dev_before == fingerprint(client.ecommerce_dev),
                'osInternetDisconnected': False, 'scope': 'Loopback Flask/Vite/Mongo functional check, not physical offline proof'}
            (ROOT / 'backend/evidence/defense-local-smoke-20261020.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
            assert before == after and report['localDevUnchanged']
        print(json.dumps({'status': 'LOCAL_COD_PASS', 'httpChecks': len(checks), 'exactCleanup': True}))


if __name__ == '__main__':
    main()
