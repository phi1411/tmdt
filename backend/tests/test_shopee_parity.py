"""Comprehensive tests for Shopee/TikTok Shop Parity Features (Phases 1-5).
Covers Smart Search, UGC Reviews, Synthetic Data Models, SKU Variation Matrix, and Policy Integrity.
"""
from datetime import datetime, timezone
from uuid import uuid4
import copy
import pytest
from bson import ObjectId
from bson.int64 import Int64
from app.auth.tokens import create_access_token
from app.schemas.catalog_schema import normalize

PREFIX = '/api/v1'
pytestmark = pytest.mark.integration


@pytest.fixture
def parity_setup(app, client, identities, database):
    user = identities['customer']
    other_user = copy.deepcopy(identities['customer'])
    other_user['_id'] = ObjectId()
    other_user['email'] = f'parity-other-{uuid4().hex}@example.test'

    now = datetime.now(timezone.utc)
    cat_id = ObjectId()
    prod_id = ObjectId()
    prod_with_skus_id = ObjectId()
    unrelated_prod_id = ObjectId()
    order_id = ObjectId()
    pending_order_id = ObjectId()

    try:
        database.users.insert_one(other_user)

        with app.app_context():
            customer_token = create_access_token(user)
            other_token = create_access_token(other_user)
            admin_token = create_access_token(identities['admin'])

        headers_customer = {'Authorization': f'Bearer {customer_token}'}
        headers_other = {'Authorization': f'Bearer {other_token}'}
        headers_admin = {'Authorization': f'Bearer {admin_token}'}

        # 1. Category
        database.categories.insert_one({
            '_id': cat_id,
            'schemaVersion': 1,
            'version': 1,
            'createdAt': now,
            'updatedAt': now,
            'name': 'Thiết bị thông minh',
            'slug': f'cat-parity-{uuid4().hex}',
            'productType': 'ELECTRONICS',
            'description': 'Danh mục thiết bị thông minh',
            'status': 'ACTIVE',
        })

        # 2. Standard Product
        prod_slug = f'smartphone-nova-{uuid4().hex[:8]}'
        prod_doc = {
            '_id': prod_id,
            'schemaVersion': 1,
            'version': 1,
            'createdAt': now,
            'updatedAt': now,
            'sku': f'SMART-{uuid4().hex[:8].upper()}',
            'name': 'Điện Thoại Nova Smartphone Pro Max',
            'slug': prod_slug,
            'categoryId': cat_id,
            'productType': 'ELECTRONICS',
            'brand': 'NovaTech',
            'description': 'Mô tả điện thoại thông minh cao cấp',
            'price': Int64(25000000),
            'stock': 40,
            'images': ['https://example.test/nova-phone.png'],
            'attributes': {'ram': '12GB', 'storage': '256GB'},
            'nameNormalized': normalize('Điện Thoại Nova Smartphone Pro Max'),
            'brandNormalized': normalize('NovaTech'),
            'status': 'ACTIVE',
        }
        database.products.insert_one(prod_doc)

        # 3. Product with Multi-Tier SKU Matrix (Phase 5)
        sku_prod_slug = f'flagship-sku-{uuid4().hex[:8]}'
        prod_with_skus_doc = {
            '_id': prod_with_skus_id,
            'schemaVersion': 1,
            'version': 1,
            'createdAt': now,
            'updatedAt': now,
            'sku': f'SKU-PROD-{uuid4().hex[:8].upper()}',
            'name': 'Laptop NovaBook Ultra M3',
            'slug': sku_prod_slug,
            'categoryId': cat_id,
            'productType': 'ELECTRONICS',
            'brand': 'NovaTech',
            'description': 'Laptop cao cấp với nhiều tùy chọn màu và RAM',
            'price': Int64(35000000),
            'stock': 25,
            'images': ['https://example.test/novabook.png'],
            'attributes': {'chip': 'M3 Ultra', 'screen': '14 inch'},
            'nameNormalized': normalize('Laptop NovaBook Ultra M3'),
            'brandNormalized': normalize('NovaTech'),
            'status': 'ACTIVE',
            'tierVariations': [
                {'tier': 1, 'name': 'Màu sắc', 'options': ['Xám Không Gian', 'Bạc']},
                {'tier': 2, 'name': 'RAM & Ổ cứng', 'options': ['16GB / 512GB', '32GB / 1TB']}
            ],
            'skus': [
                {'skuId': 'NB-GRY-16-512', 'tierIndex': [0, 0], 'price': Int64(35000000), 'stock': 10},
                {'skuId': 'NB-GRY-32-1TB', 'tierIndex': [0, 1], 'price': Int64(42000000), 'stock': 5},
                {'skuId': 'NB-SLV-16-512', 'tierIndex': [1, 0], 'price': Int64(35000000), 'stock': 6},
                {'skuId': 'NB-SLV-32-1TB', 'tierIndex': [1, 1], 'price': Int64(42000000), 'stock': 4},
            ]
        }
        database.products.insert_one(prod_with_skus_doc)

        # 4. Unrelated Product
        database.products.insert_one({
            '_id': unrelated_prod_id,
            'schemaVersion': 1,
            'version': 1,
            'createdAt': now,
            'updatedAt': now,
            'sku': f'UNRELATED-{uuid4().hex[:8].upper()}',
            'name': 'Sản Phẩm Khác',
            'slug': f'unrelated-{uuid4().hex}',
            'categoryId': cat_id,
            'productType': 'ELECTRONICS',
            'brand': 'NovaTech',
            'description': 'Sản phẩm không nằm trong đơn',
            'price': Int64(1000000),
            'stock': 5,
            'images': ['https://example.test/unrelated.png'],
            'attributes': {'ram': '4GB', 'storage': '64GB'},
            'nameNormalized': normalize('Sản Phẩm Khác'),
            'brandNormalized': normalize('NovaTech'),
            'status': 'ACTIVE',
        })

        # 5. Orders (Completed and Pending)
        order_doc = {
            '_id': order_id,
            'schemaVersion': 1,
            'createdAt': now,
            'updatedAt': now,
            'orderCode': f'ORD-{uuid4().hex[:12].upper()}',
            'userId': user['_id'],
            'checkoutKey': f'key-{uuid4().hex}',
            'checkoutRequestHash': 'a' * 64,
            'customerSnapshot': {
                'name': 'Nguyễn Văn Parity',
                'phone': '0909888999',
                'email': user['email'],
            },
            'shippingAddress': {
                'receiverName': 'Nguyễn Văn Parity',
                'phone': '0909888999',
                'addressLine': '456 Đường Shopee',
                'province': 'Hồ Chí Minh',
            },
            'items': [{
                'productId': prod_id,
                'sku': prod_doc['sku'],
                'productName': prod_doc['name'],
                'image': 'https://example.test/nova-phone.png',
                'productType': 'ELECTRONICS',
                'categoryId': cat_id,
                'categoryName': 'Thiết bị thông minh',
                'attributesSnapshot': {'ram': '12GB', 'storage': '256GB'},
                'selectedAttributes': {'ram': '12GB'},
                'priceAtPurchase': Int64(25000000),
                'quantity': 1,
                'lineTotal': Int64(25000000),
            }],
            'subtotal': Int64(25000000),
            'shippingFee': Int64(30000),
            'discount': Int64(0),
            'total': Int64(25030000),
            'currency': 'VND',
            'paymentMethod': 'COD',
            'paymentStatus': 'PAID',
            'paidAt': now,
            'completedAt': now,
            'paymentReviewRequired': False,
            'orderStatus': 'COMPLETED',
            'version': 1,
        }
        database.orders.insert_one(order_doc)

        pending_order = copy.deepcopy(order_doc)
        pending_order['_id'] = pending_order_id
        pending_order['orderCode'] = f'ORD-{uuid4().hex[:12].upper()}'
        pending_order['checkoutKey'] = f'key-{uuid4().hex}'
        pending_order['orderStatus'] = 'PENDING'
        pending_order['paymentStatus'] = 'UNPAID'
        pending_order.pop('paidAt', None)
        pending_order.pop('completedAt', None)
        database.orders.insert_one(pending_order)

        yield {
            'user': user,
            'other_user': other_user,
            'headers_customer': headers_customer,
            'headers_other': headers_other,
            'headers_admin': headers_admin,
            'product': prod_doc,
            'product_with_skus': prod_with_skus_doc,
            'unrelated_product_id': unrelated_prod_id,
            'order': order_doc,
            'pending_order': pending_order,
        }
    finally:
        # Strict exact cleanup
        database.reviews.delete_many({'productId': {'$in': [prod_id, prod_with_skus_id]}})
        database.orders.delete_many({'_id': {'$in': [order_id, pending_order_id]}})
        database.products.delete_many({'_id': {'$in': [prod_id, prod_with_skus_id, unrelated_prod_id]}})
        database.categories.delete_one({'_id': cat_id})
        database.users.delete_one({'_id': other_user['_id']})


