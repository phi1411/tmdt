"""Admin account list/detail and Customer status HTTP endpoints."""
from flask import Blueprint, request
from app.auth import require_roles
from app.schemas.admin_user_schema import STATUS_SCHEMA, parse_user_query
from app.schemas.validation import parse_json_body, single_query_values
from app.services.user_service import UserService
from app.utils.ids import parse_object_id
from app.utils.responses import success, paginated

admin_users_blueprint = Blueprint('admin_users', __name__)


@admin_users_blueprint.before_request
def reject_detail_query_fields():
    if request.endpoint != 'admin_users.users':
        single_query_values(request.args, set())


@admin_users_blueprint.get('/admin/users')
@require_roles('ADMIN')
def users():
    filters, pagination = parse_user_query(request.args)
    accounts, total = UserService().list_accounts(filters, pagination)
    return paginated(accounts, pagination, total)


@admin_users_blueprint.get('/admin/users/<user_id>')
@require_roles('ADMIN')
def user(user_id):
    return success(UserService().account(parse_object_id(user_id)))


@admin_users_blueprint.patch('/admin/users/<user_id>/status')
@require_roles('ADMIN')
def status(user_id):
    user_id = parse_object_id(user_id)
    values = parse_json_body(STATUS_SCHEMA)
    return success(UserService().change_status(user_id, values['status'], values['expectedVersion']))
