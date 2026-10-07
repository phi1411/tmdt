import math
import re
from urllib.parse import urlsplit
from app.errors import ValidationError
from app.schemas.catalog_schema import body_schema, properties, request_shape, VERSION_SCHEMA, normalize, nonblank
from app.schemas.pagination import Pagination, query_integer
from app.schemas.query_contract import PRODUCT_QUERY_FIELDS, PRODUCT_SORTS, DEFAULT_PRODUCT_SORT
from app.schemas.validation import single_query_values, validate_payload
from app.utils.ids import parse_object_id

PRODUCT_FIELDS = ('sku', 'name', 'slug', 'categoryId', 'productType', 'brand', 'description',
                  'price', 'stock', 'images', 'attributes', 'status')
PROPERTIES, CANONICAL = properties('products', PRODUCT_FIELDS)
CREATE_SCHEMA = body_schema(PROPERTIES, PRODUCT_FIELDS)
PATCH_SCHEMA = body_schema({**{k: v for k, v in PROPERTIES.items() if k != 'sku'},
                            'expectedVersion': VERSION_SCHEMA}, ['expectedVersion'])
FULL_SCHEMA = {**CREATE_SCHEMA, 'oneOf': request_shape(CANONICAL['oneOf'])}


def validate_product(payload):
    validate_payload(payload, FULL_SCHEMA)
    nonblank(payload, ['name', 'sku'])
    if not normalize(payload['name']):
        raise ValidationError(details=[{'field': 'name', 'reason': 'Tên chuẩn hóa không được trống'}])
    parse_object_id(payload['categoryId'], 'categoryId')
    for url in payload['images']:
        try:
            parts = urlsplit(url)
            valid = parts.hostname and not parts.username and not parts.password and not re.search(r'\s|[\\\x00-\x1f\x7f]', url)
            parts.port
            valid = valid and (parts.scheme == 'https' or (parts.scheme == 'http' and parts.hostname in {'localhost', '127.0.0.1'}))
        except ValueError:
            valid = False
        if not valid:
            raise ValidationError(details=[{'field': 'images', 'reason': 'Ảnh phải là URL HTTPS hoặc HTTP loopback'}])
    validate_numbers(payload['attributes'])


def validate_numbers(value):
    if isinstance(value, dict):
        for item in value.values():
            validate_numbers(item)
    elif isinstance(value, list):
        for item in value:
            validate_numbers(item)
    elif (type(value) is float and not math.isfinite(value)) or (type(value) is int and not -(2**63) <= value < 2**63):
        raise ValidationError(details=[{'field': 'attributes', 'reason': 'Số không hữu hạn hoặc vượt giới hạn BSON'}])


def parse_product_query(args, admin=False):
    values = single_query_values(args, PRODUCT_QUERY_FIELDS | ({'status'} if admin else set()))
    pagination = Pagination.from_query(values)
    sort = values.get('sort', DEFAULT_PRODUCT_SORT)
    if sort not in PRODUCT_SORTS:
        raise ValidationError(details=[{'field': 'sort', 'reason': 'Thứ tự không được hỗ trợ'}])
    query = {} if admin else {'status': 'ACTIVE'}
    for field in ('productType', 'status'):
        if field in values:
            validate_payload(values[field], PROPERTIES[field])
            query[field] = values[field]
    if 'categoryId' in values:
        query['categoryId'] = parse_object_id(values['categoryId'], 'categoryId')
    if 'q' in values:
        validate_payload(values['q'].strip(), {'type': 'string', 'maxLength': 100})
        tokens = normalize(values['q']).split()
        if len(tokens) > 8:
            raise ValidationError(details=[{'field': 'q', 'reason': 'Tối đa 8 từ tìm kiếm'}])
        if tokens:
            query['$and'] = [{'nameNormalized': {'$regex': re.escape(token)}} for token in tokens]
    if 'brand' in values:
        validate_payload(values['brand'], PROPERTIES['brand'])
        brand = normalize(values['brand'])
        if brand:
            query['brandNormalized'] = brand
    low = query_integer(values['minPrice'], 'minPrice', 0, 1000000000) if 'minPrice' in values else None
    high = query_integer(values['maxPrice'], 'maxPrice', 0, 1000000000) if 'maxPrice' in values else None
    if low is not None and high is not None and low > high:
        raise ValidationError(details=[{'field': 'minPrice', 'reason': 'Giá tối thiểu vượt giá tối đa'}])
    if low is not None or high is not None:
        query['price'] = {**({'$gte': low} if low is not None else {}), **({'$lte': high} if high is not None else {})}
    for field, path, length in [('size', 'sizes', 50), ('color', 'colors', 50), ('ram', 'ram', 100), ('capacity', 'capacity', 100)]:
        if field in values:
            validate_payload(values[field], {'type': 'string', 'minLength': 1, 'maxLength': length})
            query[f'attributes.{path}'] = values[field]
    return query, PRODUCT_SORTS[sort], pagination
