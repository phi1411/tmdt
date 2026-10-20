"""Customer cart HTTP boundary; owner is always the live JWT identity."""
from flask import Blueprint, request
from app.auth import get_current_user, require_roles
from app.schemas.cart_schema import ADD_SCHEMA, UPDATE_SCHEMA, VERSION_SCHEMA, COUPON_SCHEMA
from app.schemas.validation import parse_json_body, single_query_values
from app.services.cart_service import CartService
from app.utils.ids import parse_object_id
from app.utils.responses import success, no_content

cart_blueprint = Blueprint('cart', __name__)


@cart_blueprint.patch('/cart/coupon')
@require_roles('CUSTOMER')
def set_coupon():
    payload = values(COUPON_SCHEMA)
    return success(CartService().coupon(get_current_user()['_id'], payload['cartVersion'], payload['code']))


def values(schema):
    single_query_values(request.args, set())
    return parse_json_body(schema)


@cart_blueprint.get('/cart')
@require_roles('CUSTOMER')
def get_cart():
    single_query_values(request.args, set())
    return success(CartService().get(get_current_user()['_id']))


@cart_blueprint.post('/cart/items')
@require_roles('CUSTOMER')
def add_item():
    payload = values(ADD_SCHEMA)
    product_id = parse_object_id(payload['productId'], 'productId')
    return success(CartService().mutate(get_current_user()['_id'], payload['cartVersion'], 'add',
                   product_id, payload['quantity'], payload.get('selectedAttributes', {})))


@cart_blueprint.patch('/cart/items/<line_id>')
@require_roles('CUSTOMER')
def update_item(line_id):
    payload = values(UPDATE_SCHEMA)
    return success(CartService().mutate(get_current_user()['_id'], payload['cartVersion'], 'update',
                                       quantity=payload['quantity'], target=line_id))


@cart_blueprint.delete('/cart/items/<line_id>')
@require_roles('CUSTOMER')
def remove_item(line_id):
    payload = values(VERSION_SCHEMA)
    CartService().mutate(get_current_user()['_id'], payload['cartVersion'], 'remove', target=line_id)
    return no_content()


@cart_blueprint.delete('/cart')
@require_roles('CUSTOMER')
def clear_cart():
    payload = values(VERSION_SCHEMA)
    CartService().mutate(get_current_user()['_id'], payload['cartVersion'], 'clear')
    return no_content()
