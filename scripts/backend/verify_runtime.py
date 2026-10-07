"""HTTP smoke + database fingerprint checks; never changes MongoDB data/design."""
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from bson import json_util

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app import create_app


def http(method, url):
    try:
        response = urlopen(Request(url, method=method), timeout=10)
    except HTTPError as error:
        response = error
    with response:
        return {'status': response.status, 'body': json.loads(response.read()), 'requestId': response.headers['X-Request-ID']}


if __name__ == '__main__':
    app = create_app()
    try:
        base = f"http://{app.config['API_HOST']}:{app.config['API_PORT']}/api/v1"
        healthy = http('GET', base + '/health')
        missing = http('GET', base + '/not-present')
        wrong_method = http('POST', base + '/health')
        assert healthy['status'] == 200 and healthy['body']['data']['status'] == 'ok'
        assert missing['status'] == 404 and missing['body']['error']['code'] == 'NOT_FOUND'
        assert wrong_method['status'] == 405 and wrong_method['body']['error']['code'] == 'METHOD_NOT_ALLOWED'
        for result in (healthy, missing, wrong_method):
            assert result['requestId'] == result['body']['meta']['requestId']
        mongo = app.extensions['mongo']
        database = mongo.database
        names = ('users', 'categories', 'products', 'carts', 'orders', 'payment_attempts')
        snapshot = {
            'counts': {name: database[name].count_documents({}) for name in names},
            'documents': {name: list(database[name].find({}).sort('_id', 1)) for name in names},
            'collections': list(database.list_collections()),
            'indexes': {name: list(database[name].list_indexes()) for name in names},
        }
        after = hashlib.sha256(json_util.dumps(snapshot, json_options=json_util.CANONICAL_JSON_OPTIONS, sort_keys=True).encode()).hexdigest()
        before_path = ROOT / '.local/phase04-db-before.json'
        before = json_util.loads(before_path.read_text(encoding='utf-8'))
        assert before['digest'] == after, 'Dev documents/validators/indexes changed during backend foundation'
        assert before['counts'] == snapshot['counts']
        assert all(mongo.client.ecommerce_test[name].count_documents({}) == 0 for name in names), 'Test fixtures were not fully removed'
        suite = ET.parse(ROOT / 'backend/evidence/pytest.xml').getroot().find('testsuite')
        assert suite is not None and suite.attrib['failures'] == suite.attrib['errors'] == suite.attrib['skipped'] == '0'
        report = {
            'status': 'LIVE_BACKEND_FOUNDATION_PASS', 'database': database.name,
            'replicaSet': mongo.client.admin.command('hello')['setName'],
            'health': healthy, 'notFound': missing, 'methodNotAllowed': wrong_method,
            'pytest': dict(suite.attrib), 'counts': snapshot['counts'],
            'databaseFingerprintBefore': before['digest'], 'databaseFingerprintAfter': after,
            'devDataValidatorsIndexesUnchanged': True, 'testDatabaseEmptyAfterCleanup': True,
            'implementedRoutes': [rule.rule for rule in app.url_map.iter_rules()],
            'fullBusinessFeaturesImplemented': False, 'frontendCreated': False,
        }
        (ROOT / 'backend/evidence/runtime-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print({'status': report['status'], 'health': healthy['status'], 'tests': suite.attrib['tests'], 'databaseUnchanged': True})
    finally:
        app.extensions['mongo'].close()
