"""Auth/User HTTP integration against real rs0 with exact fixture cleanup."""
import copy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier
from uuid import uuid4
import pytest
import jwt
from bson import ObjectId
from app.auth.passwords import hash_password, verify_password
from app.auth.tokens import create_access_token, decode_access_token
from app.auth.rate_limit import AuthRateLimiter
from app.repositories.user_repository import UserRepository
from werkzeug.exceptions import TooManyRequests

PASSWORD = 'Mật khẩu test 2026'
BASE = '/api/v1'
ADDRESS = {'receiverName': 'Nguyễn Test', 'phone': '+84901234567', 'addressLine': '123 Test',
           'province': 'Hồ Chí Minh', 'ward': 'Phường Test', 'district': 'Quận Test', 'label': 'Nhà'}
pytestmark = pytest.mark.integration


@pytest.fixture(scope='session')
def password_hash():
    return hash_password(PASSWORD)


@pytest.fixture
def user_factory(database, password_hash):
    ids = []

    def create(**overrides):
        now = datetime.now(timezone.utc)
        user = {'_id': ObjectId(), 'schemaVersion': 1, 'createdAt': now, 'updatedAt': now,
                'name': 'Nguyễn Test', 'email': f'phase05a-{uuid4().hex}@example.test', 'phone': '',
                'passwordHash': password_hash, 'role': 'CUSTOMER', 'status': 'ACTIVE',
                'tokenVersion': 0, 'version': 1, 'addresses': [], 'defaultAddressId': None, **overrides}
        ids.append(user['_id'])
        database.users.insert_one(user)
        return user

    yield create
    database.users.delete_many({'_id': {'$in': ids}})


@pytest.fixture
def signup_emails(database):
    emails = []
    yield emails
    if emails:
        database.users.delete_many({'email': {'$in': emails}})


@pytest.fixture
def customer(user_factory):
    return user_factory()


@pytest.fixture
def admin(user_factory):
    return user_factory(role='ADMIN')


def headers(app, user):
    with app.app_context():
        return {'Authorization': f'Bearer {create_access_token(user)}'}


def signup_payload(emails, **overrides):
    email = f'phase05a-{uuid4().hex}@example.test'
    emails.append(email)
    return {'name': 'Nguyễn Test', 'email': email, 'password': PASSWORD, **overrides}


def assert_public(account):
    assert set(account) == {'id', 'name', 'email', 'phone', 'role', 'status', 'version', 'createdAt'}
    assert account['createdAt'].endswith('Z')


def test_register_normalization_hash_and_unique_defaults(client, database, signup_emails):
    payload = signup_payload(signup_emails)
    email = payload['email']
    payload.update(email='  ' + email.upper() + '  ', name='  Nguyễn Test  ', phone=' +84901234567 ')
    response = client.post(BASE + '/auth/register', json=payload)
    assert response.status_code == 201
    user = response.json['data']['user']
    assert_public(user)
    assert user['email'] == email and user['role'] == 'CUSTOMER' and user['name'] == 'Nguyễn Test'
    stored = database.users.find_one({'email': email})
    assert verify_password(stored['passwordHash'], PASSWORD)
    assert stored['passwordHash'].startswith('$argon2id$v=19$m=19456,t=2,p=1$')
    assert stored['addresses'] == [] and stored['defaultAddressId'] is None
    assert stored['tokenVersion'] == 0 and stored['version'] == stored['schemaVersion'] == 1
    assert stored['phone'] == '+84901234567'
    assert PASSWORD not in response.text and 'passwordHash' not in response.text
    duplicate = client.post(BASE + '/auth/register', json=payload)
    assert duplicate.status_code == 409 and duplicate.json['error']['code'] == 'DUPLICATE_RESOURCE'
    assert database.users.count_documents({'email': email}) == 1


@pytest.mark.parametrize('patch', [
    {'email': 'bad'}, {'email': 'x@x'}, {'email': 'a b@example.test'}, {'email': 'x' * 255},
    {'email': {'$ne': None}}, {'password': 'short'}, {'password': 'x'*129}, {'password': None},
    {'name': ''}, {'name': '   '}, {'name': 'x'*101}, {'phone': 'invalid'}, {'phone': '1234567'},
    {'role': 'ADMIN'}, {'role': 'CUSTOMER'}, {'status': 'ACTIVE'}, {'tokenVersion': 0},
    {'passwordHash': 'fake'}, {'_id': str(ObjectId())}, {'addresses': []}, {'version': 1},
])
def test_register_rejects_invalid_or_forbidden_fields(client, database, signup_emails, patch):
    payload = signup_payload(signup_emails, **patch)
    response = client.post(BASE + '/auth/register', json=payload)
    assert response.status_code == 422
    assert response.json['error']['details']
    assert database.users.count_documents({'email': signup_emails[0]}) == 0


