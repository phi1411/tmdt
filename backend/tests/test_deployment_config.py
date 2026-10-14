"""Production config stays isolated from local settings and fails closed."""
import pytest
from app.config import ConfigurationError, load_config


@pytest.fixture
def production(monkeypatch):
    monkeypatch.setattr('app.config.parse_uri', lambda uri: {'options': {'replicaSet': 'atlas-fixture', 'tls': True}})
    return {'APP_ENV': 'production', 'MONGODB_URI': 'mongodb+srv://fixture.mongodb.net/',
            'MONGODB_REPLICA_SET': 'atlas-fixture', 'MONGODB_DB': 'novamart_demo',
            'JWT_SECRET': 'test-production-secret-' * 3, 'JWT_ISSUER': 'novamart-api',
            'JWT_AUDIENCE': 'novamart-web', 'FRONTEND_ORIGIN': 'https://shop.example.test', 'VNPAY_ENABLED': False}


def test_production_port_and_atlas_replica(production):
    config = load_config({**production, 'PORT': '10000', 'API_PORT': '5001'})
    assert config['API_PORT'] == 10000 and config['API_HOST'] == '0.0.0.0'
    assert config['MONGODB_REPLICA_SET'] == 'atlas-fixture' and not config['TESTING']
    assert config['DEBUG'] is False


@pytest.mark.parametrize('change', [
    {'MONGODB_URI': 'mongodb://localhost:27017/?replicaSet=rs0'},
    {'MONGODB_URI': 'mongodb+srv://fixture.example.test/'},
    {'MONGODB_REPLICA_SET': 'wrong'}, {'MONGODB_REPLICA_SET': ''},
    {'FRONTEND_ORIGIN': ''}, {'FRONTEND_ORIGIN': 'http://shop.example.test'},
    {'PORT': '0'}, {'PORT': '65536'}, {'PORT': 'invalid'},
])
def test_production_invalid_settings(production, change):
    with pytest.raises(ConfigurationError):
        load_config({**production, **change})


@pytest.mark.parametrize('option,value', [('tls', False), ('tlsInsecure', True),
    ('tlsAllowInvalidCertificates', True), ('tlsAllowInvalidHostnames', True), ('directConnection', True)])
def test_production_rejects_insecure_or_direct_connection(monkeypatch, production, option, value):
    monkeypatch.setattr('app.config.parse_uri', lambda uri: {'options': {'replicaSet': 'atlas-fixture', option: value}})
    with pytest.raises(ConfigurationError):
        load_config(production)


def test_production_does_not_read_local_dotenv(monkeypatch, production):
    monkeypatch.setattr('app.config.dotenv_values', lambda *a, **k: pytest.fail('Production inherited local dotenv'))
    assert load_config(production)['MONGODB_DB'] == 'novamart_demo'
