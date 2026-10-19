"""Real rs0 regressions for SKU invariants and atomic verified reviews."""
import copy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier, local
from uuid import uuid4
import pytest
from bson import ObjectId
from bson.int64 import Int64
from app.repositories.product_repository import ProductRepository
from app.repositories.review_repository import ReviewRepository
from app.services.payment_service import PaymentService
from test_shopee_parity import parity_setup

pytestmark = pytest.mark.integration


@pytest.fixture
def commerce(parity_setup, database):
    data = parity_setup
    try:
        yield data
    finally:
        owners = [data['user']['_id'], data['other_user']['_id']]
        database.orders.delete_many({'userId': {'$in': owners}})
        database.carts.delete_many({'userId': {'$in': owners}})


def selection(data, index=0):
    product = data['product_with_skus']
    sku = product['skus'][index]
    return {**{tier['name']: tier['options'][option] for tier, option in zip(product['tierVariations'], sku['tierIndex'])}, 'skuId': sku['skuId']}


def add(client, data, index=0, quantity=1, headers=None):
    headers = headers or data['headers_customer']
    cart = client.get('/api/v1/cart', headers=headers).json['data']
    return client.post('/api/v1/cart/items', headers=headers, json={
        'cartVersion': cart['version'], 'quantity': quantity, 'selectedAttributes': selection(data,index),
        'productId': str(data['product_with_skus']['_id'])})


def quote(client, data, headers=None, user=None):
    return client.get('/api/v1/checkout/quote', headers=headers or data['headers_customer'], query_string={
        'addressId': str((user or data['user'])['defaultAddressId']), 'paymentMethod': 'COD'}).json['data']


def checkout(client, data, q=None, headers=None, user=None):
    q = q or quote(client,data,headers,user)
    return client.post('/api/v1/orders', headers={**(headers or data['headers_customer']), 'Idempotency-Key':uuid4().hex}, json={
        'cartVersion':q['cartVersion'],'quoteToken':q['quoteToken'],
        'addressId':str((user or data['user'])['defaultAddressId']),'paymentMethod':'COD'})


@pytest.mark.parametrize('tamper', ['mismatch', 'unknown', 'extra'])
def test_sku_selection_tampering_rejected(client, commerce, tamper):
    chosen = selection(commerce, 1)
    if tamper == 'mismatch': chosen['skuId'] = commerce['product_with_skus']['skus'][0]['skuId']
    elif tamper == 'unknown': chosen['skuId'] = 'UNKNOWN'
    else: chosen['unexpected'] = 'value'
    response = client.post('/api/v1/cart/items',headers=commerce['headers_customer'],json={
        'cartVersion':0,'quantity':1,'productId':str(commerce['product_with_skus']['_id']),'selectedAttributes':chosen})
    assert response.status_code == 422


def test_different_skus_have_independent_quantity_limits(client, commerce, database):
    database.products.update_one({'_id':commerce['product_with_skus']['_id']},{'$set':{'skus.0.stock':1,'skus.1.stock':1}})
    assert add(client,commerce,0).status_code == 200
    assert add(client,commerce,1).status_code == 200
    assert add(client,commerce,0).status_code == 409


def test_admin_create_variant_roundtrip_derives_price_and_stock(client, commerce, database):
    from app.schemas.product_schema import PRODUCT_FIELDS
    source = commerce['product_with_skus']
    payload = {key: copy.deepcopy(source[key]) for key in PRODUCT_FIELDS}
    payload.update(sku='HARDEN-' + uuid4().hex[:12].upper(), slug='harden-' + uuid4().hex,
        categoryId=str(source['categoryId']), price=1, stock=0,
        tierVariations=source['tierVariations'], skus=[{**sku, 'price':int(sku['price'])} for sku in source['skus']])
    try:
        response = client.post('/api/v1/admin/products', headers=commerce['headers_admin'], json=payload)
        assert response.status_code == 201, response.json
        created = response.json['data']
        stored = database.products.find_one({'sku':payload['sku']})
        assert created['stock'] == sum(sku['stock'] for sku in source['skus'])
        assert created['price'] == min(sku['price'] for sku in source['skus'])
        assert all(isinstance(sku['price'], Int64) for sku in stored['skus'])
        assert created['tierVariations'] == source['tierVariations']
    finally:
        database.products.delete_many({'sku':payload['sku']})


