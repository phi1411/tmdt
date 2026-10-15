"""Deterministic dev fixtures. Default dry run; --reset writes only owned local DBs."""
from __future__ import annotations
import argparse
import copy
import os
import random
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'db'))
from common import ROOT, COLLECTIONS, connection, apply_foundation, oid, digest, normalize, read_json, write_ejson, load_env
from argon2 import PasswordHasher
from bson.int64 import Int64
from pymongo import UpdateOne
from pymongo.read_concern import ReadConcern

ANCHOR = datetime(2026, 10, 1, tzinfo=timezone.utc)
START = ANCHOR - timedelta(days=90)
SEED = 20261007
TYPES = ('ELECTRONICS', 'FASHION', 'HOME_APPLIANCE')
SOURCE_CATEGORIES = {
    'ELECTRONICS': {'smartphones', 'laptops', 'tablets', 'mobile-accessories'},
    'FASHION': {'mens-shirts', 'mens-shoes', 'mens-watches', 'womens-dresses', 'womens-shoes', 'womens-bags', 'womens-watches', 'tops', 'sunglasses'},
    'HOME_APPLIANCE': {'furniture', 'kitchen-accessories'},
}

def common(namespace, i):
    return {'_id': oid(namespace, i), 'schemaVersion': 1, 'createdAt': START - timedelta(days=1), 'updatedAt': START - timedelta(days=1)}

def attributes(source, kind, i):
    category = source['category']
    dims = source.get('dimensions', {})
    attrs = {'sourceCategory': category, 'sourceProductId': source['id'], 'dimensions': {k: str(v) + ' cm' for k, v in dims.items()}}
    if kind == 'ELECTRONICS':
        if category in {'smartphones', 'laptops', 'tablets'}:
            attrs.update(ram=['8GB', '16GB', '12GB'][i % 3], storage=['256GB', '512GB', '128GB'][i % 3], chip=['Demo CPU A', 'Demo CPU B'][i % 2], screen='15.6 inch' if category == 'laptops' else '6.7 inch', battery='5000mAh' if category != 'laptops' else '60Wh')
        else:
            attrs.update(connectivity={'bluetooth': True, 'usb': 'USB-C'}, accessoryType=source['title'], warranty='12 months', compatibility=['Android', 'iOS'])
    elif kind == 'FASHION':
        if category in {'mens-shoes', 'womens-shoes'}:
            attrs.update(sizes=['38', '39', '40', '41', '42'], colors=['Black', 'White'], material='Synthetic leather', gender='Unisex', sole='Rubber')
        elif 'watches' in category or category in {'womens-bags', 'sunglasses'}:
            attrs.update(colors=['Black', 'Brown'], material='Stainless steel' if 'watches' in category else 'Synthetic leather', gender='Women' if category.startswith('womens') else 'Unisex', care='Wipe dry', style='Casual')
        else:
            attrs.update(sizes=['S', 'M', 'L', 'XL'], colors=['Blue', 'White', 'Black'], material='Cotton', gender='Women' if category.startswith('womens') else 'Unisex', fit='Regular', care='Wash at 30 C')
    elif category == 'furniture':
        attrs.update(material='Wood', assemblyRequired=True, room='Bedroom' if 'bed' in source['title'].lower() else 'Living room', finish='Natural', loadCapacity='100 kg')
    else:
        attrs.update(material='Stainless steel' if any(w in source['title'].lower() for w in ('knife', 'spoon', 'fork', 'pot', 'pan')) else 'Food-safe composite', capacity=['1L', '2L', '3L'][i % 3], dishwasherSafe=True, useCase=source['title'], care='Clean after use')
        if any(w in source['title'].lower() for w in ('electric', 'microwave', 'blender')):
            attrs.update(power='800W', voltage='220V')
    return attrs

