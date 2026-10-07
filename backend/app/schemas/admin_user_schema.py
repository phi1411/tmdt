"""Admin account query and status allowlists."""
from app.schemas.user_schema import VERSION, object_schema
from app.schemas.validation import single_query_values, validate_payload
from app.schemas.pagination import Pagination

STATUS_SCHEMA = object_schema({'status': {'type': 'string', 'enum': ['ACTIVE', 'BLOCKED']},
                               'expectedVersion': VERSION}, ['status', 'expectedVersion'])
FILTER_SCHEMA = object_schema({'q': {'type': 'string', 'maxLength': 100},
                               'role': {'enum': ['CUSTOMER', 'ADMIN']},
                               'status': {'enum': ['ACTIVE', 'BLOCKED']}})


def parse_user_query(args):
    values = single_query_values(args, {'q', 'role', 'status', 'page', 'pageSize'})
    pagination = Pagination.from_query(values)
    filters = {k: v for k, v in values.items() if k in {'q', 'role', 'status'}}
    validate_payload(filters, FILTER_SCHEMA)
    if 'q' in filters:
        filters['q'] = filters['q'].strip().lower()
    return filters, pagination
