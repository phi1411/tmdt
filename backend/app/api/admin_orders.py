"""Admin order actions; no client-controlled state/timestamp/snapshot writes."""
from flask import Blueprint, request
from app.auth import get_current_user, require_roles
from app.schemas.admin_order_schema import admin_order_query
from app.schemas.order_schema import CANCEL_SCHEMA
from app.schemas.validation import parse_json_body, single_query_values
from app.services.order_service import OrderService
from app.utils.ids import parse_object_id
from app.utils.responses import success, paginated

admin_orders_blueprint = Blueprint('admin_orders', __name__)


@admin_orders_blueprint.get('/admin/orders')
@require_roles('ADMIN')
def list_orders():
    filters, pagination = admin_order_query(request.args)
    items, total = OrderService().admin_list(filters, pagination)
    return paginated(items, pagination, total)


@admin_orders_blueprint.get('/admin/orders/<order_id>')
@require_roles('ADMIN')
def detail(order_id):
    single_query_values(request.args, set())
    return success(OrderService().admin_detail(parse_object_id(order_id)))


def action_response(order_id, action):
    single_query_values(request.args, set())
    order_id = parse_object_id(order_id)
    values = parse_json_body(CANCEL_SCHEMA)
    return success(OrderService().admin_action(order_id, action, values['expectedVersion'], get_current_user()['_id']))


@admin_orders_blueprint.post('/admin/orders/<order_id>/confirm')
@require_roles('ADMIN')
def confirm(order_id):
    return action_response(order_id, 'confirm')


@admin_orders_blueprint.post('/admin/orders/<order_id>/ship')
@require_roles('ADMIN')
def ship(order_id):
    return action_response(order_id, 'ship')


@admin_orders_blueprint.post('/admin/orders/<order_id>/complete')
@require_roles('ADMIN')
def complete(order_id):
    return action_response(order_id, 'complete')


@admin_orders_blueprint.post('/admin/orders/<order_id>/cancel')
@require_roles('ADMIN')
def cancel(order_id):
    return action_response(order_id, 'cancel')
