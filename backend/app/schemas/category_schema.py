from app.schemas.catalog_schema import body_schema, properties, VERSION_SCHEMA, nonblank
from app.schemas.pagination import Pagination
from app.schemas.validation import single_query_values, validate_payload

CATEGORY_FIELDS = ('name', 'slug', 'productType', 'description', 'status')
PROPERTIES, _ = properties('categories', CATEGORY_FIELDS)
CREATE_SCHEMA = body_schema({k: v for k, v in PROPERTIES.items() if k != 'status'}, ['name', 'slug', 'productType'])
PATCH_SCHEMA = body_schema({**PROPERTIES, 'expectedVersion': VERSION_SCHEMA}, ['expectedVersion'])


def validate_category(payload):
    validate_payload(payload, body_schema(PROPERTIES, CATEGORY_FIELDS))
    nonblank(payload, ['name'])


def parse_category_query(args, admin=False):
    values = single_query_values(args, {'page', 'pageSize', 'status'} if admin else {'page', 'pageSize'})
    pagination = Pagination.from_query(values)
    if 'status' in values:
        validate_payload(values['status'], PROPERTIES['status'])
    query = {} if admin else {'status': 'ACTIVE'}
    if 'status' in values:
        query['status'] = values['status']
    return query, pagination
