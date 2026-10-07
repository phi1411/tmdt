"""PHASE05A evidence: read-only dev fingerprint and real HTTP on owned test DB."""
import argparse
import hashlib
import json
import secrets
import sys
import xml.etree.ElementTree as ET
from importlib.metadata import version
from pathlib import Path
from threading import Thread
from uuid import uuid4
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from bson import ObjectId, json_util
from werkzeug.serving import make_server

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app import create_app

NAMES = ('users', 'categories', 'products', 'carts', 'orders', 'payment_attempts')
BASELINE = ROOT / '.local/phase05a-db-before.json'


def fingerprint(database):
    snapshot = {
        'counts': {n: database[n].count_documents({}) for n in NAMES},
        'documents': {n: list(database[n].find({}).sort('_id', 1)) for n in NAMES},
        'collections': list(database.list_collections()),
        'indexes': {n: list(database[n].list_indexes()) for n in NAMES},
    }
    digest = hashlib.sha256(json_util.dumps(snapshot, json_options=json_util.CANONICAL_JSON_OPTIONS,
                                           sort_keys=True).encode()).hexdigest()
    return {'digest': digest, 'counts': snapshot['counts']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--capture', action='store_true')
    args = parser.parse_args()
    dev_app = create_app()
    try:
        before = fingerprint(dev_app.extensions['mongo'].database)
        if args.capture:
            with BASELINE.open('x', encoding='utf-8') as file:
                json.dump(before, file, indent=2)
            print('Saved PHASE05A read-only dev fingerprint')
            return
        assert before == json.loads(BASELINE.read_text(encoding='utf-8')), 'Dev DB changed since baseline'
        config = {key: dev_app.config[key] for key in ('MONGODB_URI', 'JWT_SECRET', 'JWT_ISSUER', 'JWT_AUDIENCE')}
        config.update(APP_ENV='testing', MONGODB_DB='ecommerce_dev', MONGODB_TEST_DB='ecommerce_test', LOG_LEVEL='ERROR')
        test_app = create_app(config)
        database = test_app.extensions['mongo'].database
        emails = []
        server = None
        try:
            assert database.name == 'ecommerce_test'
            marker = json.loads((ROOT / '.local/ecommerce_test.ownership.json').read_text(encoding='utf-8'))
            assert marker == {'project': str(ROOT), 'database': 'ecommerce_test', 'endpoint': 'localhost:27017/rs0'}
            assert all(database[n].count_documents({}) == 0 for n in NAMES)
            server = make_server('127.0.0.1', 0, test_app, threaded=True)
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f'http://127.0.0.1:{server.server_port}/api/v1'
            checks = []

            def http(method, path, expected, payload=None, token=None):
                headers = {'Content-Type': 'application/json'}
                if token:
                    headers['Authorization'] = f'Bearer {token}'
                raw = json.dumps(payload).encode() if payload is not None else None
                try:
                    response = urlopen(Request(base + path, data=raw, headers=headers, method=method), timeout=10)
                except HTTPError as error:
                    response = error
                with response:
                    content = response.read()
                    assert response.status == expected, (method, path, response.status)
                    body = json.loads(content) if content else None
                    if body:
                        assert body['meta']['requestId'] == response.headers['X-Request-ID']
                        assert 'passwordHash' not in body.get('data', {}) and 'tokenVersion' not in content.decode()
                    checks.append({'method': method, 'path': path, 'status': response.status})
                    return body['data'] if body and 'data' in body else body

            password = secrets.token_urlsafe(24)
            email = f'phase05a-http-{uuid4().hex}@example.test'
            emails.append(email)
            http('GET', '/health', 200)
            user = http('POST', '/auth/register', 201, {'name': 'HTTP Customer', 'email': email, 'password': password})['user']
            login = http('POST', '/auth/login', 200, {'email': email, 'password': password})
            token = login['accessToken']
            http('GET', '/auth/me', 200, token=token)
            http('GET', '/users/me', 200, token=token)
            profile = http('PATCH', '/users/me', 200, {'name': 'Updated HTTP Customer', 'expectedVersion': 1}, token)
            address = http('POST', '/users/me/addresses', 201, {
                'receiverName': 'HTTP Customer', 'phone': '0901234567', 'addressLine': '123 Test',
                'province': 'Hồ Chí Minh', 'expectedVersion': profile['version'],
            }, token)
            address_id = address['address']['id']
            address = http('PATCH', f'/users/me/addresses/{address_id}', 200,
                           {'label': 'Home', 'expectedVersion': address['version']}, token)
            default = http('PATCH', '/users/me/default-address', 200,
                           {'addressId': address_id, 'expectedVersion': address['version']}, token)
            http('DELETE', f'/users/me/addresses/{address_id}', 204, {'expectedVersion': default['version']}, token)
            http('GET', '/admin/users', 403, token=token)
            # Admin exists only as controlled test fixture, never public signup.
            from app.auth.passwords import hash_password
            from datetime import datetime, timezone
            admin_email = f'phase05a-http-{uuid4().hex}@example.test'
            emails.append(admin_email)
            now = datetime.now(timezone.utc)
            database.users.insert_one({'_id': ObjectId(), 'schemaVersion': 1, 'name': 'HTTP Admin',
                'email': admin_email, 'phone': '', 'passwordHash': hash_password(password), 'role': 'ADMIN',
                'status': 'ACTIVE', 'tokenVersion': 0, 'version': 1, 'createdAt': now, 'updatedAt': now,
                'addresses': [], 'defaultAddressId': None})
            admin_token = http('POST', '/auth/login', 200, {'email': admin_email, 'password': password})['accessToken']
            http('GET', '/admin/users?pageSize=1', 200, token=admin_token)
            target = http('GET', f"/admin/users/{user['id']}", 200, token=admin_token)
            blocked = http('PATCH', f"/admin/users/{user['id']}/status", 200,
                           {'status': 'BLOCKED', 'expectedVersion': target['version']}, admin_token)
            http('GET', '/auth/me', 401, token=token)
            http('PATCH', f"/admin/users/{user['id']}/status", 200,
                 {'status': 'ACTIVE', 'expectedVersion': blocked['version']}, admin_token)
            token = http('POST', '/auth/login', 200, {'email': email, 'password': password})['accessToken']
            http('PATCH', '/auth/password', 200, {'currentPassword': password, 'newPassword': password + 'new'}, token)
            http('GET', '/auth/me', 401, token=token)
        finally:
            if server:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)
            if emails:
                database.users.delete_many({'email': {'$in': emails}})
            test_app.extensions['mongo'].close()
        after = fingerprint(dev_app.extensions['mongo'].database)
        assert before == after
        assert all(dev_app.extensions['mongo'].client.ecommerce_test[n].count_documents({}) == 0 for n in NAMES)
        suite = ET.parse(ROOT / 'backend/evidence/phase05a-pytest.xml').getroot().find('testsuite')
        assert suite is not None and all(suite.attrib[key] == '0' for key in ('failures', 'errors', 'skipped'))
        report = {'status': 'PHASE05A_HTTP_PASS', 'httpChecks': checks, 'counts': after['counts'],
                  'pytest': dict(suite.attrib),
                  'runtime': {'python': sys.version.split()[0],
                              **{name: version(name) for name in ('Flask', 'pymongo', 'pytest', 'argon2-cffi', 'PyJWT')},
                              'mongodb': dev_app.extensions['mongo'].client.admin.command('buildInfo')['version'],
                              'replicaSet': dev_app.extensions['mongo'].client.admin.command('hello')['setName']},
                  'databaseFingerprintBefore': before['digest'], 'databaseFingerprintAfter': after['digest'],
                  'devDataValidatorsIndexesUnchanged': True, 'testDatabaseEmptyAfterCleanup': True,
                  'frontendCreatedByThisWorker': False, 'workerScope': 'AUTH_USERS_ONLY'}
        (ROOT / 'backend/evidence/phase05a-runtime-verification.json').write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print({'status': report['status'], 'httpChecks': len(checks), 'devDatabaseUnchanged': True})
    finally:
        dev_app.extensions['mongo'].close()


if __name__ == '__main__':
    main()
