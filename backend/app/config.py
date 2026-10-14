"""Validated environment configuration; no database URI or secret fallback."""
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse
from dotenv import dotenv_values
from pymongo.uri_parser import parse_uri
from app.services.vnpay_provider import validate_settings

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class ConfigurationError(RuntimeError):
    """Deployment configuration failure, with no secret values in the message."""


def _required(values, key):
    value = values.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f'{key} is required')
    return value.strip()


def _integer(values, key, default, minimum, maximum):
    value = values.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ConfigurationError(f'{key} must be an integer')
    try:
        result = int(value)
    except (TypeError, ValueError):
        raise ConfigurationError(f'{key} must be an integer') from None
    if not minimum <= result <= maximum:
        raise ConfigurationError(f'{key} is outside the allowed range')
    return result


def load_config(overrides=None, env_file=None):
    overrides = dict(overrides or {})
    environment = overrides.get('APP_ENV', os.environ.get('APP_ENV', 'development'))
    path = Path(env_file) if env_file is not None else PROJECT_ROOT / '.env'
    # Testing does not inherit the private development file by default.
    file_values = dict(dotenv_values(path, interpolate=False)) if env_file is not None or environment == 'development' else {}
    values = {**file_values, **os.environ, **overrides}
    environment = values.get('APP_ENV', 'development')
    if environment not in {'development', 'testing', 'production'}:
        raise ConfigurationError('APP_ENV must be development, testing or production')
    uri = _required(values, 'MONGODB_URI')
    try:
        parsed_uri = parse_uri(uri)
    except Exception:
        raise ConfigurationError('MONGODB_URI is invalid') from None
    if environment == 'production':
        replica = _required(values, 'MONGODB_REPLICA_SET')
        hostname = urlparse(uri).hostname or ''
        if not uri.startswith('mongodb+srv://') or not hostname.endswith('.mongodb.net'):
            raise ConfigurationError('Production requires an Atlas SRV connection')
        if parsed_uri['options'].get('replicaSet') != replica:
            raise ConfigurationError('Production replica set must match the configured Atlas replica set')
        if any(parsed_uri['options'].get(key) is True for key in ('tlsInsecure', 'tlsAllowInvalidCertificates', 'tlsAllowInvalidHostnames')) or parsed_uri['options'].get('tls') is False:
            raise ConfigurationError('Production requires verified TLS')
    else:
        replica = values.get('MONGODB_REPLICA_SET', 'rs0')
        if replica != 'rs0' or parsed_uri['options'].get('replicaSet') != replica:
            raise ConfigurationError('MONGODB_URI must configure the locked replica set rs0')
    if parsed_uri['options'].get('directConnection'):
        raise ConfigurationError('Direct connections are not supported by this application')
    database = _required(values, 'MONGODB_TEST_DB' if environment == 'testing' else 'MONGODB_DB')
    if database in {'admin', 'local', 'config'} or '/' in database or '.' in database:
        raise ConfigurationError('Application database name is invalid')
    if environment == 'testing' and (not database.endswith('_test') or database == values.get('MONGODB_DB')):
        raise ConfigurationError('Testing requires a separate database ending in _test')
    secret = _required(values, 'JWT_SECRET')
    if len(secret.encode('utf-8')) < 32 or secret.startswith('REPLACE_'):
        raise ConfigurationError('JWT_SECRET must be a private secret of at least 32 bytes')
    origin_value = values.get('CORS_ORIGINS', values.get('FRONTEND_ORIGIN', ''))
    if not isinstance(origin_value, str):
        raise ConfigurationError('CORS_ORIGINS must be a comma-separated string')
    origins = [origin.strip() for origin in origin_value.split(',') if origin.strip()]
    if environment == 'production' and not origins:
        raise ConfigurationError('Production requires an explicit frontend origin')
    for origin in origins:
        parsed = urlparse(origin)
        if parsed.scheme not in {'http', 'https'} or not parsed.netloc or parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password or '*' in origin:
            raise ConfigurationError('CORS origins must be exact HTTP(S) origins without paths')
        if environment == 'production' and parsed.scheme != 'https':
            raise ConfigurationError('Production frontend origins must use HTTPS')
    level = str(values.get('LOG_LEVEL', 'INFO')).upper()
    if level not in {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}:
        raise ConfigurationError('LOG_LEVEL is invalid')
    enabled_value = values.get('VNPAY_ENABLED', False)
    if type(enabled_value) is bool:
        vnpay_enabled = enabled_value
    elif isinstance(enabled_value, str) and enabled_value in {'true', 'false', '1', '0'}:
        vnpay_enabled = enabled_value in {'true', '1'}
    else:
        raise ConfigurationError('VNPAY_ENABLED must be a boolean or true/false/1/0')
    vnpay_config = validate_settings(values, vnpay_enabled, ConfigurationError)
    return {
        'APP_ENV': environment, 'TESTING': environment == 'testing',
        'DEBUG': False, 'PROPAGATE_EXCEPTIONS': False, 'API_PREFIX': '/api/v1',
        'MONGODB_URI': uri, 'MONGODB_DB': database, 'MONGODB_REPLICA_SET': replica,
        'MONGODB_TIMEOUT_MS': _integer(values, 'MONGODB_TIMEOUT_MS', 3000, 100, 30000),
        'JWT_SECRET': secret, 'JWT_ALGORITHM': 'HS256',
        'JWT_ISSUER': _required(values, 'JWT_ISSUER'), 'JWT_AUDIENCE': _required(values, 'JWT_AUDIENCE'),
        'JWT_ACCESS_TTL_SECONDS': _integer(values, 'JWT_ACCESS_TTL_SECONDS', 1800, 60, 86400),
        'API_HOST': str(values.get('API_HOST', '0.0.0.0' if environment == 'production' else '127.0.0.1')),
        'API_PORT': _integer(values, 'PORT' if environment == 'production' and 'PORT' in values else 'API_PORT', 5000, 1, 65535),
        'MAX_CONTENT_LENGTH': _integer(values, 'MAX_CONTENT_LENGTH', 1048576, 1024, 10485760),
        'CORS_ORIGINS': origins, 'LOG_LEVEL': level,
        'SHIPPING_FEE_VND': _integer(values, 'SHIPPING_FEE_VND', 30000, 0, 1000000),
        'QUOTE_TTL_SECONDS': _integer(values, 'QUOTE_TTL_SECONDS', 300, 1, 3600),
        'PAYMENT_HOLD_MINUTES': _integer(values, 'PAYMENT_HOLD_MINUTES', 15, 15, 15),
        'PAYMENT_EXPIRY_POLL_SECONDS': _integer(values, 'PAYMENT_EXPIRY_POLL_SECONDS', 30, 30, 30),
        'VNPAY_ENABLED': vnpay_enabled, **vnpay_config,
    }
