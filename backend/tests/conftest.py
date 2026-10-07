"""Real-DB foundation fixtures, guarded test-only writes and exact cleanup."""
import copy
import json
import secrets
from pathlib import Path
from uuid import uuid4
import pytest
from bson import ObjectId
from app import create_app

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def settings():
    return {
        'APP_ENV': 'testing', 'MONGODB_URI': 'mongodb://localhost:27017/?replicaSet=rs0',
        'MONGODB_DB': 'ecommerce_dev', 'MONGODB_TEST_DB': 'ecommerce_test',
        'JWT_SECRET': secrets.token_urlsafe(48), 'JWT_ISSUER': 'ecommerce-api',
        'JWT_AUDIENCE': 'ecommerce-web', 'FRONTEND_ORIGIN': 'http://localhost:5173',
        'LOG_LEVEL': 'ERROR',
    }


@pytest.fixture
def app(settings):
    application = create_app(settings)
    yield application
    application.extensions['mongo'].close()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def database(app):
    database = app.extensions['mongo'].database
    assert database.name == 'ecommerce_test'
    marker = json.loads((ROOT / '.local/ecommerce_test.ownership.json').read_text(encoding='utf-8'))
    assert marker == {'project': str(ROOT), 'database': 'ecommerce_test', 'endpoint': 'localhost:27017/rs0'}
    assert database.client.admin.command('hello')['setName'] == 'rs0'
    assert {c['name'] for c in database.list_collections()} == {'users', 'categories', 'products', 'carts', 'orders', 'payment_attempts'}
    return database


@pytest.fixture
def identities(database):
    # Clone a valid schema example read-only from dev. Never mutate its source.
    original = database.client.ecommerce_dev.users.find_one({'role': 'CUSTOMER', 'status': 'ACTIVE'})
    assert original
    ids = []
    users = {}
    try:
        for label, role, status in [('customer', 'CUSTOMER', 'ACTIVE'), ('admin', 'ADMIN', 'ACTIVE'), ('blocked', 'CUSTOMER', 'BLOCKED')]:
            user = copy.deepcopy(original)
            user['_id'] = ObjectId()
            user['email'] = f'phase04-{uuid4().hex}@example.test'
            user.update(role=role, status=status, tokenVersion=0)
            ids.append(user['_id'])
            database.users.insert_one(user)
            users[label] = user
        yield users
    finally:
        # Exact IDs only; never drop/reset a database, collection, or other test data.
        database.users.delete_many({'_id': {'$in': ids}})
