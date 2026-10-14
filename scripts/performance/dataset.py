"""Deterministic synthetic BSON documents, canonical schema; never dev seed."""
from __future__ import annotations

import copy
import random
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from bson import json_util
from bson.int64 import Int64
from perf_common import ROOT, NAMES, INDEXES, DATASET_FILE, oid, normalize, data_hashes, save

SEED = 20261008
ANCHOR = datetime(2026, 10, 1, tzinfo=timezone.utc)
START = datetime(2026, 7, 31, 17, tzinfo=timezone.utc)
END = datetime(2026, 8, 7, 17, tzinfo=timezone.utc)
ZONE = ZoneInfo('Asia/Ho_Chi_Minh')
TYPES = ('ELECTRONICS', 'FASHION', 'HOME_APPLIANCE')


def samples(name):
    return json_util.loads((ROOT / f'database/samples/{name}.json').read_text(encoding='utf-8'),
                          json_options=json_util.JSONOptions(tz_aware=True))


def report_oracle(orders):
    qualified = sorted([o for o in orders if o['orderStatus'] == 'COMPLETED' and o['paymentStatus'] == 'PAID'
                        and START <= o['completedAt'] < END], key=lambda o: (o['completedAt'], o['_id']), reverse=True)
    days, products = {}, {}
    for order in qualified:
        local = order['completedAt'].astimezone(ZONE)
        bucket = datetime(local.year, local.month, local.day, tzinfo=ZONE).astimezone(timezone.utc)
        day = days.setdefault(bucket, {'_id': bucket, 'revenue': 0, 'orders': 0})
        day['revenue'] += order['subtotal'] - order['discount']
        day['orders'] += 1
        for item in order['items']:
            row = products.setdefault(item['productId'], {'productId': item['productId'],
                'productName': item['productName'], 'quantity': 0, 'revenue': 0})
            row['quantity'] += item['quantity']
            row['revenue'] += item['lineTotal']
    top = sorted(products.values(), key=lambda p: (-p['quantity'], -p['revenue'], p['productId']))[:5]
    return {'qualifiedOrders': len(qualified), 'totalRevenue': sum(o['subtotal'] for o in qualified),
            'productsSold': sum(item['quantity'] for o in qualified for item in o['items']),
            'revenue-day': [days[key] for key in sorted(days)], 'top-products': top}


