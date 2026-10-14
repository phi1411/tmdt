"""Customer attempt creation; public provider IPN and read-only Return."""
from flask import Blueprint, current_app, g, jsonify, request
from app.auth import get_current_user, require_roles
from app.schemas.checkout_schema import idempotency_key
from app.schemas.user_schema import object_schema, VERSION
from app.schemas.validation import parse_json_body, single_query_values
from app.services.payment_service import PaymentService
from app.services.vnpay_provider import ProviderValidationError
from app.utils.ids import parse_object_id
from app.utils.logging import log_failure
from app.utils.responses import success

payments_blueprint = Blueprint('payments', __name__)
CREATE_ATTEMPT_SCHEMA = object_schema({'expectedVersion': VERSION}, ['expectedVersion'])
IPN_MESSAGES = {'00': 'Confirm Success', '02': 'Order already confirmed', '01': 'Order not found',
                '04': 'Invalid amount', '97': 'Invalid signature', '99': 'Unable to process'}


@payments_blueprint.post('/orders/<order_id>/payment-attempts')
@require_roles('CUSTOMER')
def create_attempt(order_id):
    single_query_values(request.args, set())
    payload = parse_json_body(CREATE_ATTEMPT_SCHEMA)
    data, created = PaymentService().create(get_current_user()['_id'], parse_object_id(order_id), payload,
        idempotency_key(request.headers.get('Idempotency-Key')), request.remote_addr)
    return success(data, 201 if created else 200)


@payments_blueprint.get('/payments/vnpay/return')
def payment_return():
    return success(PaymentService().return_result(request.args))


@payments_blueprint.get('/payments/vnpay/ipn')
def payment_ipn():
    try:
        code = PaymentService().ipn(request.args)
    except ProviderValidationError as error:
        code = error.code
    except Exception as error:
        log_failure(current_app, 'payment.ipn_failed', error, g.request_id, request.method, request.endpoint)
        code = '99'
    # Provider exception to our normal JSON envelope. Acknowledge only after commit.
    return jsonify({'RspCode': code, 'Message': IPN_MESSAGES[code]}), 200
