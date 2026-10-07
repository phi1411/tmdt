"""Customer-owned profile and embedded address endpoints."""
from flask import Blueprint, request
from app.auth import get_current_user, require_roles
from app.schemas.user_schema import (PROFILE_SCHEMA, ADDRESS_CREATE_SCHEMA, ADDRESS_UPDATE_SCHEMA,
                                     DEFAULT_ADDRESS_SCHEMA, VERSION_SCHEMA, ADDRESS_FIELDS, normalize_fields)
from app.schemas.validation import parse_json_body, single_query_values
from app.services.user_service import UserService
from app.utils.ids import parse_object_id
from app.utils.responses import success, no_content

users_blueprint = Blueprint('users', __name__)


@users_blueprint.before_request
def reject_query_fields():
    single_query_values(request.args, set())


@users_blueprint.get('/users/me')
@require_roles('CUSTOMER')
def me():
    return success(UserService().profile(get_current_user()))


@users_blueprint.patch('/users/me')
@require_roles('CUSTOMER')
def profile():
    values = parse_json_body(PROFILE_SCHEMA)
    fields = normalize_fields(values, {'name', 'phone'})
    return success(UserService().update_profile(get_current_user(), fields, values['expectedVersion']))


@users_blueprint.post('/users/me/addresses')
@require_roles('CUSTOMER')
def add_address():
    values = parse_json_body(ADDRESS_CREATE_SCHEMA)
    fields = normalize_fields(values, ADDRESS_FIELDS, phone_required=True)
    return success(UserService().add_address(get_current_user(), fields, values['expectedVersion']), status=201)


@users_blueprint.patch('/users/me/addresses/<address_id>')
@require_roles('CUSTOMER')
def update_address(address_id):
    address_id = parse_object_id(address_id, 'addressId')
    values = parse_json_body(ADDRESS_UPDATE_SCHEMA)
    fields = normalize_fields(values, ADDRESS_FIELDS, phone_required=True)
    return success(UserService().update_address(get_current_user(), address_id, fields, values['expectedVersion']))


@users_blueprint.delete('/users/me/addresses/<address_id>')
@require_roles('CUSTOMER')
def remove_address(address_id):
    address_id = parse_object_id(address_id, 'addressId')
    values = parse_json_body(VERSION_SCHEMA)
    UserService().remove_address(get_current_user(), address_id, values['expectedVersion'])
    return no_content()


@users_blueprint.patch('/users/me/default-address')
@require_roles('CUSTOMER')
def default_address():
    values = parse_json_body(DEFAULT_ADDRESS_SCHEMA)
    address_id = parse_object_id(values['addressId'], 'addressId')
    return success(UserService().default_address(get_current_user(), address_id, values['expectedVersion']))