@pytest.mark.parametrize('fault', ['duplicate_id', 'duplicate_combination', 'invalid_index', 'unsafe_image', 'stock_overflow'])
def test_admin_rejects_invalid_sku_matrix(client, commerce, fault):
    source = commerce['product_with_skus']
    skus = [{**sku, 'price':int(sku['price'])} for sku in source['skus']]
    if fault == 'duplicate_id': skus[1]['skuId'] = skus[0]['skuId']
    elif fault == 'duplicate_combination': skus[1]['tierIndex'] = skus[0]['tierIndex']
    elif fault == 'invalid_index': skus[0]['tierIndex'] = [99, 0]
    elif fault == 'unsafe_image': skus[0]['image'] = 'javascript:alert(1)'
    else: skus[0]['stock'] = 2147483647
    response = client.patch('/api/v1/admin/products/' + str(source['_id']), headers=commerce['headers_admin'], json={
        'expectedVersion':source['version'], 'tierVariations':source['tierVariations'], 'skus':skus})
    assert response.status_code == 422, response.json


def test_sku_decrement_cancel_once_and_snapshot(client, commerce, database):
    product=commerce['product_with_skus']; pid=product['_id']
    assert add(client,commerce,1).status_code==200
    created=checkout(client,commerce)
    assert created.status_code==201
    order=created.json['data']['order']
    saved=database.products.find_one({'_id':pid})
    assert saved['skus'][1]['stock']==4 and saved['stock']==24
    assert order['items'][0]['priceAtPurchase']==42000000
    assert order['items'][0]['selectedAttributes']['skuId']==product['skus'][1]['skuId']
    payload={'expectedVersion':saved['version'],'tierVariations':product['tierVariations'],
        'skus':[{**s,'price':int(s['price'])} for s in saved['skus']]}
    payload['skus'][1]['price']=45000000
    changed=client.patch('/api/v1/admin/products/'+str(pid),headers=commerce['headers_admin'],json=payload)
    assert changed.status_code==200,changed.json
    historical=client.get('/api/v1/orders/'+order['id'],headers=commerce['headers_customer'])
    assert historical.json['data']['items'][0]['priceAtPurchase']==42000000
    for _ in range(2):
        cancelled=client.post('/api/v1/orders/'+order['id']+'/cancel',headers=commerce['headers_customer'],json={'expectedVersion':order['version']})
        assert cancelled.status_code==200
    saved=database.products.find_one({'_id':pid})
    assert saved['skus'][1]['stock']==5 and saved['stock']==25


def test_sku_cannot_be_removed_while_order_holds_stock(client, commerce, database):
    assert add(client,commerce).status_code==200
    assert checkout(client,commerce).status_code==201
    p=database.products.find_one({'_id':commerce['product_with_skus']['_id']})
    response=client.patch('/api/v1/admin/products/'+str(p['_id']),headers=commerce['headers_admin'],json={
        'expectedVersion':p['version'],'tierVariations':[],'skus':[]})
    assert response.status_code==409 and response.json['error']['code']=='SKU_IN_USE'


