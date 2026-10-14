"""Quote and checkout HTTP contract; POST /orders is registered only here."""
from flask import Blueprint, request
from app.auth import get_current_user, require_roles
from app.schemas.checkout_schema import CHECKOUT_SCHEMA, METHOD, idempotency_key
from app.schemas.user_schema import object_schema
from app.schemas.validation import parse_json_body, single_query_values, validate_payload
from app.services.checkout_service import CheckoutService
from app.utils.ids import parse_object_id
from app.utils.responses import success

checkout_blueprint = Blueprint('checkout', __name__)


@checkout_blueprint.get('/checkout/quote')
@require_roles('CUSTOMER')
def quote():
    values = single_query_values(request.args, {'addressId', 'paymentMethod'})
    validate_payload(values, object_schema({'addressId': {'type': 'string'}, 'paymentMethod': METHOD},
                                          ['addressId', 'paymentMethod']))
    return success(CheckoutService().quote(get_current_user(), parse_object_id(values['addressId'], 'addressId'),
                                          values['paymentMethod']))


@checkout_blueprint.post('/orders')
@require_roles('CUSTOMER')
def create_order():
    single_query_values(request.args, set())
    payload = parse_json_body(CHECKOUT_SCHEMA)
    key = idempotency_key(request.headers.get('Idempotency-Key'))
    result, created = CheckoutService().create(get_current_user(), payload, key,
                                               parse_object_id(payload['addressId'], 'addressId'), request.remote_addr)
    return success(result, status=201 if created else 200,
                   location='/api/v1/orders/' + str(result['order']['_id']) if created else None)
