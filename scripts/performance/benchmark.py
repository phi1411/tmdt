"""PHASE07B: reproducible real MongoDB benchmark; writes only ecommerce_benchmark."""
from __future__ import annotations

import argparse
import copy
import math
import platform
import random
import statistics
import sys
from datetime import datetime, timedelta, timezone
from importlib.metadata import version
from time import perf_counter_ns

from bson import json_util
from werkzeug.datastructures import MultiDict
from perf_common import (ROOT, DB_NAME, NAMES, LOCAL, EVIDENCE, DATASET_FILE, INDEXES, READ_INDEXES,
    connection, benchmark_db, fingerprint, source_manifest, exclusive_lock, save, read_json,
    verify_owned_dataset, digest, explain_stats, walk)
from dataset import setup, START, END, oid, SEED
from app.repositories.product_repository import ProductRepository, PRODUCT_PROJECTION
from app.repositories.dashboard_repository import DashboardRepository
from app.schemas.product_schema import parse_product_query
from app.schemas.dashboard_schema import ReportWindow


def query_specs(db):
    public_params = [
        ('products-category-price', {'productType': 'ELECTRONICS', 'categoryId': str(oid('category', 0)),
            'minPrice': '2000000', 'maxPrice': '5000000', 'sort': 'price_asc'}, 'ix_products_category_price'),
        ('products-type-brand-price', {'productType': 'ELECTRONICS', 'brand': 'Benchmark Brand 1',
            'minPrice': '2000000', 'maxPrice': '5000000', 'sort': 'price_desc'}, 'ix_products_type_price')]
    specs = []
    for name, params, index in public_params:
        query, sort, pagination = parse_product_query(MultiDict(params))
        command = {'find': 'products', 'filter': query, 'sort': dict(sort), 'projection': PRODUCT_PROJECTION, 'limit': 20}
        specs.append({'name': name, 'index': index, 'kind': 'product-selection', 'command': command,
                      'source': 'parse_product_query + PRODUCT_SORTS/PROJECTION', 'apiParams': params})
        # Capture the pipeline emitted by the actual repository method rather than duplicate it.
        class Capture:
            def aggregate(self, pipeline):
                self.pipeline = pipeline
                return iter([{'items': [], 'count': []}])
        recorder = Capture()
        repository = object.__new__(ProductRepository)
        repository.collection = recorder
        repository.list(query, sort, pagination, public=True)
        specs.append({'name': name+'-full-api', 'index': index, 'kind': 'product-full-repository',
            'command': {'aggregate': 'products', 'pipeline': recorder.pipeline, 'cursor': {}},
            'source': 'ProductRepository.list/public=True/page1/pageSize20', 'apiParams': params})
    reports = object.__new__(DashboardRepository)
    reports.database = db
    for name in ('revenue-day', 'top-products'):
        specs.append({'name': name, 'index': 'ix_orders_qualified_completed', 'kind': 'canonical-dashboard',
            'command': {'aggregate': 'orders', 'pipeline': reports.pipeline(name, ReportWindow(START, END)), 'cursor': {}},
            'source': 'DashboardRepository.pipeline + canonical database/aggregations/'+name+'.json'})
    return specs


def execute(db, spec, hint=None):
    command = spec['command']
    if 'find' in command:
        cursor = db[command['find']].find(command['filter'], command['projection'], max_time_ms=60000)
        if hint is not None:
            cursor = cursor.hint(hint)
        return list(cursor.sort(list(command['sort'].items())).limit(command['limit']))
    kwargs = {'maxTimeMS': 60000, 'allowDiskUse': False}
    if hint is not None:
        kwargs['hint'] = hint
    return list(db[command['aggregate']].aggregate(command['pipeline'], **kwargs))


def explain(db, spec, hint, rows):
    command = copy.deepcopy(spec['command'])
    command['maxTimeMS'] = 60000
    if hint is not None:
        command['hint'] = hint
    if 'aggregate' in command:
        command['allowDiskUse'] = False
    raw = db.command('explain', command, verbosity='executionStats')
    stats = explain_stats(raw, len(rows))
    if spec['kind'] == 'product-full-repository':
        stats.update(pagedItemsReturned=len(rows[0]['items']), matchingTotal=rows[0]['count'][0]['total'])
    return {'command': command, 'summary': stats, 'rawExplain': raw, 'resultDigest': digest(rows)}