@pytest.mark.parametrize('field', ['name', 'email', 'password'])
def test_register_required_fields(client, signup_emails, field):
    payload = signup_payload(signup_emails)
    payload.pop(field)
    response = client.post(BASE + '/auth/register', json=payload)
    assert response.status_code == 422
    assert {'field': field, 'reason': 'Thiếu trường bắt buộc'} in response.json['error']['details']


@pytest.mark.parametrize('password', ['a'*12, 'a'*128, '  mật khẩu dài đủ  ', '😀'*12])
def test_password_boundaries_unicode_and_spaces(app, client, signup_emails, password):
    payload = signup_payload(signup_emails, password=password)
    assert client.post(BASE + '/auth/register', json=payload).status_code == 201
    login = client.post(BASE + '/auth/login', json={'email': payload['email'], 'password': password})
    assert login.status_code == 200
    if password.strip() != password:
        assert client.post(BASE + '/auth/login', json={'email': payload['email'], 'password': password.strip()}).status_code == 401


def test_login_success_jwt_and_current_identity(app, client, customer):
    response = client.post(BASE + '/auth/login', json={'email': ' ' + customer['email'].upper() + ' ', 'password': PASSWORD})
    assert response.status_code == 200
    data = response.json['data']
    assert set(data) == {'accessToken', 'expiresIn', 'user'}
    assert_public(data['user'])
    assert data['expiresIn'] == 1800
    with app.app_context():
        claims = decode_access_token(data['accessToken'])
    assert claims['sub'] == str(customer['_id'])
    assert claims['iss'] == app.config['JWT_ISSUER'] and claims['aud'] == app.config['JWT_AUDIENCE']
    assert claims['exp'] - claims['iat'] == data['expiresIn'] and claims['tokenVersion'] == 0
    assert 'role' not in claims and PASSWORD not in response.text
    me = client.get(BASE + '/auth/me', headers={'Authorization': 'Bearer ' + data['accessToken']})
    assert me.json['data'] == data['user']
    assert 'addresses' not in me.json['data']


def test_login_wrong_unknown_blocked_and_invalid_hash_are_generic(client, customer, user_factory):
    blocked = user_factory(status='BLOCKED')
    corrupt = user_factory(passwordHash='$argon2id$invalid')
    errors = []
    for email, password in [(customer['email'], PASSWORD+'wrong'), ('missing@example.test', PASSWORD),
                            (blocked['email'], PASSWORD), (corrupt['email'], PASSWORD)]:
        response = client.post(BASE + '/auth/login', json={'email': email, 'password': password})
        assert response.status_code == 401 and response.headers['WWW-Authenticate'] == 'Bearer'
        errors.append(response.json['error'])
    assert all(error == errors[0] for error in errors)


@pytest.mark.parametrize('patch', [{'email': {'$ne': None}}, {'password': {'$gt': ''}}, {'role': 'ADMIN'},
                                 {'email': 'bad'}, {'password': 'short'}])
def test_login_input_allowlist(client, customer, patch):
    response = client.post(BASE + '/auth/login', json={'email': customer['email'], 'password': PASSWORD, **patch})
    assert response.status_code == 422


PROTECTED = [
    ('GET', '/auth/me', None, 'any'),
    ('PATCH', '/auth/password', {'currentPassword': PASSWORD, 'newPassword': PASSWORD+'new'}, 'any'),
    ('GET', '/users/me', None, 'customer'), ('PATCH', '/users/me', {'name': 'Changed', 'expectedVersion': 1}, 'customer'),
    ('POST', '/users/me/addresses', {**ADDRESS, 'expectedVersion': 1}, 'customer'),
    ('PATCH', '/users/me/addresses/000000000000000000000001', {'label': 'Home', 'expectedVersion': 1}, 'customer'),
    ('DELETE', '/users/me/addresses/000000000000000000000001', {'expectedVersion': 1}, 'customer'),
    ('PATCH', '/users/me/default-address', {'addressId': '000000000000000000000001', 'expectedVersion': 1}, 'customer'),
    ('GET', '/admin/users', None, 'admin'), ('GET', '/admin/users/000000000000000000000001', None, 'admin'),
    ('PATCH', '/admin/users/000000000000000000000001/status', {'status': 'BLOCKED', 'expectedVersion': 1}, 'admin'),
]


