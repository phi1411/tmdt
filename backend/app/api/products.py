from flask import Blueprint, request
from app.schemas.product_schema import parse_product_query
from app.schemas.validation import single_query_values
from app.services.product_service import ProductService
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
    from app.services.review_service import ReviewService
    from bson import ObjectId
    if ObjectId.is_valid(identifier):
        pid = ObjectId(identifier)
    else:
        product = ProductService().detail({'slug': identifier, 'status': 'ACTIVE'}, public=True)
        pid = product['_id']
    reviews, stats = ReviewService().get_product_reviews(pid)
    return success({'reviews': reviews, 'stats': stats})