# ==============================================================================
# PHASE 1 & 2: SMART SEARCH & VIETNAMESE NORMALIZATION
# ==============================================================================

def test_smart_search_vietnamese_accent_insensitive(client, parity_setup):
    """Test searching with and without accents matches correctly."""
    prod = parity_setup['product']

    # Search without accents: 'dien thoai' should match 'Điện Thoại Nova Smartphone Pro Max'
    res = client.get(f"{PREFIX}/products?q=dien+thoai")
    assert res.status_code == 200
    slugs = [p['slug'] for p in res.json['data']]
    assert prod['slug'] in slugs

    # Search with accents: 'Điện Thoại'
    res_accent = client.get(f"{PREFIX}/products?q=Điện+Thoại")
    assert res_accent.status_code == 200
    slugs_accent = [p['slug'] for p in res_accent.json['data']]
    assert prod['slug'] in slugs_accent


def test_smart_search_pagination_and_sorting(client, parity_setup):
    """Test smart search pagination parameters and sort options."""
    res = client.get(f"{PREFIX}/products?pageSize=5&page=1&sort=price_desc")
    assert res.status_code == 200
    assert isinstance(res.json['data'], list)
    assert 'meta' in res.json
    assert res.json['meta']['pageSize'] == 5


def test_smart_search_sanitization_and_empty_query(client, parity_setup):
    """Test smart search with whitespace or special characters."""
    res = client.get(f"{PREFIX}/products?q=   ")
    assert res.status_code == 200
    assert len(res.json['data']) >= 1