@pytest.mark.parametrize('method,path,payload,role', PROTECTED)
def test_guest_and_wrong_role_matrix(app, client, customer, admin, method, path, payload, role):
    response = client.open(BASE + path, method=method, json=payload)
    assert response.status_code == 401
    assert response.headers['WWW-Authenticate'] == 'Bearer'
    if role != 'any':
        wrong = customer if role == 'admin' else admin
        assert client.open(BASE + path, method=method, json=payload, headers=headers(app, wrong)).status_code == 403


@pytest.mark.parametrize('kind', ['invalid', 'expired'])
def test_auth_me_invalid_expired_tokens(app, client, customer, kind):
    token = 'garbage'
    if kind == 'expired':
        with app.app_context():
            claims = decode_access_token(create_access_token(customer))
        now = int(datetime.now(timezone.utc).timestamp())
        claims.update(iat=now-100, nbf=now-100, exp=now-1)
        token = jwt.encode(claims, app.config['JWT_SECRET'], algorithm='HS256')
    assert client.get(BASE + '/auth/me', headers={'Authorization': f'Bearer {token}'}).status_code == 401


def test_password_change_revokes_all_old_tokens_and_login(app, client, database, customer):
    auth = headers(app, customer)
    another_token = headers(app, customer)
    before = database.users.find_one({'_id': customer['_id']})
    response = client.patch(BASE + '/auth/password', headers=auth,
                            json={'currentPassword': PASSWORD, 'newPassword': '  Mật khẩu mới 2026  '})
    assert response.status_code == 200 and response.json['data'] == {'reauthenticationRequired': True}
    for old in (auth, another_token):
        assert client.get(BASE + '/auth/me', headers=old).status_code == 401
    after = database.users.find_one({'_id': customer['_id']})
    assert after['tokenVersion'] == 1 and after['version'] == 2 and after['updatedAt'] >= before['updatedAt']
    assert after['passwordHash'] != before['passwordHash']
    assert client.post(BASE + '/auth/login', json={'email': customer['email'], 'password': PASSWORD}).status_code == 401
    login = client.post(BASE + '/auth/login', json={'email': customer['email'], 'password': '  Mật khẩu mới 2026  '})
    assert login.status_code == 200
    assert client.get(BASE + '/auth/me', headers={'Authorization': 'Bearer ' + login.json['data']['accessToken']}).status_code == 200


@pytest.mark.parametrize('payload,status', [
    ({'currentPassword': PASSWORD+'wrong', 'newPassword': PASSWORD+'new'}, 401),
    ({'currentPassword': PASSWORD, 'newPassword': 'weak'}, 422),
    ({'currentPassword': PASSWORD, 'newPassword': 'x'*129}, 422),
    ({'currentPassword': PASSWORD, 'newPassword': PASSWORD+'new', 'tokenVersion': 0}, 422),
])
def test_password_failure_does_not_mutate(app, client, database, customer, payload, status):
    before = database.users.find_one({'_id': customer['_id']})
    assert client.patch(BASE + '/auth/password', json=payload, headers=headers(app, customer)).status_code == status
    assert database.users.find_one({'_id': customer['_id']}) == before


def test_admin_can_change_own_password(app, client, admin):
    assert client.patch(BASE + '/auth/password', headers=headers(app, admin),
                        json={'currentPassword': PASSWORD, 'newPassword': PASSWORD+'new'}).status_code == 200


def test_profile_get_update_normalize_version_and_stale(app, client, database, customer):
    auth = headers(app, customer)
    data = client.get(BASE + '/users/me', headers=auth).json['data']
    assert data['addresses'] == [] and data['defaultAddressId'] is None
    assert data['version'] == 1 and 'tokenVersion' not in data and 'passwordHash' not in data
    response = client.patch(BASE + '/users/me', headers=auth,
                            json={'name': '  Updated Customer  ', 'phone': ' +84901234567 ', 'expectedVersion': 1})
    assert response.status_code == 200
    assert response.json['data']['name'] == 'Updated Customer'
    assert response.json['data']['phone'] == '+84901234567' and response.json['data']['version'] == 2
    assert database.users.find_one({'_id': customer['_id']})['tokenVersion'] == 0
    assert client.patch(BASE + '/users/me', headers=auth, json={'name': 'stale', 'expectedVersion': 1}).status_code == 409
    assert client.get(BASE + '/auth/me', headers=auth).status_code == 200
    assert client.patch(BASE + '/users/me', headers=auth, json={'phone': '', 'expectedVersion': 2}).status_code == 200


