"""Auth HTTP contract; business decisions live in services."""
from flask import Blueprint, current_app, request
from app.auth import get_current_user, require_auth
from app.schemas.auth_schema import REGISTER_SCHEMA, LOGIN_SCHEMA, PASSWORD_SCHEMA, register_input, normalize_email
from app.schemas.validation import parse_json_body, single_query_values
from app.schemas.user_response import public_account
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.utils.responses import success

auth_blueprint = Blueprint('auth', __name__)


@auth_blueprint.before_request
def reject_query_fields():
    single_query_values(request.args, set())


@auth_blueprint.post('/auth/register')
def register():
    current_app.extensions['auth_rate_limiter'].check('register', request.remote_addr or '')
    values = register_input(parse_json_body(REGISTER_SCHEMA))
    return success(AuthService().register(values), status=201)


@auth_blueprint.post('/auth/login')
def login():
    limiter = current_app.extensions['auth_rate_limiter']
    # Count IP attempts even for malformed input; do not trust forwarded headers.
    limiter.check('login', request.remote_addr or '')
    values = parse_json_body(LOGIN_SCHEMA)
    email = normalize_email(values['email'])
    limiter.check('login', '', email, account_only=True)
    return success(AuthService().login(email, values['password']))


@auth_blueprint.get('/auth/me')
@require_auth
def me():
    return success(public_account(UserService().current(get_current_user())))


@auth_blueprint.patch('/auth/password')
@require_auth
def password():
    identity = get_current_user()
    current_app.extensions['auth_rate_limiter'].check('password', request.remote_addr or '', str(identity['_id']))
    values = parse_json_body(PASSWORD_SCHEMA)
    return success(AuthService().change_password(identity, values['currentPassword'], values['newPassword']))
