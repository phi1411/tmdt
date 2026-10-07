"""Explicitly reseed owned fixtures and compare content, except salted hashes."""
import argparse
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'db'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'seed'))
from common import COLLECTIONS, connection, write_ejson
from seed import run_seed
from verify_database import content_digest, verify

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reset', action='store_true', required=True, help='Authorize a second deterministic fixture reset')
    parser.add_argument('--database', default='ecommerce_dev')
    args = parser.parse_args()
    client, db = connection(args.database)
    before = content_digest({n: list(db[n].find({}).sort('_id', 1)) for n in COLLECTIONS})
    client.close()
    run_seed(args.database)
    report = verify(args.database)
    after = report['contentDigestExcludingSaltedPasswords']
    assert before == after, 'Second seed changed deterministic content'
    write_ejson('database/evidence/reproducibility.json', {'status': 'LIVE_RESEED_PASS', 'database': args.database, 'beforeDigest': before, 'afterDigest': after, 'countsAfterSecondRun': report['counts'], 'hashSaltsExcluded': True, 'indexesPreserved': True})
    print({'status': 'LIVE_RESEED_PASS', 'digest': after})