@pytest.mark.parametrize('patch', [{'role': 'ADMIN'}, {'status': 'BLOCKED'}, {'email': 'new@example.test'},
                                 {'passwordHash': 'private'}, {'tokenVersion': 3}, {'_id': str(ObjectId())},
                                 {'addresses': []}, {'version': 1}, {'name': ' '}, {'phone': '123'},
                                 {'expectedVersion': True}, {'expectedVersion': 1.0}, {'expectedVersion': 0},
                                 {'expectedVersion': 2147483648}, {}])
def test_profile_invalid_forbidden_or_empty_update(app, client, database, customer, patch):
    before = database.users.find_one({'_id': customer['_id']})
    payload = {'expectedVersion': 1, **patch}
    assert client.patch(BASE + '/users/me', json=payload, headers=headers(app, customer)).status_code == 422
    assert database.users.find_one({'_id': customer['_id']}) == before


def test_address_crud_default_reset_and_ownership(app, client, database, customer, user_factory):
    auth = headers(app, customer)
    other = user_factory()
    created = client.post(BASE + '/users/me/addresses', json={**ADDRESS, 'expectedVersion': 1}, headers=auth)
    assert created.status_code == 201
    data = created.json['data']
    address_id = data['address']['id']
    assert data['version'] == 2 and '_id' not in data['address']
    other_auth = headers(app, other)
    for method, path, payload in [
        ('PATCH', '/users/me/addresses/'+address_id, {'label': 'other', 'expectedVersion': 1}),
        ('DELETE', '/users/me/addresses/'+address_id, {'expectedVersion': 1}),
        ('PATCH', '/users/me/default-address', {'addressId': address_id, 'expectedVersion': 1}),
    ]:
        assert client.open(BASE+path, method=method, json=payload, headers=other_auth).status_code == 404
    updated = client.patch(BASE+'/users/me/addresses/'+address_id, json={'addressLine': 'Changed', 'expectedVersion': 2}, headers=auth)
    assert updated.status_code == 200 and updated.json['data']['version'] == 3
    assert updated.json['data']['address']['receiverName'] == ADDRESS['receiverName']
    assert updated.json['data']['address']['addressLine'] == 'Changed'
    default = client.patch(BASE+'/users/me/default-address', json={'addressId': address_id, 'expectedVersion': 3}, headers=auth)
    assert default.json['data'] == {'defaultAddressId': address_id, 'version': 4}
    assert client.delete(BASE+'/users/me/addresses/'+address_id, json={'expectedVersion': 3}, headers=auth).status_code == 409
    deleted = client.delete(BASE+'/users/me/addresses/'+address_id, json={'expectedVersion': 4}, headers=auth)
    assert deleted.status_code == 204 and deleted.data == b''
    user = database.users.find_one({'_id': customer['_id']})
    assert user['version'] == 5 and user['addresses'] == [] and user['defaultAddressId'] is None
    assert client.get(BASE+'/users/me', headers=auth).json['data']['version'] == 5


@pytest.mark.parametrize('patch', [{'receiverName': ' '}, {'phone': ''}, {'phone': '123'}, {'phone': 'x'*16},
                                 {'addressLine': ''}, {'addressLine': 'x'*301}, {'province': ' '}, {'ward': ''},
                                 {'district': None}, {'label': ''}, {'label': 'x'*51}, {'_id': str(ObjectId())},
                                 {'id': str(ObjectId())}, {'userId': str(ObjectId())}, {'expectedVersion': False}])
def test_invalid_address_input(app, client, customer, patch):
    assert client.post(BASE+'/users/me/addresses', json={**ADDRESS, 'expectedVersion': 1, **patch}, headers=headers(app, customer)).status_code == 422


@pytest.mark.parametrize('field', ['receiverName', 'phone', 'addressLine', 'province', 'expectedVersion'])
def test_address_required(app, client, customer, field):
    payload = {**ADDRESS, 'expectedVersion': 1}
    payload.pop(field)
    assert client.post(BASE+'/users/me/addresses', json=payload, headers=headers(app, customer)).status_code == 422


