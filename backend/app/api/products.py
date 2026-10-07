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
