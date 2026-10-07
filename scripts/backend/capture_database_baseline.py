"""Capture a read-only pre-test fingerprint; never replace existing evidence."""
import hashlib
import sys
from pathlib import Path
from bson import json_util

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app import create_app


if __name__ == '__main__':
    destination = ROOT / '.local/phase04-db-before.json'
    if destination.exists():
        raise SystemExit('Baseline already exists; keep the original pre-test evidence')
    app = create_app()
    try:
        database = app.extensions['mongo'].database
        names = ('users', 'categories', 'products', 'carts', 'orders', 'payment_attempts')
        snapshot = {
            'counts': {name: database[name].count_documents({}) for name in names},
            'documents': {name: list(database[name].find({}).sort('_id', 1)) for name in names},
            'collections': list(database.list_collections()),
            'indexes': {name: list(database[name].list_indexes()) for name in names},
        }
        digest = hashlib.sha256(json_util.dumps(snapshot, json_options=json_util.CANONICAL_JSON_OPTIONS, sort_keys=True).encode()).hexdigest()
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('x', encoding='utf-8') as output:
            output.write(json_util.dumps({'digest': digest, 'counts': snapshot['counts']}) + '\n')
        print('Pre-test database fingerprint saved locally; MongoDB was only read')
    finally:
        app.extensions['mongo'].close()
