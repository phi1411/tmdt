"""Read-only 07C Compass pipelines, live Dashboard API and forced plan comparison."""
import copy
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from bson import json_util
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'backend'), str(ROOT / 'scripts/backend')]
from app import create_app
from verify_auth_users import fingerprint


def main():
    app = create_app()
    db = app.extensions['mongo'].database
    out = ROOT / 'database/evidence'
    before = fingerprint(db)
    seed_start = datetime(2026, 7, 3, tzinfo=timezone.utc)
    seed_end = datetime(2026, 10, 1, tzinfo=timezone.utc)
    pipeline_root = ROOT / 'database/aggregations'
    try:
        assert db.name == 'ecommerce_dev' and db.client.admin.command('hello')['isWritablePrimary']
        bound, results = {}, {}
        for name in ('top-products', 'revenue-day', 'revenue-month', 'sales-summary'):
            pipeline = json_util.loads((pipeline_root / (name + '.json')).read_text(encoding='utf-8'),
                                       json_options=json_util.JSONOptions(tz_aware=True))
            pipeline[0]['$match']['completedAt'] = {'$gte': seed_start, '$lt': seed_end}
            bound[name] = pipeline
            results[name] = list(db.orders.aggregate(pipeline, maxTimeMS=10000))
            if name in {'top-products', 'revenue-day'}:
                # Compass Text View accepts shell-style date expressions; EJSON retained alongside it.
                text = json_util.dumps(pipeline, indent=2, ensure_ascii=False)
                import re
                text = re.sub(r'\{\s*"\$date":\s*"([^"]+)"\s*\}', r'ISODate("\1")', text)
                (out / ('phase07c-' + name + '.compass.txt')).write_text(text + '\n', encoding='utf-8')
                (out / ('phase07c-' + name + '.ejson')).write_text(json_util.dumps(pipeline, indent=2), encoding='utf-8')
        summary = results['sales-summary'][0]
        assert summary['totalRevenue'] == 10103259022 and summary['totalProductsSold'] == 434
        assert len(results['top-products']) == 5

        category = db.categories.find_one({'slug': 'dien-tu', 'productType': 'ELECTRONICS'})
        if category is None:
            category = db.categories.find_one({'productType': 'ELECTRONICS', 'slug': {'$not': {'$regex': '^defense-07c-'}}})
        assert category
        query = {'categoryId': category['_id'], 'status': 'ACTIVE', 'price': {'$gte': 1000000, '$lte': 20000000}}
        sort = {'price': 1, '_id': 1}
        plans, ids = {}, {}
        for name, hint in [('natural', {'$natural': 1}), ('indexed', 'ix_products_category_price'), ('planner', None)]:
            command = {'find': 'products', 'filter': query, 'sort': sort, 'limit': 10}
            if hint is not None:
                command['hint'] = hint
            raw = db.command('explain', command, verbosity='executionStats')
            def stages(value):
                found = []
                if isinstance(value, dict):
                    if 'stage' in value:
                        found.append(value['stage'])
                    for child in value.values():
                        found.extend(stages(child))
                elif isinstance(value, list):
                    for child in value:
                        found.extend(stages(child))
                return found
            stats = raw['executionStats']
            cursor = db.products.find(query).sort(list(sort.items())).limit(10)
            if hint is not None:
                cursor = cursor.hint(hint)
            ids[name] = [str(p['_id']) for p in cursor]
            plans[name] = {'stages': sorted(set(stages(raw['queryPlanner']['winningPlan']))),
                **{k: stats[k] for k in ('nReturned', 'totalDocsExamined', 'totalKeysExamined', 'executionTimeMillis')},
                'rawExplain': raw}
        assert ids['natural'] == ids['indexed'] == ids['planner'] and len(ids['indexed']) == 10
        assert 'COLLSCAN' in plans['natural']['stages'] and 'IXSCAN' in plans['indexed']['stages']
        shell = '''// READ ONLY — no index deletion/creation; same query/results.
const demoDb07c = db.getSiblingDB("ecommerce_dev");
const demoFilter07c = {categoryId:ObjectId("CATEGORY_ID"),status:"ACTIVE",price:{$gte:1000000,$lte:20000000}};
const demoSort07c = {price:1,_id:1};
const demoScan07c = demoDb07c.products.find(demoFilter07c).sort(demoSort07c).limit(10).hint({$natural:1}).explain("executionStats");
const demoIndex07c = demoDb07c.products.find(demoFilter07c).sort(demoSort07c).limit(10).hint("ix_products_category_price").explain("executionStats");
printjson({withoutUsingIndex:{plan:demoScan07c.queryPlanner.winningPlan,stats:demoScan07c.executionStats},withIndex:{plan:demoIndex07c.queryPlanner.winningPlan,stats:demoIndex07c.executionStats}});
'''.replace('CATEGORY_ID', str(category['_id']))
        (out / 'phase07c-index.mongodb.js').write_text(shell, encoding='utf-8')

        # Replay the already-delivered 07B query on its separate database; never rebuild/drop an index.
        perf_source = ROOT / 'docs/evidence/performance/before-index.json'
        if perf_source.exists():
            bench = db.client['ecommerce_benchmark']
            command = json_util.loads(perf_source.read_text(encoding='utf-8'))['queries']['products-category-price']['command']
            bench_counts = {name: bench[name].count_documents({}) for name in ('products', 'orders')}
            assert bench_counts == {'products': 30000, 'orders': 10000}, '07B dataset changed; inspect before presenting its saved metrics'
            bench_plans, bench_ids = {}, {}
            for label, hint in [('natural', {'$natural': 1}), ('indexed', 'ix_products_category_price'), ('planner', None)]:
                replay_command = {**command, **({'hint': hint} if hint is not None else {})}
                raw = bench.command('explain', replay_command, verbosity='executionStats')
                cursor = bench.products.find(command['filter'], command['projection']).sort(list(command['sort'].items())).limit(command['limit'])
                if hint is not None:
                    cursor = cursor.hint(hint)
                bench_ids[label] = [str(p['_id']) for p in cursor]
                bench_plans[label] = {'stages': sorted(set(stages(raw['queryPlanner']['winningPlan']))),
                    **{k: raw['executionStats'][k] for k in ('nReturned', 'totalDocsExamined', 'totalKeysExamined', 'executionTimeMillis')},
                    'rawExplain': raw}
            assert bench_ids['natural'] == bench_ids['indexed'] == bench_ids['planner'] and len(bench_ids['indexed']) == 20
            assert bench_plans['natural']['totalDocsExamined'] == 30000 and bench_plans['indexed']['totalDocsExamined'] == 20
            assert bench_counts == {name: bench[name].count_documents({}) for name in bench_counts}
            benchmark_proof = {'phase': '07C', 'mode': 'READ_ONLY_REPLAY_OF_07B', 'database': bench.name,
                'source': 'docs/evidence/performance/before-index.json', 'counts': bench_counts, 'command': command,
                'plans': bench_plans, 'sameOrderedProductIds': bench_ids['indexed'], 'resultsEqual': True,
                'newOrDroppedIndexes': [], 'notANewLatencyBenchmark': True}
            (out / 'phase07c-benchmark-query.json').write_text(json_util.dumps(benchmark_proof, indent=2), encoding='utf-8')
            import re
            command_text = json_util.dumps(command, indent=2)
            command_text = re.sub(r'\{\s*"\$oid":\s*"([^"]+)"\s*\}', r'ObjectId("\1")', command_text)
            benchmark_shell = '''// READ ONLY replay of 07B; do not create/drop indexes or use this DB for checkout.
const benchDb07c = db.getSiblingDB("ecommerce_benchmark");
const benchCommand07c = COMMAND;
const benchNatural07c = benchDb07c.runCommand({explain:{...benchCommand07c,hint:{$natural:1}},verbosity:"executionStats"});
const benchIndex07c = benchDb07c.runCommand({explain:{...benchCommand07c,hint:"ix_products_category_price"},verbosity:"executionStats"});
printjson({withoutUsingIndex:{plan:benchNatural07c.queryPlanner.winningPlan,stats:benchNatural07c.executionStats},withIndex:{plan:benchIndex07c.queryPlanner.winningPlan,stats:benchIndex07c.executionStats}});
'''.replace('COMMAND', command_text)
            (out / 'phase07c-benchmark-index.mongodb.js').write_text(benchmark_shell, encoding='utf-8')

        password = dotenv_values(ROOT / '.env', interpolate=False)['SEED_DEMO_PASSWORD']
        headers = {'Content-Type': 'application/json'}
        request = Request('http://127.0.0.1:5001/api/v1/auth/login',
            data=json.dumps({'email': 'admin@example.test', 'password': password}).encode(), headers=headers)
        with urlopen(request, timeout=10) as response:
            token = json.loads(response.read())['data']['accessToken']
        now = datetime.now(timezone.utc).replace(microsecond=0)
        window = {'from': (now - timedelta(days=30)).isoformat().replace('+00:00', 'Z'),
                  'to': (now + timedelta(days=1)).isoformat().replace('+00:00', 'Z')}
        reports = {}
        for endpoint in ('summary', 'revenue', 'top-products', 'category-revenue', 'order-status'):
            params = {**window, **({'interval': 'day'} if endpoint == 'revenue' else {})}
            request = Request('http://127.0.0.1:5001/api/v1/admin/dashboard/' + endpoint + '?' + urlencode(params),
                              headers={'Authorization': 'Bearer ' + token})
            with urlopen(request, timeout=15) as response:
                assert response.status == 200
                body = json.loads(response.read())
                reports[endpoint] = body['data']
        after = fingerprint(db)
        assert after == before, 'Dev changed during read-only checks; inspect concurrent activity'
        evidence = {'phase': '07C', 'mode': 'READ_ONLY', 'before': before, 'after': after, 'devUnchangedDuringQueryChecks': True,
            'fixedSeedWindow': {'from': seed_start.isoformat(), 'to': seed_end.isoformat()},
            'seedResults': results, 'boundPipelines': bound, 'liveDashboardWindow': window, 'liveDashboardReports': reports,
            'indexQuery': query, 'indexSort': sort, 'limit': 10, 'plans': plans, 'sameOrderedProductIds': ids['indexed'],
            'resultsEqual': True, 'newIndexes': [], 'phase07bReportPresent': (ROOT / 'docs/phase-07b-performance-review.md').exists()}
        (out / 'phase07c-query-verification.json').write_text(json_util.dumps(evidence, indent=2, ensure_ascii=False), encoding='utf-8')
        print(json.dumps({'phase': '07C', 'seedRevenue': summary['totalRevenue'], 'seedUnits': summary['totalProductsSold'],
            'dashboardEndpoints': len(reports), 'natural': {k:v for k,v in plans['natural'].items() if k != 'rawExplain'},
            'indexed': {k:v for k,v in plans['indexed'].items() if k != 'rawExplain'}, 'resultsEqual': True, 'devUnchanged': True}))
    finally:
        app.extensions['mongo'].close()


if __name__ == '__main__':
    main()
