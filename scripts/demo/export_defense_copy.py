"""Export canonical Extended JSON and import into an owned local demo database.

Atlas is read-only. No overwrite/drop/reseed: existing destination must be an
exact previous copy with a matching private ownership marker.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/deploy'))
from migrate_sku_reviews import COLLECTIONS, fingerprint, read_json
from bson import json_util
from pymongo import MongoClient
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern

PRIVATE = ROOT / '.local/defense-final'
DATABASE = 'ecommerce_defense'


def run(config_file):
    cfg = json.loads(config_file.read_text(encoding='utf-8'))
    assert urlsplit(cfg['uri']).hostname == 'cluster0.asxeso0.mongodb.net' and cfg['database'] == 'novamart_demo'
    export = PRIVATE / 'compass-export'
    export.mkdir(parents=True, exist_ok=True)
    marker = PRIVATE / 'local-copy-ownership.json'
    ownership = {'project': str(ROOT), 'destination': DATABASE, 'endpoint': '127.0.0.1:27017/rs0'}
    with MongoClient(cfg['uri'], tls=True, replicaSet='atlas-uczcqo-shard-0', tz_aware=True) as source_client, MongoClient('mongodb://127.0.0.1:27017/?replicaSet=rs0', tz_aware=True, serverSelectionTimeoutMS=15000) as local_client:
        hello = local_client.admin.command('hello')
        assert hello['setName'] == 'rs0' and hello['isWritablePrimary']
        source = source_client[cfg['database']]
        target = local_client.get_database(DATABASE, write_concern=WriteConcern('majority'))
        local_dev_before = fingerprint(local_client.ecommerce_dev)
        before = fingerprint(source)
        existing = target.list_collection_names()
        if marker.exists():
            assert json.loads(marker.read_text(encoding='utf-8')) == ownership, 'Ownership mismatch'
        else:
            assert not existing, 'Refusing to claim an existing local database'
            marker.write_text(json.dumps(ownership, indent=2), encoding='utf-8')
        # One consistent read snapshot for all exported business documents.
        with source_client.start_session() as session:
            with session.start_transaction(read_concern=ReadConcern('snapshot')):
                documents = {n: list(source[n].find(session=session).sort('_id', 1)) for n in COLLECTIONS}
        metadata = {n: {'options': source[n].options(), 'indexes': list(source[n].list_indexes())} for n in COLLECTIONS}
        for name, docs in documents.items():
            text = json_util.dumps(docs, json_options=json_util.CANONICAL_JSON_OPTIONS, ensure_ascii=False, indent=2)
            (export / (name + '.json')).write_text(text, encoding='utf-8')
            decoded = json_util.loads(text, json_options=json_util.CANONICAL_JSON_OPTIONS.with_options(tz_aware=True))
            assert json_util.dumps(decoded, json_options=json_util.CANONICAL_JSON_OPTIONS, sort_keys=True) == json_util.dumps(docs, json_options=json_util.CANONICAL_JSON_OPTIONS, sort_keys=True)
            documents[name] = decoded
        (export / 'metadata.ejson').write_text(json_util.dumps(metadata, json_options=json_util.CANONICAL_JSON_OPTIONS), encoding='utf-8')
        if existing:
            assert set(existing) == set(COLLECTIONS) and fingerprint(target) == before, 'Existing copy differs: preserve it; do not overwrite'
        else:
            for name in COLLECTIONS:
                target.create_collection(name, **metadata[name]['options'])
                for index in metadata[name]['indexes']:
                    if index['name'] != '_id_':
                        options = {k: v for k, v in index.items() if k not in {'key', 'v', 'ns'}}
                        target[name].create_index(list(index['key'].items()), **options)
            with local_client.start_session() as session:
                with session.start_transaction(read_concern=ReadConcern('snapshot'), write_concern=WriteConcern('majority')):
                    for name in COLLECTIONS:
                        if documents[name]:
                            target[name].insert_many(documents[name], session=session)
        assert fingerprint(source) == before == fingerprint(target), 'Source changed concurrently or import differs'
        assert fingerprint(local_client.ecommerce_dev) == local_dev_before
        assert all(source[n].options() == target[n].options() and list(source[n].list_indexes()) == list(target[n].list_indexes()) for n in COLLECTIONS)
        invalid = {n: target[n].count_documents({'$nor': [read_json(f'database/validators/{n}.json')]}) for n in COLLECTIONS}
        assert not any(invalid.values())
        report = {'recordedAtUtc': datetime.now(timezone.utc).isoformat(), 'status': 'CANONICAL_EXPORT_IMPORT_PASS',
            'sourceDatabase': source.name, 'destinationDatabase': target.name,
            'sourceReadOnly': True, 'resetReseedOrOverwrite': False,
            'counts': {n: len(documents[n]) for n in COLLECTIONS}, 'sourceFingerprint': before,
            'destinationFingerprint': fingerprint(target), 'bsonTypesPreserved': True,
            'validatorsOptionsIndexesEqual': True, 'invalidDocuments': invalid,
            'localDevFingerprint': local_dev_before, 'localDevUnchanged': True,
            'compassGuiImportExport': 'MANUAL_NOT_PERFORMED',
            'privateExportDirectory': '.local/defense-final/compass-export'}
        (ROOT / 'backend/evidence/defense-export-import-20261020.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--connection-file', type=Path, required=True)
    run(parser.parse_args().connection_file)