def test_concurrent_sku_last_unit_only_one_checkout(app, client, commerce, database):
    pid=commerce['product_with_skus']['_id']
    database.products.update_one({'_id':pid},{'$set':{'skus.0.stock':1,'stock':16}})
    assert add(client,commerce).status_code==200
    assert add(client,commerce,headers=commerce['headers_other']).status_code==200
    q1=quote(client,commerce)
    q2=quote(client,commerce,commerce['headers_other'],commerce['other_user'])
    barrier=Barrier(2)
    def submit(other):
        barrier.wait(timeout=10)
        with app.test_client() as connection:
            return checkout(connection,commerce,q2 if other else q1,
                commerce['headers_other'] if other else commerce['headers_customer'],
                commerce['other_user'] if other else commerce['user']).status_code
    with ThreadPoolExecutor(max_workers=2) as pool: statuses=list(pool.map(submit,[False,True]))
    assert sorted(statuses)==[201,409]
    assert database.products.find_one({'_id':pid})['skus'][0]['stock']==0


def test_sku_expiry_restores_once(app, client, commerce, database):
    assert add(client,commerce).status_code==200
    order=checkout(client,commerce).json['data']['order']
    oid=ObjectId(order['id'])
    database.orders.update_one({'_id':oid},{'$set':{'paymentMethod':'VNPAY','paymentStatus':'PENDING',
        'paymentExpiresAt':datetime.now(timezone.utc)-timedelta(seconds=1)}})
    with app.app_context():
        for _ in range(2): PaymentService().expire(oid,commerce['user']['_id'])
    p=database.products.find_one({'_id':commerce['product_with_skus']['_id']})
    assert p['stock']==25 and p['skus'][0]['stock']==10


def test_review_summary_rolls_back_with_insert(client, commerce, database, monkeypatch):
    def fail(*args,**kwargs): raise RuntimeError('injected summary failure')
    monkeypatch.setattr(ProductRepository,'update_rating_summary',fail)
    response=client.post('/api/v1/products/'+commerce['product']['slug']+'/reviews',headers=commerce['headers_customer'],json={
        'orderId':str(commerce['order']['_id']),'rating':5})
    assert response.status_code==500
    assert database.reviews.count_documents({'productId':commerce['product']['_id']})==0


def test_concurrent_reviews_summary_is_exact(app, commerce, database, monkeypatch):
    second=copy.deepcopy(commerce['order'])
    second.update(_id=ObjectId(),orderCode='REVIEW-'+uuid4().hex.upper(),checkoutKey=uuid4().hex)
    database.orders.insert_one(second)
    barrier, state=Barrier(2),local()
    original=ReviewRepository.insert
    def synchronized(self,document,session=None):
        if not getattr(state,'waited',False):
            state.waited=True
            barrier.wait(timeout=10)
        return original(self,document,session)
    monkeypatch.setattr(ReviewRepository,'insert',synchronized)
    def submit(pair):
        oid,rating=pair
        with app.test_client() as client:
            return client.post('/api/v1/products/'+commerce['product']['slug']+'/reviews',headers=commerce['headers_customer'],
                json={'orderId':str(oid),'rating':rating}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses=list(pool.map(submit,[(commerce['order']['_id'],5),(second['_id'],3)]))
    assert statuses==[201,201]
    p=database.products.find_one({'_id':commerce['product']['_id']})
    assert p['ratingSummary']['totalReviews']==2 and p['ratingSummary']['averageRating']==4.0


def test_review_public_projection_pagination_and_visibility(client, commerce, database):
    response=client.post('/api/v1/products/'+commerce['product']['slug']+'/reviews',headers=commerce['headers_customer'],json={
        'orderId':str(commerce['order']['_id']),'rating':5,'reviewText':'Một đánh giá'})
    assert response.status_code==201
    feed=client.get('/api/v1/products/'+commerce['product']['slug']+'/reviews?pageSize=1&rating=5&hasComment=true')
    assert feed.status_code==200 and feed.json['meta']['total']==1
    assert not {'userId','orderId','orderCode','schemaVersion'} & set(feed.json['data']['reviews'][0])
    assert client.get('/api/v1/products/'+str(ObjectId())+'/reviews').status_code==404
    database.categories.update_one({'_id':commerce['product']['categoryId']},{'$set':{'status':'ARCHIVED'}})
    assert client.get('/api/v1/products/'+commerce['product']['slug']+'/reviews').status_code==404