def test_address_unknown_id_and_malformed_id(app, client, customer):
    auth = headers(app, customer)
    for identifier, status in [('bad', 400), (str(ObjectId()), 404)]:
        assert client.patch(BASE+'/users/me/addresses/'+identifier, json={'label': 'Home', 'expectedVersion': 1}, headers=auth).status_code == status
        assert client.delete(BASE+'/users/me/addresses/'+identifier, json={'expectedVersion': 1}, headers=auth).status_code == status
        assert client.patch(BASE+'/users/me/default-address', json={'addressId': identifier, 'expectedVersion': 1}, headers=auth).status_code == status


def test_address_patch_allowlist_empty_and_stale(app, client, customer):
    auth = headers(app, customer)
    added = client.post(BASE+'/users/me/addresses', json={**ADDRESS, 'expectedVersion': 1}, headers=auth).json['data']
    path = BASE+'/users/me/addresses/'+added['address']['id']
    for payload in [{'expectedVersion': 2}, {'phone': '', 'expectedVersion': 2}, {'role': 'ADMIN', 'expectedVersion': 2}]:
        assert client.patch(path, json=payload, headers=auth).status_code == 422
    assert client.patch(path, json={'label': 'Home', 'expectedVersion': 1}, headers=auth).status_code == 409


def test_admin_list_detail_filters_pagination_and_projection(app, client, customer, admin, user_factory):
    user_factory(status='BLOCKED')
    auth = headers(app, admin)
    listed = client.get(BASE+'/admin/users?role=CUSTOMER&status=ACTIVE&page=1&pageSize=1', headers=auth)
    assert listed.status_code == 200 and listed.json['meta']['total'] == 1
    assert listed.json['meta']['totalPages'] == 1 and len(listed.json['data']) == 1
    assert_public(listed.json['data'][0])
    detail = client.get(BASE+'/admin/users/'+str(customer['_id']), headers=auth)
    assert detail.status_code == 200
    assert_public(detail.json['data'])
    assert 'addresses' not in detail.json['data']
    found = client.get(BASE+'/admin/users', query_string={'q': '  '+customer['email'].upper()+'  '}, headers=auth)
    assert len(found.json['data']) == 1 and found.json['data'][0]['id'] == str(customer['_id'])
    by_name = client.get(BASE+'/admin/users', query_string={'q': 'NGUYỄN'}, headers=auth)
    assert by_name.json['meta']['total'] == 3
    empty = client.get(BASE+'/admin/users?q=.*', headers=auth)
    assert empty.json['data'] == [] and empty.json['meta']['totalPages'] == 0
    page2 = client.get(BASE+'/admin/users?page=2&pageSize=1', headers=auth)
    assert len(page2.json['data']) == 1 and page2.json['meta']['total'] == 3
    assert client.get(BASE+'/admin/users/'+str(ObjectId()), headers=auth).status_code == 404
    assert client.get(BASE+'/admin/users/bad', headers=auth).status_code == 400


@pytest.mark.parametrize('query,status', [('role=SELLER', 422), ('status=DISABLED', 422), ('q='+'a'*101, 422),
                                        ('pageSize=101', 422), ('page=0', 422), ('page=abc', 400),
                                        ('sort=name', 422), ('q=a&q=b', 422), ('$where=x', 422), ('limit=10', 422)])
def test_admin_query_validation(app, client, admin, query, status):
    assert client.get(BASE+'/admin/users?'+query, headers=headers(app, admin)).status_code == status


def test_admin_block_reactivate_noop_versions_and_token_revocation(app, client, database, customer, admin):
    auth = headers(app, admin)
    customer_auth = headers(app, customer)
    path = BASE+'/admin/users/'+str(customer['_id'])+'/status'
    noop = client.patch(path, json={'status': 'ACTIVE', 'expectedVersion': 1}, headers=auth)
    assert noop.status_code == 200 and noop.json['data']['version'] == 1
    assert database.users.find_one({'_id': customer['_id']})['tokenVersion'] == 0
    blocked = client.patch(path, json={'status': 'BLOCKED', 'expectedVersion': 1}, headers=auth)
    assert blocked.status_code == 200 and blocked.json['data']['version'] == 2
    assert client.get(BASE+'/auth/me', headers=customer_auth).status_code == 401
    assert client.get(BASE+'/users/me', headers=customer_auth).status_code == 401
    assert client.post(BASE+'/auth/login', json={'email': customer['email'], 'password': PASSWORD}).status_code == 401
    assert client.patch(path, json={'status': 'ACTIVE', 'expectedVersion': 1}, headers=auth).status_code == 409
    assert client.patch(path, json={'status': 'ACTIVE', 'expectedVersion': 2}, headers=auth).status_code == 200
    assert client.get(BASE+'/auth/me', headers=customer_auth).status_code == 401
    assert client.post(BASE+'/auth/login', json={'email': customer['email'], 'password': PASSWORD}).status_code == 200
    stored = database.users.find_one({'_id': customer['_id']})
    assert stored['version'] == 3 and stored['tokenVersion'] == 2


