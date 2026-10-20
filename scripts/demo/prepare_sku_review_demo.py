"""Create deliberately retained, labelled demo fixtures through existing public APIs.

One-shot with a private recovery journal. A second execution only verifies the
completed fixtures; it never silently deletes, reseeds or replays partial writes.
"""
import argparse
import copy
import hashlib
import json
import secrets
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode, urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/deploy'))
from rehearse_vnpay_sandbox import http
from migrate_sku_reviews import COLLECTIONS, fingerprint, read_json, selected_indexes
from bson import ObjectId, json_util
from pymongo import MongoClient

PRIVATE = ROOT / '.local/defense-final'
JOURNAL = PRIVATE / 'demo-journal.json'
REPORT = ROOT / 'backend/evidence/defense-demo-final-20261020.json'


def save(journal):
    JOURNAL.write_text(json.dumps(journal, ensure_ascii=False, indent=2), encoding='utf-8')


def verify(db, j):
    owned = {name: set() for name in COLLECTIONS}
    for name, field in (('users', 'userId'), ('categories', 'categoryId'), ('products', 'productId'),
                        ('products', 'accessoryId'), ('orders', 'orderId'), ('reviews', 'reviewId')):
        owned[name].add(ObjectId(j[field]))
    owner = ObjectId(j['userId'])
    owned['carts'] = {d['_id'] for d in db.carts.find({'userId': owner})}
    original = {n: list(db[n].find({'_id': {'$nin': list(owned[n])}}).sort('_id', 1)) for n in COLLECTIONS}
    digest = hashlib.sha256(json_util.dumps(original, json_options=json_util.CANONICAL_JSON_OPTIONS, sort_keys=True).encode()).hexdigest()
    assert digest == j['beforeFingerprint'], 'Unrelated baseline changed: inspect; never reset'
    order = db.orders.find_one({'_id': ObjectId(j['orderId']), 'userId': owner})
    product = db.products.find_one({'_id': ObjectId(j['productId'])})
    accessory = db.products.find_one({'_id': ObjectId(j['accessoryId'])})
    review = db.reviews.find_one({'_id': ObjectId(j['reviewId']), 'userId': owner, 'orderId': order['_id']})
    assert order['orderStatus'] == 'COMPLETED' and order['paymentStatus'] == 'PAID'
    assert len(order['items']) == 2 and order['subtotal'] == 150000 and order['total'] == 180000
    assert next(i for i in order['items'] if i['productId'] == accessory['_id'])['priceAtPurchase'] == 50000
    assert accessory['price'] == 60000 and accessory['stock'] == 9
    assert product['stock'] == 19 and [s['stock'] for s in product['skus']] == [9, 10]
    assert review['rating'] == 4 and review['status'] == 'VISIBLE' and 'Dữ liệu trình diễn' in review['reviewText']
    assert product['ratingSummary']['totalReviews'] == 1 and product['ratingSummary']['averageRating'] == 4
    invalid = {n: db[n].count_documents({'$nor': [read_json(f'database/validators/{n}.json')]}) for n in COLLECTIONS}
    assert not any(invalid.values()), invalid
    assert all(db[n].options()['validator'] == read_json(f'database/validators/{n}.json') for n in COLLECTIONS)
    assert all(dict(db[i['collection']].index_information()[i['name']]['key']) == i['keys'] for i in selected_indexes())
    report = {'recordedAtUtc': datetime.now(timezone.utc).isoformat(), 'status': 'RETAINED_DEMO_PASS',
        'intentionalPersistentFixtures': True, 'database': db.name, 'orderCode': order['orderCode'],
        'products': [{'sku': product['sku'], 'slug': product['slug'], 'stock': product['stock'], 'skuStocks': [s['stock'] for s in product['skus']]},
                     {'sku': accessory['sku'], 'slug': accessory['slug'], 'stock': accessory['stock'], 'currentPrice': int(accessory['price']), 'orderSnapshotPrice': 50000}],
        'review': {'rating': 4, 'verifiedPurchase': True, 'labelledDemo': True}, 'orderState': 'COMPLETED/PAID',
        'counts': {n: db[n].count_documents({}) for n in COLLECTIONS}, 'originalCorpusFingerprint': digest,
        'originalCorpusUnchanged': True, 'fullFingerprint': fingerprint(db), 'invalidDocuments': invalid,
        'validators': 7, 'declaredIndexes': len(selected_indexes()), 'revenueDeltaVnd': 150000,
        'shippingExcludedVnd': 30000, 'seedResetOrReseed': False}
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


