from flask import Blueprint, request
from app.auth import require_roles
from app.schemas.catalog_schema import DELETE_SCHEMA
from app.schemas.product_schema import CREATE_SCHEMA, PATCH_SCHEMA, parse_product_query
from app.schemas.validation import parse_json_body, single_query_values
from app.services.product_service import ProductService
from app.utils.ids import parse_object_id
from app.utils.responses import success, paginated, no_content

admin_products_blueprint = Blueprint('admin_products', __name__)


@admin_products_blueprint.get('/admin/products')
@require_roles('ADMIN')
def admin_list():
    query, sort, pagination = parse_product_query(request.args, admin=True)
    items, total = ProductService().list(query, sort, pagination)
    return paginated(items, pagination, total)


@admin_products_blueprint.get('/admin/products/<product_id>')
@require_roles('ADMIN')
def admin_detail(product_id):
    single_query_values(request.args, set())
    return success(ProductService().detail({'_id': parse_object_id(product_id)}))


@admin_products_blueprint.post('/admin/products')
@require_roles('ADMIN')
def create():
    single_query_values(request.args, set())
    product = ProductService().create(parse_json_body(CREATE_SCHEMA))
    return success(product, 201, location=f"/api/v1/admin/products/{product['_id']}")


@admin_products_blueprint.patch('/admin/products/<product_id>')
@require_roles('ADMIN')
def update(product_id):
    single_query_values(request.args, set())
    return success(ProductService().update(parse_object_id(product_id), parse_json_body(PATCH_SCHEMA)))


@admin_products_blueprint.delete('/admin/products/<product_id>')
@require_roles('ADMIN')
def archive(product_id):
    single_query_values(request.args, set())
    payload = parse_json_body(DELETE_SCHEMA)
    ProductService().archive(parse_object_id(product_id), payload['expectedVersion'])
    return no_content()