def generate(product_count, order_count):
    rng = random.Random(SEED)
    user_base = samples('users')[0]
    users = []
    for number in range(40):
        user = copy.deepcopy(user_base)
        address = copy.deepcopy(user['addresses'][0])
        address.update(_id=oid('address', number), receiverName=f'Khách benchmark {number:03}',
                       phone='0900000000', addressLine='Địa chỉ BENCHMARK DATASET', province='Demo')
        user.update(_id=oid('user', number), name=f'Khách benchmark {number:03}',
            email=f'benchmark{number:03}@example.test', phone='0900000000', role='CUSTOMER', status='ACTIVE',
            version=1, tokenVersion=0, createdAt=ANCHOR-timedelta(days=450), updatedAt=ANCHOR,
            addresses=[address], defaultAddressId=address['_id'])
        users.append(user)
    category_bases = {row['productType']: row for row in samples('categories')}
    categories = []
    for type_number, product_type in enumerate(TYPES):
        for slot in range(10):
            category = copy.deepcopy(category_bases[product_type])
            category.update(_id=oid('category', type_number*10+slot), name=f'Benchmark {product_type} {slot}',
                slug=f'benchmark-{product_type.lower().replace("_", "-")}-{slot}', description='BENCHMARK DATASET',
                status='ACTIVE', version=1, createdAt=ANCHOR-timedelta(days=450), updatedAt=ANCHOR)
            categories.append(category)
    category_by_id = {row['_id']: row for row in categories}
    product_bases = {row['productType']: row for row in samples('products')}
    products = []
    for number in range(product_count):
        type_number = number % 3
        product_type = TYPES[type_number]
        product = copy.deepcopy(product_bases[product_type])
        category = categories[type_number*10+(number//3)%10]
        name, brand = f'Sản phẩm BENCHMARK {number:05}', f'Benchmark Brand {rng.randrange(5)}'
        status_roll = rng.randrange(10)
        product.update(_id=oid('product', number), sku=f'BENCH-{number:05}', slug=f'benchmark-product-{number:05}',
            name=name, nameNormalized=normalize(name), brand=brand, brandNormalized=normalize(brand),
            categoryId=category['_id'], productType=product_type, description='BENCHMARK DATASET, không phải seed chính thức',
            price=Int64(rng.randrange(1_000_000, 20_000_001)), stock=1000,
            status='ACTIVE' if status_roll < 7 else ('INACTIVE' if status_roll < 9 else 'ARCHIVED'),
            createdAt=ANCHOR-timedelta(days=rng.randrange(366, 400)), updatedAt=ANCHOR, version=1)
        products.append(product)
    order_base = samples('orders')[0]
    orders, reserved = [], Counter()
    for number in range(order_count):
        order = copy.deepcopy(order_base)
        customer = users[number % len(users)]
        created = datetime(2026, 1, 1, tzinfo=timezone.utc)+timedelta(seconds=rng.randrange(270*86400))
        event = created+timedelta(hours=48)
        status = 'COMPLETED' if number % 10 < 6 else ('PENDING', 'CONFIRMED', 'SHIPPING', 'CANCELLED')[number % 10-6]
        items = []
        for product in rng.sample(products, rng.randrange(2, 6)):
            category = category_by_id[product['categoryId']]
            quantity, price = rng.randrange(1, 4), Int64(int(product['price'])*97//100)
            selection = {}
            for attribute, selected in [('sizes', 'size'), ('colors', 'color')]:
                if product['attributes'].get(attribute):
                    selection[selected] = product['attributes'][attribute][0]
            items.append({'productId': product['_id'], 'sku': product['sku'], 'productName': product['name'],
                'image': product['images'][0] if product['images'] else '', 'productType': product['productType'],
                'categoryId': category['_id'], 'categoryName': category['name'],
                'attributesSnapshot': copy.deepcopy(product['attributes']), 'selectedAttributes': selection,
                'priceAtPurchase': price, 'quantity': quantity, 'lineTotal': Int64(price*quantity)})
            if status != 'CANCELLED':
                reserved[product['_id']] += quantity
        for field in ('paidAt', 'completedAt', 'paymentExpiresAt', 'cancelledAt', 'expiredAt', 'stockReleasedAt'):
            order.pop(field, None)
        subtotal = Int64(sum(item['lineTotal'] for item in items))
        order.update(_id=oid('order', number), orderCode=f'BENCH-2026-{number:06}', userId=customer['_id'],
            checkoutKey=f'benchmark-checkout-{number:06}', checkoutRequestHash=('0'*64),
            customerSnapshot={key: customer[key] for key in ('name', 'email', 'phone')},
            shippingAddress={key: value for key, value in customer['addresses'][0].items() if key != '_id'},
            items=items, subtotal=subtotal, shippingFee=Int64(30000), discount=Int64(0), total=Int64(subtotal+30000),
            paymentMethod='COD', paymentStatus='PAID' if status == 'COMPLETED' else 'UNPAID',
            paymentReviewRequired=False, orderStatus=status, version=1, createdAt=created, updatedAt=event)
        if status == 'COMPLETED':
            order.update(completedAt=event, paidAt=event)
        elif status == 'CANCELLED':
            order.update(cancelledAt=event, stockReleasedAt=event)
        orders.append(order)
    for product in products:
        product['stock'] -= reserved[product['_id']]
        assert product['stock'] >= 0
    return {'users': users, 'categories': categories, 'products': products, 'orders': orders,
            'carts': [], 'payment_attempts': []}, report_oracle(orders)


def setup(db, product_count, order_count):
    if db.list_collection_names():
        raise RuntimeError('Setup requires an empty owned benchmark database; use verified cleanup first')
    documents, oracle = generate(product_count, order_count)
    for name in NAMES:
        validator = json_util.loads((ROOT / f'database/validators/{name}.json').read_text(encoding='utf-8'))
        db.create_collection(name, validator=validator, validationLevel='strict', validationAction='error')
    for index in INDEXES:
        if index['kind'] == 'INVARIANT':
            db[index['collection']].create_index(list(index['keys'].items()), **index['options'])
    for name in NAMES:
        rows = documents[name]
        for offset in range(0, len(rows), 500):
            db[name].insert_many(rows[offset:offset+500], ordered=True)
    metadata = {'label': 'BENCHMARK DATASET — không phải seed chính thức', 'generatorSeed': SEED,
        'anchorUtc': ANCHOR, 'config': {'products': product_count, 'orders': order_count},
        'collections': data_hashes(db), 'oracle': oracle, 'window': {'from': START, 'to': END},
        'statusDistribution': dict(Counter(order['orderStatus'] for order in documents['orders']))}
    save(DATASET_FILE, metadata)
    return metadata