def build_catalog():
    import hashlib
    metadata = read_json('database/sources/provenance.json')
    assert hashlib.sha256((ROOT / 'database/sources/dummyjson-products.json').read_bytes()).hexdigest() == metadata['sha256'], 'Cached source checksum changed; record an intentional new source version before reseeding'
    raw = read_json('database/sources/dummyjson-products.json')['products']
    categories = []
    products = []
    origins = []
    for group, (name, slug) in zip(TYPES, [('Điện tử', 'dien-tu'), ('Thời trang', 'thoi-trang'), ('Gia dụng', 'gia-dung')]):
        category = common('category', len(categories))
        category.update(name=name, slug=slug, productType=group, description=f'Danh mục demo {name}', status='ACTIVE', version=1)
        categories.append(category)
        pool = sorted([p for p in raw if p['category'] in SOURCE_CATEGORIES[group]], key=lambda p: p['id'])
        if not pool:
            raise ValueError(f'Missing source group {group}')
        for i in range(60):
            source = pool[i % len(pool)]
            variant = i // len(pool)
            index = len(products)
            title = source['title'] + (f' — bản demo {variant + 1:02d}' if variant else '')
            price = int((Decimal(str(source['price'])) * Decimal(25000) * (Decimal(1) + Decimal(variant) / 20)).quantize(Decimal(1), rounding=ROUND_HALF_UP))
            product = common('product', index)
            product.update(sku=f'DEMO-{group[:3]}-{i+1:03d}', name=title, slug=f'{normalize(title).replace(" ", "-").replace("—", "").strip("-")}-{index+1:03d}', productType=group, categoryId=category['_id'], brand=source.get('brand', ''), description=source.get('description', '') + ' Thuộc tính và giá được biên soạn cho dữ liệu demo; không phải thông số thương mại đã xác minh.', nameNormalized=normalize(title), brandNormalized=normalize(source.get('brand', '')), price=Int64(max(1, min(price, 1_000_000_000))), stock=100, images=source.get('images', [source['thumbnail']])[:8], attributes=attributes(source, group, i), status='ACTIVE', version=1)
            # Slugs use only the locked lowercase ASCII/hyphen shape.
            import re
            product['slug'] = re.sub('[^a-z0-9-]+', '-', product['slug'])
            product['slug'] = re.sub('-+', '-', product['slug']).strip('-')
            if index == 0:
                product['price'] = Int64(10_000_000)
            products.append(product)
            origins.append({'productId': product['_id'], 'sourceId': source['id'], 'variant': variant + 1, 'specifications': 'CURATED_DEMO', 'basePrice': product['price']})
    return categories, products, origins

def build_users(password):
    hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)
    users = []
    names = ['Nguyễn An', 'Trần Bình', 'Lê Chi', 'Phạm Dũng', 'Hoàng Hà', 'Vũ Lan']
    for i in range(40):
        user = common('user', i)
        name = 'Quản trị Demo' if i == 0 else f'{names[(i-1)%len(names)]} {i:02d}'
        address = {'_id': oid('address', i), 'label': 'Nhà demo', 'receiverName': name, 'phone': f'090000{i:04d}', 'addressLine': f'{i+1} Đường Dữ Liệu Mẫu', 'province': 'Thành phố Hồ Chí Minh', 'district': 'Quận 1', 'ward': 'Phường Bến Nghé'}
        user.update(email='admin@example.test' if i == 0 else f'customer{i:02d}@example.test', passwordHash=hasher.hash(password), role='ADMIN' if i == 0 else 'CUSTOMER', status='BLOCKED' if i == 39 else 'ACTIVE', tokenVersion=0, version=1, name=name, phone=address['phone'], addresses=[address], defaultAddressId=address['_id'])
        users.append(user)
    return users

