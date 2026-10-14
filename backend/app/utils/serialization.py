"""API JSON mapping: BSON IDs/dates/money, with private-field redaction."""
from datetime import datetime, timezone
from math import isfinite
from bson import ObjectId
from bson.int64 import Int64
from flask.json.provider import DefaultJSONProvider

PRIVATE_FIELDS = frozenset({
    'passwordHash', 'password', 'currentPassword', 'newPassword', 'tokenVersion',
    'checkoutKey', 'checkoutRequestHash', 'requestHash', 'hashSecret',
    'JWT_SECRET', 'VNPAY_HASH_SECRET', 'VNP_HASH_SECRET', 'QUOTE_SIGNING_SECRET', 'SEED_DEMO_PASSWORD',
})


def to_api(value):
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise TypeError('API dates must be timezone-aware')
        return value.astimezone(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    if isinstance(value, Int64):
        return int(value)
    if isinstance(value, dict):
        if '_id' in value and 'id' in value:
            raise TypeError('Ambiguous _id/id mapping')
        return {('id' if key == '_id' else key): to_api(item) for key, item in value.items() if key not in PRIVATE_FIELDS}
    if isinstance(value, (list, tuple)):
        return [to_api(item) for item in value]
    if isinstance(value, float) and not isfinite(value):
        raise TypeError('Non-finite JSON numbers are not supported')
    return value


class APIJSONProvider(DefaultJSONProvider):
    ensure_ascii = False
    sort_keys = False

    def loads(self, value, **kwargs):
        def reject_constant(value):
            raise ValueError('Non-finite constants are not valid JSON')
        kwargs.setdefault('parse_constant', reject_constant)
        return super().loads(value, **kwargs)

    def response(self, *args, **kwargs):
        # Sanitize outgoing responses only. Flask's test client also uses dumps
        # for incoming JSON; redacting there would silently drop password input.
        value = self._prepare_response_obj(args, kwargs)
        return super().response(to_api(value))
