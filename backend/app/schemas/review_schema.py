"""Strict review inputs aligned with the locked reviews validator."""
from app.schemas.user_schema import object_schema

CREATE_REVIEW_SCHEMA = object_schema({
    'orderId': {
        'type': 'string',
        'pattern': '^[0-9a-fA-F]{24}$',
    },
    'rating': {
        'type': 'integer',
        'minimum': 1,
        'maximum': 5,
    },
    'reviewText': {
        'type': 'string',
        'maxLength': 2000,
    },
    'images': {
        'type': 'array',
        'maxItems': 5,
        'items': {
            'type': 'string',
            'maxLength': 2048,
        },
    },
}, ['orderId', 'rating'])

REVIEW_PUBLIC_FIELDS = (
    '_id', 'productId',
    'userSnapshot', 'skuSpecSnapshot', 'rating', 'reviewText',
    'images', 'helpfulCount', 'sellerFeedback', 'status', 'createdAt', 'updatedAt'
)


def review_response(review, owner=False):
    fields = REVIEW_PUBLIC_FIELDS + (('orderId', 'orderCode', 'userId') if owner else ())
    return {key: review[key] for key in fields if key in review}