@pytest.mark.parametrize('status', ['ACTIVE', 'BLOCKED'])
def test_admin_accounts_are_protected_even_noop(app, client, database, admin, user_factory, status):
    other = user_factory(role='ADMIN')
    for target in (admin, other):
        before = database.users.find_one({'_id': target['_id']})
        response = client.patch(BASE+'/admin/users/'+str(target['_id'])+'/status',
                                json={'status': status, 'expectedVersion': 1}, headers=headers(app, admin))
        assert response.status_code == 409 and response.json['error']['code'] == 'BUSINESS_RULE_VIOLATION'
        assert database.users.find_one({'_id': target['_id']}) == before


@pytest.mark.parametrize('patch', [{'status': 'DISABLED'}, {'role': 'ADMIN'}, {'passwordHash': 'fake'},
                                 {'tokenVersion': 8}, {'expectedVersion': True}])
def test_admin_status_allowlist(app, client, customer, admin, patch):
    response = client.patch(BASE+'/admin/users/'+str(customer['_id'])+'/status',
                            json={'status': 'BLOCKED', 'expectedVersion': 1, **patch}, headers=headers(app, admin))
    assert response.status_code == 422


def test_no_extra_auth_routes(client):
    for method, path in [('POST', '/auth/refresh'), ('POST', '/auth/logout'), ('POST', '/auth/forgot-password'),
                         ('POST', '/auth/social-login')]:
        assert client.open(BASE+path, method=method).status_code == 404


def test_login_rate_limits_account_normalization_and_retry_after(app, client, customer):
    for i in range(10):
        response = client.post(BASE+'/auth/login', json={'email': customer['email'].upper() if i % 2 else customer['email'], 'password': PASSWORD+'wrong'},
                               environ_overrides={'REMOTE_ADDR': f'127.0.1.{i}'})
        assert response.status_code == 401
    response = client.post(BASE+'/auth/login', json={'email': customer['email'], 'password': PASSWORD}, environ_overrides={'REMOTE_ADDR': '127.0.2.1'})
    assert response.status_code == 429 and response.json['error']['code'] == 'RATE_LIMITED'
    assert 1 <= int(response.headers['Retry-After']) <= 61


def test_login_ip_limit_ignores_spoofed_forwarded_headers(client):
    for i in range(30):
        response = client.post(BASE+'/auth/login', json={'email': f'missing-{i}@example.test', 'password': PASSWORD},
                               headers={'X-Forwarded-For': f'192.0.2.{i}'})
        assert response.status_code == 401
    assert client.post(BASE+'/auth/login', json={'email': 'last@example.test', 'password': PASSWORD}).status_code == 429


def test_register_rate_limit_includes_invalid_requests(client):
    for _ in range(10):
        assert client.post(BASE+'/auth/register', json={}).status_code == 422
    assert client.post(BASE+'/auth/register', json={}).status_code == 429


def test_limiter_expiry_bounded_store_and_thread_safety():
    now = [100.0]
    limiter = AuthRateLimiter(clock=lambda: now[0])
    def attempt(_):
        try:
            limiter.check('register', 'same-ip')
            return True
        except TooManyRequests:
            return False
    with ThreadPoolExecutor(max_workers=12) as executor:
        assert sum(executor.map(attempt, range(24))) == 10
    assert all(isinstance(key, bytes) for key in limiter.buckets)
    now[0] += 60
    limiter.check('register', 'same-ip')
    limiter.MAX_BUCKETS = 1
    with pytest.raises(TooManyRequests):
        limiter.check('register', 'another-ip')


def test_concurrent_registration_unique_index(app, database, signup_emails, monkeypatch):
    payload = signup_payload(signup_emails)
    barrier = Barrier(2)
    original = UserRepository.insert
    def insert(self, document):
        barrier.wait(timeout=10)
        return original(self, document)
    monkeypatch.setattr(UserRepository, 'insert', insert)
    def request(_):
        with app.test_client() as client:
            return client.post(BASE+'/auth/register', json=payload).status_code
    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(request, range(2))) == [201, 409]
    assert database.users.count_documents({'email': payload['email']}) == 1