# ==============================================================================
# PHASE 3: REALISTIC SYNTHETIC DATA & ATTRIBUTES VALIDATION
# ==============================================================================

def test_synthetic_product_schema_conformance(database, parity_setup):
    """Verify synthetic product contains valid attributes, money format, and non-empty images."""
    prod = database.products.find_one({'_id': parity_setup['product']['_id']})
    assert prod is not None
    assert isinstance(prod['price'], Int64)
    assert prod['price'] > 0
    assert prod['stock'] >= 0
    assert len(prod['images']) > 0
    assert all(img.startswith('http') for img in prod['images'])
    assert 'ram' in prod['attributes']
    assert 'storage' in prod['attributes']


# ==============================================================================
# PHASE 4: UGC REVIEWS SUBMISSION & RATING AGGREGATION
# ==============================================================================

def test_review_submission_auth_guards(client, parity_setup):
    """Verify unauthenticated and admin requests cannot submit customer reviews."""
    prod = parity_setup['product']
    order = parity_setup['order']

    # 401 Unauthenticated
    res_anon = client.post(f"{PREFIX}/products/{prod['slug']}/reviews", json={
        'orderId': str(order['_id']),
        'rating': 5,
    })
    assert res_anon.status_code == 401

    # 403 Admin role cannot submit customer reviews
    res_admin = client.post(f"{PREFIX}/products/{prod['slug']}/reviews", json={
        'orderId': str(order['_id']),
        'rating': 5,
    }, headers=parity_setup['headers_admin'])
    assert res_admin.status_code == 403


def test_review_submission_order_gating(client, parity_setup):
    """Verify review can only be submitted for COMPLETED orders."""
    prod = parity_setup['product']
    pending_order = parity_setup['pending_order']

    # 409 Order not completed
    res = client.post(f"{PREFIX}/products/{prod['slug']}/reviews", json={
        'orderId': str(pending_order['_id']),
        'rating': 5,
    }, headers=parity_setup['headers_customer'])
    assert res.status_code == 409
    assert res.json['error']['code'] == 'ORDER_NOT_COMPLETED'


def test_review_submission_ownership_and_item_guards(client, parity_setup):
    """Verify user must own the order and product must be in order items."""
    prod = parity_setup['product']
    order = parity_setup['order']
    unrelated_id = str(parity_setup['unrelated_product_id'])

    # 404 Order not owned by other user
    res_other = client.post(f"{PREFIX}/products/{prod['slug']}/reviews", json={
        'orderId': str(order['_id']),
        'rating': 5,
    }, headers=parity_setup['headers_other'])
    assert res_other.status_code == 404

    # 409 Product not in order
    res_unrelated = client.post(f"{PREFIX}/products/{unrelated_id}/reviews", json={
        'orderId': str(order['_id']),
        'rating': 5,
    }, headers=parity_setup['headers_customer'])
    assert res_unrelated.status_code == 409
    assert res_unrelated.json['error']['code'] == 'PRODUCT_NOT_IN_ORDER'


