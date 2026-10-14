"""Local-only benchmark ownership, hashes and explain extraction."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from contextlib import contextmanager
from pathlib import Path

from bson import ObjectId, json_util
from bson.json_util import CANONICAL_JSON_OPTIONS
from pymongo.write_concern import WriteConcern

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts/db'), str(ROOT / 'scripts/backend'), str(ROOT / 'backend')]
from common import connection, normalize
from verify_auth_users import fingerprint

DB_NAME = 'ecommerce_benchmark'
NAMES = ('users', 'categories', 'products', 'carts', 'orders', 'payment_attempts')
LOCAL = ROOT / '.local/performance'
EVIDENCE = ROOT / 'docs/evidence/performance'
MARKER = ROOT / '.local/ecommerce_benchmark.ownership.json'
EXPECTED_MARKER = {'project': str(ROOT), 'database': DB_NAME, 'endpoint': 'localhost:27017/rs0'}
DATASET_FILE = LOCAL / 'dataset.json'
INDEXES = json.loads((ROOT / 'database/indexes/candidate-indexes.json').read_text(encoding='utf-8'))['indexes']
READ_INDEXES = ('ix_products_category_price', 'ix_products_type_price', 'ix_orders_qualified_completed')


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json_util.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def digest(value, canonical=False):
    options = CANONICAL_JSON_OPTIONS if canonical else json_util.RELAXED_JSON_OPTIONS
    return hashlib.sha256(json_util.dumps(value, json_options=options, sort_keys=True,
        ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def oid(namespace, number):
    return ObjectId(hashlib.sha256(f'novamart:benchmark:07b:{namespace}:{number}'.encode()).hexdigest()[:24])


def source_manifest():
    paths = list((ROOT / 'backend/app').rglob('*.py')) + list((ROOT / 'backend/tests').glob('*.py'))
    paths += [ROOT / 'docs/api-contract.md', ROOT / 'database/indexes/candidate-indexes.json']
    for directory in ('validators', 'aggregations', 'samples'):
        paths += list((ROOT / 'database' / directory).glob('*.json'))
    return {str(path.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(paths)}


@contextmanager
def exclusive_lock():
    LOCAL.mkdir(parents=True, exist_ok=True)
    path = LOCAL / 'run.lock'
    lock = path.open('x', encoding='utf-8')
    try:
        with lock:
            lock.write(str(os.getpid()))
            lock.flush()
            yield
    finally:
        # Windows cannot unlink an open file; close before removing the owned lock.
        path.unlink()


def benchmark_db(client, claim=False):
    # connection() above already verified loopback27017/rs0 PRIMARY.
    db = client.get_database(DB_NAME, write_concern=WriteConcern('majority'))
    if not MARKER.exists():
        if not claim or db.list_collection_names():
            raise RuntimeError('Refusing existing/unowned benchmark database')
        with MARKER.open('x', encoding='utf-8') as file:
            json.dump(EXPECTED_MARKER, file)
    if read_json(MARKER) != EXPECTED_MARKER:
        raise RuntimeError('Benchmark ownership marker mismatch')
    if set(db.list_collection_names()) - set(NAMES):
        raise RuntimeError('Foreign collections in benchmark database')
    return db


def data_hashes(db):
    result = {}
    for name in NAMES:
        hasher, count = hashlib.sha256(), 0
        for row in db[name].find({}).sort('_id', 1):
            hasher.update(json_util.dumps(row, json_options=CANONICAL_JSON_OPTIONS, sort_keys=True,
                ensure_ascii=False, separators=(',', ':')).encode()+b'\n')
            count += 1
        result[name] = {'count': count, 'digest': hasher.hexdigest()}
    return result


def verify_owned_dataset(db):
    if db.name != DB_NAME:
        raise RuntimeError('Only literal ecommerce_benchmark can be written or cleaned')
    if set(db.list_collection_names()) != set(NAMES) or not DATASET_FILE.exists():
        raise RuntimeError('Benchmark dataset not fully initialized; refusing write/cleanup')
    metadata = json_util.loads(DATASET_FILE.read_text(encoding='utf-8'),
                              json_options=json_util.JSONOptions(tz_aware=True))
    if data_hashes(db) != metadata['collections']:
        raise RuntimeError('Benchmark contents changed; refusing write/cleanup')
    for name in NAMES:
        options = db[name].options()
        validator = read_json(ROOT / f'database/validators/{name}.json')
        if options.get('validator') != validator or options.get('validationLevel') != 'strict' or options.get('validationAction') != 'error':
            raise RuntimeError('Benchmark validator differs from canonical')
        allowed = {'_id_'} | {i['name'] for i in INDEXES if i['collection'] == name and
                             (i['kind'] == 'INVARIANT' or i['name'] in READ_INDEXES)}
        actual_indexes = list(db[name].list_indexes())
        required = {'_id_'} | {i['name'] for i in INDEXES if i['collection'] == name and i['kind'] == 'INVARIANT'}
        if not required <= {index['name'] for index in actual_indexes}:
            raise RuntimeError('Required benchmark integrity index missing')
        for index in actual_indexes:
            if index['name'] not in allowed:
                raise RuntimeError('Unexpected benchmark index')
            if index['name'] != '_id_':
                entry = next(i for i in INDEXES if i['name'] == index['name'])
                assert list(index['key'].items()) == list(entry['keys'].items())
                for key, value in entry['options'].items():
                    assert index.get(key) == value
                for option in ('unique', 'sparse', 'hidden'):
                    assert bool(index.get(option, False)) == bool(entry['options'].get(option, False))
                for option in ('partialFilterExpression', 'expireAfterSeconds', 'collation'):
                    assert index.get(option) == entry['options'].get(option)
    return metadata


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def explain_stats(raw, final_rows):
    cursor = next((stage['$cursor'] for stage in raw.get('stages', []) if '$cursor' in stage), None)
    node = cursor or raw
    planner, stats = node['queryPlanner'], node['executionStats']
    plan = planner['winningPlan']
    return {'winningPlan': plan,
        'statisticsScope': '$cursor' if cursor else 'optimized-root',
        'planStages': sorted({v['stage'] for v in walk(plan) if 'stage' in v}),
        'indexNames': sorted({v['indexName'] for v in walk(plan) if 'indexName' in v}),
        **{key: stats[key] for key in ('executionTimeMillis', 'totalDocsExamined', 'totalKeysExamined', 'nReturned')},
        'finalResultRows': final_rows,
        'serverPipelineStages': [next(iter(stage)) for stage in raw.get('stages', [])],
        'spillsObserved': sum(v.get('spills', 0) for v in walk(raw))}
