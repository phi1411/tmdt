"""Catalog integration against real rs0 with exact-ID fixture cleanup."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier, local
from uuid import uuid4
import copy
import pytest
from bson import ObjectId
from bson.int64 import Int64
from app.auth.tokens import create_access_token
from app.repositories.category_repository import CategoryRepository
from app.repositories.product_repository import ProductRepository

PREFIX = '/api/v1'
pytestmark = pytest.mark.integration
TYPES = ['ELECTRONICS', 'FASHION', 'HOME_APPLIANCE']
ATTRIBUTES = [
    {'ram': '8GB', 'storage': '256GB', 'chip': 'Demo', 'screen': '6 inch', 'battery': '5000mAh'},
    {'sizes': ['S', 'M'], 'colors': ['Black', 'White'], 'material': 'Cotton', 'gender': 'Unisex'},
    {'power': '1700W', 'capacity': '6L', 'voltage': '220V', 'material': 'Steel'},
]


@pytest.fixture
def catalog(app, client, identities, database):
    with app.app_context():
        headers = {role: {'Authorization': f"Bearer {create_access_token(identities[role])}"} for role in ('admin', 'customer')}
    ids = {'categories': [], 'products': []}
    tag = 'catalog' + uuid4().hex

    def post(collection, payload, expected=201):
        response = client.post(f'{PREFIX}/admin/{collection}', json=payload, headers=headers['admin'])
        if response.status_code == 201:
            ids[collection].append(ObjectId(response.json['data']['id']))
        assert response.status_code == expected, response.json
        return response

    def category(product_type='ELECTRONICS'):
        return post('categories', {'name': 'Danh mục test', 'slug': 'cat-' + uuid4().hex, 'productType': product_type}).json['data']

    def payload(category_id, product_type='ELECTRONICS', **changes):
        n = TYPES.index(product_type)
        return {'sku': 'TEST_' + uuid4().hex.upper(), 'name': f'{tag} Điện thoại Đẹp {n}',
                'slug': 'prod-' + uuid4().hex, 'categoryId': category_id, 'productType': product_type,
                'brand': 'Thương Hiệu', 'description': 'Mô tả', 'price': 100 + n * 100,
                'stock': 10, 'images': ['https://example.test/image.png'], 'attributes': copy.deepcopy(ATTRIBUTES[n]),
                'status': 'ACTIVE', **changes}

    try:
        categories = [category(t) for t in TYPES]
        products = [post('products', payload(c['id'], t)).json['data'] for c, t in zip(categories, TYPES)]
        for status in ('INACTIVE', 'ARCHIVED'):
            products.append(post('products', payload(categories[0]['id'], status=status)).json['data'])
        yield {'headers': headers, 'post': post, 'category': category, 'payload': payload,
               'categories': categories, 'products': products, 'tag': tag, 'ids': ids}
    finally:
        database.products.delete_many({'_id': {'$in': ids['products']}})
        database.categories.delete_many({'_id': {'$in': ids['categories']}})


def admin_get(client, catalog, path):
    return client.get(PREFIX + '/admin/' + path, headers=catalog['headers']['admin'])


def patch(client, catalog, resource, changes, expected=200):
    response = client.patch(PREFIX + '/admin/' + resource, json=changes, headers=catalog['headers']['admin'])
    assert response.status_code == expected, response.json
    return response


def public_results(client, catalog, **query):
    response = client.get(PREFIX + '/products', query_string={'q': catalog['tag'], **query})
    assert response.status_code == 200, response.json
    return response.json


def test_categories_public_admin_archive_and_delete(client, catalog):
    category = catalog['category']()
    detail = client.get(PREFIX + '/categories/' + category['slug'])
    assert detail.status_code == 200 and detail.json['data']['id'] == category['id']
    patch(client, catalog, 'categories/' + category['id'], {'status': 'ARCHIVED', 'expectedVersion': 1})
    assert client.get(PREFIX + '/categories/' + category['slug']).status_code == 404
    public = client.get(PREFIX + '/categories?pageSize=100').json
    assert category['id'] not in [c['id'] for c in public['data']]
    admin = admin_get(client, catalog, 'categories?status=ARCHIVED').json
    assert category['id'] in [c['id'] for c in admin['data']]
    response = client.delete(PREFIX + '/admin/categories/' + category['id'], json={'expectedVersion': 2}, headers=catalog['headers']['admin'])
    assert response.status_code == 204 and not response.data
    assert admin_get(client, catalog, 'categories/' + category['id']).status_code == 404


def test_categories_duplicate_validation_type_and_reference_guards(client, catalog, database):
    c = catalog['categories'][0]
    catalog['post']('categories', {'name': 'Duplicate', 'slug': c['slug'], 'productType': 'ELECTRONICS'}, 409)
    assert database.categories.find_one({'_id': ObjectId(c['id'])})['version'] == 4
    response = patch(client, catalog, 'categories/' + c['id'], {'productType': 'FASHION', 'expectedVersion': 4}, 409)
    assert response.json['error']['code'] == 'CATEGORY_IN_USE'
    assert database.categories.find_one({'_id': ObjectId(c['id'])})['productType'] == 'ELECTRONICS'
    # Archived Product references still forbid category hard deletion.
    response = client.delete(PREFIX + '/admin/categories/' + c['id'], json={'expectedVersion': 4}, headers=catalog['headers']['admin'])
    assert response.status_code == 409 and response.json['error']['code'] == 'CATEGORY_IN_USE'
    assert database.categories.find_one({'_id': ObjectId(c['id'])})['version'] == 4
    patch(client, catalog, 'categories/' + c['id'], {'name': 'Tên mới', 'expectedVersion': 1}, 409)


@pytest.mark.parametrize('changes', [
    {'name': ''}, {'name': '   '}, {'slug': 'Bad Slug'}, {'productType': 'HOME'},
    {'parentId': '123'}, {'status': 'INACTIVE'}, {'description': 'a' * 2001},
])
def test_category_invalid_create(client, catalog, changes):
    catalog['post']('categories', {'name': 'Test', 'slug': 'cat-' + uuid4().hex, 'productType': 'ELECTRONICS', **changes}, 422)


@pytest.mark.parametrize('resource', ['categories', 'products'])
@pytest.mark.parametrize('method,path', [('get', ''), ('post', ''), ('get', '/000000000000000000000001'), ('patch', '/000000000000000000000001'), ('delete', '/000000000000000000000001')])
def test_admin_authorization_matrix(client, catalog, resource, method, path):
    endpoint = PREFIX + '/admin/' + resource + path
    for headers, status in [({}, 401), (catalog['headers']['customer'], 403)]:
        response = getattr(client, method)(endpoint, headers=headers, json={})
        assert response.status_code == status


@pytest.mark.parametrize('index', [0, 1, 2])
def test_polymorphic_roundtrip_public_projection(client, catalog, database, index):
    p = catalog['products'][index]
    response = client.get(PREFIX + '/products/' + p['slug'])
    assert response.status_code == 200
    data = response.json['data']
    assert data['attributes'] == ATTRIBUTES[index] and data['productType'] == TYPES[index]
    assert data['category']['id'] == p['categoryId']
    assert {'id', 'sku', 'name', 'slug', 'categoryId', 'category', 'brand', 'description', 'price', 'stock', 'images', 'attributes', 'version', 'createdAt', 'updatedAt'} <= data.keys()
    assert not {'status', 'schemaVersion', 'nameNormalized', 'brandNormalized'} & data.keys()
    assert isinstance(database.products.find_one({'_id': ObjectId(p['id'])})['price'], Int64)
    assert type(data['price']) is int and data['createdAt'].endswith('Z')
    assert admin_get(client, catalog, 'products/' + p['id']).json['data']['status'] == 'ACTIVE'


def test_product_visibility_and_category_current_state(client, catalog):
    for p in catalog['products'][3:]:
        assert client.get(PREFIX + '/products/' + p['slug']).status_code == 404
    assert client.get(PREFIX + '/products/does-not-exist').status_code == 404
    p = catalog['products'][0]
    c = admin_get(client, catalog, 'categories/' + p['categoryId']).json['data']
    patch(client, catalog, 'categories/' + c['id'], {'status': 'ARCHIVED', 'expectedVersion': c['version']})
    assert client.get(PREFIX + '/products/' + p['slug']).status_code == 404
    result = public_results(client, catalog)
    assert result['meta']['total'] == 2 and p['id'] not in [item['id'] for item in result['data']]
    assert admin_get(client, catalog, 'products/' + p['id']).status_code == 200


def test_pagination_sort_ties_and_empty_results(client, catalog, database):
    for i, p in enumerate(catalog['products'][:3]):
        database.products.update_one({'_id': ObjectId(p['id'])}, {'$set': {'createdAt': datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=i)}})
    for sort, expected in [('price_asc', [100, 200, 300]), ('price_desc', [300, 200, 100]), ('latest', [300, 200, 100])]:
        result = public_results(client, catalog, sort=sort)
        assert [p['price'] for p in result['data']] == expected
    result = public_results(client, catalog, page=2, pageSize=2, sort='price_asc')
    assert [p['price'] for p in result['data']] == [300]
    assert {k: v for k, v in result['meta'].items() if k != 'requestId'} == {'page': 2, 'pageSize': 2, 'total': 3, 'totalPages': 2}
    assert public_results(client, catalog, page=10)['data'] == []
    result = public_results(client, catalog, q=uuid4().hex)
    assert result['data'] == [] and result['meta']['totalPages'] == 0
    # All equal price/date: stable ID tie breaker in both directions.
    ids = [ObjectId(p['id']) for p in catalog['products'][:3]]
    database.products.update_many({'_id': {'$in': ids}}, {'$set': {'price': Int64(100), 'createdAt': datetime(2026, 1, 1, tzinfo=timezone.utc)}})
    for sort, reverse in [('price_asc', False), ('price_desc', True), ('latest', True)]:
        assert [p['id'] for p in public_results(client, catalog, sort=sort)['data']] == [str(i) for i in sorted(ids, reverse=reverse)]


@pytest.mark.parametrize('q', ['ĐIỆN đẹp', 'dien dep', ' đẹp   ĐIỆN ', 'thoai dien'])
def test_vietnamese_search_and_token_and(client, catalog, q):
    assert public_results(client, catalog, q=catalog['tag'] + ' ' + q)['meta']['total'] == 3


def test_empty_search_brand_and_literal_regex(client, catalog):
    assert client.get(PREFIX + '/products?q=%20%20&brand=%20').status_code == 200
    assert public_results(client, catalog, brand=' THƯƠNG   HIỆU ')['meta']['total'] == 3
    p = catalog['products'][0]
    patch(client, catalog, 'products/' + p['id'], {'name': catalog['tag'] + ' Điện [.*] $', 'expectedVersion': p['version']})
    for literal in ('[.*]', '$'):
        result = public_results(client, catalog, q=catalog['tag'] + ' ' + literal)
        assert result['meta']['total'] == 1 and result['data'][0]['id'] == p['id']


@pytest.mark.parametrize('query,expected', [
    ({'productType': 'ELECTRONICS'}, [100]), ({'productType': 'FASHION'}, [200]),
    ({'brand': 'thuong hieu'}, [100, 200, 300]), ({'brand': 'missing'}, []),
    ({'minPrice': '200'}, [200, 300]), ({'maxPrice': '200'}, [100, 200]),
    ({'minPrice': '200', 'maxPrice': '200'}, [200]),
    ({'ram': '8GB'}, [100]), ({'size': 'S', 'color': 'Black'}, [200]),
    ({'capacity': '6L'}, [300]), ({'productType': 'FASHION', 'ram': '8GB'}, []),
    ({'brand': 'thuong hieu', 'productType': 'HOME_APPLIANCE', 'minPrice': '250', 'capacity': '6L'}, [300]),
])
def test_filters(client, catalog, query, expected):
    assert [p['price'] for p in public_results(client, catalog, sort='price_asc', **query)['data']] == expected


def test_category_filter_and_admin_status(client, catalog):
    c = catalog['categories'][0]
    assert public_results(client, catalog, categoryId=c['id'])['meta']['total'] == 1
    assert public_results(client, catalog, categoryId=c['id'], productType='FASHION')['meta']['total'] == 0
    result = admin_get(client, catalog, 'products?q=' + catalog['tag']).json
    assert result['meta']['total'] == 5
    result = admin_get(client, catalog, 'products?q=' + catalog['tag'] + '&status=INACTIVE').json
    assert result['meta']['total'] == 1


@pytest.mark.parametrize('query,status', [
    ('search=abc', 422), ('status=INACTIVE', 422), ('page=0', 422), ('page=1.2', 400),
    ('pageSize=101', 422), ('pageSize=abc', 400), ('q=a&q=b', 422), ('sort=newest', 422),
    ('sort=name_asc', 422), ('categoryId=invalid', 400), ('minPrice=1.5', 400),
    ('minPrice=300&maxPrice=100', 422), ('productType=HOME', 422), ('q=' + 'a' * 101, 422),
    ('q=a+b+c+d+e+f+g+h+i', 422), ('attributes.ram=8GB', 422), ('q[$ne]=x', 422),
])
def test_query_validation(client, query, status):
    assert client.get(PREFIX + '/products?' + query).status_code == status


@pytest.mark.parametrize('changes', [
    {'price': True}, {'price': 1.2}, {'price': 0}, {'price': 1000000001},
    {'stock': -1}, {'stock': True}, {'stock': 1.1}, {'stock': 2147483648},
    {'sku': 'lowercase'}, {'name': ' '}, {'slug': 'BAD'}, {'status': 'DISABLED'},
    {'images': ['javascript:alert(1)']}, {'images': ['http://example.test/a']},
    {'images': ['https:///a']}, {'images': ['https://example.test:invalid/a']},
    {'images': ['https://user:secret@example.test/a']}, {'images': ['/relative.png']},
    {'attributes': {}}, {'attributes': {'ram': 8}}, {'attributes': {'$op': 'bad'}},
    {'attributes': {'a': {'b': {'c': {'d': 'too deep'}}}}},
    {'attributes': {'custom': 2**64}}, {'attributes': {'custom': 'x' * 501}},
    {'_id': '000000000000000000000001'}, {'nameNormalized': 'client value'}, {'createdAt': 'now'},
])
def test_product_invalid_payload(client, catalog, changes):
    catalog['post']('products', catalog['payload'](catalog['categories'][0]['id'], **changes), 422)


@pytest.mark.parametrize('index,attributes', [(1, {'sizes': 'M'}), (1, {'colors': ['Black', 'Black']}), (1, {'gender': 1}), (2, {'power': 1700}), (2, {'capacity': []})])
def test_known_attributes_wrong_type(client, catalog, index, attributes):
    catalog['post']('products', catalog['payload'](catalog['categories'][index]['id'], TYPES[index], attributes=attributes), 422)


def test_dynamic_unknown_attributes_optional_known_fields_and_loopback_images(client, catalog):
    attributes = {'bluetooth': True, 'weight': 1.5, 'notes': None, 'dimensions': {'width': 10, 'options': ['a', 1], 'nested': {'value': 'ok'}}}
    p = catalog['post']('products', catalog['payload'](catalog['categories'][0]['id'], attributes=attributes,
        images=['http://localhost:5001/image', 'http://127.0.0.1/image'], stock=0)).json['data']
    assert client.get(PREFIX + '/products/' + p['slug']).json['data']['attributes'] == attributes


def test_duplicates_category_rules_and_rollback(client, catalog, database):
    p = catalog['products'][0]
    c = catalog['categories'][0]
    before_version = database.categories.find_one({'_id': ObjectId(c['id'])})['version']
    for field in ('sku', 'slug'):
        response = catalog['post']('products', catalog['payload'](c['id'], **{field: p[field]}), 409)
        assert response.json['error']['code'] == 'DUPLICATE_RESOURCE'
        assert database.categories.find_one({'_id': ObjectId(c['id'])})['version'] == before_version
    for category_id in (str(ObjectId()), catalog['categories'][1]['id']):
        response = catalog['post']('products', catalog['payload'](category_id), 409)
        assert response.json['error']['code'] == 'CATEGORY_UNAVAILABLE'
    patch(client, catalog, 'categories/' + c['id'], {'status': 'ARCHIVED', 'expectedVersion': before_version})
    catalog['post']('products', catalog['payload'](c['id']), 409)


def test_patch_preserves_fields_normalization_version_and_archive(client, catalog, database):
    p = catalog['products'][0]
    resource = 'products/' + p['id']
    changed = patch(client, catalog, resource, {'price': 12000000, 'expectedVersion': 1}).json['data']
    assert changed['version'] == 2 and changed['stock'] == p['stock'] and changed['attributes'] == p['attributes']
    patch(client, catalog, resource, {'stock': 99, 'expectedVersion': 1}, 409)
    assert admin_get(client, catalog, resource).json['data']['stock'] == 10
    changed = patch(client, catalog, resource, {'name': catalog['tag'] + ' Áo mới', 'brand': 'Đổi', 'stock': 0,
        'attributes': {'custom': 'new'}, 'expectedVersion': 2}).json['data']
    assert changed['version'] == 3 and changed['attributes'] == {'custom': 'new'}
    stored = database.products.find_one({'_id': ObjectId(p['id'])})
    assert stored['nameNormalized'] == catalog['tag'] + ' ao moi' and stored['brandNormalized'] == 'doi'
    for changes in ({'sku': 'NEW'}, {'_id': p['id']}, {'price': 1}, {}):
        body = changes if changes == {'price': 1} else {**changes, 'expectedVersion': 3}
        patch(client, catalog, resource, body, 422)
    response = client.delete(PREFIX + '/admin/' + resource, json={'expectedVersion': 2}, headers=catalog['headers']['admin'])
    assert response.status_code == 409
    response = client.delete(PREFIX + '/admin/' + resource, json={'expectedVersion': 3}, headers=catalog['headers']['admin'])
    assert response.status_code == 204
    archived = admin_get(client, catalog, resource).json['data']
    assert archived['status'] == 'ARCHIVED' and archived['stock'] == 0 and archived['version'] == 4
    assert client.delete(PREFIX + '/admin/' + resource, json={'expectedVersion': 3}, headers=catalog['headers']['admin']).status_code == 204
    assert admin_get(client, catalog, resource).json['data']['version'] == 4
    patch(client, catalog, resource, {'name': 'no edit', 'expectedVersion': 4}, 409)
    restored = patch(client, catalog, resource, {'status': 'ACTIVE', 'expectedVersion': 4}).json['data']
    assert restored['status'] == 'ACTIVE' and restored['version'] == 5


def test_product_type_move_requires_compatible_replacement_and_active_category(client, catalog):
    p = catalog['products'][0]
    target = catalog['categories'][1]
    resource = 'products/' + p['id']
    changes = {'categoryId': target['id'], 'productType': 'FASHION', 'expectedVersion': 1}
    patch(client, catalog, resource, changes, 422)
    patch(client, catalog, resource, {**changes, 'attributes': {'sizes': 1}}, 422)
    result = patch(client, catalog, resource, {**changes, 'attributes': ATTRIBUTES[1]}).json['data']
    assert result['productType'] == 'FASHION' and result['category']['id'] == target['id']
    c = admin_get(client, catalog, 'categories/' + target['id']).json['data']
    patch(client, catalog, 'categories/' + c['id'], {'status': 'ARCHIVED', 'expectedVersion': c['version']})
    patch(client, catalog, resource, {'status': 'INACTIVE', 'expectedVersion': 2})
    patch(client, catalog, resource, {'status': 'ACTIVE', 'expectedVersion': 3}, 409)


@pytest.mark.parametrize('action', ['archive', 'delete'])
@pytest.mark.parametrize('operation', ['create', 'move'])
def test_category_product_race_real_transactions(app, client, catalog, database, monkeypatch, action, operation):
    target = catalog['category']()
    barrier = Barrier(2)
    thread_state = local()
    original = CategoryRepository.patch

    def synchronized(self, query, fields, now, session=None):
        if query.get('_id') == ObjectId(target['id']) and not getattr(thread_state, 'waited', False):
            thread_state.waited = True
            barrier.wait(timeout=10)
        return original(self, query, fields, now, session)

    monkeypatch.setattr(CategoryRepository, 'patch', synchronized)

    def write_product():
        with app.test_client() as worker:
            if operation == 'create':
                response = worker.post(PREFIX + '/admin/products', json=catalog['payload'](target['id']), headers=catalog['headers']['admin'])
                if response.status_code == 201:
                    catalog['ids']['products'].append(ObjectId(response.json['data']['id']))
                return response.status_code
            p = catalog['products'][0]
            return worker.patch(PREFIX + '/admin/products/' + p['id'], json={'categoryId': target['id'], 'expectedVersion': 1}, headers=catalog['headers']['admin']).status_code

    def write_category():
        with app.test_client() as worker:
            url = PREFIX + '/admin/categories/' + target['id']
            if action == 'delete':
                return worker.delete(url, json={'expectedVersion': 1}, headers=catalog['headers']['admin']).status_code
            return worker.patch(url, json={'status': 'ARCHIVED', 'expectedVersion': 1}, headers=catalog['headers']['admin']).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        p_future, c_future = pool.submit(write_product), pool.submit(write_category)
        p_status, c_status = p_future.result(timeout=20), c_future.result(timeout=20)
    assert p_status in {200, 201, 409} and c_status in {200, 204, 409}
    assert (p_status in {200, 201}) != (c_status in {200, 204})
    category = database.categories.find_one({'_id': ObjectId(target['id'])})
    products = list(database.products.find({'categoryId': ObjectId(target['id'])}))
    if category is None:
        assert products == []
    elif category['status'] == 'ARCHIVED':
        assert products == []
    else:
        assert len(products) == 1


def test_concurrent_product_patch_prevents_lost_update(app, catalog, monkeypatch):
    barrier = Barrier(2)
    thread_state = local()
    original = ProductRepository.patch

    def synchronized(self, *args, **kwargs):
        if not getattr(thread_state, 'waited', False):
            thread_state.waited = True
            barrier.wait(timeout=10)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(ProductRepository, 'patch', synchronized)

    def write(value):
        with app.test_client() as worker:
            return worker.patch(PREFIX + '/admin/products/' + catalog['products'][0]['id'], json={'stock': value, 'expectedVersion': 1}, headers=catalog['headers']['admin']).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(write, value) for value in (7, 8)]
        statuses = [f.result(timeout=20) for f in futures]
    assert sorted(statuses) == [200, 409]


def test_publish_vs_category_archive_race(app, client, catalog, database, monkeypatch):
    p = catalog['products'][3]
    category = admin_get(client, catalog, 'categories/' + p['categoryId']).json['data']
    barrier = Barrier(2)
    thread_state = local()
    original = CategoryRepository.patch

    def synchronized(self, query, fields, now, session=None):
        if query.get('_id') == ObjectId(category['id']) and not getattr(thread_state, 'waited', False):
            thread_state.waited = True
            barrier.wait(timeout=10)
        return original(self, query, fields, now, session)

    monkeypatch.setattr(CategoryRepository, 'patch', synchronized)

    def publish():
        with app.test_client() as worker:
            return worker.patch(PREFIX + '/admin/products/' + p['id'], json={'status': 'ACTIVE', 'expectedVersion': 1}, headers=catalog['headers']['admin']).status_code

    def archive():
        with app.test_client() as worker:
            return worker.patch(PREFIX + '/admin/categories/' + category['id'], json={'status': 'ARCHIVED', 'expectedVersion': category['version']}, headers=catalog['headers']['admin']).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(publish), pool.submit(archive)]
        statuses = [f.result(timeout=20) for f in futures]
    assert sorted(statuses) == [200, 409]
    stored = database.products.find_one({'_id': ObjectId(p['id'])})
    category = database.categories.find_one({'_id': ObjectId(category['id'])})
    assert (stored['status'] == 'ACTIVE') == (category['status'] == 'ACTIVE')


@pytest.mark.parametrize('path', ['/products/missing', '/categories/missing', '/admin/products/000000000000000000000001', '/admin/categories/000000000000000000000001'])
def test_detail_unknown_query_rejected(client, catalog, path):
    assert client.get(PREFIX + path + '?status=ACTIVE', headers=catalog['headers']['admin']).status_code == 422


def test_version_caps_reject_without_driver_error(client, catalog, database):
    p = catalog['products'][0]
    c = catalog['categories'][0]
    database.products.update_one({'_id': ObjectId(p['id'])}, {'$set': {'version': 2147483647}})
    response = patch(client, catalog, 'products/' + p['id'], {'price': 120, 'expectedVersion': 2147483647}, 409)
    assert response.json['error']['code'] == 'VERSION_LIMIT'
    database.categories.update_one({'_id': ObjectId(c['id'])}, {'$set': {'version': 2147483647}})
    response = patch(client, catalog, 'categories/' + c['id'], {'name': 'new', 'expectedVersion': 2147483647}, 409)
    assert response.json['error']['code'] == 'VERSION_LIMIT'
    catalog['post']('products', catalog['payload'](c['id']), 409)
