"""Real browser/Flask/rs0 verification with exact-ID test fixture cleanup."""
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
from threading import Thread
from datetime import datetime, timezone
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
from app import create_app
from app.auth.tokens import create_access_token
from bson import ObjectId, json_util
from bson.int64 import Int64
from pymongo import MongoClient
from werkzeug.serving import make_server


def fingerprint(db):
    data = {name: {'documents': list(db[name].find().sort('_id', 1)), 'options': db[name].options(),
                   'indexes': list(db[name].list_indexes())} for name in sorted(db.list_collection_names())}
    return hashlib.sha256(json_util.dumps(data, json_options=json_util.CANONICAL_JSON_OPTIONS,
                                         sort_keys=True).encode()).hexdigest()


def main():
    client = MongoClient('mongodb://localhost:27017/?replicaSet=rs0', tz_aware=True)
    db = client.ecommerce_test
    marker = json.loads((ROOT / '.local/ecommerce_test.ownership.json').read_text())
    assert marker == {'project': str(ROOT), 'database': db.name, 'endpoint': 'localhost:27017/rs0'}
    assert client.admin.command('hello')['setName'] == 'rs0'
    assert all(db[name].count_documents({}) == 0 for name in db.list_collection_names())
    before = fingerprint(client.ecommerce_dev)
    test_before = fingerprint(db)
    uid, cid, pid, aid = [ObjectId() for _ in range(4)]
    app = server = preview = None
    config_path = ROOT / '.local/coupon-browser/session.json'
    config_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        now = datetime.now(timezone.utc)
        user = copy.deepcopy(client.ecommerce_dev.users.find_one({'role': 'CUSTOMER', 'status': 'ACTIVE'}))
        assert user
        user.update(_id=uid, email='coupon-' + uuid4().hex + '@example.test', name='Khách kiểm thử mã',
                    phone='0901234567', version=1, tokenVersion=0, createdAt=now, updatedAt=now,
                    addresses=[{'_id': aid, 'receiverName': 'Khách kiểm thử', 'phone': '0901234567',
                                'addressLine': '123 Đường kiểm thử', 'province': 'Hồ Chí Minh'}], defaultAddressId=aid)
        db.users.insert_one(user)
        db.categories.insert_one({'_id': cid, 'schemaVersion': 1, 'version': 1, 'createdAt': now, 'updatedAt': now,
                                  'name': 'Coupon test', 'slug': 'coupon-' + uuid4().hex, 'productType': 'ELECTRONICS',
                                  'description': '', 'status': 'ACTIVE'})
        db.products.insert_one({'_id': pid, 'schemaVersion': 1, 'version': 1, 'createdAt': now, 'updatedAt': now,
            'sku': 'COUPON-' + uuid4().hex.upper(), 'name': 'Sản phẩm kiểm thử mã', 'slug': 'coupon-' + uuid4().hex,
            'categoryId': cid, 'productType': 'ELECTRONICS', 'brand': '', 'description': '', 'price': Int64(250000),
            'stock': 10, 'images': ['http://127.0.0.1:5000/coupon-fixture.png'], 'attributes': {'material': 'Fixture'},
            'nameNormalized': 'san pham kiem thu ma', 'brandNormalized': '', 'status': 'ACTIVE'})
        app = create_app({'APP_ENV': 'testing', 'MONGODB_URI': 'mongodb://localhost:27017/?replicaSet=rs0',
                          'MONGODB_DB': 'ecommerce_dev', 'MONGODB_TEST_DB': 'ecommerce_test',
                          'JWT_SECRET': secrets.token_urlsafe(48), 'FRONTEND_ORIGIN': 'http://127.0.0.1:5175',
                          'JWT_ISSUER': 'ecommerce-api', 'JWT_AUDIENCE': 'ecommerce-web',
                          'LOG_LEVEL': 'ERROR', 'VNPAY_ENABLED': True, 'VNP_TMN_CODE': 'TEST0001',
                          'VNP_HASH_SECRET': 'fixture-only-deterministic-merchant-key-not-a-live-credential',
                          'VNP_PAYMENT_URL': 'https://sandbox.vnpayment.vn/paymentv2/vpcpay.html',
                          'VNP_RETURN_URL': 'http://127.0.0.1:5000/api/v1/payments/vnpay/return',
                          'VNP_IPN_URL': 'http://127.0.0.1:5000/api/v1/payments/vnpay/ipn'})
        @app.get('/coupon-fixture.png')
        def image():
            return app.response_class(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a5xkAAAAASUVORK5CYII='), mimetype='image/png')
        with app.app_context():
            token = create_access_token(user)
        test_client = app.test_client()
        response = test_client.post('/api/v1/cart/items', json={'productId': str(pid), 'quantity': 2,
                                    'selectedAttributes': {}, 'cartVersion': 0}, headers={'Authorization': 'Bearer ' + token})
        assert response.status_code == 200, response.json
        config_path.write_text(json.dumps({'token': token}), encoding='utf-8')
        server = make_server('127.0.0.1', 5000, app, threaded=True)
        Thread(target=server.serve_forever, daemon=True).start()
        node = shutil.which('node')
        assert node
        preview = subprocess.Popen([node, str(ROOT / 'frontend/node_modules/vite/bin/vite.js'), 'preview',
                                    '--host', '127.0.0.1', '--port', '5175', '--strictPort'], cwd=ROOT / 'frontend',
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        subprocess.run([node, str(ROOT / 'frontend/tests/cart-coupon-e2e.mjs'), str(config_path)],
                       cwd=ROOT / 'frontend', check=True)
    finally:
        if server:
            server.shutdown()
        if preview:
            preview.terminate(); preview.wait(timeout=15)
        if app:
            app.extensions['mongo'].close()
        for name in ('payment_attempts', 'orders', 'carts'):
            db[name].delete_many({'userId': uid})
        db.products.delete_one({'_id': pid}); db.categories.delete_one({'_id': cid}); db.users.delete_one({'_id': uid})
        config_path.unlink(missing_ok=True)
        integrity = {'developmentFingerprintBefore': before, 'developmentFingerprintAfter': fingerprint(client.ecommerce_dev),
                     'testFingerprintBefore': test_before, 'testFingerprintAfter': fingerprint(db),
                     'testCounts': {n: db[n].count_documents({}) for n in db.list_collection_names()}}
        (ROOT / 'backend/evidence/cart-coupon-browser-integrity.json').write_text(json.dumps(integrity, indent=2), encoding='utf-8')
        client.close()
        assert integrity['developmentFingerprintBefore'] == integrity['developmentFingerprintAfter']
        assert integrity['testFingerprintBefore'] == integrity['testFingerprintAfter']


if __name__ == '__main__':
    main()
