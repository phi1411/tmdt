"""Bounded cart inputs; persisted line identity follows locked schema v1."""
from app.schemas.user_schema import object_schema

CART_VERSION = {'type': 'integer', 'minimum': 0, 'maximum': 2147483647}
QUANTITY = {'type': 'integer', 'minimum': 1, 'maximum': 99}
SELECTION = {
    'type': 'object',
    'maxProperties': 10,
    'patternProperties': {
        '^.+$': {'type': 'string', 'minLength': 1, 'maxLength': 100}
    },
    'additionalProperties': False
}
ADD_SCHEMA = object_schema({'productId': {'type': 'string'}, 'quantity': QUANTITY,
                           'selectedAttributes': SELECTION, 'cartVersion': CART_VERSION},
                          ['productId', 'quantity', 'cartVersion'])
UPDATE_SCHEMA = object_schema({'quantity': QUANTITY, 'cartVersion': CART_VERSION},
                             ['quantity', 'cartVersion'])
VERSION_SCHEMA = object_schema({'cartVersion': CART_VERSION}, ['cartVersion'])