def build_orders(products, categories, users):
    """Called with Products read back through PyMongo inside the seed transaction."""
    rng = random.Random(SEED)
    products = sorted(products, key=lambda p: p['sku'])
    demo = next(p for p in products if p['_id'] == oid('product', 0))
    categories = {c['_id']: c for c in categories}
    customers = sorted([u for u in users if u['role'] == 'CUSTOMER' and u['status'] == 'ACTIVE'], key=lambda u: u['email'])
    states = [('COMPLETED', 'COD')]*40 + [('COMPLETED', 'VNPAY')]*20 + [('PENDING', 'COD')]*5 + [('PENDING', 'VNPAY')]*5 + [('CONFIRMED', 'COD')]*10 + [('SHIPPING', 'COD')]*10 + [('CANCELLED', 'COD')]*5 + [('EXPIRED', 'VNPAY')]*5
    orders, attempts = [], []
    ledger = {p['_id']: {'initial': 100, 'sold': 0, 'reserved': 0, 'released': 0} for p in products}
    for i, (status, method) in enumerate(states):
        user = customers[i % len(customers)]
        created = START + timedelta(days=rng.randrange(87), hours=rng.randrange(24), minutes=rng.randrange(60))
        if status == 'PENDING' and method == 'VNPAY':
            created = ANCHOR - timedelta(minutes=10 - (i-65))
        count = rng.randint(2, 5)
        chosen = rng.sample(products, count)
        if i == 0:
            chosen = [demo] + [p for p in chosen if p['_id'] != demo['_id']][:count-1]
        order = common('order', i)
        address = {k: v for k, v in user['addresses'][0].items() if k not in {'_id', 'label'}}
        paid = status == 'COMPLETED'
        items = []
        for product in chosen:
            quantity = rng.randint(1, 3)
            selection = {}
            if product['productType'] == 'FASHION':
                for key, options in [('size', 'sizes'), ('color', 'colors')]:
                    if product['attributes'].get(options):
                        selection[key] = rng.choice(product['attributes'][options])
            items.append({'productId': product['_id'], 'sku': product['sku'], 'productName': product['name'], 'image': product['images'][0] if product['images'] else '', 'productType': product['productType'], 'categoryId': product['categoryId'], 'categoryName': categories[product['categoryId']]['name'], 'attributesSnapshot': copy.deepcopy(product['attributes']), 'selectedAttributes': selection, 'priceAtPurchase': product['price'], 'quantity': quantity, 'lineTotal': Int64(product['price'] * quantity)})
            ledger[product['_id']]['sold' if paid else 'released' if status in {'CANCELLED', 'EXPIRED'} else 'reserved'] += quantity
        subtotal = Int64(sum(item['lineTotal'] for item in items))
        order.update(createdAt=created, updatedAt=created, orderCode=f'DEMO-2026-{i+1:04d}', userId=user['_id'], checkoutKey=f'seed-checkout-{i+1:04d}', checkoutRequestHash=digest({'cartVersion': 1, 'addressId': str(user['defaultAddressId']), 'paymentMethod': method, 'quoteToken': f'DEV-FIXTURE-{i+1}'}), customerSnapshot={k: user[k] for k in ['name', 'phone', 'email']}, shippingAddress=address, items=items, subtotal=subtotal, shippingFee=Int64(30000), discount=Int64(0), total=Int64(subtotal+30000), currency='VND', paymentMethod=method, paymentStatus='PAID' if paid else 'FAILED' if status == 'EXPIRED' else 'PENDING' if method == 'VNPAY' else 'UNPAID', paymentReviewRequired=False, orderStatus=status, version=1)
        if method == 'VNPAY':
            order['paymentExpiresAt'] = created + timedelta(minutes=15)
        if paid:
            order['completedAt'] = created + timedelta(days=2)
            order['paidAt'] = created + timedelta(minutes=3) if method == 'VNPAY' else order['completedAt']
            order['updatedAt'] = order['completedAt']
        elif status == 'CANCELLED':
            order['cancelledAt'] = order['stockReleasedAt'] = order['updatedAt'] = created + timedelta(hours=1)
        elif status == 'EXPIRED':
            order['expiredAt'] = order['stockReleasedAt'] = order['updatedAt'] = order['paymentExpiresAt'] + timedelta(seconds=1)
        elif status in {'CONFIRMED', 'SHIPPING'}:
            order['updatedAt'] = created + timedelta(hours=1)
        orders.append(order)
        if method == 'VNPAY':
            attempt = common('attempt', i)
            txn = f'DEMO2026{i+1:04d}'
            attempt.update(createdAt=created, updatedAt=created, orderId=order['_id'], userId=user['_id'], attemptKey=f'seed-attempt-{i+1:04d}', requestHash=digest({'orderId': str(order['_id']), 'attemptKey': f'seed-attempt-{i+1:04d}'}), txnRef=txn, provider='VNPAY', amount=order['total'], currency='VND', status='SUCCEEDED' if paid else 'EXPIRED' if status == 'EXPIRED' else 'PENDING', version=1, expiresAt=order['paymentExpiresAt'], paymentRequest={'version': '2.1.0', 'command': 'pay', 'tmnCode': 'DEMO0001', 'amountScaled': Int64(order['total']*100), 'currency': 'VND', 'txnRef': txn, 'orderInfo': f'Demo order {i+1}', 'orderType': 'other', 'locale': 'vn', 'returnUrl': 'http://localhost:5173/payment/return', 'clientIp': '127.0.0.1', 'createdAt': created, 'expiresAt': order['paymentExpiresAt']})
            if paid:
                attempt.update(updatedAt=order['paidAt'], providerTransactionNo=str(800000000+i), responseCode='00', transactionStatus='00', bankCode='DEMO', verifiedAt=order['paidAt'], providerPaidAt=order['paidAt'], callbackFingerprint=digest({'fixture': i, 'status': 'SUCCEEDED'}))
            elif status == 'EXPIRED':
                attempt.update(updatedAt=order['expiredAt'], expiredAt=order['expiredAt'])
            attempts.append(attempt)
    return orders, attempts, ledger

