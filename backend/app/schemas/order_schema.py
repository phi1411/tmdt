"""Owner history filters and immutable order response allowlists."""
from datetime import datetime, timezone
from app.errors import ValidationError
from app.schemas.user_schema import object_schema, VERSION

STATUSES = {'PENDING', 'CONFIRMED', 'SHIPPING', 'COMPLETED', 'CANCELLED', 'EXPIRED'}
CANCEL_SCHEMA = object_schema({'expectedVersion': VERSION}, ['expectedVersion'])
PUBLIC_FIELDS = ('_id', 'orderCode', 'userId', 'customerSnapshot', 'shippingAddress', 'items',
                 'subtotal', 'shippingFee', 'discount', 'total', 'currency', 'paymentMethod',
                 'paymentStatus', 'paymentReviewRequired', 'orderStatus', 'version',
                 'createdAt', 'updatedAt', 'paymentExpiresAt', 'paidAt', 'completedAt',
                 'cancelledAt', 'expiredAt', 'stockReleasedAt')
SUMMARY_FIELDS = ('_id', 'orderCode', 'orderStatus', 'paymentStatus', 'paymentMethod',
                  'paymentReviewRequired', 'total', 'currency', 'version', 'createdAt', 'updatedAt')


def order_response(order):
    return {key: order[key] for key in PUBLIC_FIELDS if key in order}


def history_query(values):
    query = {}
    if 'status' in values:
        if values['status'] not in STATUSES:
            raise ValidationError(details=[{'field': 'status', 'reason': 'Trạng thái không hợp lệ'}])
        query['orderStatus'] = values['status']
    bounds = {}
    for field, operator in [('from', '$gte'), ('to', '$lt')]:
        if field not in values:
            continue
        try:
            value = values[field]
            if len(value) > 40 or 'T' not in value or not value.endswith(('Z', '+00:00')):
                raise ValueError()
            parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
            if parsed.utcoffset() != timezone.utc.utcoffset(parsed):
                raise ValueError()
            bounds[operator] = parsed
        except (ValueError, TypeError):
            raise ValidationError(details=[{'field': field, 'reason': 'Cần thời điểm ISO UTC'}]) from None
    if len(bounds) == 2 and bounds['$gte'] >= bounds['$lt']:
        raise ValidationError(details=[{'field': 'to', 'reason': 'to phải sau from'}])
    if bounds:
        query['createdAt'] = bounds
    return query
