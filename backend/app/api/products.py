from flask import Blueprint, request
from app.auth import get_current_user, require_roles
from app.schemas.product_schema import parse_product_query
from app.schemas.review_schema import CREATE_REVIEW_SCHEMA
from app.schemas.validation import parse_json_body, single_query_values
from app.services.product_service import ProductService
from app.services.review_service import ReviewService
from app.utils.responses import success, paginated

products_blueprint = Blueprint('products', __name__)


@products_blueprint.get('/products')
def public_list():
    query, sort, pagination = parse_product_query(request.args)
    items, total = ProductService().list(query, sort, pagination, public=True)
    return paginated(items, pagination, total)


@products_blueprint.get('/products/<slug>')
def public_detail(slug):
    single_query_values(request.args, set())
    return success(ProductService().detail({'slug': slug, 'status': 'ACTIVE'}, public=True))


@products_blueprint.get('/products/<identifier>/reviews')
def product_reviews(identifier):
    from app.schemas.pagination import Pagination, query_integer
    from app.errors import ValidationError
    values = single_query_values(request.args, {'page', 'pageSize', 'rating', 'hasComment'})
    rating = query_integer(values['rating'], 'rating', 1, 5) if 'rating' in values else None
    if values.get('hasComment', 'false') not in {'true', 'false'}:
        raise ValidationError(details=[{'field': 'hasComment', 'reason': 'Giá trị phải là true/false'}])
    reviews, stats, meta = ReviewService().get_product_reviews(identifier, Pagination.from_query(values), rating, values.get('hasComment') == 'true')
    return success({'reviews': reviews, 'stats': stats}, meta=meta)


@products_blueprint.post('/products/<identifier>/reviews')
@require_roles('CUSTOMER')
def submit_review(identifier):
    single_query_values(request.args, set())
    payload = parse_json_body(CREATE_REVIEW_SCHEMA)
    result = ReviewService().create_review(get_current_user(), identifier, payload)
    return success(result, status=201)