def prepare(db, credentials_file):
    PRIVATE.mkdir(parents=True, exist_ok=True)
    if JOURNAL.exists():
        j = json.loads(JOURNAL.read_text(encoding='utf-8'))
        assert j.get('completed'), 'Partial journal exists: inspect exact owned writes before continuing'
        return verify(db, j)
    run = 'defense-final-20261020'
    email = run + '@example.test'
    assert not db.users.find_one({'email': email}) and not db.categories.find_one({'slug': run})
    assert not db.products.find_one({'sku': {'$in': ['DEFENSE-FINAL-SKU', 'DEFENSE-FINAL-SNAPSHOT']}})
    backup = {'documents': {n: list(db[n].find().sort('_id', 1)) for n in COLLECTIONS},
        'options': list(db.list_collections()), 'indexes': {n: list(db[n].list_indexes()) for n in COLLECTIONS}}
    (PRIVATE / 'before-demo-backup.ejson').write_text(json_util.dumps(backup, json_options=json_util.CANONICAL_JSON_OPTIONS), encoding='utf-8')
    j = {'run': run, 'email': email, 'password': secrets.token_urlsafe(24), 'beforeFingerprint': fingerprint(db), 'completed': False}
    save(j)
    admin = http('POST', '/auth/login', {'email': 'admin@example.test', 'password': json.loads(credentials_file.read_text(encoding='utf-8'))['adminPassword']})['accessToken']
    j['userId'] = http('POST', '/auth/register', {'name': 'Khách demo đồ án', 'email': email, 'password': j['password'], 'phone': '0901234567'}, expected=201)['user']['id']; save(j)
    customer = http('POST', '/auth/login', {'email': email, 'password': j['password']})['accessToken']
    profile = http('GET', '/users/me', token=customer)
    address = http('POST', '/users/me/addresses', {'expectedVersion': profile['version'], 'receiverName': 'Khách demo đồ án', 'phone': '0901234567', 'addressLine': 'Địa chỉ dữ liệu trình diễn', 'province': 'Hồ Chí Minh'}, customer, expected=201)['address']['id']
    j['categoryId'] = http('POST', '/admin/categories', {'name': 'Demo bảo vệ — SKU và snapshot', 'slug': run, 'productType': 'FASHION'}, admin, expected=201)['id']; save(j)
    image = 'https://cdn.dummyjson.com/product-images/mens-shirts/gigabyte-aorus-men-tshirt/1.webp'
    base = {'categoryId': j['categoryId'], 'productType': 'FASHION', 'brand': '', 'description': 'Dữ liệu trình diễn đồ án NoSQL; không phải hàng bán thực tế.', 'images': [image], 'status': 'ACTIVE'}
    product = http('POST', '/admin/products', {**base, 'sku': 'DEFENSE-FINAL-SKU', 'name': 'Áo demo SKU — chọn M hoặc XL', 'slug': 'ao-demo-sku-m-xl', 'price': 100000, 'stock': 20,
        'attributes': {'sizes': ['M', 'XL'], 'colors': ['Đen'], 'material': 'Cotton'},
        'tierVariations': [{'name': 'Size', 'options': ['M', 'XL']}],
        'skus': [{'skuId': 'DEFENSE-FINAL-SKU-M', 'tierIndex': [0], 'price': 100000, 'stock': 10}, {'skuId': 'DEFENSE-FINAL-SKU-XL', 'tierIndex': [1], 'price': 120000, 'stock': 10}]}, admin, expected=201)
    j['productId'] = product['id']; save(j)
    accessory = http('POST', '/admin/products', {**base, 'sku': 'DEFENSE-FINAL-SNAPSHOT', 'name': 'Áo demo snapshot — giá cũ được giữ', 'slug': 'ao-demo-snapshot-gia-cu', 'price': 50000, 'stock': 10, 'attributes': {'material': 'Cotton'}}, admin, expected=201)
    j['accessoryId'] = accessory['id']; save(j)
    cart = http('GET', '/cart', token=customer)
    for pid, selection in ((product['id'], {'Size': 'M'}), (accessory['id'], {})):
        cart = http('POST', '/cart/items', {'cartVersion': cart['version'], 'productId': pid, 'quantity': 1, 'selectedAttributes': selection}, customer)
    quote = http('GET', '/checkout/quote?' + urlencode({'addressId': address, 'paymentMethod': 'COD'}), token=customer)
    order = http('POST', '/orders', {'cartVersion': cart['version'], 'addressId': address, 'paymentMethod': 'COD', 'quoteToken': quote['quoteToken']}, customer, key=run, expected=201)['order']
    j['orderId'] = order['id']; j['orderCode'] = order['orderCode']; save(j)
    snapshot = copy.deepcopy(order['items'])
    window = urlencode({'from': (datetime.now(timezone.utc)-timedelta(days=1)).isoformat(), 'to': (datetime.now(timezone.utc)+timedelta(days=1)).isoformat()})
    before_revenue = http('GET', '/admin/dashboard/summary?' + window, token=admin)['totalRevenue']
    for action in ('confirm', 'ship', 'complete'):
        order = http('POST', '/admin/orders/' + order['id'] + '/' + action, {'expectedVersion': order['version']}, admin)
    assert http('GET', '/admin/dashboard/summary?' + window, token=admin)['totalRevenue'] - before_revenue == 150000
    j['reviewId'] = http('POST', '/products/' + product['id'] + '/reviews', {'orderId': order['id'], 'rating': 4, 'reviewText': 'Dữ liệu trình diễn đồ án: mua Size M, kiểm chứng đánh giá sau đơn hoàn tất; không phải phản hồi khách hàng thật.'}, customer, expected=201)['id']; save(j)
    current = http('GET', '/admin/products/' + accessory['id'], token=admin)
    http('PATCH', '/admin/products/' + accessory['id'], {'expectedVersion': current['version'], 'price': 60000}, admin)
    assert http('GET', '/orders/' + order['id'], token=customer)['items'] == snapshot
    j['completed'] = True; save(j)
    (PRIVATE / 'demo-credentials.md').write_text('# Tài khoản demo riêng — không chiếu màn hình\n\nWebsite: https://novamart-web.onrender.com\n\nCustomer: ' + email + '\n\nPassword: ' + j['password'] + '\n\nOrder: ' + order['orderCode'] + '\n\nAdmin: admin@example.test; mật khẩu giữ nguyên trong .local/render-deployment/browser-credentials.json của checkout gốc.\n', encoding='utf-8')
    return verify(db, j)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--connection-file', type=Path, required=True)
    parser.add_argument('--admin-credentials-file', type=Path, required=True)
    args = parser.parse_args()
    cfg = json.loads(args.connection_file.read_text(encoding='utf-8'))
    assert urlsplit(cfg['uri']).hostname == 'cluster0.asxeso0.mongodb.net' and cfg['database'] == 'novamart_demo'
    with MongoClient(cfg['uri'], tls=True, replicaSet='atlas-uczcqo-shard-0', tz_aware=True, serverSelectionTimeoutMS=15000) as client:
        result = prepare(client[cfg['database']], args.admin_credentials_file)
        print(json.dumps(result, ensure_ascii=False, indent=2))
