"""Flask application factory for health, Auth/User and Catalog APIs."""
from time import perf_counter
from uuid import uuid4
from flask import Flask, g, request
from flask_cors import CORS
from werkzeug.exceptions import RequestEntityTooLarge
from app.config import load_config
from app.db import init_mongo
from app.errors.handlers import register_error_handlers
from app.utils.logging import configure_logging
from app.utils.serialization import APIJSONProvider


def create_app(config=None, env_file=None):
    app = Flask(__name__, static_folder=None)
    app.config.update(load_config(config, env_file))
    app.json = APIJSONProvider(app)
    configure_logging(app)

    @app.before_request
    def begin_request():
        g.request_id = uuid4().hex
        g.request_started = perf_counter()
        if request.content_length and request.content_length > app.config['MAX_CONTENT_LENGTH']:
            raise RequestEntityTooLarge()

    @app.after_request
    def finish_request(response):
        response.headers['X-Request-ID'] = g.request_id
        response.headers['X-Content-Type-Options'] = 'nosniff'
        app.logger.info('request', extra={
            'event': 'request.completed', 'request_id': g.request_id,
            'method': request.method, 'endpoint': request.endpoint,
            'status': response.status_code,
            'duration_ms': round((perf_counter() - g.request_started) * 1000, 3),
        })
        return response

    register_error_handlers(app)
    CORS(app, resources={r'/api/v1/.*': {'origins': app.config['CORS_ORIGINS']}},
         supports_credentials=False, allow_headers=['Authorization', 'Content-Type', 'Idempotency-Key'],
         expose_headers=['X-Request-ID', 'Location'], methods=['GET', 'POST', 'PATCH', 'DELETE', 'OPTIONS'])
    init_mongo(app)
    from app.auth.rate_limit import AuthRateLimiter
    from app.auth.passwords import hash_password
    import secrets
    app.extensions['auth_rate_limiter'] = AuthRateLimiter()
    app.extensions['auth_dummy_hash'] = hash_password(secrets.token_urlsafe(32))
    from app.api import register_blueprints
    register_blueprints(app)
    return app
