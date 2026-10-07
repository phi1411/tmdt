import io
import json
import logging
from datetime import datetime, timezone
import pytest
from bson import ObjectId
from bson.int64 import Int64
from pymongo.errors import DuplicateKeyError, ServerSelectionTimeoutError
from werkzeug.exceptions import NotFound
from app import create_app
from app.config import ConfigurationError, load_config
from app.errors import BadRequestError, AuthenticationError, AuthorizationError, NotFoundError, ConflictError, BusinessRuleError, ValidationError, ServiceUnavailableError
from app.schemas.validation import parse_json_body, single_query_values
from app.schemas.pagination import Pagination
from app.schemas.query_contract import PRODUCT_QUERY_FIELDS
from app.utils.ids import parse_object_id
from app.utils.responses import success, no_content, paginated
from app.utils.serialization import to_api
from app.utils.logging import SafeJSONFormatter


@pytest.mark.integration
def test_startup_health_reuses_client(app, client):
    mongo = app.extensions['mongo']
    original = mongo.client
    for _ in range(2):
        response = client.get('/api/v1/health')
        assert response.status_code == 200
        assert response.json['data'] == {'status': 'ok', 'checks': {'backend': 'ok', 'database': 'ok', 'replicaSet': 'ok'}}
        assert response.json['meta']['requestId'] == response.headers['X-Request-ID']
    assert mongo.client is original and not mongo.closed
    assert mongo.database.name == 'ecommerce_test'
    assert original.admin.command('hello')['isWritablePrimary']
    assert list(app.url_map.iter_rules())[0].rule == '/api/v1/health'


def test_environment_precedence_and_test_isolation(monkeypatch, tmp_path, settings):
    for key in settings:
        monkeypatch.delenv(key, raising=False)
    env_file = tmp_path / '.env'
    env_file.write_text('\n'.join(f'{k}={v}' for k, v in settings.items())+'\nAPI_PORT=5100\n', encoding='utf-8')
    monkeypatch.setenv('API_PORT', '5200')
    assert load_config({'API_PORT': 5300}, env_file)['API_PORT'] == 5300
    assert load_config(env_file=env_file)['API_PORT'] == 5200
    assert load_config(env_file=env_file)['MONGODB_DB'] == 'ecommerce_test'


@pytest.mark.parametrize('override', [
    {'JWT_SECRET': ''}, {'JWT_SECRET': 'REPLACE_WITH_RANDOM_SECRET'}, {'MONGODB_URI': ''},
    {'MONGODB_URI': 'invalid'}, {'MONGODB_URI': 'mongodb://localhost:27017/'},
    {'MONGODB_URI': 'mongodb://localhost:27017/?replicaSet=other'},
    {'MONGODB_URI': 'mongodb://localhost:27017/?replicaSet=rs0&directConnection=true'},
    {'MONGODB_TEST_DB': 'ecommerce_dev'}, {'APP_ENV': 'unknown'}, {'API_PORT': 'bad'},
    {'JWT_ACCESS_TTL_SECONDS': False}, {'MAX_CONTENT_LENGTH': 0}, {'CORS_ORIGINS': '*'},
])
def test_invalid_config_fails_without_secret_values(settings, override):
    with pytest.raises(ConfigurationError) as caught:
        load_config({**settings, **override})
    assert settings['JWT_SECRET'] not in str(caught.value)


def test_missing_required_config_is_not_defaulted(monkeypatch):
    for key in ('MONGODB_URI', 'MONGODB_TEST_DB', 'JWT_SECRET'):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(ConfigurationError):
        load_config({'APP_ENV': 'testing'})


def test_startup_rejects_unavailable_database(settings):
    with pytest.raises(ConfigurationError, match='not ready'):
        create_app({**settings, 'MONGODB_URI': 'mongodb://localhost:1/?replicaSet=rs0', 'MONGODB_TIMEOUT_MS': 100})


def test_wrong_topology_is_not_silently_accepted(app, monkeypatch):
    mongo = app.extensions['mongo']
    monkeypatch.setattr(type(mongo.client.admin), 'command', lambda self, name: {'setName': 'wrong', 'isWritablePrimary': True, 'logicalSessionTimeoutMinutes': 30})
    with pytest.raises(ConfigurationError):
        mongo.health()


def test_health_failure_has_safe_503(app, client, monkeypatch):
    def down():
        raise ServerSelectionTimeoutError('mongodb://hidden:password@secret-host')
    monkeypatch.setattr(app.extensions['mongo'], 'health', down)
    response = client.get('/api/v1/health')
    assert response.status_code == 503 and response.json['error']['code'] == 'SERVICE_UNAVAILABLE'
    assert 'hidden' not in response.text and 'password' not in response.text