def race_profile_reads(monkeypatch):
    barrier = Barrier(2)
    original = UserRepository.find_profile
    def read(self, user_id):
        snapshot = original(self, user_id)
        barrier.wait(timeout=10)
        return snapshot
    monkeypatch.setattr(UserRepository, 'find_profile', read)


def test_concurrent_profile_updates_one_winner(app, database, customer, monkeypatch):
    race_profile_reads(monkeypatch)
    auth = headers(app, customer)
    def request(index):
        with app.test_client() as client:
            return client.patch(BASE+'/users/me', json={'name': f'Winner {index}', 'expectedVersion': 1}, headers=auth).status_code
    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(request, range(2))) == [200, 409]
    user = database.users.find_one({'_id': customer['_id']})
    assert user['version'] == 2 and user['name'] in {'Winner 0', 'Winner 1'}


def test_concurrent_add_at_address_limit(app, client, database, user_factory, monkeypatch):
    addresses = [{'_id': ObjectId(), **ADDRESS} for _ in range(9)]
    customer = user_factory(addresses=addresses)
    auth = headers(app, customer)
    with monkeypatch.context() as patch:
        race_profile_reads(patch)
        def request(_):
            with app.test_client() as thread_client:
                return thread_client.post(BASE+'/users/me/addresses', json={**ADDRESS, 'expectedVersion': 1}, headers=auth).status_code
        with ThreadPoolExecutor(max_workers=2) as executor:
            assert sorted(executor.map(request, range(2))) == [201, 409]
    stored = database.users.find_one({'_id': customer['_id']})
    assert len(stored['addresses']) == 10 and stored['version'] == 2
    assert len({a['_id'] for a in stored['addresses']}) == 10
    response = client.post(BASE+'/users/me/addresses', json={**ADDRESS, 'expectedVersion': 2}, headers=auth)
    assert response.status_code == 409 and response.json['error']['code'] == 'BUSINESS_RULE_VIOLATION'


def test_concurrent_default_set_and_delete_no_dangling_reference(app, database, user_factory, monkeypatch):
    address_id = ObjectId()
    customer = user_factory(addresses=[{'_id': address_id, **ADDRESS}])
    auth = headers(app, customer)
    race_profile_reads(monkeypatch)
    def request(operation):
        with app.test_client() as client:
            if operation == 'delete':
                return client.delete(BASE+'/users/me/addresses/'+str(address_id), json={'expectedVersion': 1}, headers=auth).status_code
            return client.patch(BASE+'/users/me/default-address', json={'addressId': str(address_id), 'expectedVersion': 1}, headers=auth).status_code
    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(request, ['delete', 'default']))
    assert sorted(statuses) in ([200, 409], [204, 409])
    user = database.users.find_one({'_id': customer['_id']})
    assert user['version'] == 2
    assert user['defaultAddressId'] is None or user['defaultAddressId'] in {a['_id'] for a in user['addresses']}


def test_concurrent_admin_status_same_version_one_winner(app, database, customer, admin, monkeypatch):
    race_profile_reads(monkeypatch)
    auth = headers(app, admin)
    def request(_):
        with app.test_client() as client:
            return client.patch(BASE+'/admin/users/'+str(customer['_id'])+'/status',
                                json={'status': 'BLOCKED', 'expectedVersion': 1}, headers=auth).status_code
    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(request, range(2))) == [200, 409]
    user = database.users.find_one({'_id': customer['_id']})
    assert user['version'] == 2 and user['tokenVersion'] == 1 and user['status'] == 'BLOCKED'


def test_block_between_password_verify_and_write_prevents_change(app, client, database, customer, monkeypatch):
    before = database.users.find_one({'_id': customer['_id']})
    original = UserRepository.change_password
    def block_before_write(self, *args, **kwargs):
        database.users.update_one({'_id': customer['_id']}, {'$set': {'status': 'BLOCKED'}, '$inc': {'tokenVersion': 1, 'version': 1}})
        return original(self, *args, **kwargs)
    monkeypatch.setattr(UserRepository, 'change_password', block_before_write)
    response = client.patch(BASE+'/auth/password', json={'currentPassword': PASSWORD, 'newPassword': PASSWORD+'new'}, headers=headers(app, customer))
    assert response.status_code == 401
    after = database.users.find_one({'_id': customer['_id']})
    assert after['passwordHash'] == before['passwordHash'] and after['tokenVersion'] == 1


