"""Customer snapshot history/detail/cancellation; no admin management routes."""
from flask import Blueprint, request
from app.auth import get_current_user, require_roles
from app.schemas.order_schema import CANCEL_SCHEMA, history_query
from app.schemas.pagination import Pagination
from app.schemas.validation import parse_json_body, single_query_values
from app.services.order_service import OrderService
from app.utils.ids import parse_object_id
from app.utils.responses import success, paginated

orders_blueprint = Blueprint('orders', __name__)


@orders_blueprint.get('/orders')
@require_roles('CUSTOMER')
def list_orders():
    values = single_query_values(request.args, {'status', 'from', 'to', 'page', 'pageSize'})
    pagination = Pagination.from_query(values)
    items, total = OrderService().list(get_current_user()['_id'], history_query(values), pagination)
    return paginated(items, pagination, total)


@orders_blueprint.get('/orders/<order_id>')
@require_roles('CUSTOMER')
def detail(order_id):
    single_query_values(request.args, set())
    return success(OrderService().detail(get_current_user()['_id'], parse_object_id(order_id)))


@orders_blueprint.post('/orders/<order_id>/cancel')
@require_roles('CUSTOMER')
def cancel(order_id):
    single_query_values(request.args, set())
    order_id = parse_object_id(order_id)
    values = parse_json_body(CANCEL_SCHEMA)
    return success(OrderService().cancel(get_current_user()['_id'], order_id, values['expectedVersion']))