@pytest.mark.parametrize('error,status,code', [
    (BadRequestError(), 400, 'BAD_REQUEST'), (AuthenticationError(), 401, 'UNAUTHENTICATED'),
    (AuthorizationError(), 403, 'FORBIDDEN'), (NotFoundError(), 404, 'NOT_FOUND'),
    (ConflictError(), 409, 'CONFLICT'), (BusinessRuleError(), 409, 'BUSINESS_RULE_VIOLATION'),
    (ValidationError(details=[{'field': 'quantity', 'reason': 'Không hợp lệ'}]), 422, 'VALIDATION_ERROR'),
    (ServiceUnavailableError(), 503, 'SERVICE_UNAVAILABLE'),
    (DuplicateKeyError('secret raw document'), 409, 'DUPLICATE_RESOURCE'),
    (ServerSelectionTimeoutError('private connection'), 503, 'SERVICE_UNAVAILABLE'),
    (RuntimeError('password=DO_NOT_EXPOSE_TOKEN'), 500, 'INTERNAL_ERROR'),
])
def test_error_envelope(app, client, error, status, code):
    @app.get('/api/v1/_test/error')
    def fail():
        raise error
    response = client.get('/api/v1/_test/error')
    assert response.status_code == status
    assert set(response.json) == {'error', 'meta'}
    assert set(response.json['error']) == {'code', 'message', 'details'}
    assert response.json['error']['code'] == code
    assert isinstance(response.json['error']['details'], list)
    assert response.headers['X-Request-ID'] == response.json['meta']['requestId']
    assert 'DO_NOT_EXPOSE_TOKEN' not in response.text and 'Traceback' not in response.text
    if status == 401:
        assert response.headers['WWW-Authenticate'] == 'Bearer'


def test_framework_errors_and_http_semantics(client):
    assert client.get('/api/v1/not-present').json['error']['code'] == 'NOT_FOUND'
    response = client.post('/api/v1/health')
    assert response.status_code == 405 and 'GET' in response.headers['Allow']
    assert client.get('/api/v1/health', data='x'*1048577).status_code == 413


def test_objectid_dates_money_and_private_fields(app, client):
    user_id = ObjectId()
    @app.get('/api/v1/_test/serialize')
    def serialize():
        return success({'_id': user_id, 'price': Int64(12345), 'createdAt': datetime(2026, 10, 7, tzinfo=timezone.utc), 'passwordHash': 'PRIVATE_HASH', 'nested': {'password': 'PRIVATE_PASSWORD'}, 'tokenVersion': 5})
    data = client.get('/api/v1/_test/serialize').json['data']
    assert data == {'id': str(user_id), 'price': 12345, 'createdAt': '2026-10-07T00:00:00.000Z', 'nested': {}}
    assert parse_object_id(str(user_id)) == user_id
    with pytest.raises(TypeError): to_api(datetime(2026, 10, 7))
    with pytest.raises(TypeError): to_api(float('nan'))


@pytest.mark.parametrize('value', ['bad', 'A'*24, {'$ne': None}, None])
def test_invalid_ids(value):
    with pytest.raises(BadRequestError): parse_object_id(value)


def test_201_204_pagination_envelopes(app, client):
    @app.post('/api/v1/_test/created')
    def created(): return success({'id': 'created'}, status=201, location='/api/v1/_test/created')
    @app.delete('/api/v1/_test/empty')
    def empty(): return no_content()
    @app.get('/api/v1/_test/list')
    def listed(): return paginated([], Pagination(page=2, page_size=20), 180)
    created_response = client.post('/api/v1/_test/created')
    assert created_response.status_code == 201 and created_response.headers['Location'] == '/api/v1/_test/created'
    empty_response = client.delete('/api/v1/_test/empty')
    assert empty_response.status_code == 204 and empty_response.data == b''
    assert client.get('/api/v1/_test/list').json['meta']['totalPages'] == 9


BODY_SCHEMA = {'type': 'object', 'required': ['items', 'method'], 'additionalProperties': False, 'properties': {
    'method': {'type': 'string', 'enum': ['COD', 'VNPAY']},
    'items': {'type': 'array', 'minItems': 1, 'items': {'type': 'object', 'required': ['quantity'], 'additionalProperties': False, 'properties': {'quantity': {'type': 'integer', 'minimum': 1, 'maximum': 99}}}},
    'password': {'type': 'string', 'minLength': 12},
}}


