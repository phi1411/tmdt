"""Read-only Atlas smoke through the real production Waitress entry point.

Credentials are read only from ignored local files; no database writes or seeds.
"""
import json
import os
import secrets
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import dotenv_values
from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'backend'), str(ROOT / 'scripts/backend')]
from app import create_app
from verify_auth_users import fingerprint
from cleanup_phase06ab_database import snapshot, canonical_schema_check, orphan_check


def main():
    private = json.loads((ROOT / '.local/atlas-upload/connection.json').read_text(encoding='utf-8'))
    assert private['database'] == 'novamart_demo'
    origin = 'https://novamart-runtime.example.test'
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 5003))  # Never replace another listener.
    local_app = create_app()
    local = local_app.extensions['mongo'].database
    atlas_client = MongoClient(private['uri'], serverSelectionTimeoutMS=15000, tz_aware=True)
    atlas = atlas_client[private['database']]
    before = {'local': fingerprint(local), 'atlas': fingerprint(atlas)}
    hello = atlas_client.admin.command('hello')
    assert hello.get('isWritablePrimary') and hello.get('logicalSessionTimeoutMinutes')
    schema = canonical_schema_check(snapshot(atlas))
    orphan_check(snapshot(atlas))
    env = dict(os.environ)
    # Production ignores the development .env and uses a different signing secret.
    env.update(APP_ENV='production', MONGODB_URI=private['uri'], MONGODB_DB=atlas.name,
        MONGODB_REPLICA_SET=hello['setName'], MONGODB_TIMEOUT_MS='15000',
        JWT_SECRET=secrets.token_urlsafe(48), JWT_ISSUER='novamart-api', JWT_AUDIENCE='novamart-web',
        FRONTEND_ORIGIN=origin, CORS_ORIGINS=origin, PORT='5003', API_HOST='127.0.0.1',
        LOG_LEVEL='ERROR', VNPAY_ENABLED='false')
    out = ROOT / '.local/render-runtime'
    out.mkdir(parents=True, exist_ok=True)
    checks = []
    process = None
    def http(method, path, expected=200, payload=None, token=None, request_origin=origin):
        headers = {'Content-Type': 'application/json', 'Origin': request_origin}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        req = Request('http://127.0.0.1:5003/api/v1' + path, method=method, headers=headers,
            data=json.dumps(payload).encode() if payload is not None else None)
        try:
            response = urlopen(req, timeout=30)
        except HTTPError as error:
            response = error
        with response:
            assert response.status == expected, (method, path, response.status)
            allowed = response.headers.get('Access-Control-Allow-Origin')
            assert allowed == origin if request_origin == origin else allowed is None
            body = json.loads(response.read())
            assert body['meta']['requestId'] == response.headers['X-Request-ID']
            checks.append({'method': method, 'path': path, 'status': response.status,
                           'cors': 'allowed' if allowed else 'not_allowed'})
            return body.get('data')
    try:
        with (out / 'server.log').open('w', encoding='utf-8') as log:
            process = subprocess.Popen([sys.executable, 'backend/serve.py'], cwd=ROOT, env=env,
                stdout=log, stderr=log,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            for _ in range(60):
                assert process.poll() is None, 'Production process exited; inspect private log'
                try:
                    with socket.create_connection(('127.0.0.1', 5003), timeout=0.5):
                        break
                except OSError:
                    time.sleep(0.5)
            else:
                raise AssertionError('Production startup timed out')
            health = http('GET', '/health')
            http('GET', '/health', request_origin='https://untrusted.example.test')
            http('GET', '/categories')
            listing = http('GET', '/products?q=07C')
            assert listing
            product = listing[0]
            detail = http('GET', '/products/' + product['slug'])
            assert detail['images']
            seed_password = dotenv_values(ROOT / '.env', interpolate=False)['SEED_DEMO_PASSWORD']
            fixture = json.loads((ROOT / '.local/phase07c/fixture.json').read_text(encoding='utf-8'))
            admin = http('POST', '/auth/login', payload={'email': 'admin@example.test', 'password': seed_password})['accessToken']
            customer = http('POST', '/auth/login', payload={'email': 'defense07c@example.test', 'password': fixture['customerPassword']})['accessToken']
            http('GET', '/auth/me', token=customer)
            http('GET', '/orders', token=customer)
            http('GET', '/admin/users', expected=401)
            http('GET', '/admin/users', expected=403, token=customer)
            http('GET', '/auth/me', expected=401, token='invalid.jwt.token')
            for report in ('summary', 'revenue', 'top-products', 'category-revenue', 'order-status'):
                http('GET', '/admin/dashboard/' + report + '?from=2026-10-01T00%3A00%3A00Z&to=2026-11-01T00%3A00%3A00Z', token=admin)
            http('GET', '/admin/products/' + product['id'], token=admin)
            http('GET', '/unknown', expected=404)
        after = {'local': fingerprint(local), 'atlas': fingerprint(atlas)}
        assert after == before, 'Database changed during read-only production smoke'
        receipt = {'status': 'PRODUCTION_WSGI_ATLAS_READ_ONLY_PASS', 'publicDeployment': False,
            'recordedAtUtc': datetime.now(timezone.utc).isoformat(), 'server': 'Waitress 3.0.2',
            'expectedReplicaSet': hello['setName'], 'database': atlas.name, 'health': health,
            'checks': checks, 'before': before, 'after': after, 'schema': schema,
            'orphans': 0, 'databaseWrites': 0, 'vnpayEnabled': False,
            'limitations': ['Local Windows WSGI, not Render Linux/public TLS/proxy', 'No live payment sandbox']}
        (ROOT / 'backend/evidence/render-prep-runtime.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
        print(json.dumps({'status': receipt['status'], 'httpChecks': len(checks), 'counts': before['atlas']['counts'], 'databasesUnchanged': True}))
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        atlas_client.close()
        local_app.extensions['mongo'].close()


if __name__ == '__main__':
    main()
