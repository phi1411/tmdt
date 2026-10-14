"""One-off, exact-ID FE-01A artifact cleanup; dry run unless --apply is supplied."""
import argparse
import copy
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from bson import ObjectId, json_util
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'backend'), str(ROOT / 'scripts/db')]
from app import create_app
from common import selected_indexes
from verify_auth_users import NAMES, fingerprint
from verify_integration_05ab import source_manifest

TARGET_EMAIL = 'khach_muy2lxi4@example.test'
KEEP_EMAIL = 'khachtest_1791374905461@example.test'
IDS = {'users': ObjectId('6ac637d404fbb6846343e36a'),
       'carts': ObjectId('6ac637e804fbb6846343e36c'),
       'orders': ObjectId('6ac637f004fbb6846343e36e')}
PRODUCT_ID = ObjectId('fccf6cac7ecfce2486e5eb09')
CATEGORY_ID = ObjectId('7197a05f34d94cd99a58f60b')


def encoded(value):
    return json_util.dumps(value, json_options=json_util.CANONICAL_JSON_OPTIONS, sort_keys=True)


def digest(value):
    return hashlib.sha256(encoded(value).encode()).hexdigest()


def snapshot(db, session=None, metadata=None):
    documents = {n: list(db[n].find({}, session=session).sort('_id', 1)) for n in NAMES}
    return {'counts': {n: len(rows) for n, rows in documents.items()}, 'documents': documents,
            **(metadata or {'collections': list(db.list_collections()),
                            'indexes': {n: list(db[n].list_indexes()) for n in NAMES}})}


def canonical_schema_check(state):
    assert {c['name'] for c in state['collections']} == set(NAMES)
    for collection in state['collections']:
        name, options = collection['name'], collection['options']
        canonical = json.loads((ROOT / f'database/validators/{name}.json').read_text(encoding='utf-8'))
        assert options['validator'] == canonical
        assert options['validationLevel'] == 'strict' and options['validationAction'] == 'error'
    specs = selected_indexes()
    assert len(specs) == 14
    for name in NAMES:
        actual = {i['name']: i for i in state['indexes'][name]}
        expected = {i['options']['name']: i for i in specs if i['collection'] == name}
        assert set(actual) == {'_id_', *expected}
        assert list(actual['_id_']['key'].items()) == [('_id', 1)]
        for key, spec in expected.items():
            assert list(actual[key]['key'].items()) == list(spec['keys'].items())
            assert all(actual[key].get(k) == v for k, v in spec['options'].items())
    return {'validators': 6, 'declaredIndexes': 14, 'idIndexes': 6, 'canonicalMatch': True}


