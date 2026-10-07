"""Export Product/Order demo data to canonical Extended JSON, preserving BSON."""
import argparse
import hashlib
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'db'))
from common import ROOT, connection, write_ejson

def export(database):
    client, db = connection(database)
    try:
        manifest = {'database': db.name, 'format': 'CANONICAL_EXTENDED_JSON_ARRAY', 'collections': {}, 'credentialsIncluded': False}
        for name in ('products', 'orders'):
            path = ROOT / f'database/exports/{name}.json'
            docs = list(db[name].find({}).sort('_id', 1))
            write_ejson(path, docs)
            manifest['collections'][name] = {'file': path.name, 'count': len(docs), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        write_ejson('database/exports/manifest.json', manifest)
        print({name: item['count'] for name, item in manifest['collections'].items()})
    finally:
        client.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', default='ecommerce_dev')
    export(parser.parse_args().database)
