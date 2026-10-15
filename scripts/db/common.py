"""Development database tooling only; no application/service implementation."""
from __future__ import annotations
import hashlib
import json
import os
import sys
import unicodedata
from pathlib import Path
from urllib.parse import urlparse
from bson import ObjectId, json_util
from bson.json_util import CANONICAL_JSON_OPTIONS
from pymongo import MongoClient
from pymongo.write_concern import WriteConcern

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).resolve().parents[2]
COLLECTIONS = ('users', 'categories', 'products', 'carts', 'orders', 'payment_attempts', 'reviews')
ALLOWED_DATABASES = {'ecommerce_dev', 'ecommerce_test', 'ecommerce_roundtrip'}
WORKLOAD_INDEXES = {'ix_products_category_price', 'ix_orders_user_history', 'ix_orders_qualified_completed'}

def load_env():
    path = ROOT / '.env'
    if path.exists():
        for line in path.read_text(encoding='utf-8').splitlines():
            if line.strip() and not line.lstrip().startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip())

def connection(database=None, claim=False):
    load_env()
    name = database or os.environ.get('MONGODB_DB', 'ecommerce_dev')
    if name not in ALLOWED_DATABASES:
        raise ValueError('Tooling restricted to ecommerce_dev/test/roundtrip')
    uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/?replicaSet=rs0')
    parsed = urlparse(uri)
    if parsed.scheme != 'mongodb' or parsed.hostname not in {'localhost', '127.0.0.1'} or parsed.port not in {None, 27017}:
        raise ValueError('Only this local rs0 endpoint is allowed')
    client = MongoClient(uri, tz_aware=True, serverSelectionTimeoutMS=10000)
    hello = client.admin.command('hello')
    if hello.get('setName') != 'rs0' or not hello.get('isWritablePrimary'):
        raise RuntimeError('Expected a healthy writable primary in rs0')
    db = client.get_database(name, write_concern=WriteConcern('majority'))
    marker = ROOT / '.local' / f'{name}.ownership.json'
    if claim:
        if not marker.exists():
            if db.list_collection_names():
                raise RuntimeError('Refusing to claim an existing unmarked database')
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.write_text(json.dumps({'project': str(ROOT), 'database': name, 'endpoint': 'localhost:27017/rs0'}), encoding='utf-8')
        expected = {'project': str(ROOT), 'database': name, 'endpoint': 'localhost:27017/rs0'}
        if json.loads(marker.read_text(encoding='utf-8')) != expected:
            raise RuntimeError('Database ownership marker mismatch')
    return client, db

def read_json(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))

def write_ejson(path, value):
    path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json_util.dumps(value, json_options=CANONICAL_JSON_OPTIONS, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def read_ejson(path):
    return json_util.loads(Path(path).read_text(encoding='utf-8'), json_options=CANONICAL_JSON_OPTIONS.with_options(tz_aware=True))

def oid(namespace, number):
    return ObjectId(hashlib.sha256(f'tmdt:phase03:{namespace}:{number}'.encode()).hexdigest()[:24])

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()

def normalize(value):
    value = unicodedata.normalize('NFKD', value.casefold().replace('đ', 'd'))
    return ' '.join(''.join(c for c in value if not unicodedata.combining(c)).split())

def selected_indexes():
    return [i for i in read_json('database/indexes/candidate-indexes.json')['indexes'] if i['kind'] == 'INVARIANT' or i['name'] in WORKLOAD_INDEXES]

def apply_foundation(db, collections=COLLECTIONS):
    existing = set(db.list_collection_names())
    if existing - set(COLLECTIONS):
        raise RuntimeError('Unexpected business collections; refusing to modify')
    for name in collections:
        validator = read_json(f'database/validators/{name}.json')
        if name not in existing:
            db.create_collection(name, validator=validator, validationLevel='strict', validationAction='error')
        else:
            db.command('collMod', name, validator=validator, validationLevel='strict', validationAction='error')
    for index in selected_indexes():
        if index['collection'] in collections:
            db[index['collection']].create_index(list(index['keys'].items()), **index['options'])

def pipeline(name, start, end):
    stages = read_ejson(ROOT / f'database/aggregations/{name}.json')
    if stages and '$match' in stages[0]:
        match = stages[0]['$match']
        for field in ('createdAt', 'completedAt'):
            if field in match:
                match[field] = {'$gte': start, '$lt': end}
    return stages
