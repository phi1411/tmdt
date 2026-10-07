"""Infrastructure readiness orchestration, no application business workflow."""
from flask import current_app, g, request
from pymongo.errors import PyMongoError
from app.config import ConfigurationError
from app.db import get_mongo
from app.errors import ServiceUnavailableError
from app.utils.logging import log_failure


def check_health():
    try:
        checks = get_mongo().health()
    except (PyMongoError, ConfigurationError) as error:
        log_failure(current_app, 'database.health_failed', error, g.request_id, request.method, request.endpoint)
        raise ServiceUnavailableError() from None
    return {'status': 'ok', 'checks': checks}
