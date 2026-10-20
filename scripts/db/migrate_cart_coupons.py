"""Additive Cart/Order validators only; never rewrite documents or indexes."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from bson import json_util
from common import ROOT, connection


def fingerprint(db):
    data = {name: {'documents': list(db[name].find().sort('_id', 1)),
                   'indexes': list(db[name].list_indexes())} for name in ('carts', 'orders')}
    return hashlib.sha256(json_util.dumps(data, json_options=json_util.CANONICAL_JSON_OPTIONS,
                                         sort_keys=True).encode()).hexdigest()


def migrate(db, apply=False):
    names = ('carts', 'orders')
    options = {name: db[name].options() for name in names}
    validators = {name: json.loads((ROOT / f'database/validators/{name}.json').read_text(encoding='utf-8'))
                  for name in names}
    for name in names:
        if db[name].count_documents({'$nor': [validators[name]]}):
            raise RuntimeError(f'{name}: existing documents do not satisfy new validator')
    before = fingerprint(db)
    if not apply:
        return {'database': db.name, 'compatible': True, 'applied': False, 'fingerprint': before}
    backup = ROOT / '.local/coupon-migration' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup.mkdir(parents=True)
    (backup / 'validators-before.json').write_text(json_util.dumps(options, indent=2), encoding='utf-8')
    applied = []
    try:
        for name in names:
            db.command('collMod', name, validator=validators[name], validationLevel='strict', validationAction='error')
            applied.append(name)
        after = fingerprint(db)
        if after != before:
            raise RuntimeError('Concurrent document/index writes detected; review migration evidence')
        return {'database': db.name, 'compatible': True, 'applied': True,
                'documentsAndIndexesUnchanged': True, 'fingerprint': after}
    except Exception:
        for name in reversed(applied):
            old = options[name]
            db.command('collMod', name, validator=old.get('validator', {}),
                       validationLevel=old.get('validationLevel', 'strict'),
                       validationAction=old.get('validationAction', 'error'))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', choices=['ecommerce_test', 'ecommerce_dev'], default='ecommerce_test')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    client, db = connection(args.database, claim=True)
    try:
        print(json.dumps(migrate(db, args.apply), ensure_ascii=False))
    finally:
        client.close()
