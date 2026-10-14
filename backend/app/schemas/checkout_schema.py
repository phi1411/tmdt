"""Checkout intent never accepts client prices, totals or owner/state fields."""
from app.errors import ValidationError
from app.schemas.cart_schema import CART_VERSION
from app.schemas.user_schema import object_schema

METHOD = {'type': 'string', 'enum': ['COD', 'VNPAY']}
CHECKOUT_SCHEMA = object_schema({
    'cartVersion': CART_VERSION, 'addressId': {'type': 'string'}, 'paymentMethod': METHOD,
    'quoteToken': {'type': 'string', 'minLength': 1, 'maxLength': 4096},
}, ['cartVersion', 'addressId', 'paymentMethod', 'quoteToken'])


def idempotency_key(value):
    # Opaque printable ASCII, preserved exactly; never silently trim a key.
    if not isinstance(value, str) or not 8 <= len(value) <= 128 or any(not 33 <= ord(c) <= 126 for c in value):
        raise ValidationError(details=[{'field': 'Idempotency-Key', 'reason': 'Cần khóa 8..128 ký tự ASCII không khoảng trắng'}])
    return value
