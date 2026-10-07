"""Request shapes derived from canonical Catalog validators; no DB changes."""
import json
import unicodedata
from pathlib import Path
from app.errors import ValidationError

VALIDATORS = Path(__file__).resolve().parents[3] / 'database' / 'validators'
VERSION_SCHEMA = {'type': 'integer', 'minimum': 1, 'maximum': 2147483647}


def normalize(value):
    text = unicodedata.normalize('NFKD', value).casefold().replace('đ', 'd')
    return ' '.join(''.join(c for c in text if not unicodedata.combining(c)).split())


def request_shape(value):
    if isinstance(value, list):
        return [request_shape(item) for item in value]
    if not isinstance(value, dict):
        return value
    result = {k: request_shape(v) for k, v in value.items() if k != 'bsonType'}
    if 'bsonType' in value:
        mapping = {'object': 'object', 'array': 'array', 'string': 'string', 'int': 'integer',
                   'long': 'integer', 'double': 'number', 'bool': 'boolean', 'null': 'null', 'objectId': 'string'}
        types = value['bsonType']
        result['type'] = list(dict.fromkeys(mapping[t] for t in types)) if isinstance(types, list) else mapping[types]
    return result


def properties(collection, fields):
    source = json.loads((VALIDATORS / f'{collection}.json').read_text(encoding='utf-8'))['$jsonSchema']
    return {field: request_shape(source['properties'][field]) for field in fields}, source


def body_schema(props, required=()):
    return {'type': 'object', 'properties': props, 'required': list(required), 'additionalProperties': False}


def nonblank(payload, fields):
    for field in fields:
        if field in payload and not payload[field].strip():
            raise ValidationError(details=[{'field': field, 'reason': 'Nội dung không được để trống'}])


DELETE_SCHEMA = body_schema({'expectedVersion': VERSION_SCHEMA}, ['expectedVersion'])
