"""Foundation-only auth probes, registered in test apps; no public Auth APIs."""
import copy
from datetime import datetime, timezone
import pytest
import jwt
from bson import ObjectId
from app.auth import get_current_user, require_auth, require_roles
from app.auth.tokens import create_access_token, decode_access_token
from app.auth.passwords import hash_password, verify_password
from app.errors import AuthenticationError, ValidationError
from app.utils.responses import success


def register_probes(app):
    @app.get('/api/v1/_test/private')
    @require_auth
    def private():
        return success(get_current_user())

    @app.get('/api/v1/_test/admin')
    @require_roles('ADMIN')
    def admin():
        return success(get_current_user())


def token_for(app, user):
    with app.app_context():
        return create_access_token(user)


def authorization(token):
    return {'Authorization': f'Bearer {token}'}


@pytest.mark.integration
def test_customer_admin_permissions_with_real_repository(app, client, identities):
    register_probes(app)
    customer = token_for(app, identities['customer'])
    admin = token_for(app, identities['admin'])
    assert client.get('/api/v1/_test/private').status_code == 401
    response = client.get('/api/v1/_test/private', headers=authorization(customer))
    assert response.status_code == 200 and response.json['data']['id'] == str(identities['customer']['_id'])
    assert 'passwordHash' not in response.text and 'tokenVersion' not in response.json['data']
    assert client.get('/api/v1/_test/admin', headers=authorization(customer)).status_code == 403
    assert client.get('/api/v1/_test/admin', headers=authorization(admin)).status_code == 200


@pytest.mark.integration
def test_blocked_changed_version_and_missing_user_reject(app, client, identities, database):
    register_probes(app)
    user = identities['customer']
    token = token_for(app, user)
    database.users.update_one({'_id': user['_id']}, {'$set': {'status': 'BLOCKED'}})
    assert client.get('/api/v1/_test/private', headers=authorization(token)).status_code == 401
    database.users.update_one({'_id': user['_id']}, {'$set': {'status': 'ACTIVE', 'tokenVersion': 1}})
    assert client.get('/api/v1/_test/private', headers=authorization(token)).status_code == 401
    database.users.delete_one({'_id': user['_id']})
    assert client.get('/api/v1/_test/private', headers=authorization(token)).status_code == 401


@pytest.mark.integration
def test_role_is_current_database_value_not_token_claim(app, client, identities, database):
    register_probes(app)
    user = identities['customer']
    token = token_for(app, user)
    with app.app_context():
        claims = decode_access_token(token)
        claims['role'] = 'ADMIN'
        forged_role = jwt.encode(claims, app.config['JWT_SECRET'], algorithm='HS256')
    assert client.get('/api/v1/_test/admin', headers=authorization(forged_role)).status_code == 403
    # Authorization checks the live role every new request, not a cached JWT role.
    database.users.update_one({'_id': user['_id']}, {'$set': {'role': 'ADMIN'}})
    assert client.get('/api/v1/_test/admin', headers=authorization(token)).status_code == 200


@pytest.mark.parametrize('case', ['expired', 'future', 'wrong-issuer', 'wrong-audience', 'missing-sub', 'bad-sub', 'bool-version', 'float-exp', 'missing-exp', 'wrong-signature', 'wrong-algorithm', 'unsigned', 'bad-lifetime'])
def test_jwt_claims_and_algorithm_strict(app, client, identities, case):
    register_probes(app)
    original = token_for(app, identities['customer'])
    with app.app_context():
        claims = decode_access_token(original)
    now = int(datetime.now(timezone.utc).timestamp())
    key, algorithm = app.config['JWT_SECRET'], 'HS256'
    if case == 'expired': claims.update(iat=now-100, nbf=now-100, exp=now-1)
    elif case == 'future': claims.update(iat=now+100, nbf=now+100, exp=now+200)
    elif case == 'wrong-issuer': claims['iss'] = 'other'
    elif case == 'wrong-audience': claims['aud'] = 'other'
    elif case == 'missing-sub': claims.pop('sub')
    elif case == 'bad-sub': claims['sub'] = 'bad'
    elif case == 'bool-version': claims['tokenVersion'] = True
    elif case == 'float-exp': claims['exp'] = float(now+100)
    elif case == 'missing-exp': claims.pop('exp')
    elif case == 'wrong-signature': key = 'different-private-test-signing-key-123456'
    elif case == 'wrong-algorithm': algorithm = 'HS384'
    elif case == 'unsigned': key, algorithm = '', 'none'
    elif case == 'bad-lifetime': claims['exp'] = now+999999
    token = jwt.encode(claims, key, algorithm=algorithm)
    assert client.get('/api/v1/_test/private', headers=authorization(token)).status_code == 401


@pytest.mark.parametrize('header', ['', 'Basic raw', 'Bearer', 'Bearer a b', 'Bearer garbage', 'Bearer '+'x'*4097])
def test_malformed_bearer_header(app, client, header):
    register_probes(app)
    assert client.get('/api/v1/_test/private', headers={'Authorization': header}).status_code == 401


def test_blocked_cannot_issue_token(app, identities):
    with app.app_context(), pytest.raises(AuthenticationError):
        create_access_token(identities['blocked'])


def test_argon2_hashing_and_policy():
    password = 'Mật khẩu demo 2026'
    hashed = hash_password(password)
    assert hashed.startswith('$argon2id$v=19$m=19456,t=2,p=1$')
    assert verify_password(hashed, password)
    assert not verify_password(hashed, password+'wrong')
    assert not verify_password('not-a-hash', password)
    with pytest.raises(ValidationError): hash_password('short')


def test_real_seed_hash_is_supported(database):
    from dotenv import dotenv_values
    from app.config import PROJECT_ROOT
    env = dotenv_values(PROJECT_ROOT / '.env', interpolate=False)
    user = database.client.ecommerce_dev.users.find_one({'role': 'ADMIN'})
    assert verify_password(user['passwordHash'], env['SEED_DEMO_PASSWORD'])
