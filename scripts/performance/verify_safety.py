"""Meaningful real-DB validation and refusal probes; exact fixture cleanup."""
import copy
import json
from datetime import datetime, timezone

from bson import ObjectId
from pymongo.errors import WriteError
from perf_common import (ROOT, LOCAL, EVIDENCE, MARKER, EXPECTED_MARKER, NAMES, connection,
    benchmark_db, verify_owned_dataset, data_hashes, fingerprint, exclusive_lock, save)
from benchmark import cleanup


def main():
    checks = []
    with exclusive_lock():
        client, dev = connection('ecommerce_dev')
        before = fingerprint(dev)
        db = benchmark_db(client)
        metadata = verify_owned_dataset(db)
        fixture_id = ObjectId()
        try:
            try:
                verify_owned_dataset(dev)
                raise AssertionError('Dev DB unexpectedly accepted by benchmark guard')
            except RuntimeError:
                checks.append('dev database explicitly refused before cleanup validation')
            try:
                with exclusive_lock():
                    raise AssertionError('Concurrent lock unexpectedly acquired')
            except FileExistsError:
                checks.append('concurrent runner refused')
            marker_text = MARKER.read_text(encoding='utf-8')
            try:
                MARKER.write_text(json.dumps({**EXPECTED_MARKER, 'database': 'ecommerce_dev'}), encoding='utf-8')
                try:
                    benchmark_db(client)
                    raise AssertionError('Wrong marker unexpectedly accepted')
                except RuntimeError:
                    checks.append('wrong ownership marker refused')
            finally:
                MARKER.write_text(marker_text, encoding='utf-8')
            backup_path = LOCAL / 'ownership-probe.backup.json'
            assert not backup_path.exists()
            MARKER.rename(backup_path)
            try:
                try:
                    benchmark_db(client, claim=True)
                    raise AssertionError('Unmarked existing DB unexpectedly claimed')
                except RuntimeError:
                    checks.append('existing unmarked benchmark refused')
            finally:
                backup_path.rename(MARKER)
            invalid = copy.deepcopy(db.products.find_one({}))
            invalid.update(_id=fixture_id, sku='BENCH-GUARD-FOREIGN', slug='benchmark-guard-foreign', price=1.5)
            try:
                db.products.insert_one(invalid)
                raise AssertionError('Invalid BSON money unexpectedly accepted')
            except WriteError as error:
                assert error.code == 121
                checks.append('canonical validator rejects float money121')
            invalid['price'] = db.products.find_one({})['price']
            db.products.insert_one(invalid)
            try:
                try:
                    cleanup(db)
                    raise AssertionError('Foreign fixture unexpectedly cleaned up')
                except RuntimeError:
                    checks.append('changed dataset refuses destructive cleanup')
                assert set(db.list_collection_names()) == set(NAMES)
            finally:
                db.products.delete_one({'_id': fixture_id})
            assert data_hashes(db) == metadata['collections']
            for name in NAMES:
                assert db.command('validate', name, full=True)['valid']
            checks.append('six real collections BSON/index validation valid')
            product_orphans = list(db.products.aggregate([
                {'$lookup': {'from': 'categories', 'localField': 'categoryId', 'foreignField': '_id', 'as': 'reference'}},
                {'$match': {'reference.0': {'$exists': False}}}, {'$count': 'count'}]))
            order_orphans = list(db.orders.aggregate([
                {'$lookup': {'from': 'users', 'localField': 'userId', 'foreignField': '_id', 'as': 'reference'}},
                {'$match': {'reference.0': {'$exists': False}}}, {'$count': 'count'}]))
            item_orphans = list(db.orders.aggregate([
                {'$unwind': '$items'},
                {'$lookup': {'from': 'products', 'localField': 'items.productId', 'foreignField': '_id', 'as': 'reference'}},
                {'$match': {'reference.0': {'$exists': False}}}, {'$count': 'count'}]))
            assert not product_orphans and not order_orphans and not item_orphans
            assert db.products.count_documents({'stock': {'$lt': 0}}) == 0
            assert db.orders.count_documents({'$expr': {'$ne': ['$subtotal', {'$sum': '$items.lineTotal'}]}}) == 0
            assert db.orders.count_documents({'$expr': {'$ne': ['$total', {'$add': ['$subtotal', '$shippingFee']}]}}) == 0
            checks.append('real reference/money/stock invariants pass')
            verify_owned_dataset(db)
        finally:
            db.products.delete_one({'_id': fixture_id})
            after = fingerprint(dev)
            client.close()
        assert before == after
        save(EVIDENCE / 'safety-verification.json', {'status': 'PERFORMANCE_SAFETY_PASS',
            'recordedAtUtc': datetime.now(timezone.utc), 'checks': checks, 'devBefore': before, 'devAfter': after,
            'benchmarkDatasetRestoredExactly': True, 'devUnchanged': True})
    print('Safety probes PASS:', len(checks), 'checks; dev unchanged')


if __name__ == '__main__':
    main()
