"""Exact BSON clone to one explicitly authorized Atlas demo database; no deletes."""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from bson import json_util
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'backend'), str(ROOT / 'scripts/backend'), str(ROOT / 'scripts/db')]
from app import create_app
from verify_auth_users import NAMES, fingerprint
from cleanup_phase06ab_database import snapshot, canonical_schema_check, orphan_check
from common import apply_foundation

PRIVATE = ROOT / '.local/atlas-upload'
JOURNAL = PRIVATE / 'journal.json'
OUT = ROOT / 'database/evidence/atlas-demo-upload.json'
HOST = 'cluster0.asxeso0.mongodb.net'
DATABASE = 'novamart_demo'


def encoded(value):
    return json_util.dumps(value, json_options=json_util.CANONICAL_JSON_OPTIONS, sort_keys=True)


def digest(value):
    return hashlib.sha256(encoded(value).encode()).hexdigest()


def reports(db):
    outputs = {}
    for name in ('sales-summary', 'revenue-day', 'top-products'):
        stages = json_util.loads((ROOT / f'database/aggregations/{name}.json').read_text(encoding='utf-8'))
        outputs[name] = list(db.orders.aggregate(stages, maxTimeMS=15000))
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    config = json.loads((PRIVATE / 'connection.json').read_text(encoding='utf-8'))
    assert urlsplit(config['uri']).scheme == 'mongodb+srv' and urlsplit(config['uri']).hostname == HOST
    assert config['database'] == DATABASE
    local = create_app()
    remote = None
    result = {'status': 'STARTED', 'recordedAtUtc': datetime.now(timezone.utc).isoformat(),
              'sourceDatabase': 'ecommerce_dev', 'targetDatabase': DATABASE, 'localWrites': 0,
              'deleteDropResetReseedPerformed': False, 'applicationConfigChanged': False}
    try:
        source = local.extensions['mongo'].database
        assert source.name == 'ecommerce_dev' and source.client.admin.command('hello')['setName'] == 'rs0'
        before = fingerprint(source)
        with source.client.start_session() as session:
            with session.start_transaction(read_concern=ReadConcern('snapshot')):
                rows = {n: list(source[n].find({}, session=session).sort('_id', 1)) for n in NAMES}
        source_schema = canonical_schema_check(snapshot(source))
        orphan_check({'documents': rows})
        digests = {n: digest(docs) for n, docs in rows.items()}
        counts = {n: len(docs) for n, docs in rows.items()}
        assert fingerprint(source) == before, 'Source changed during capture; retry only after review'
        remote = MongoClient(config['uri'], tz_aware=True, serverSelectionTimeoutMS=15000,
                             connectTimeoutMS=10000, socketTimeoutMS=30000)
        remote.admin.command('ping')
        hello = remote.admin.command('hello')
        assert hello.get('isWritablePrimary') and hello.get('setName') and hello.get('logicalSessionTimeoutMinutes')
        target = remote.get_database(DATABASE, write_concern=WriteConcern('majority'))
        collections = target.list_collection_names()
        owned = JOURNAL.exists()
        if owned:
            journal = json.loads(JOURNAL.read_text(encoding='utf-8'))
            assert journal['project'] == str(ROOT) and journal['host'] == HOST and journal['database'] == DATABASE
            assert journal['sourceDigests'] == digests and journal['sourceFingerprint'] == before
            assert set(collections) <= set(NAMES), 'Unknown destination collections'
            # Never fill around an unexplained partial import.
            nonempty = any(target[n].count_documents({}) for n in NAMES)
            if nonempty:
                assert all(digest(list(target[n].find({}).sort('_id', 1))) == digests[n] for n in NAMES), 'Destination contains different data; refusing mutation'
        else:
            assert collections == [], 'Destination already exists; no overwrite authorized'
            nonempty = False
        result.update(sourceCounts=counts, sourceFingerprintBefore=before, sourceDocumentDigests=digests,
                      sourceSchema=source_schema, replicaSetDiscovered=hello['setName'],
                      targetEmptyBefore=not nonempty)
        if not args.apply:
            result['status'] = 'PLAN_READY_NO_WRITES'
            print(json.dumps(result))
            return
        if not owned:
            journal = {'project': str(ROOT), 'host': HOST, 'database': DATABASE,
                       'sourceFingerprint': before, 'sourceDigests': digests,
                       'ownedIds': {n: [str(d['_id']) for d in docs] for n, docs in rows.items()}}
            JOURNAL.write_text(json.dumps(journal, indent=2), encoding='utf-8')
            (PRIVATE / 'source-backup.ejson').write_text(encoded(rows), encoding='utf-8')
        if not nonempty:
            apply_foundation(target)
            canonical_schema_check(snapshot(target))
            with remote.start_session() as session:
                session.start_transaction(read_concern=ReadConcern('snapshot'), write_concern=WriteConcern('majority'))
                try:
                    assert all(target[n].count_documents({}, session=session) == 0 for n in NAMES)
                    for n in NAMES:
                        if rows[n]:
                            target[n].insert_many(rows[n], session=session, ordered=True)
                    for attempt in range(3):
                        try:
                            session.commit_transaction()
                            break
                        except PyMongoError as error:
                            if not error.has_error_label('UnknownTransactionCommitResult') or attempt == 2:
                                raise
                except Exception:
                    if session.in_transaction:
                        session.abort_transaction()
                    raise
        actual = snapshot(target)
        checks = {n: {'count': actual['counts'][n], 'canonicalBsonEqual': digest(actual['documents'][n]) == digests[n]}
                  for n in NAMES}
        assert all(c['canonicalBsonEqual'] for c in checks.values())
        schema = canonical_schema_check(actual)
        refs = orphan_check(actual)
        source_reports, target_reports = reports(source), reports(target)
        assert encoded(source_reports) == encoded(target_reports), 'Aggregation outputs differ'
        after = fingerprint(source)
        assert before == after, 'Local corpus changed during upload; do not overwrite baseline'
        result.update(status='ATLAS_DATABASE_UPLOAD_PASS', targetCounts=actual['counts'], documentChecks=checks,
                      targetSchema=schema, orphans=refs, sourceFingerprintAfter=after, sourceExactUnchanged=True,
                      transactionImportCommitted=True, aggregationOutputsEqual=True,
                      aggregationDigests={n: digest(v) for n, v in target_reports.items()},
                      aggregationRows={n: len(v) for n, v in target_reports.items()},
                      backendFrontendDeployed=False, vnpayLive='BLOCKED')
        OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({k: result[k] for k in ('status', 'targetDatabase', 'targetCounts', 'targetSchema',
                         'sourceExactUnchanged', 'transactionImportCommitted', 'aggregationOutputsEqual')}))
    except Exception as error:
        result.update(status='FAILED_REVIEW_REQUIRED', errorType=type(error).__name__, code=getattr(error, 'code', None))
        # Suppress exception messages, connection strings and private documents.
        OUT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({k: result[k] for k in ('status', 'errorType', 'code')}))
        raise SystemExit(1)
    finally:
        if remote is not None:
            remote.close()
        local.extensions['mongo'].close()


if __name__ == '__main__':
    main()