@pytest.mark.parametrize('payload', [
    {'method': 'COD'}, {'method': 'OTHER', 'items': [{'quantity': 1}]},
    {'method': 'COD', 'items': [{'quantity': True}]}, {'method': 'COD', 'items': [{'quantity': 1.0}]},
    {'method': 'COD', 'items': [{'quantity': 0}]}, {'method': 'COD', 'items': [{'quantity': 1, 'price': 100}]},
    {'method': 'COD', 'items': [{'quantity': 1}], 'role': 'ADMIN'},
])
def test_api_validation_nested_required_enum_types(app, client, payload):
    @app.post('/api/v1/_test/validate')
    def validate(): return success(parse_json_body(BODY_SCHEMA))
    response = client.post('/api/v1/_test/validate', json=payload)
    assert response.status_code == 422 and response.json['error']['details']


def test_json_syntax_content_type_and_incoming_password_preserved(app, client):
    @app.post('/api/v1/_test/validate')
    def validate():
        value = parse_json_body(BODY_SCHEMA)
        assert value.get('password') == 'private-demo-password'
        return success(value)
    assert client.post('/api/v1/_test/validate', data='{', content_type='application/json').status_code == 400
    assert client.post('/api/v1/_test/validate', data='{}', content_type='text/plain').status_code == 415
    valid = client.post('/api/v1/_test/validate', json={'method': 'COD', 'items': [{'quantity': 2}], 'password': 'private-demo-password'})
    assert valid.status_code == 200 and 'password' not in valid.json['data']


@pytest.mark.parametrize('values,error', [({'page': 'abc'}, BadRequestError), ({'page': '-1'}, BadRequestError), ({'page': '0'}, ValidationError), ({'pageSize': '101'}, ValidationError), ({'pageSize': '1.0'}, BadRequestError)])
def test_pagination_limits(values, error):
    with pytest.raises(error): Pagination.from_query(values)


def test_query_allowlist_duplicates_and_defaults():
    from werkzeug.datastructures import MultiDict
    assert Pagination.from_query({}).metadata(0) == {'page': 1, 'pageSize': 20, 'total': 0, 'totalPages': 0}
    for values in [MultiDict([('page', '1'), ('page', '2')]), MultiDict({'limit': '20'}), MultiDict({'$where': 'bad'})]:
        with pytest.raises(ValidationError): single_query_values(values, PRODUCT_QUERY_FIELDS)


def test_cors_allowlist(client):
    allowed = client.get('/api/v1/health', headers={'Origin': 'http://localhost:5173'})
    assert allowed.headers['Access-Control-Allow-Origin'] == 'http://localhost:5173'
    assert 'Access-Control-Allow-Credentials' not in allowed.headers
    denied = client.get('/api/v1/health', headers={'Origin': 'http://untrusted.example'})
    assert 'Access-Control-Allow-Origin' not in denied.headers
    preflight = client.options('/api/v1/health', headers={'Origin': 'http://localhost:5173', 'Access-Control-Request-Method': 'GET', 'Access-Control-Request-Headers': 'Authorization'})
    assert preflight.status_code == 200 and 'Authorization' in preflight.headers['Access-Control-Allow-Headers']


def test_safe_logging_never_renders_message_or_locals():
    record = logging.LogRecord('app', logging.ERROR, __file__, 1, 'password=secret JWT=raw-token VNPAY=secret', (), None)
    record.event = 'server.failure'
    record.request_id = 'opaque'
    output = SafeJSONFormatter().format(record)
    assert json.loads(output)['event'] == 'server.failure'
    assert 'password' not in output and 'raw-token' not in output and 'VNPAY' not in output


def test_request_logs_do_not_expose_query_headers_or_exception_message(app, client):
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(SafeJSONFormatter())
    app.logger.handlers = [handler]
    app.logger.setLevel(logging.INFO)
    @app.get('/api/v1/_test/log')
    def fail():
        raise RuntimeError('password=PRIVATE_EXCEPTION')
    client.get('/api/v1/_test/log?password=PRIVATE_QUERY', headers={'Authorization': 'Bearer PRIVATE_JWT'})
    output = stream.getvalue()
    assert 'server.failure' in output and 'request.completed' in output and 'frames' in output
    assert all(secret not in output for secret in ('PRIVATE_EXCEPTION', 'PRIVATE_QUERY', 'PRIVATE_JWT'))
    assert logging.getLogger('werkzeug').level >= logging.WARNING


def test_nonfinite_json_is_bad_request(app, client):
    @app.post('/api/v1/_test/json')
    def parse(): return success(parse_json_body(BODY_SCHEMA))
    response = client.post('/api/v1/_test/json', data='{"method":"COD","items":[{"quantity":NaN}]}', content_type='application/json')
    assert response.status_code == 400