def test_revoke_between_profile_read_and_write_prevents_mutation(app, client, database, customer, monkeypatch):
    original = UserRepository.compare_and_set
    def revoke_before_write(self, *args, **kwargs):
        database.users.update_one({'_id': customer['_id']}, {'$inc': {'tokenVersion': 1, 'version': 1}})
        return original(self, *args, **kwargs)
    monkeypatch.setattr(UserRepository, 'compare_and_set', revoke_before_write)
    response = client.patch(BASE+'/users/me', json={'name': 'Forbidden update', 'expectedVersion': 1}, headers=headers(app, customer))
    assert response.status_code == 409
    assert database.users.find_one({'_id': customer['_id']})['name'] == customer['name']


def test_concurrent_password_changes_only_one_succeeds(app, database, customer, monkeypatch):
    barrier = Barrier(2)
    original = UserRepository.change_password
    def write(self, *args, **kwargs):
        barrier.wait(timeout=10)
        return original(self, *args, **kwargs)
    monkeypatch.setattr(UserRepository, 'change_password', write)
    auth = headers(app, customer)
    def request(index):
        with app.test_client() as client:
            return client.patch(BASE+'/auth/password', json={'currentPassword': PASSWORD, 'newPassword': PASSWORD+str(index)}, headers=auth).status_code
    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(request, range(2))) == [200, 401]
    user = database.users.find_one({'_id': customer['_id']})
    assert user['version'] == 2 and user['tokenVersion'] == 1
    assert sum(verify_password(user['passwordHash'], PASSWORD+str(i)) for i in range(2)) == 1


def test_profile_address_and_block_do_not_rewrite_order_snapshot(app, client, database, customer, admin):
    order = copy.deepcopy(database.client.ecommerce_dev.orders.find_one({}))
    order.update(_id=ObjectId(), userId=customer['_id'], orderCode='TEST-'+uuid4().hex.upper(),
                 checkoutKey='phase05a-'+uuid4().hex)
    try:
        database.orders.insert_one(order)
        original = database.orders.find_one({'_id': order['_id']})
        auth = headers(app, customer)
        assert client.patch(BASE+'/users/me', json={'name': 'New name', 'phone': '0901234567', 'expectedVersion': 1}, headers=auth).status_code == 200
        assert client.post(BASE+'/users/me/addresses', json={**ADDRESS, 'expectedVersion': 2}, headers=auth).status_code == 201
        assert client.patch(BASE+'/admin/users/'+str(customer['_id'])+'/status', json={'status': 'BLOCKED', 'expectedVersion': 3}, headers=headers(app, admin)).status_code == 200
        assert database.orders.find_one({'_id': order['_id']}) == original
    finally:
        database.orders.delete_one({'_id': order['_id']})


def test_versions_cannot_overflow_bson_int(app, client, user_factory, admin):
    customer = user_factory(version=2147483647, tokenVersion=2147483647)
    auth = headers(app, customer)
    assert client.patch(BASE+'/users/me', json={'name': 'New', 'expectedVersion': 2147483647}, headers=auth).status_code == 409
    assert client.patch(BASE+'/auth/password', json={'currentPassword': PASSWORD, 'newPassword': PASSWORD+'new'}, headers=auth).status_code == 409
    assert client.patch(BASE+'/admin/users/'+str(customer['_id'])+'/status', json={'status': 'BLOCKED', 'expectedVersion': 2147483647}, headers=headers(app, admin)).status_code == 409


@pytest.mark.parametrize('path,role', [('/auth/me', 'customer'), ('/users/me', 'customer'), ('/admin/users/{id}', 'admin')])
def test_detail_endpoints_reject_unknown_query(app, client, customer, admin, path, role):
    auth = headers(app, admin if role == 'admin' else customer)
    assert client.get(BASE+path.format(id=customer['_id'])+'?q=unexpected', headers=auth).status_code == 422


@pytest.mark.parametrize('method,path', [('POST', '/auth/register'), ('POST', '/auth/login')])
def test_auth_json_syntax_and_content_type(client, method, path):
    assert client.open(BASE+path, method=method, data='{', content_type='application/json').status_code == 400
    assert client.open(BASE+path, method=method, data='{}', content_type='text/plain').status_code == 415