def storage(db):
    return {name: {key: (result[key] if key in result else None)
            for key in ('count', 'size', 'storageSize', 'totalIndexSize', 'indexSizes', 'nindexes')}
            for name in ('products', 'orders') for result in [db.command('collStats', name, scale=1)]}


def timing(db, spec, modes, repeats, warmups, expected_hash):
    rng, samples = random.Random(SEED), {mode: [] for mode in modes}
    order = list(modes)
    for iteration in range(warmups+repeats):
        rng.shuffle(order)
        for mode in order:
            started = perf_counter_ns()
            rows = execute(db, spec, modes[mode])
            elapsed = (perf_counter_ns()-started)/1_000_000
            assert digest(rows) == expected_hash, 'Result changed during latency measurement'
            if iteration >= warmups:
                samples[mode].append(elapsed)
    return {mode: {'p50ClientMs': statistics.median(values),
        'p95ClientMs': sorted(values)[math.ceil(.95*len(values))-1],
        'minClientMs': min(values), 'maxClientMs': max(values), 'samplesClientMs': values}
        for mode, values in samples.items()}


def index_audit(dev):
    applied = {name: {i['name']: dict(i) for i in dev[name].list_indexes()} for name in NAMES}
    rows = []
    for entry in INDEXES:
        actual = applied[entry['collection']].get(entry['name'])
        if actual:
            assert list(actual['key'].items()) == list(entry['keys'].items())
            for key, value in entry['options'].items():
                assert actual.get(key) == value
        classification = 'KEEP' if actual else 'CANDIDATE'
        reason = ('Unique/integrity; không drop để benchmark' if entry['kind'] == 'INVARIANT'
                  else 'Workload ứng dụng hiện có; không thay index dev' if actual
                  else 'Đã đo ở benchmark riêng, chưa áp dụng dev' if entry['name'] in READ_INDEXES
                  else 'Có use case, chưa đo workload riêng để justify apply')
        rows.append({'collection': entry['collection'], 'name': entry['name'], 'keys': entry['keys'],
            'options': entry['options'], 'queryPattern': entry['queryPattern'], 'classification': classification,
            'appliedToDev': bool(actual), 'testedOnBenchmark': entry['name'] in READ_INDEXES, 'reason': reason})
    known = {'_id_'} | {entry['name'] for entry in INDEXES}
    unknown = [{'collection': name, 'index': value} for name in NAMES for index, value in applied[name].items() if index not in known]
    return {'devIndexes': applied, 'declaredApplied': sum(len(values)-1 for values in applied.values()),
        'automaticIdIndexes': len(NAMES), 'manifestEntries': len(INDEXES), 'audit': rows,
        'unknownIndexes': unknown, 'removeRedundant': [], 'indexesRemovedFromDev': [],
        'conclusion': 'Không chứng minh index dư thừa; giữ tất cả unique/integrity và workload đã áp dụng.'}


