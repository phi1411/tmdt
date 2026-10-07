"""Strict API IDs; never hand client query operators to PyMongo."""
import re
from bson import ObjectId
from app.errors import BadRequestError


def parse_object_id(value, field='id'):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{24}', value):
        raise BadRequestError(details=[{'field': field, 'reason': 'ID phải là chuỗi hex chữ thường gồm 24 ký tự'}])
    return ObjectId(value)
