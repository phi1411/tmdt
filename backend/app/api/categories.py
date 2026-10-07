from flask import Blueprint, request
from app.auth import require_roles
from app.schemas.catalog_schema import DELETE_SCHEMA
from app.schemas.category_schema import CREATE_SCHEMA, PATCH_SCHEMA, parse_category_query
from app.schemas.validation import parse_json_body, single_query_values
from app.services.category_service import CategoryService
from app.utils.ids import parse_object_id
from app.utils.responses import success, paginated, no_content

categories_blueprint = Blueprint('categories', __name__)


@categories_blueprint.get('/categories')
def public_list():
    query, pagination = parse_category_query(request.args)
    items, total = CategoryService().list(query, pagination)
    return paginated(items, pagination, total)


@categories_blueprint.get('/categories/<slug>')
def public_detail(slug):
    single_query_values(request.args, set())
    return success(CategoryService().detail({'slug': slug, 'status': 'ACTIVE'}))


@categories_blueprint.get('/admin/categories')
@require_roles('ADMIN')
def admin_list():
    query, pagination = parse_category_query(request.args, admin=True)
    items, total = CategoryService().list(query, pagination)
    return paginated(items, pagination, total)


@categories_blueprint.get('/admin/categories/<category_id>')
@require_roles('ADMIN')
def admin_detail(category_id):
    single_query_values(request.args, set())
    return success(CategoryService().detail({'_id': parse_object_id(category_id)}))


@categories_blueprint.post('/admin/categories')
@require_roles('ADMIN')
def create():
    single_query_values(request.args, set())
    category = CategoryService().create(parse_json_body(CREATE_SCHEMA))
    return success(category, 201, location=f"/api/v1/admin/categories/{category['_id']}")


@categories_blueprint.patch('/admin/categories/<category_id>')
@require_roles('ADMIN')
def update(category_id):
    single_query_values(request.args, set())
    return success(CategoryService().update(parse_object_id(category_id), parse_json_body(PATCH_SCHEMA)))


@categories_blueprint.delete('/admin/categories/<category_id>')
@require_roles('ADMIN')
def delete(category_id):
    single_query_values(request.args, set())
    payload = parse_json_body(DELETE_SCHEMA)
    CategoryService().delete(parse_object_id(category_id), payload['expectedVersion'])
    return no_content()