def run(db, dev, metadata, repeats, warmups):
    # A true before-build run: keep unique constraints, remove only our three benchmark read indexes.
    for index in INDEXES:
        if index['name'] in READ_INDEXES and index['name'] in db[index['collection']].index_information():
            db[index['collection']].drop_index(index['name'])
    specs = query_specs(db)
    before, baseline_rows, baseline_times = {}, {}, {}
    modes_before = {'noSuitableIndex': None}
    for spec in specs:
        name = spec['name']
        rows = execute(db, spec)
        assert rows, 'Empty benchmark query is not useful evidence'
        before[name] = explain(db, spec, None, rows)
        stages = before[name]['summary']['planStages']
        assert 'COLLSCAN' in stages and 'IXSCAN' not in stages, (name, stages)
        baseline_rows[name] = rows
        baseline_times[name] = timing(db, spec, modes_before, repeats, warmups, digest(rows))
        print('BEFORE', name, before[name]['summary']['totalDocsExamined'], flush=True)
    storage_before = storage(db)
    builds = {}
    for entry in INDEXES:
        if entry['name'] in READ_INDEXES:
            start = perf_counter_ns()
            db[entry['collection']].create_index(list(entry['keys'].items()), **entry['options'])
            builds[entry['name']] = (perf_counter_ns()-start)/1_000_000
    storage_after = storage(db)
    after, comparison = {}, {}
    for spec in specs:
        name = spec['name']
        modes = {'natural': {'$natural': 1}, 'namedIndex': spec['index'], 'plannerUnhinted': None}
        comparisons = {}
        for mode, hint in modes.items():
            rows = execute(db, spec, hint)
            assert rows == baseline_rows[name], (name, mode, 'unequal results')
            comparisons[mode] = explain(db, spec, hint, rows)
        assert 'COLLSCAN' in comparisons['natural']['summary']['planStages']
        assert 'IXSCAN' in comparisons['namedIndex']['summary']['planStages']
        assert comparisons['namedIndex']['summary']['totalDocsExamined'] <= before[name]['summary']['totalDocsExamined']
        if spec['kind'] == 'canonical-dashboard':
            assert baseline_rows[name] == metadata['oracle'][name], (name, 'independent oracle mismatch')
        after[name] = comparisons
        latency = timing(db, spec, modes, repeats, warmups, digest(baseline_rows[name]))
        a, b = before[name]['summary'], comparisons['namedIndex']['summary']
        comparison[name] = {'kind': spec['kind'], 'source': spec['source'], 'apiParams': spec.get('apiParams'),
            'withoutIndex': a, 'withNamedIndex': b, 'plannerUnhinted': comparisons['plannerUnhinted']['summary'],
            'documentScanReductionPercent': round(100*(1-b['totalDocsExamined']/a['totalDocsExamined']), 3),
            'resultsEqualAcrossAllModes': True, 'resultDigest': digest(baseline_rows[name]),
            'latency': {**baseline_times[name], **latency}}
        print('AFTER', name, b['totalDocsExamined'], b['totalKeysExamined'], flush=True)
    # The full repository page must agree with the corresponding selector on IDs/order.
    for number in (0, 2):
        selector, full = specs[number]['name'], specs[number+1]['name']
        assert [row['_id'] for row in baseline_rows[selector]] == [row['_id'] for row in baseline_rows[full][0]['items']]
    broad = copy.deepcopy(next(spec for spec in specs if spec['name'] == 'revenue-day'))
    broad['command']['pipeline'][0]['$match']['completedAt'] = {'$gte': datetime(2026, 1, 1, tzinfo=timezone.utc),
                                                               '$lt': datetime(2026, 7, 1, tzinfo=timezone.utc)}
    sensitivity = {}
    broad_rows = None
    for mode, hint in [('natural', {'$natural': 1}), ('namedIndex', 'ix_orders_qualified_completed')]:
        rows = execute(db, broad, hint)
        if broad_rows is None:
            broad_rows = rows
        assert rows == broad_rows
        sensitivity[mode] = explain(db, broad, hint, rows)
    # Read-only small dev dataset: scan/cardinality evidence, no timing speedup claim.
    category = dev.products.find_one({'status': 'ACTIVE', 'productType': 'ELECTRONICS'})['categoryId']
    query, sort, _ = parse_product_query(MultiDict({'categoryId': str(category), 'productType': 'ELECTRONICS',
        'minPrice': '1000000', 'maxPrice': '20000000', 'sort': 'price_asc'}))
    small = {'kind': 'product-selection', 'command': {'find': 'products', 'filter': query,
                'sort': dict(sort), 'projection': PRODUCT_PROJECTION, 'limit': 20}}
    dev_smoke = {}
    small_rows = None
    for mode, hint in [('natural', {'$natural': 1}), ('namedIndex', 'ix_products_category_price'), ('plannerUnhinted', None)]:
        rows = execute(dev, small, hint)
        if small_rows is None:
            small_rows = rows
        assert rows == small_rows
        dev_smoke[mode] = explain(dev, small, hint, rows)
    save(EVIDENCE / 'before-index.json', {'label': 'True pre-build: no suitable read index; unique indexes retained',
        'indexesBefore': {name: [i['name'] for i in db[name].list_indexes() if i['name'] not in READ_INDEXES] for name in NAMES},
        'queries': before})
    save(EVIDENCE / 'after-index.json', {'label': 'Same BSON dataset, named/natural/unhinted hints', 'queries': after})
    save(EVIDENCE / 'aggregation-explain.json', {'canonical': {name: {'before': before[name], 'after': after[name]}
        for name in ('revenue-day', 'top-products')}, 'wideRangeSensitivity': sensitivity,
        'note': 'Index helps initial match/latest sort; unwind/group/final rank are not all index-backed.'})
    save(EVIDENCE / 'dev-seed-smoke.json', {'counts': {name: dev[name].count_documents({}) for name in NAMES},
        'queries': dev_smoke, 'note': 'Small functional dataset: no millisecond speedup conclusion.'})
    save(EVIDENCE / 'index-audit.json', index_audit(dev))
    save(EVIDENCE / 'storage.json', {'beforeReadIndexes': storage_before, 'afterReadIndexes': storage_after,
        'indexBuildClientMs': builds, 'writeUpdateBenchmark': 'NOT_MEASURED',
        'note': 'Extra index storage and maintenance on insert/update; no write throughput claim.'})
    server = db.client.admin.command('buildInfo')
    hello = db.client.admin.command('hello')
    result = {'status': 'PHASE 07B PERFORMANCE EVIDENCE PASS', 'recordedAtUtc': datetime.now(timezone.utc),
        'runtime': {'mongo': server['version'], 'pymongo': version('pymongo'), 'python': platform.python_version(),
            'platform': platform.platform(), 'logicalCpuCount': __import__('os').cpu_count(),
            'replicaSet': hello['setName'], 'primary': hello['primary'],
            'storageEngine': db.client.admin.command('serverStatus')['storageEngine']['name']},
        'database': DB_NAME, 'dataset': metadata, 'warmupsPerMode': warmups, 'repeatsPerMode': repeats,
        'method': 'Warm cache, single client, fully materialized cursor, perf_counter_ns; shuffled mode order after build',
        'queryComparison': comparison, 'schemaChanged': False, 'businessRuleChanged': False,
        'devIndexesCreatedOrDropped': False}
    save(EVIDENCE / 'benchmark-results.json', result)
    write_summary(result)
    return result


