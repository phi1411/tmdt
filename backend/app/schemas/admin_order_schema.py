"""Allowlisted Admin order filters; fixed latest sort and snapshot DTOs."""
import re
from app.errors import ValidationError
from app.schemas.order_schema import STATUSES, order_response
from app.schemas.dashboard_schema import utc_date
from app.schemas.pagination import Pagination
from app.schemas.validation import single_query_values

PAYMENT_STATUSES = {'UNPAID', 'PENDING', 'PAID', 'FAILED', 'REVIEW_REQUIRED'}


def admin_order_query(args):
    values = single_query_values(args, {'status', 'paymentStatus', 'from', 'to', 'orderCode', 'page', 'pageSize'})
    pagination = Pagination.from_query(values)
    query = {}
    for key, allowed, database_key in [('status', STATUSES, 'orderStatus'),
                                       ('paymentStatus', PAYMENT_STATUSES, 'paymentStatus')]:
        if key in values:
            if values[key] not in allowed:
                raise ValidationError(details=[{'field': key, 'reason': 'Trạng thái không hợp lệ'}])
            query[database_key] = values[key]
    if 'orderCode' in values:
        code = values['orderCode']
        if not re.fullmatch(r'[A-Z0-9-]{1,64}', code):
            raise ValidationError(details=[{'field': 'orderCode', 'reason': 'Cần mã đơn chính xác, tối đa 64 ký tự chữ hoa/số/-'}])
        query['orderCode'] = code
    bounds = {}
    for field, operator in [('from', '$gte'), ('to', '$lt')]:
        if field in values:
            bounds[operator] = utc_date(values[field], field)
    if len(bounds) == 2 and bounds['$gte'] >= bounds['$lt']:
        raise ValidationError(details=[{'field': 'to', 'reason': 'to phải sau from'}])
    if bounds:
        query['createdAt'] = bounds
    return query, pagination


def allowed_actions(order):
    if order['version'] >= 2147483647:
        return []
    status, method, payment = order['orderStatus'], order['paymentMethod'], order['paymentStatus']
    result = []
    ready = payment == ('UNPAID' if method == 'COD' else 'PAID')
    if status == 'PENDING' and method == 'COD' and ready:
        result.append('confirm')
    if status == 'CONFIRMED' and ready:
        result.append('ship')
    if status == 'SHIPPING' and ready:
        result.append('complete')
    if (status in {'PENDING', 'CONFIRMED'} and payment not in {'PAID', 'REVIEW_REQUIRED'}
            and not order['paymentReviewRequired'] and 'stockReleasedAt' not in order):
        result.append('cancel')
    return result


def admin_order_response(order):
    return {**order_response(order), 'allowedActions': allowed_actions(order)}
