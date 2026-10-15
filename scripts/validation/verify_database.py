"""Live MongoDB phase-03 checks. No mock, no business endpoints, no benchmark claim."""
from __future__ import annotations
import argparse
import copy
import os
import sys
from collections import Counter, defaultdict
from datetime import timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'db'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'seed'))
from common import ROOT, COLLECTIONS, connection, apply_foundation, selected_indexes, read_json, read_ejson, write_ejson, pipeline, digest, normalize, oid
from seed import ANCHOR, START, build_catalog, expected_ids
from bson import ObjectId, json_util
from bson.int64 import Int64
from argon2 import PasswordHasher, extract_parameters
from pymongo.errors import OperationFailure, DuplicateKeyError

def content_digest(data):
    clean = copy.deepcopy(data)
    for user in clean.get('users', []):
        user.pop('passwordHash', None)
    payload = json_util.dumps(clean, json_options=json_util.CANONICAL_JSON_OPTIONS, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    import hashlib
    return hashlib.sha256(payload.encode()).hexdigest()

def validate_documents(db):
    rows = {name: list(db[name].find({}).sort('_id', 1)) for name in COLLECTIONS}
    expected_counts = {'users': 40, 'categories': 3, 'products': len(rows['products']), 'carts': 0, 'orders': 100, 'payment_attempts': 30}
    if 'reviews' in rows:
        expected_counts['reviews'] = len(rows['reviews'])
    assert {k: len(v) for k, v in rows.items()} == expected_counts
    expected = expected_ids()
    for name, docs in rows.items():
        if name not in {'products', 'reviews'}:
            assert {d['_id'] for d in docs} == expected[name], f'{name} fixture IDs'
        else:
            assert expected[name].issubset({d['_id'] for d in docs}), f'{name} fixture IDs'
        for doc in docs:
            assert isinstance(doc['_id'], ObjectId) and type(doc['schemaVersion']) is int
            assert doc['createdAt'] <= doc['updatedAt']
    users = {d['_id']: d for d in rows['users']}
    cats = {d['_id']: d for d in rows['categories']}
    products = {d['_id']: d for d in rows['products']}
    orders = {d['_id']: d for d in rows['orders']}
    _, base_products, _ = build_catalog()
    base = {p['_id']: p for p in base_products}
    for t in ('ELECTRONICS', 'FASHION', 'HOME_APPLIANCE'):
        assert Counter(p['productType'] for p in products.values())[t] >= 60
    assert sum(u['role'] == 'ADMIN' for u in users.values()) == 1
    hasher = PasswordHasher()
    password = os.environ['SEED_DEMO_PASSWORD']
    for user in users.values():
        assert user['email'] == user['email'].strip().lower()
        assert user['defaultAddressId'] in {a['_id'] for a in user['addresses']}
        assert hasher.verify(user['passwordHash'], password)
        params = extract_parameters(user['passwordHash'])
        assert (params.memory_cost, params.time_cost, params.parallelism) == (19456, 2, 1)
    for product in products.values():
        assert product['productType'] == cats[product['categoryId']]['productType']
        assert product['nameNormalized'] == normalize(product['name'])
        assert product['brandNormalized'] == normalize(product['brand'])
        assert type(product['price']) is Int64 and type(product['stock']) is int
        assert product['images'] and all(u.startswith('https://') and 'localhost' not in u for u in product['images'])
    sold, reserved, released = Counter(), Counter(), Counter()
    for order in orders.values():
        assert order['userId'] in users and users[order['userId']]['role'] == 'CUSTOMER'
        assert 2 <= len(order['items']) <= 5
        assert len({x['productId'] for x in order['items']}) == len(order['items'])
        for field in ('subtotal', 'total', 'shippingFee', 'discount'):
            assert type(order[field]) is Int64
        for item in order['items']:
            assert item['productId'] in products and item['categoryId'] in cats
            product = base[item['productId']]
            for field, origin in [('sku', 'sku'), ('productName', 'name'), ('productType', 'productType'), ('categoryId', 'categoryId'), ('attributesSnapshot', 'attributes'), ('priceAtPurchase', 'price')]:
                assert item[field] == product[origin], f'Snapshot origin mismatch {field}'
            assert item['categoryName'] == cats[item['categoryId']]['name']
            assert item['image'] == product['images'][0]
            assert type(item['priceAtPurchase']) is Int64 and type(item['lineTotal']) is Int64 and type(item['quantity']) is int
            assert 1 <= item['quantity'] <= 3
            assert item['lineTotal'] == item['priceAtPurchase'] * item['quantity']
            for option, attr in [('size', 'sizes'), ('color', 'colors')]:
                if product['productType'] == 'FASHION' and product['attributes'].get(attr):
                    assert item['selectedAttributes'].get(option) in product['attributes'][attr]
            target = sold if order['orderStatus'] == 'COMPLETED' else released if order['orderStatus'] in {'CANCELLED', 'EXPIRED'} else reserved
            target[item['productId']] += item['quantity']
        assert order['subtotal'] == sum(i['lineTotal'] for i in order['items'])
        assert order['discount'] == 0 and order['shippingFee'] == 30000
        assert order['total'] == order['subtotal'] + order['shippingFee'] - order['discount']
        for field in ('completedAt', 'paidAt', 'cancelledAt', 'expiredAt', 'stockReleasedAt'):
            if field in order:
                assert order['createdAt'] <= order[field] <= order['updatedAt']
        status, method, payment = order['orderStatus'], order['paymentMethod'], order['paymentStatus']
        if status == 'COMPLETED':
            assert payment == 'PAID' and order['paidAt'] <= order['completedAt'] < ANCHOR
        elif status in {'CANCELLED', 'EXPIRED'}:
            event = 'cancelledAt' if status == 'CANCELLED' else 'expiredAt'
            assert order['stockReleasedAt'] == order[event]
            if status == 'EXPIRED':
                assert method == 'VNPAY' and payment == 'FAILED' and order['expiredAt'] >= order['paymentExpiresAt']
        if method == 'COD':
            assert 'paymentExpiresAt' not in order and payment == ('PAID' if status == 'COMPLETED' else 'UNPAID')
        else:
            assert order['total'] <= 9_999_999_999 and order['paymentExpiresAt'] == order['createdAt'] + timedelta(minutes=15)
            if status == 'PENDING':
                assert payment == 'PENDING' and order['createdAt'] <= ANCHOR < order['paymentExpiresAt']
    attempts_by_order = Counter()
    for attempt in rows['payment_attempts']:
        order = orders[attempt['orderId']]
        request = attempt['paymentRequest']
        attempts_by_order[order['_id']] += 1
        assert order['paymentMethod'] == 'VNPAY' and attempt['userId'] == order['userId']
        assert type(attempt['amount']) is Int64 and type(request['amountScaled']) is Int64
        assert attempt['amount'] == order['total'] and request['amountScaled'] == 100*order['total']
        assert attempt['txnRef'] == request['txnRef'] and request['createdAt'] == attempt['createdAt']
        assert attempt['expiresAt'] == order['paymentExpiresAt'] == request['expiresAt']
        if attempt['status'] == 'SUCCEEDED':
            assert order['paymentStatus'] == 'PAID' and attempt['verifiedAt'] == order['paidAt'] < attempt['expiresAt']
            assert attempt['responseCode'] == attempt['transactionStatus'] == '00'
        elif attempt['status'] == 'EXPIRED':
            assert order['orderStatus'] == 'EXPIRED' and attempt['expiredAt'] == order['expiredAt']
        else:
            assert order['orderStatus'] == 'PENDING' and attempt['status'] == 'PENDING'
    for order in orders.values():
        assert attempts_by_order[order['_id']] == (1 if order['paymentMethod'] == 'VNPAY' else 0)
    manifest = read_ejson(ROOT / f'database/evidence/seed-manifest-{db.name}.json')
    for entry in manifest['inventory']:
        key = entry['productId']
        assert entry['sold'] == sold[key] and entry['reserved'] == reserved[key] and entry['released'] == released[key]
        # Each released unit was first held and then restored once: net effect zero.
        assert entry['initial'] - sold[key] - reserved[key] - released[key] + released[key] == entry['final'] == products[key]['stock'] >= 0
    demo = next(i for i in orders[oid('order', 0)]['items'] if i['productId'] == oid('product', 0))
    assert demo['priceAtPurchase'] == 10_000_000 and products[oid('product', 0)]['price'] == 12_000_000
    return rows

def live_constraints(client, test_db, rows):
    apply_foundation(test_db)
    assert not any(test_db[n].count_documents({}) for n in COLLECTIONS), 'Constraint probe database must be empty'
    accepted, rejected, duplicates = [], [], []
    examples = {name: copy.deepcopy(docs[0]) for name, docs in rows.items() if docs}
    user = rows['users'][0]
    examples['carts'] = {'_id': ObjectId(), 'schemaVersion': 1, 'createdAt': START, 'updatedAt': START, 'userId': user['_id'], 'version': 1, 'items': []}
    if 'reviews' not in examples and rows['products'] and rows['orders']:
        examples['reviews'] = {
            '_id': ObjectId(),
            'schemaVersion': 1,
            'createdAt': START,
            'updatedAt': START,
            'productId': rows['products'][0]['_id'],
            'orderId': rows['orders'][0]['_id'],
            'userId': user['_id'],
            'orderCode': 'ORD-DEMO-001',
            'rating': 5,
            'reviewText': 'San pham tuyet voi',
            'status': 'VISIBLE'
        }

    def probe(name, doc, expected_code=None, label=''):
        doc = copy.deepcopy(doc)
        doc['_id'] = ObjectId()
        with client.start_session() as session:
            session.start_transaction()
            try:
                test_db[name].insert_one(doc, session=session)
                assert expected_code is None, f'Invalid document accepted: {label}'
                accepted.append(label)
            except OperationFailure as exc:
                assert expected_code == exc.code, f'{label}: expected {expected_code}, got {exc.code}'
                rejected.append({'case': label, 'code': exc.code})
            finally:
                session.abort_transaction()
    for name, base in examples.items():
        probe(name, base, label=f'{name}:valid')
        bad = copy.deepcopy(base); bad.pop('schemaVersion')
        probe(name, bad, 121, f'{name}:required')
        bad = copy.deepcopy(base); bad['schemaVersion'] = 99
        probe(name, bad, 121, f'{name}:enum')
        bad = copy.deepcopy(base); bad['version'] = '1'
        probe(name, bad, 121, f'{name}:type')
    for kind, field, invalid in [('ELECTRONICS', 'ram', 8), ('FASHION', 'sizes', 'M'), ('HOME_APPLIANCE', 'power', 800)]:
        base = copy.deepcopy(next(p for p in rows['products'] if p['productType'] == kind))
        probe('products', base, label=f'{kind}:polymorphic')
        base['attributes'][field] = invalid
        probe('products', base, 121, f'{kind}:wrong-attribute')
    for name, field, value in [('users', 'role', 'SELLER'), ('categories', 'productType', 'OTHER'), ('products', 'productType', 'OTHER'), ('orders', 'orderStatus', 'PROCESSING'), ('payment_attempts', 'provider', 'REAL_PAYMENT')]:
        bad = copy.deepcopy(examples[name]); bad[field] = value
        probe(name, bad, 121, f'{name}:business-enum')
    completed = next(o for o in rows['orders'] if o['orderStatus'] == 'COMPLETED')
    for label, mutate in [('missing-snapshot-price', lambda o: o['items'][0].pop('priceAtPurchase')), ('missing-completedAt', lambda o: o.pop('completedAt')), ('completed-unpaid', lambda o: o.update(paymentStatus='UNPAID')), ('price-int-instead-long', lambda o: o['items'][0].update(priceAtPurchase=1000))]:
        bad = copy.deepcopy(completed); mutate(bad)
        probe('orders', bad, 121, label)
    base = copy.deepcopy(examples['carts'])
    base['items'] = [{'lineId': 'a'*64, 'productId': rows['products'][0]['_id'], 'quantity': 0, 'selectedAttributes': {}}]
    probe('carts', base, 121, 'cart-zero-quantity')
    bad = copy.deepcopy(examples['products']); bad['attributes']['$where'] = 'bad'
    probe('products', bad, 121, 'unsafe-attribute-key')
    bad = copy.deepcopy(examples['payment_attempts']); bad['cardNumber'] = 'fixture-not-allowed'
    probe('payment_attempts', bad, 121, 'payment-sensitive-field')
    for spec in selected_indexes():
        if not spec['options'].get('unique'):
            continue
        name = spec['collection']
        first = copy.deepcopy(next(a for a in rows[name] if a['status'] == 'SUCCEEDED')) if name == 'payment_attempts' else copy.deepcopy(examples[name])
        if spec['name'] == 'uq_attempts_pending_order':
            first = copy.deepcopy(next(a for a in rows[name] if a['status'] == 'PENDING'))
        elif spec['name'] == 'uq_attempts_provider_txn':
            first = copy.deepcopy(next(a for a in rows[name] if a['status'] == 'SUCCEEDED'))
        second = copy.deepcopy(first)
        first['_id'], second['_id'] = ObjectId(), ObjectId()
        # Change other unique keys so the reported conflict is this constraint.
        for key, value in [('email', 'probe2@example.test'), ('slug', 'probe-second'), ('sku', 'PROBE-SECOND'), ('orderCode', 'PROBE-SECOND'), ('checkoutKey', 'probe-key-second'), ('txnRef', 'PROBESECOND'), ('attemptKey', 'probe-key-second'), ('providerTransactionNo', '999999999')]:
            if key in second and key not in spec['keys']:
                second[key] = value
        if name == 'payment_attempts' and 'txnRef' not in spec['keys']:
            second['paymentRequest']['txnRef'] = second['txnRef']
        if name == 'payment_attempts' and 'orderId' not in spec['keys']:
            second['orderId'] = ObjectId()
        with client.start_session() as session:
            session.start_transaction()
            try:
                test_db[name].insert_one(first, session=session)
                try:
                    test_db[name].insert_one(second, session=session)
                except DuplicateKeyError as exc:
                    assert spec['name'] in str(exc), f'Wrong index conflict for {spec["name"]}'
                    duplicates.append({'index': spec['name'], 'code': exc.code})
                else:
                    raise AssertionError(f'Unique constraint not enforced: {spec["name"]}')
            finally:
                session.abort_transaction()
    assert not any(test_db[n].count_documents({}) for n in COLLECTIONS)
    return {'accepted': accepted, 'rejected': rejected, 'uniqueRejected': duplicates, 'probesRolledBack': True}

def aggregates(db, rows):
    names = ['revenue-day', 'revenue-month', 'top-products', 'category-revenue', 'sales-summary', 'order-count', 'order-status', 'customer-count']
    stages = {name: pipeline(name, START, ANCHOR) for name in names}
    out = {name: list(db['users' if name == 'customer-count' else 'orders'].aggregate(stages[name])) for name in names}
    qualified = [o for o in rows['orders'] if o['orderStatus'] == 'COMPLETED' and o['paymentStatus'] == 'PAID' and START <= o['completedAt'] < ANCHOR]
    revenue = sum(o['subtotal'] - o['discount'] for o in qualified)
    quantity = sum(i['quantity'] for o in qualified for i in o['items'])
    assert out['sales-summary'] == [{'totalRevenue': revenue, 'qualifiedOrders': 60, 'totalProductsSold': quantity}]
    buckets = {unit: defaultdict(lambda: {'revenue': 0, 'orders': 0}) for unit in ('day', 'month')}
    product_stats, category_stats = {}, Counter()
    for order in sorted(qualified, key=lambda o: (o['completedAt'], str(o['_id'])), reverse=True):
        date = order['completedAt'].astimezone(ZoneInfo('Asia/Ho_Chi_Minh'))
        for unit in ('day', 'month'):
            bucket = date.replace(hour=0, minute=0, second=0, microsecond=0, **({'day': 1} if unit == 'month' else {}))
            buckets[unit][bucket]['revenue'] += order['subtotal']-order['discount']; buckets[unit][bucket]['orders'] += 1
        for item in order['items']:
            stats = product_stats.setdefault(item['productId'], {'productId': item['productId'], 'productName': item['productName'], 'quantity': 0, 'revenue': 0})
            stats['quantity'] += item['quantity']; stats['revenue'] += item['lineTotal']
            category_stats[item['categoryId']] += item['lineTotal']
    for unit in ('day', 'month'):
        assert out[f'revenue-{unit}'] == [{'_id': key, **value} for key, value in sorted(buckets[unit].items())]
    assert out['top-products'] == sorted(product_stats.values(), key=lambda x: (-x['quantity'], -x['revenue'], str(x['productId'])))[:5]
    assert {r['categoryId']: r['revenue'] for r in out['category-revenue']} == dict(category_stats)
    assert sum(r['revenue'] for r in out['category-revenue']) == revenue
    assert sum(o['total'] for o in qualified)-revenue == 1_800_000
    assert list(out['order-count'][0].values()) == [100]
    assert list(out['customer-count'][0].values()) == [39]
    assert {r['status']: r['count'] for r in out['order-status']} == dict(Counter(o['orderStatus'] for o in rows['orders']))
    # Change the current catalog temporarily; pipeline results must stay identical.
    with db.client.start_session() as session:
        session.start_transaction()
        try:
            db.products.update_one({'_id': oid('product', 0)}, {'$set': {'price': Int64(99_000_000), 'name': 'Tên hiện tại tạm để kiểm tra snapshot'}}, session=session)
            for name in names[:5]:
                assert list(db.orders.aggregate(stages[name], session=session)) == out[name], f'Historical query depends on current Product: {name}'
        finally:
            session.abort_transaction()
    write_ejson('database/evidence/aggregation-results.json', {'database': db.name, 'from': START, 'toExclusive': ANCHOR, 'timezone': 'Asia/Ho_Chi_Minh', 'pipelinesExecuted': stages, 'results': out, 'expectedIndependentlyVerified': True, 'snapshotPriceMutationRolledBack': True})
    return out

def explain_baseline(db):
    query = {'status': 'ACTIVE', 'categoryId': oid('category', 0), 'price': {'$gte': Int64(1_000_000), '$lte': Int64(20_000_000)}}
    command = {'find': 'products', 'filter': query, 'sort': {'price': 1, '_id': 1}, 'limit': 10}
    runs = {}
    for name, hint in [('planner', None), ('natural', {'$natural': 1}), ('namedIndex', 'ix_products_category_price')]:
        find = copy.deepcopy(command)
        if hint is not None:
            find['hint'] = hint
        result = db.command('explain', find, verbosity='executionStats')
        stats = result['executionStats']
        plan = result['queryPlanner']['winningPlan']
        def stages(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    if key == 'stage': yield child
                    else: yield from stages(child)
            elif isinstance(value, list):
                for child in value: yield from stages(child)
        runs[name] = {'winningPlan': plan, 'stages': list(stages(plan)), **{k: stats[k] for k in ('nReturned', 'totalDocsExamined', 'totalKeysExamined', 'executionTimeMillis')}, 'rawExplain': result}
    assert 'IXSCAN' in runs['namedIndex']['stages'] and 'COLLSCAN' in runs['natural']['stages']
    assert runs['planner']['nReturned'] == runs['natural']['nReturned'] == runs['namedIndex']['nReturned']
    natural_rows = list(db.products.find(query).sort([('price', 1), ('_id', 1)]).limit(10).hint([('$natural', 1)]))
    assert natural_rows == list(db.products.find(query).sort([('price', 1), ('_id', 1)]).limit(10).hint('ix_products_category_price'))
    write_ejson('database/evidence/explain-baseline.json', {'database': db.name, 'command': command, 'runs': runs, 'fullBenchmark': False, 'timingInterpretation': 'Single execution on 180 documents; 0ms is timer resolution, not a latency guarantee'})
    return {name: {k: v for k, v in run.items() if k != 'rawExplain'} for name, run in runs.items()}

def verify(database):
    client, db = connection(database)
    test_client, test_db = connection('ecommerce_test', claim=True)
    try:
        assert set(db.list_collection_names()) == set(COLLECTIONS)
        assert client.server_info()['version'].startswith('8.0.')
        configs = {row['name']: row['options'] for row in db.list_collections()}
        for name in COLLECTIONS:
            assert configs[name]['validator'] == read_json(f'database/validators/{name}.json')
            assert configs[name]['validationLevel'] == 'strict' and configs[name]['validationAction'] == 'error'
        indexes = {name: list(db[name].list_indexes()) for name in COLLECTIONS}
        for name in COLLECTIONS:
            wanted = [i for i in selected_indexes() if i['collection'] == name]
            actual = {i['name']: i for i in indexes[name]}
            assert set(actual) == {'_id_'} | {i['name'] for i in wanted}
            for spec in wanted:
                assert list(actual[spec['name']]['key'].items()) == list(spec['keys'].items())
                for option in ('unique', 'partialFilterExpression'):
                    if option in spec['options']: assert actual[spec['name']][option] == spec['options'][option]
        rows = validate_documents(db)
        before = content_digest(rows)
        probes = live_constraints(test_client, test_db, rows)
        output = aggregates(db, rows)
        explain = explain_baseline(db)
        assert before == content_digest({name: list(db[name].find({}).sort('_id', 1)) for name in COLLECTIONS})
        status = client.admin.command('replSetGetStatus')
        report = {'status': 'LIVE_MONGODB_PASS', 'mongodbVersion': client.server_info()['version'], 'pythonVersion': sys.version.split()[0], 'database': db.name, 'replicaSet': status['set'], 'replicaMembers': [{k: m[k] for k in ('name', 'health', 'stateStr')} for m in status['members']], 'storageEngine': client.admin.command('serverStatus')['storageEngine']['name'], 'collections': list(COLLECTIONS), 'validatorsApplied': len(COLLECTIONS), 'validatorTests': probes, 'counts': {k: len(v) for k, v in rows.items()}, 'productDistribution': dict(Counter(p['productType'] for p in rows['products'])), 'orderStatusDistribution': dict(Counter(o['orderStatus'] for o in rows['orders'])), 'paymentMethodDistribution': dict(Counter(o['paymentMethod'] for o in rows['orders'])), 'paymentStatusDistribution': dict(Counter(o['paymentStatus'] for o in rows['orders'])), 'attemptStatusDistribution': dict(Counter(a['status'] for a in rows['payment_attempts'])), 'orderItemCountDistribution': dict(Counter(str(len(o['items'])) for o in rows['orders'])), 'productsWithImages': sum(bool(p['images']) for p in rows['products']), 'passwordsVerified': 40, 'snapshotOriginVerified': True, 'stockReconciled': True, 'aggregationsExecuted': 8, 'salesSummary': output['sales-summary'], 'revenueByMonth': output['revenue-month'], 'top5': output['top-products'], 'actualIndexes': indexes, 'declaredIndexes': len(selected_indexes()), 'automaticIdIndexes': len(COLLECTIONS), 'explain': explain, 'contentDigestExcludingSaltedPasswords': before, 'businessFeaturesImplemented': False, 'frontendImplemented': False, 'fullBenchmarkRun': False}
        write_ejson('database/evidence/verification.json', report)
        print({'status': report['status'], 'counts': report['counts'], 'accepted': len(probes['accepted']), 'invalidRejected': len(probes['rejected']), 'uniqueRejected': len(probes['uniqueRejected']), 'salesSummary': report['salesSummary'], 'digest': before})
        return report
    finally:
        client.close(); test_client.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', default='ecommerce_dev')
    verify(parser.parse_args().database)