def write_summary(result):
    lines = ['# Benchmark summary — PHASE07B', '', '**BENCHMARK DATASET**, không phải seed chính thức của đề.', '',
        '| Query | BEFORE plan | Docs / keys | AFTER plan | Docs / keys | Final rows | Giảm docs |',
        '| --- | --- | ---: | --- | ---: | ---: | ---: |']
    for name, row in result['queryComparison'].items():
        a, b = row['withoutIndex'], row['withNamedIndex']
        lines.append(f"| {name} | COLLSCAN | {a['totalDocsExamined']:,} / {a['totalKeysExamined']} | IXSCAN | "
                     f"{b['totalDocsExamined']:,} / {b['totalKeysExamined']} | {b['finalResultRows']} | {row['documentScanReductionPercent']}% |")
    lines += ['', 'Full-api trả1facet document chứa20items; selection trả20Products; Revenue/Top5 là rows cuối pipeline.', '',
        '| Query | No suitable index p50 / p95 ms | Natural p50 / p95 ms | Named p50 / p95 ms | Planner p50 / p95 ms |',
        '| --- | ---: | ---: | ---: | ---: |']
    for name, row in result['queryComparison'].items():
        values = [f"{row['latency'][mode]['p50ClientMs']:.3f} / {row['latency'][mode]['p95ClientMs']:.3f}"
                  for mode in ('noSuitableIndex', 'natural', 'namedIndex', 'plannerUnhinted')]
        lines.append('| '+name+' | '+' | '.join(values)+' |')
    lines += ['', f"Warmups{result['warmupsPerMode']}/repeats{result['repeatsPerMode']}, single-node rs0/WiredTiger, fully materialized cursor.",
        'Timings là observations local warm cache; không claim speedup X lần hoặc latency production.',
        'Explain bỏ qua plan cache; client latency đo riêng với query thật. Index chỉ hỗ trợ các stages đầu phù hợp, không toàn bộ aggregation.',
        'Raw plans/samples/hashes: [results](benchmark-results.json), [before](before-index.json), [after](after-index.json), [aggregations](aggregation-explain.json).',
        'Index tăng storage và chi phí duy trì khi insert/update. Write throughput chưa đo; không thêm index mọi tổ hợp.', '']
    (EVIDENCE / 'benchmark-summary.md').write_text('\n'.join(lines), encoding='utf-8')