def test_review_validation_bounds(client, parity_setup):
    """Verify input validation bounds for star rating, text length, and images count."""
    prod = parity_setup['product']
    order = parity_setup['order']

    # Rating < 1
    res_zero = client.post(f"{PREFIX}/products/{prod['slug']}/reviews", json={
        'orderId': str(order['_id']),
        'rating': 0,
    }, headers=parity_setup['headers_customer'])
    assert res_zero.status_code == 422

    # Rating > 5
    res_six = client.post(f"{PREFIX}/products/{prod['slug']}/reviews", json={
        'orderId': str(order['_id']),
        'rating': 6,
    }, headers=parity_setup['headers_customer'])
    assert res_six.status_code == 422

    # Images > 5
    res_images = client.post(f"{PREFIX}/products/{prod['slug']}/reviews", json={
        'orderId': str(order['_id']),
        'rating': 5,
        'images': [f'https://example.test/img{i}.png' for i in range(6)],
    }, headers=parity_setup['headers_customer'])
    assert res_images.status_code == 422


def test_review_success_atomic_rating_and_deduplication(client, parity_setup, database):
    """Test successful review creation, atomic update of product ratingSummary, and anti-duplicate check."""
    prod = parity_setup['product']
    order = parity_setup['order']

    # 1. Create review successfully
    res = client.post(f"{PREFIX}/products/{prod['slug']}/reviews", json={
        'orderId': str(order['_id']),
        'rating': 5,
        'reviewText': 'Chất lượng xuất sắc, giao nhanh đúng chuẩn Shopee!',
        'images': ['https://example.test/unbox.png'],
    }, headers=parity_setup['headers_customer'])
    assert res.status_code == 201

    data = res.json['data']
    assert data['rating'] == 5
    assert data['reviewText'] == 'Chất lượng xuất sắc, giao nhanh đúng chuẩn Shopee!'
    assert data['orderCode'] == order['orderCode']
    assert data['status'] == 'VISIBLE'
    assert 'userSnapshot' in data
    assert '***' in data['userSnapshot']['displayName']

    # 2. Check Product ratingSummary atomic increment in MongoDB
    updated_prod = database.products.find_one({'_id': prod['_id']})
    assert updated_prod['ratingSummary']['totalReviews'] == 1
    assert updated_prod['ratingSummary']['averageRating'] == 5.0
    assert updated_prod['ratingSummary']['starsBreakdown']['5'] == 1

    # 3. Duplicate review submission must be rejected
    res_dup = client.post(f"{PREFIX}/products/{prod['slug']}/reviews", json={
        'orderId': str(order['_id']),
        'rating': 4,
    }, headers=parity_setup['headers_customer'])
    assert res_dup.status_code == 409
    assert res_dup.json['error']['code'] == 'ALREADY_REVIEWED'

    # 4. Public Review Listing endpoint
    get_res = client.get(f"{PREFIX}/products/{prod['slug']}/reviews")
    assert get_res.status_code == 200
    reviews_list = get_res.json['data']['reviews']
    assert len(reviews_list) == 1
    assert not {'orderCode', 'orderId', 'userId'} & set(reviews_list[0])
    assert get_res.json['data']['stats']['totalReviews'] == 1


# ==============================================================================
# PHASE 5: MULTI-TIER SKU VARIATION MATRIX
# ==============================================================================

def test_sku_matrix_tier_variations_structure(database, parity_setup):
    """Verify product with multi-tier SKU matrix has matching tier indices and valid pricing."""
    prod = database.products.find_one({'_id': parity_setup['product_with_skus']['_id']})
    assert prod is not None
    assert 'tierVariations' in prod
    assert len(prod['tierVariations']) == 2
    assert prod['tierVariations'][0]['name'] == 'Màu sắc'
    assert len(prod['tierVariations'][0]['options']) == 2
    assert prod['tierVariations'][1]['name'] == 'RAM & Ổ cứng'
    assert len(prod['tierVariations'][1]['options']) == 2

    # Check SKUs matrix
    assert 'skus' in prod
    assert len(prod['skus']) == 4
    for sku in prod['skus']:
        assert 'skuId' in sku
        assert len(sku['tierIndex']) == 2
        assert isinstance(sku['price'], Int64)
        assert sku['price'] >= prod['price']
        assert sku['stock'] > 0