def expected_ids():
    return {'categories': {oid('category', i) for i in range(3)}, 'products': {oid('product', i) for i in range(180)}, 'users': {oid('user', i) for i in range(40)}, 'orders': {oid('order', i) for i in range(100)}, 'carts': set(), 'payment_attempts': {oid('attempt', i) for i in list(range(40, 60))+list(range(65, 70))+list(range(95, 100))}, 'reviews': set()}

def run_seed(database):
    load_env()
    password = os.environ.get('SEED_DEMO_PASSWORD', '')
    if not 12 <= len(password) <= 128:
        raise ValueError('Set SEED_DEMO_PASSWORD (12..128 chars) in ignored .env before writing seed')
    categories, base_products, origins = build_catalog()
    users = build_users(password)
    client, db = connection(database, claim=True)
    try:
        apply_foundation(db)
        expected = expected_ids()
        for name in COLLECTIONS:
            if any(row['_id'] not in expected[name] for row in db[name].find({}, {'_id': 1})):
                raise RuntimeError(f'Refusing reset: {name} contains data outside deterministic fixtures')
        def commit_seed(session):
            for name in reversed(COLLECTIONS):
                db[name].delete_many({}, session=session)
            db.categories.insert_many(categories, session=session)
            db.users.insert_many(users, session=session)
            db.products.insert_many(base_products, session=session)
            persisted = list(db.products.find({}, session=session))
            persisted_categories = list(db.categories.find({}, session=session))
            persisted_users = list(db.users.find({}, session=session))
            orders, attempts, ledger = build_orders(persisted, persisted_categories, persisted_users)
            db.orders.insert_many(orders, session=session)
            db.payment_attempts.insert_many(attempts, session=session)
            updates = []
            for p in persisted:
                entry = ledger[p['_id']]
                entry['final'] = entry['initial'] - entry['sold'] - entry['reserved']
                assert entry['final'] >= 0
                fields = {'stock': entry['final'], 'updatedAt': ANCHOR, 'version': 2}
                if p['_id'] == oid('product', 0):
                    fields['price'] = Int64(12_000_000)
                    fields['version'] = 3
                updates.append(UpdateOne({'_id': p['_id']}, {'$set': fields}))
            db.products.bulk_write(updates, session=session)
            return ledger
        with client.start_session() as session:
            ledger = session.with_transaction(commit_seed, write_concern=db.write_concern, read_concern=ReadConcern('snapshot'))
        manifest = {'database': database, 'randomSeed': SEED, 'anchor': ANCHOR, 'windowStart': START, 'source': 'Cached DummyJSON + explicitly curated demo specifications/variants; USD * fixed 25000 for synthetic VND prices', 'productsReadFromMongoInsideTransaction': True, 'paymentFixturesOnly': True, 'origins': origins, 'inventory': [{'productId': key, **value} for key, value in sorted(ledger.items(), key=lambda item: str(item[0]))], 'snapshotDemo': {'productId': oid('product', 0), 'orderId': oid('order', 0), 'snapshotPrice': Int64(10_000_000), 'currentPrice': Int64(12_000_000)}, 'counts': {name: db[name].count_documents({}) for name in COLLECTIONS}}
        manifest['sourceSha256'] = read_json('database/sources/provenance.json')['sha256']
        write_ejson(f'database/evidence/seed-manifest-{database}.json', manifest)
        print(manifest['counts'])
    finally:
        client.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', default='ecommerce_dev')
    parser.add_argument('--reset', action='store_true', help='Explicit owned-fixture reset + atomic seed; indexes preserved')
    args = parser.parse_args()
    if args.reset:
        run_seed(args.database)
    else:
        categories, products, origins = build_catalog()
        print({'mode': 'DRY_RUN_NO_DB_WRITE', 'database': args.database, 'categories': len(categories), 'products': len(products), 'users': 40, 'orders': 100, 'carts': 0, 'payment_attempts': 30, 'groups': dict(Counter(p['productType'] for p in products))})