def cleanup(db):
    metadata = verify_owned_dataset(db)
    # Target is a literal, guarded local DB; verify all collection contents before any drop.
    assert db.name == DB_NAME
    for name in NAMES:
        db[name].drop()
    assert not db.list_collection_names()
    DATASET_FILE.unlink()
    return {'status': 'OWNED_BENCHMARK_CLEANUP_PASS', 'deletedCollections': list(NAMES),
            'deletedDataset': metadata['collections'], 'devTouched': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('setup', 'run', 'all', 'cleanup', 'reproduce'))
    parser.add_argument('--products', type=int, default=30000)
    parser.add_argument('--orders', type=int, default=10000)
    parser.add_argument('--warmups', type=int, default=5)
    parser.add_argument('--repeats', type=int, default=30)
    args = parser.parse_args()
    if not 10000 <= args.products <= 50000 or not 2000 <= args.orders <= 20000 or args.warmups < 3 or args.repeats < 30:
        parser.error('products10000..50000/orders2000..20000/warmups>=3/repeats>=30')
    with exclusive_lock():
        client, dev = connection('ecommerce_dev')
        before, sources = fingerprint(dev), source_manifest()
        successful = False
        try:
            db = benchmark_db(client, claim=args.command in ('setup', 'all'))
            if args.command == 'reproduce':
                original = verify_owned_dataset(db)
                receipt = cleanup(db)
                assert not db.list_collection_names()
                metadata = setup(db, original['config']['products'], original['config']['orders'])
                assert metadata['collections'] == original['collections'], 'Dataset reproduction differs'
                save(EVIDENCE / 'reproducibility-verification.json', {
                    'status': 'BENCHMARK_CLEANUP_REPRODUCIBILITY_PASS',
                    'cleanupReceipt': receipt, 'recreatedCollections': metadata['collections'],
                    'bsonHashesReproducedExactly': True})
                save(EVIDENCE / 'dataset-manifest.json', metadata)
            if args.command in ('setup', 'all'):
                if db.list_collection_names():
                    metadata = verify_owned_dataset(db)
                    assert metadata['config'] == {'products': args.products, 'orders': args.orders}, 'Cleanup required before resizing dataset'
                else:
                    metadata = setup(db, args.products, args.orders)
                save(EVIDENCE / 'dataset-manifest.json', metadata)
            if args.command in ('run', 'all', 'reproduce'):
                metadata = verify_owned_dataset(db)
                run(db, dev, metadata, args.repeats, args.warmups)
                verify_owned_dataset(db)
            if args.command == 'cleanup':
                save(EVIDENCE / 'cleanup-verification.json', cleanup(db))
            successful = True
        finally:
            after = fingerprint(dev)
            integrity = {'command': args.command, 'commandSucceeded': successful,
                'before': before, 'after': after, 'devUnchanged': before == after,
                'sourceManifestBefore': sources, 'sourceManifestAfter': source_manifest(),
                'protectedSourceUnchanged': sources == source_manifest()}
            save(EVIDENCE / ('dev-integrity-'+args.command+'.json'), integrity)
            client.close()
            assert integrity['devUnchanged'] and integrity['protectedSourceUnchanged'], 'Protected dev/source changed; never reverted automatically'
        print(args.command, 'PASS; dev documents/validators/indexes unchanged', flush=True)


if __name__ == '__main__':
    main()
