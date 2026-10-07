from flask import Blueprint
from app.services.health_service import check_health
from app.utils.responses import success

health_blueprint = Blueprint('health', __name__)


@health_blueprint.get('/health')
def health():
    return success(check_health())
