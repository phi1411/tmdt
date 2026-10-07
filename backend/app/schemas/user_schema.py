"""Strict profile/address inputs aligned with the locked users validator."""
import re
from app.errors import ValidationError

MAX_VERSION = 2147483647
VERSION = {'type': 'integer', 'minimum': 1, 'maximum': MAX_VERSION}
NAME = {'type': 'string', 'minLength': 1, 'maxLength': 100}
PHONE = {'type': 'string', 'maxLength': 16}
ADDRESS_FIELDS = {
    'receiverName': NAME, 'phone': PHONE,
    'addressLine': {'type': 'string', 'minLength': 1, 'maxLength': 300},
    'province': NAME, 'ward': NAME, 'district': NAME,
    'label': {'type': 'string', 'minLength': 1, 'maxLength': 50},
}


def object_schema(properties, required=()):
    return {'type': 'object', 'additionalProperties': False,
            'properties': properties, 'required': list(required)}


PROFILE_SCHEMA = object_schema({'name': NAME, 'phone': PHONE, 'expectedVersion': VERSION}, ['expectedVersion'])
ADDRESS_CREATE_SCHEMA = object_schema({**ADDRESS_FIELDS, 'expectedVersion': VERSION},
                                      ['receiverName', 'phone', 'addressLine', 'province', 'expectedVersion'])
ADDRESS_UPDATE_SCHEMA = object_schema({**ADDRESS_FIELDS, 'expectedVersion': VERSION}, ['expectedVersion'])
VERSION_SCHEMA = object_schema({'expectedVersion': VERSION}, ['expectedVersion'])
DEFAULT_ADDRESS_SCHEMA = object_schema({'addressId': {'type': 'string'}, 'expectedVersion': VERSION},
                                       ['addressId', 'expectedVersion'])


def normalize_fields(payload, fields, phone_required=False, require_edit=True):
    result = {key: value.strip() for key, value in payload.items() if key in fields}
    if require_edit and not result:
        raise ValidationError(details=[{'field': '$', 'reason': 'Cần ít nhất một trường có thể sửa'}])
    for key, value in result.items():
        if key == 'phone':
            # Strip outer whitespace only; preserve the optional international +.
            if not re.fullmatch(r'\+?[0-9]{8,15}', value) and (phone_required or value != ''):
                raise ValidationError(details=[{'field': key, 'reason': 'Số điện thoại phải có 8 đến 15 chữ số, có thể bắt đầu bằng +'}])
        elif not value:
            raise ValidationError(details=[{'field': key, 'reason': 'Nội dung không được để trống'}])
    return result