def orphan_check(state):
    docs = state['documents']
    users, orders, products, categories = ({d['_id'] for d in docs[n]}
                                          for n in ('users', 'orders', 'products', 'categories'))
    result = {
        'cartsWithoutUser': sum(d['userId'] not in users for d in docs['carts']),
        'cartItemsWithoutProduct': sum(i['productId'] not in products for d in docs['carts'] for i in d['items']),
        'ordersWithoutUser': sum(d['userId'] not in users for d in docs['orders']),
        'orderItemsWithoutProduct': sum(i['productId'] not in products for d in docs['orders'] for i in d['items']),
        'attemptsWithoutUser': sum(d['userId'] not in users for d in docs['payment_attempts']),
        'attemptsWithoutOrder': sum(d['orderId'] not in orders for d in docs['payment_attempts']),
        'attemptOwnershipMismatch': sum(next((o['userId'] for o in docs['orders'] if o['_id'] == d['orderId']), None) != d['userId']
                                        for d in docs['payment_attempts']),
        'productsWithoutCategory': sum(d['categoryId'] not in categories for d in docs['products']),
    }
    assert not any(result.values()), result
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    baseline = json.loads((ROOT / '.local/phase06ab-before.json').read_text(encoding='utf-8'))
    delta = json.loads((ROOT / '.local/phase06ab-dev-delta.json').read_text(encoding='utf-8'))
    assert delta['additionalUserApprovedByUser'] and delta['disposition'] == 'KEEP'
    evidence = json.loads((ROOT / 'frontend/tests/e2e-results.json').read_text(encoding='utf-8'))
    assert any(TARGET_EMAIL in f.get('details', '') and f['status'] == 'PASS' for f in evidence['flows'])
    assert evidence['capturedOrder']['orderId'] == str(IDS['orders'])
    assert evidence['capturedOrder']['total'] == 2029500
    assert any('POST /cancel 200' in f['name'] and f['status'] == 'PASS' for f in evidence['flows'])
    runner = (ROOT / 'frontend/tests/e2e-customer-verification.mjs').read_text(encoding='utf-8')
    assert 'email: `khach_${uniqueId}@example.test`' in runner and 'Date.now().toString(36)' in runner
    manifest = json_util.loads((ROOT / 'database/evidence/seed-manifest-ecommerce_dev.json').read_text(encoding='utf-8'))
    seed_stock = next(x['final'] for x in manifest['inventory'] if x['productId'] == PRODUCT_ID)
    assert seed_stock == 97
    app = create_app()
    mongo = app.extensions['mongo']
    db = mongo.database
    try:
        assert db.name == 'ecommerce_dev'
        marker = json.loads((ROOT / '.local/ecommerce_dev.ownership.json').read_text(encoding='utf-8'))
        assert marker == {'project': str(ROOT), 'database': db.name, 'endpoint': 'localhost:27017/rs0'}
        hello = mongo.client.admin.command('hello')
        assert hello['setName'] == 'rs0' and hello['isWritablePrimary']
        source = source_manifest()
        before = snapshot(db)
        schema = canonical_schema_check(before)
        keep = next(d for d in before['documents']['users'] if d['email'] == KEEP_EMAIL)
        assert str(keep['_id']) == delta['additionalUserId']
        if fingerprint(db) == baseline['database']:
            assert not any(d['_id'] == oid for n, oid in IDS.items() for d in before['documents'][n])
            orphan_check(before)
            print(json.dumps({'status': 'ALREADY_CLEAN', 'fingerprint': baseline['database'], 'noWrites': True}))
            return
        target = next(d for d in before['documents']['users'] if d['_id'] == IDS['users'])
        assert target['email'] == TARGET_EMAIL and target['version'] == 3 and target['role'] == 'CUSTOMER'
        cart = next(d for d in before['documents']['carts'] if d['_id'] == IDS['carts'])
        order = next(d for d in before['documents']['orders'] if d['_id'] == IDS['orders'])
        assert cart['userId'] == order['userId'] == target['_id'] and cart['items'] == [] and cart['version'] == 3
        assert order['paymentMethod'] == 'COD' and order['paymentStatus'] == 'UNPAID'
        assert order['orderStatus'] == 'CANCELLED' and order['version'] == 2 and not order['paymentReviewRequired']
        assert order['stockReleasedAt'] == order['cancelledAt'] == order['updatedAt']
        assert len(order['items']) == 1 and order['items'][0]['productId'] == PRODUCT_ID and order['items'][0]['quantity'] == 2
        assert order['items'][0]['categoryId'] == CATEGORY_ID and order['total'] == 2029500
        for n in ('carts', 'orders', 'payment_attempts'):
            linked = [d for d in before['documents'][n] if d['userId'] == target['_id'] or d.get('orderId') == order['_id']]
            assert [d['_id'] for d in linked] == ([IDS[n]] if n in IDS else [])
        product = next(d for d in before['documents']['products'] if d['_id'] == PRODUCT_ID)
        category = next(d for d in before['documents']['categories'] if d['_id'] == CATEGORY_ID)
        assert product['stock'] == seed_stock and product['version'] == 4 and product['updatedAt'] == order['cancelledAt']
        assert category['version'] == 2 and category['updatedAt'] == order['createdAt']
        repairs = {'products': (product, {'version': 2, 'updatedAt': manifest['anchor']}),
                   'categories': (category, {'version': 1, 'updatedAt': category['createdAt']})}
        projected = copy.deepcopy(before)
        for n, oid in IDS.items():
            projected['documents'][n] = [d for d in projected['documents'][n] if d['_id'] != oid]
            projected['counts'][n] -= 1
        for n, (document, fields) in repairs.items():
            next(d for d in projected['documents'][n] if d['_id'] == document['_id']).update(fields)
        expected = {'digest': digest(projected), 'counts': projected['counts']}
        assert expected == baseline['database'], 'Projected exact cleanup differs from original 41-User baseline; refusing writes'
        orphans = orphan_check(projected)
        proof_files = ['frontend/tests/e2e-results.json', 'frontend/tests/e2e-customer-verification.mjs',
                       'docs/phase-fe-01a-integration-review.md', 'database/evidence/seed-manifest-ecommerce_dev.json']
        report = {'origin': 'FE-01A real-browser E2E, concurrent with 06AB; not backend smoke fixtures',
                  'provenance': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in proof_files},
                  'target': {'email': TARGET_EMAIL, **{n: str(oid) for n, oid in IDS.items()}, 'paymentAttempts': []},
                  'keptAccount': {'email': KEEP_EMAIL, 'id': str(keep['_id']), 'documentDigest': digest(keep)},
                  'before': {'digest': digest(before), 'counts': before['counts']}, 'expectedAfter': expected,
                  'metadataRestoration': {n: {'id': str(d['_id']), 'before': {k: d[k] for k in fields}, 'after': fields}
                                          for n, (d, fields) in repairs.items()},
                  'productStock': {'before': seed_stock, 'after': seed_stock, 'additionalStockRestoration': 0},
                  'canonicalSchemaIndexAudit': schema, 'orphanAudit': orphans, 'sourceManifest': source}
        if not args.apply:
            (ROOT / '.local/phase06ab-db-cleanup-plan.json').write_text(encoded(report) + '\n', encoding='utf-8')
            print(json.dumps({'status': 'DRY_RUN_PASS', 'before': report['before'], 'projectedAfter': expected,
                              'deleteCounts': {'users': 1, 'carts': 1, 'orders': 1, 'payment_attempts': 0}, 'stockChanged': False}))
            return
        backup = ROOT / '.local/phase06ab-db-cleanup-backup.ejson'
        assert subprocess.check_output(['git', 'check-ignore', str(backup)], cwd=ROOT).strip()
        with backup.open('x', encoding='utf-8') as file:
            file.write(encoded({'beforeFingerprint': report['before'], 'deletedDocuments': {'users': target, 'carts': cart, 'orders': order},
                                'restoredDocuments': {n: d for n, (d, _) in repairs.items()}}) + '\n')
        metadata = {k: before[k] for k in ('collections', 'indexes')}
        with mongo.client.start_session() as session:
            with session.start_transaction(read_concern=ReadConcern('snapshot'), write_concern=WriteConcern('majority')):
                assert digest(snapshot(db, session, metadata)) == report['before']['digest'], 'Concurrent document change; abort cleanup'
                for n, (doc, fields) in repairs.items():
                    result = db[n].update_one({'_id': doc['_id'], 'version': doc['version'], 'updatedAt': doc['updatedAt']},
                                             {'$set': fields}, session=session)
                    assert result.matched_count == result.modified_count == 1
                for n in ('orders', 'carts', 'users'):
                    assert db[n].delete_one({'_id': IDS[n]}, session=session).deleted_count == 1
                assert digest(snapshot(db, session, metadata)) == expected['digest'], 'Transaction result differs from baseline; abort cleanup'
        after = snapshot(db)
        assert {'digest': digest(after), 'counts': after['counts']} == expected
        assert next(d for d in after['documents']['users'] if d['_id'] == keep['_id']) == keep
        assert canonical_schema_check(after) == schema and orphan_check(after) == orphans
        assert source_manifest() == source
        assert all(mongo.client.ecommerce_test[n].count_documents({}) == 0 for n in NAMES)
        historical = copy.deepcopy(after)
        historical['documents']['users'] = [d for d in historical['documents']['users'] if d['_id'] != keep['_id']]
        historical['counts']['users'] -= 1
        assert digest(historical) == delta['historicalDigestWithoutOneAdditionalUser']
        report.update(status='PHASE 06AB DATABASE INTEGRITY PASS', after=fingerprint(db),
                      deletedCounts={'users': 1, 'carts': 1, 'orders': 1, 'payment_attempts': 0},
                      retainedAccountUnchanged=True, seedFingerprintWithoutRetainedAccount=digest(historical),
                      originalBaselineUnmodified=True, testDatabaseEmpty=True, backendAndContractUnchanged=True,
                      resetPerformed=False, reseedPerformed=False, applicationLogicModified=False,
                      completedAt=datetime.now(timezone.utc), gitHead=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip())
        (ROOT / 'backend/evidence/phase06ab-db-cleanup.json').write_text(encoded(report) + '\n', encoding='utf-8')
        print(json.dumps({'status': report['status'], 'after': report['after'], 'deletedCounts': report['deletedCounts'],
                          'keptAccountUnchanged': True, 'orphans': orphans, 'schema': schema}))
    finally:
        mongo.close()


if __name__ == '__main__':
    main()
