"""Owned roundtrip DB only: import canonical EJSON and compare BSON documents."""
import argparse
import hashlib
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'db'))
from common import ROOT, COLLECTIONS, connection, apply_foundation, read_ejson, write_ejson

def roundtrip(reset=False):
    manifest = read_ejson(ROOT / 'database/exports/manifest.json')
    data = {}
    for name, entry in manifest['collections'].items():
        if name not in {'products', 'orders'} or entry['file'] != f'{name}.json':
            raise ValueError('Only Product/Order exports allowed')
        path = ROOT / 'database/exports' / entry['file']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256'], 'Export checksum mismatch'
        data[name] = read_ejson(path)
        assert len(data[name]) == entry['count']
    assert set(data) == {'products', 'orders'}
    if not reset:
        print({'mode': 'DRY_RUN', 'target': 'ecommerce_roundtrip', 'counts': {k: len(v) for k, v in data.items()}})
        return
    client, db = connection('ecommerce_roundtrip', claim=True)
    try:
        apply_foundation(db)
        for name in COLLECTIONS:
            ids = {doc['_id'] for doc in data.get(name, [])}
            assert all(d['_id'] in ids for d in db[name].find({}, {'_id': 1})), f'Unexpected data in roundtrip {name}; refusing reset'
        def import_transaction(session):
            for name, docs in data.items():
                db[name].delete_many({}, session=session)
                db[name].insert_many(docs, session=session)
        with client.start_session() as session:
            session.with_transaction(import_transaction, write_concern=db.write_concern)
        results = {}
        for name, docs in data.items():
            actual = list(db[name].find({}).sort('_id', 1))
            assert actual == docs, f'BSON roundtrip mismatch in {name}'
            results[name] = {'count': len(actual), 'fullBsonEquality': True, 'validatorApplied': True}
        write_ejson('database/evidence/roundtrip-results.json', {'status': 'LIVE_ROUNDTRIP_PASS', 'database': db.name, 'results': results, 'scope': 'Product/Order backup slice; referenced Users/Categories intentionally not cloned. No complete application DB claim.'})
        print(results)
    finally:
        client.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reset', action='store_true')
    roundtrip(parser.parse_args().reset)
