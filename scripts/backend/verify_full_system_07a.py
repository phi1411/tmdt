"""07A isolation: exact read-only dev clones, actual Flask listener, scoped cleanup."""
import argparse
import copy
import hashlib
import json
import os
import secrets
import subprocess
import sys
from pathlib import Path
from bson import ObjectId, json_util
from dotenv import dotenv_values
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern
from werkzeug.serving import make_server

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'backend')]
from app import create_app
from verify_auth_users import NAMES, fingerprint
from cleanup_phase06ab_database import snapshot, canonical_schema_check, orphan_check

SETTINGS = ROOT / '.local/phase07a-fixture-settings.json'
JOURNAL = ROOT / '.local/phase07a-fixture-ids.json'


def verify_development(db, baseline):
    current = snapshot(db)
    actual = fingerprint(db)
    projected = copy.deepcopy(current)
    external = None
    if actual != baseline['database']:
        # Concurrent 07C owns reusable demo fixtures. Preserve them and verify the
        # original corpus independently; never treat another phase's data as ours.
        public = json.loads((ROOT / 'database/evidence/phase07c-rehearse.json').read_text(encoding='utf-8'))
        private = json.loads((ROOT / '.local/phase07c/fixture.json').read_text(encoding='utf-8'))
        assert public['phase'] == '07C' and public['database'] == db.name
        assert private['project'] == str(ROOT) and private['database'] == db.name
        assert public['before'] == baseline['database']
        fixture = public['ownedFixture']
        owner = ObjectId(fixture['userId'])
        assert private['userId'] == fixture['userId']
        assert db.users.count_documents({'_id': owner, 'email': 'defense07c@example.test'}) == 1
        excluded = {'users': {owner}, 'categories': {ObjectId(i) for i in fixture['categories'].values()},
                    'products': {ObjectId(p['id']) for p in fixture['products']}}
        for n in NAMES:
            projected['documents'][n] = [d for d in current['documents'][n]
                if d['_id'] not in excluded.get(n, set()) and not (n in ('carts', 'orders', 'payment_attempts') and d['userId'] == owner)]
            projected['counts'][n] = len(projected['documents'][n])
        digest = hashlib.sha256(json_util.dumps(projected, json_options=json_util.CANONICAL_JSON_OPTIONS, sort_keys=True).encode()).hexdigest()
        assert {'digest': digest, 'counts': projected['counts']} == baseline['database'], 'Unexplained development mutation'
        external = {'phase': '07C', 'account': 'defense07c@example.test', 'preserved': True,
                    'evidence': 'database/evidence/phase07c-rehearse.json',
                    'counts': {n: current['counts'][n] - projected['counts'][n] for n in NAMES}}
    return actual, projected, external


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['prepare', 'serve', 'legacy-customer', 'legacy-admin', 'full-journey', 'chart-visual', 'cleanup', 'check'])
    args = parser.parse_args()
    if args.mode.startswith('legacy-') or args.mode in ('full-journey', 'chart-visual'):
        env = os.environ.copy()
        env.update(E2E_BASE_URL='http://127.0.0.1:5174',
                   E2E_SEED_PASSWORD=dotenv_values(ROOT / '.env', interpolate=False)['SEED_DEMO_PASSWORD'])
        name = 'customer' if args.mode == 'legacy-customer' else 'fe-02'
        script = 'e2e-customer-verification.mjs' if name == 'customer' else 'e2e-fe-02-verification.mjs'
        if args.mode == 'full-journey': script = 'phase07a-full-system.mjs'
        if args.mode == 'chart-visual': script = 'phase07a-chart-visual.mjs'
        env['E2E_RESULTS'] = f'tests/phase07a-{name}-results.json'
        result = subprocess.run(['node', 'tests/' + script], cwd=ROOT / 'frontend', env=env)
        raise SystemExit(result.returncode)
    if args.mode == 'serve':
        app = create_app(json.loads(SETTINGS.read_text(encoding='utf-8')))
        assert app.extensions['mongo'].database.name == 'ecommerce_test'
        with make_server('127.0.0.1', 5002, app, threaded=True) as server:
            print('07A same-source Flask test listener ready', flush=True)
            server.serve_forever()
        return
    dev = create_app()
    client = dev.extensions['mongo'].client
    db, test = dev.extensions['mongo'].database, client.ecommerce_test
    try:
        baseline = json.loads((ROOT / '.local/phase07a-before.json').read_text(encoding='utf-8'))
        assert db.name == 'ecommerce_dev'
        actual, projected, external = verify_development(db, baseline)
        marker = json.loads((ROOT / '.local/ecommerce_test.ownership.json').read_text(encoding='utf-8'))
        assert marker == {'project': str(ROOT), 'database': 'ecommerce_test', 'endpoint': 'localhost:27017/rs0'}
        assert client.admin.command('hello')['setName'] == 'rs0'
        if args.mode == 'prepare':
            assert all(test[n].count_documents({}) == 0 for n in NAMES), 'Test DB must be empty; never reset it'
            canonical_schema_check(snapshot(test))
            docs = projected['documents']
            settings = {k: dev.config[k] for k in ('MONGODB_URI', 'JWT_ISSUER', 'JWT_AUDIENCE')}
            settings.update(APP_ENV='testing', MONGODB_DB='ecommerce_dev', MONGODB_TEST_DB='ecommerce_test',
                            JWT_SECRET=secrets.token_urlsafe(48), FRONTEND_ORIGIN='http://127.0.0.1:5174',
                            VNPAY_ENABLED=False, LOG_LEVEL='ERROR')
            SETTINGS.write_text(json.dumps(settings), encoding='utf-8')
            JOURNAL.write_text(json.dumps({n: [str(d['_id']) for d in docs[n]] for n in NAMES}), encoding='utf-8')
            with client.start_session() as session:
                with session.start_transaction(read_concern=ReadConcern('snapshot'), write_concern=WriteConcern('majority')):
                    for n in NAMES:
                        if docs[n]: test[n].insert_many(copy.deepcopy(docs[n]), session=session)
            print(json.dumps({'prepared': {n: len(rows) for n, rows in docs.items()}, 'database': 'ecommerce_test', 'devWrites': 0}))
        elif args.mode == 'cleanup':
            allowed = {n: {ObjectId(i) for i in ids} for n, ids in json.loads(JOURNAL.read_text(encoding='utf-8')).items()}
            rows = {n: list(test[n].find({})) for n in NAMES}
            for u in rows['users']:
                if u['_id'] not in allowed['users']:
                    assert u['email'].startswith(('khach_', 'phase07a-')), 'Unknown external User; refuse cleanup'
                    allowed['users'].add(u['_id'])
            for n in ('orders', 'carts', 'payment_attempts'):
                for d in rows[n]:
                    assert d['_id'] in allowed[n] or d['userId'] in allowed['users'], 'Unknown fixture owner'
                    allowed[n].add(d['_id'])
            for n in ('products', 'categories'):
                for d in rows[n]:
                    assert d['_id'] in allowed[n] or d['slug'].startswith('phase07a-'), 'Unknown external Catalog document'
                    allowed[n].add(d['_id'])
            cleaned = {}
            with client.start_session() as session:
                with session.start_transaction(read_concern=ReadConcern('snapshot'), write_concern=WriteConcern('majority')):
                    for n in ('payment_attempts', 'orders', 'carts', 'products', 'categories', 'users'):
                        cleaned[n] = test[n].delete_many({'_id': {'$in': sorted(allowed[n])}}, session=session).deleted_count
                    assert all(test[n].count_documents({}, session=session) == 0 for n in NAMES)
            print(json.dumps({'exactFixtureCleanup': cleaned, 'testEmpty': True}))
        if args.mode in ('cleanup', 'check'):
            assert all(test[n].count_documents({}) == 0 for n in NAMES)
            actual, projected, external = verify_development(db, baseline)
            current = snapshot(db)
            evidence = {'status': 'DATABASE_INTEGRITY_PASS', 'devBefore': baseline['database'], 'devAfter': actual,
                        'originalCorpusDigest': baseline['database']['digest'], 'originalCorpusUnchanged': True,
                        'externalFixtures': external, 'devWritesBy07A': 0,
                        'fixtureCleanupCounts': cleaned if args.mode == 'cleanup' else None,
                        'schema': canonical_schema_check(current), 'orphans': orphan_check(current), 'testEmpty': True,
                        'testSchema': canonical_schema_check(snapshot(test)),
                        'retainedAccountPresent': db.users.count_documents({'email': 'khachtest_1791374905461@example.test'}) == 1,
                        'resetPerformed': False, 'reseedPerformed': False}
            assert evidence['retainedAccountPresent']
            (ROOT / 'backend/evidence/phase07a-db-integrity.json').write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf-8')
            print(json.dumps(evidence))
    finally:
        dev.extensions['mongo'].close()


if __name__ == '__main__':
    main()
