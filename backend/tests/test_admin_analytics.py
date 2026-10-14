"""PHASE06B: real MongoDB Admin lifecycle, deterministic reports and races."""
import copy
import io
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier, local
from uuid import uuid4
import pytest
from bson import ObjectId
from bson.int64 import Int64
from pymongo.errors import WriteError, ServerSelectionTimeoutError
from app.auth.tokens import create_access_token
from app.repositories.dashboard_repository import DashboardRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.schemas.dashboard_schema import ReportWindow
from app.services.dashboard_service import DashboardService, safe_report
from app.errors import ServiceUnavailableError
from app.utils.logging import SafeJSONFormatter

BASE = '/api/v1'
START = datetime(2026, 8, 31, 17, tzinfo=timezone.utc)
END = datetime(2026, 9, 30, 17, tzinfo=timezone.utc)
WINDOW = {'from': '2026-08-31T17:00:00Z', 'to': '2026-09-30T17:00:00Z'}
REPORTS = ('summary', 'revenue', 'top-products', 'category-revenue', 'order-status')
pytestmark = pytest.mark.integration


@pytest.fixture
def scenario(app, client, identities, database):
    ids, products = [], []
    template = database.client.ecommerce_dev.orders.find_one({'paymentMethod': 'COD'})
    product_template = database.client.ecommerce_dev.products.find_one({'productType': 'ELECTRONICS'})
    category_ids = [ObjectId(), ObjectId()]
    headers = {}
    with app.app_context():
        for role in ('customer', 'admin'):
            headers[role] = {'Authorization': 'Bearer '+create_access_token(identities[role])}

    def product():
        p = copy.deepcopy(product_template)
        p.update(_id=ObjectId(), sku='TEST-'+uuid4().hex.upper(), slug='test-'+uuid4().hex,
                 price=Int64(12000000), stock=10, version=1)
        products.append(p['_id'])
        database.products.insert_one(p)
        return p['_id']

    def item(pid, quantity=1, price=100, category=0, name='Snapshot product', category_name='Snapshot category'):
        value = copy.deepcopy(template['items'][0])
        value.update(productId=pid, productName=name, quantity=quantity, priceAtPurchase=Int64(price),
                     lineTotal=Int64(quantity*price), categoryId=category_ids[category], categoryName=category_name)
        return value

    def order(status='PENDING', method='COD', payment=None, created=None, completed=None, items=None, **overrides):
        document = copy.deepcopy(template)
        for field in ('completedAt', 'paidAt', 'cancelledAt', 'stockReleasedAt', 'expiredAt', 'paymentExpiresAt'):
            document.pop(field, None)
        created = created or START + timedelta(hours=1)
        payment = payment or ('PAID' if status == 'COMPLETED' or method == 'VNPAY' and status in {'CONFIRMED', 'SHIPPING'}
                             else 'UNPAID' if method == 'COD' else 'FAILED' if status in {'CANCELLED', 'EXPIRED'} else 'PENDING')
        items = items or [item(product())]
        subtotal = sum(int(i['lineTotal']) for i in items)
        document.update(_id=ObjectId(), userId=identities['customer']['_id'],
            orderCode='TEST-'+uuid4().hex.upper(), checkoutKey=uuid4().hex, checkoutRequestHash='a'*64,
            createdAt=created, updatedAt=completed or created, version=1, orderStatus=status,
            paymentMethod=method, paymentStatus=payment, paymentReviewRequired=payment == 'REVIEW_REQUIRED',
            items=items, subtotal=Int64(subtotal), shippingFee=Int64(30000), discount=Int64(0), total=Int64(subtotal+30000))
        if method == 'VNPAY':
            document['paymentExpiresAt'] = created+timedelta(minutes=15)
        if payment in {'PAID', 'REVIEW_REQUIRED'}:
            document['paidAt'] = created+timedelta(minutes=1)
        if status == 'COMPLETED':
            document['completedAt'] = completed or created+timedelta(hours=1)
        if status in {'CANCELLED', 'EXPIRED'}:
            document['cancelledAt' if status == 'CANCELLED' else 'expiredAt'] = created+timedelta(minutes=20)
            document['stockReleasedAt'] = created+timedelta(minutes=20)
        document.update(overrides)
        ids.append(document['_id'])
        database.orders.insert_one(document)
        return document

    def call(method, path, payload=None, who='admin', status=200, query=None, test_client=None):
        response = (test_client or client).open(BASE+path, method=method, json=payload,
            headers=headers.get(who, {}), query_string=query)
        assert response.status_code == status, response.json
        if response.json:
            assert response.headers['X-Request-ID'] == response.json['meta']['requestId']
            assert not any(secret in response.text for secret in ('passwordHash', 'tokenVersion', 'checkoutKey', 'checkoutRequestHash', '$oid', '$date'))
        return response

    def action(document, action, version=None, status=200, who='admin', test_client=None):
        return call('POST', f"/admin/orders/{document['_id']}/{action}",
                    {'expectedVersion': document['version'] if version is None else version}, who, status, test_client=test_client)

    yield {'application': app, 'database': database, 'order': order, 'product': product, 'item': item, 'call': call, 'action': action,
           'headers': headers, 'categoryIds': category_ids, 'identities': identities}
    database.orders.delete_many({'_id': {'$in': ids}})
    database.products.delete_many({'_id': {'$in': products}})


def test_admin_cod_workflow_atomic_payment_timestamps_and_retry(scenario, database):
    s = scenario
    order = s['order']()
    original = copy.deepcopy(order)
    detail = s['call']('GET', '/admin/orders/'+str(order['_id'])).json['data']
    assert detail['allowedActions'] == ['confirm', 'cancel']
    for version, action, target in [(1, 'confirm', 'CONFIRMED'), (2, 'ship', 'SHIPPING'), (3, 'complete', 'COMPLETED')]:
        result = s['action'](order, action, version).json['data']
        assert result['orderStatus'] == target and result['version'] == version+1
    stored = database.orders.find_one({'_id': order['_id']})
    assert stored['completedAt'] == stored['paidAt'] == stored['updatedAt']
    assert stored['completedAt'] >= original['createdAt'] and stored['paymentStatus'] == 'PAID'
    for field in ('items', 'customerSnapshot', 'shippingAddress', 'subtotal', 'shippingFee', 'discount', 'total'):
        assert stored[field] == original[field]
    assert result['allowedActions'] == []
    assert s['action'](order, 'complete', 1).json['data'] == result
    assert database.orders.find_one({'_id': order['_id']}) == stored
    s['action'](order, 'confirm', stored['version'], 409)
    s['action'](order, 'cancel', stored['version'], 409)


def test_cod_completion_changes_revenue_by_subtotal_only(scenario):
    s = scenario
    now = datetime.now(timezone.utc)
    query = {'from': (now-timedelta(days=1)).isoformat(), 'to': (now+timedelta(days=1)).isoformat()}
    order = s['order']('SHIPPING', created=now-timedelta(hours=2))
    before = s['call']('GET', '/admin/dashboard/summary', query=query).json['data']
    assert before['totalRevenue'] == 0
    s['action'](order, 'complete')
    after = s['call']('GET', '/admin/dashboard/summary', query=query).json['data']
    assert after['totalRevenue']-before['totalRevenue'] == int(order['subtotal'])
    assert after['totalProductsSold'] == 1 and after['totalOrders'] == 1


@pytest.mark.parametrize('source,action,valid', [
    ('PENDING', 'confirm', True), ('PENDING', 'ship', False), ('PENDING', 'complete', False),
    ('CONFIRMED', 'confirm', False), ('CONFIRMED', 'ship', True), ('CONFIRMED', 'complete', False),
    ('SHIPPING', 'confirm', False), ('SHIPPING', 'ship', False), ('SHIPPING', 'complete', True),
    ('CANCELLED', 'confirm', False), ('CANCELLED', 'ship', False), ('CANCELLED', 'complete', False),
    ('COMPLETED', 'ship', False), ('COMPLETED', 'confirm', False), ('COMPLETED', 'complete', True),
])
def test_cod_transition_matrix(scenario, database, source, action, valid):
    order = scenario['order'](source)
    before = database.orders.find_one({'_id': order['_id']})
    scenario['action'](order, action, status=200 if valid else 409)
    if not valid:
        assert database.orders.find_one({'_id': order['_id']}) == before


@pytest.mark.parametrize('source,action,payment,valid', [
    ('PENDING', 'confirm', 'PENDING', False), ('PENDING', 'confirm', 'PAID', False),
    ('CONFIRMED', 'ship', 'PAID', True), ('SHIPPING', 'complete', 'PAID', True),
    ('PENDING', 'cancel', 'PENDING', True), ('PENDING', 'cancel', 'FAILED', True),
    ('CONFIRMED', 'cancel', 'PAID', False), ('SHIPPING', 'cancel', 'PAID', False),
    ('CANCELLED', 'complete', 'REVIEW_REQUIRED', False), ('EXPIRED', 'confirm', 'FAILED', False),
])
def test_vnpay_management_never_fabricates_paid(scenario, database, source, action, payment, valid):
    if source == 'PENDING' and payment == 'PAID':
        with pytest.raises(WriteError) as caught:
            scenario['order'](source, 'VNPAY', payment)
        assert caught.value.code == 121
        return
    order = scenario['order'](source, 'VNPAY', payment)
    before = database.orders.find_one({'_id': order['_id']})
    scenario['action'](order, action, status=200 if valid else 409)
    after = database.orders.find_one({'_id': order['_id']})
    if valid and action == 'complete':
        assert after['paidAt'] == before['paidAt'] and after['paymentStatus'] == 'PAID'
        assert after['completedAt'] > before['paidAt']
    if not valid:
        assert after == before


def test_admin_list_filters_facets_pagination_and_unrestricted_owner(scenario):
    s = scenario
    pending = s['order']()
    s['order']('COMPLETED', created=START+timedelta(days=2))
    s['order']('CONFIRMED', 'VNPAY', created=START+timedelta(days=3))
    listing = s['call']('GET', '/admin/orders', query={'pageSize': '1'}).json
    assert listing['meta']['total'] == 3 and listing['meta']['totalPages'] == 3
    assert len(listing['data']) == 1 and listing['data'][0]['orderStatus'] == 'CONFIRMED'
    assert not any(key in listing['data'][0] for key in ('items', 'customerSnapshot', 'shippingAddress'))
    filters = {'status': 'PENDING', 'paymentStatus': 'UNPAID', 'orderCode': pending['orderCode'], **WINDOW}
    filtered = s['call']('GET', '/admin/orders', query=filters).json
    assert filtered['meta']['total'] == 1 and filtered['data'][0]['id'] == str(pending['_id'])
    detail = s['call']('GET', '/admin/orders/'+str(pending['_id'])).json['data']
    assert detail['userId'] == str(s['identities']['customer']['_id'])
    assert detail['items'][0]['priceAtPurchase'] == 100
    empty = s['call']('GET', '/admin/orders', query={'orderCode': 'NOT-FOUND'}).json
    assert empty['data'] == [] and empty['meta']['totalPages'] == 0
    assert s['call']('GET', '/admin/orders', query={'page': '100'}).json['data'] == []


@pytest.mark.parametrize('query,status', [({'status': 'PROCESSING'}, 422), ({'orderStatus': 'PENDING'}, 422),
    ({'paymentStatus': 'OTHER'}, 422), ({'paymentMethod': 'COD'}, 422), ({'email': 'x'}, 422),
    ({'sort': 'oldest'}, 422), ({'orderCode': '.*'}, 422), ({'orderCode': 'x'*65}, 422),
    ({'from': '2026-09-01'}, 422), ({'from': WINDOW['to'], 'to': WINDOW['from']}, 422),
    ({'page': 'bad'}, 400), ({'pageSize': '101'}, 422), ({'$where': 'bad'}, 422),
    ([('status', 'PENDING'), ('status', 'CONFIRMED')], 422)])
def test_admin_filters_reject_invalid_injection_and_uncontracted_fields(scenario, query, status):
    scenario['call']('GET', '/admin/orders', query=query, status=status)


@pytest.mark.parametrize('patch', [{'expectedVersion': True}, {'expectedVersion': 1.0}, {'expectedVersion': 0},
    {'expectedVersion': 2147483648}, {'completedAt': WINDOW['from']}, {'paymentStatus': 'PAID'},
    {'orderStatus': 'COMPLETED'}, {'items': []}, {'total': 1}, {'userId': str(ObjectId())}])
def test_action_body_allowlist(scenario, patch):
    order = scenario['order']()
    scenario['call']('POST', f"/admin/orders/{order['_id']}/confirm", {'expectedVersion': 1, **patch}, status=422)


def test_admin_missing_bad_ids_unknown_queries_and_stale(scenario):
    s = scenario
    s['call']('GET', '/admin/orders/bad', status=400)
    s['call']('GET', '/admin/orders/'+str(ObjectId()), status=404)
    s['call']('POST', '/admin/orders/'+str(ObjectId())+'/confirm', {'expectedVersion': 1}, status=404)
    order = s['order']()
    s['action'](order, 'confirm', 2, 409)
    s['call']('GET', '/admin/orders/'+str(order['_id']), query={'q': 'bad'}, status=422)
    s['call']('POST', '/admin/orders/'+str(order['_id'])+'/confirm', {}, status=422)
    s['call']('POST', '/admin/orders/'+str(order['_id'])+'/confirm', {'expectedVersion': 1}, query={'q': 'bad'}, status=422)
    s['call']('PATCH', '/admin/orders/'+str(order['_id']), {'orderStatus': 'PENDING'}, status=405)


ADMIN_ROUTES = [('GET', '/admin/orders'), ('GET', '/admin/orders/{id}'),
    *[('POST', '/admin/orders/{id}/'+action) for action in ('confirm', 'ship', 'complete', 'cancel')],
    *[('GET', '/admin/dashboard/'+name) for name in REPORTS]]


@pytest.mark.parametrize('method,path', ADMIN_ROUTES)
def test_admin_endpoint_role_matrix(scenario, method, path):
    path = path.format(id=ObjectId())
    payload = {'expectedVersion': 1} if method == 'POST' else None
    scenario['call'](method, path, payload, who='guest', status=401)
    scenario['call'](method, path, payload, who='customer', status=403)


@pytest.fixture
def metrics(scenario):
    s = scenario
    p1, p2, p3 = s['product'](), s['product'](), s['product']()
    # Fixture: day1 250/3units; day2 200/5units; total450/8 units.
    first = s['order']('COMPLETED', completed=START+timedelta(hours=8),
        items=[s['item'](p1, 2, 100, name='Old snapshot'), s['item'](p2, 1, 50, 1)])
    second = s['order']('COMPLETED', 'VNPAY', created=START-timedelta(days=1), completed=START+timedelta(days=1, hours=8),
        items=[s['item'](p1, 1, 100, name='Latest snapshot'), s['item'](p3, 4, 25, 1)])
    s['order']('SHIPPING', 'VNPAY', 'PAID')
    s['order']('CANCELLED')
    s['order']('EXPIRED', 'VNPAY')
    s['order']('PENDING')
    return {'p1': p1, 'p2': p2, 'p3': p3, 'orders': [first, second], 's': s}


def test_summary_exact_revenue_date_bases_shipping_and_units(metrics):
    data = metrics['s']['call']('GET', '/admin/dashboard/summary', query=WINDOW).json['data']
    assert data['totalRevenue'] == 450 and data['totalProductsSold'] == 8
    assert data['totalOrders'] == 5
    assert data['totalCustomers'] == metrics['s']['database'].users.count_documents({'role': 'CUSTOMER'})
    assert data['currency'] == 'VND' and data['timezone'] == 'Asia/Ho_Chi_Minh'
    assert data['from'] == WINDOW['from'].replace('Z', '.000Z')
    assert data['revenueBasis'] == 'PAID_COMPLETED_MERCHANDISE' and data['fetchedAt'].endswith('Z')


@pytest.mark.parametrize('interval', ['day', 'month'])
def test_revenue_day_month_timezone_empty_buckets(metrics, interval):
    data = metrics['s']['call']('GET', '/admin/dashboard/revenue', query={**WINDOW, 'interval': interval}).json['data']
    assert data['interval'] == interval
    series = data['series']
    if interval == 'day':
        assert len(series) == 30
        assert series[:2] == [{'bucket': '2026-09-01', 'revenue': 250, 'orders': 1}, {'bucket': '2026-09-02', 'revenue': 200, 'orders': 1}]
        assert series[2:] == [{'bucket': f'2026-09-{day:02}', 'revenue': 0, 'orders': 0} for day in range(3, 31)]
    else:
        assert series == [{'bucket': '2026-09', 'revenue': 450, 'orders': 2}]


def test_top_products_latest_snapshot_and_category_totals(metrics, database):
    s = metrics['s']
    top = s['call']('GET', '/admin/dashboard/top-products', query=WINDOW).json['data']['items']
    assert [(x['productId'], x['quantity'], x['revenue']) for x in top] == [(str(metrics['p3']), 4, 100), (str(metrics['p1']), 3, 300), (str(metrics['p2']), 1, 50)]
    assert top[1]['productName'] == 'Latest snapshot'
    category = s['call']('GET', '/admin/dashboard/category-revenue', query=WINDOW).json['data']['items']
    assert [x['revenue'] for x in category] == [300, 150]
    assert sum(x['revenue'] for x in category) == 450
    for pid in (metrics['p1'], metrics['p2'], metrics['p3']):
        database.products.update_one({'_id': pid}, {'$set': {'price': Int64(999999999), 'name': 'Changed live product'}})
    assert s['call']('GET', '/admin/dashboard/top-products', query=WINDOW).json['data']['items'] == top
    database.products.delete_many({'_id': {'$in': [metrics['p1'], metrics['p2'], metrics['p3']]}})
    assert s['call']('GET', '/admin/dashboard/top-products', query=WINDOW).json['data']['items'] == top
    assert s['call']('GET', '/admin/dashboard/category-revenue', query=WINDOW).json['data']['items'] == category


def test_status_distribution_all_six_and_created_at_basis(metrics):
    data = metrics['s']['call']('GET', '/admin/dashboard/order-status', query=WINDOW).json['data']
    assert data['dateBasis'] == 'createdAt'
    assert data['items'] == [{'status': 'PENDING', 'count': 1}, {'status': 'CONFIRMED', 'count': 0},
        {'status': 'SHIPPING', 'count': 1}, {'status': 'COMPLETED', 'count': 1}, {'status': 'CANCELLED', 'count': 1}, {'status': 'EXPIRED', 'count': 1}]


def test_top_five_quantity_revenue_id_tiebreak_and_limit(scenario):
    s = scenario
    pids = [s['product']() for _ in range(7)]
    # same quantity: greater revenue first, same quantity/revenue: ObjectId ascending
    prices = [100, 100, 200, 300, 400, 500, 600]
    s['order']('COMPLETED', items=[s['item'](pid, 1, price) for pid, price in zip(pids, prices)])
    top = s['call']('GET', '/admin/dashboard/top-products', query=WINDOW).json['data']['items']
    assert len(top) == 5 and [x['productId'] for x in top] == [str(pids[i]) for i in (6, 5, 4, 3, 2)]
    tied = s['order']('COMPLETED', items=[s['item'](pids[0], 10, 100), s['item'](pids[1], 10, 100)])
    top = s['call']('GET', '/admin/dashboard/top-products', query=WINDOW).json['data']['items']
    assert [x['productId'] for x in top[:2]] == sorted([str(pids[0]), str(pids[1])])


@pytest.mark.parametrize('report', REPORTS)
def test_empty_reports_and_global_customer_count(scenario, report):
    data = scenario['call']('GET', '/admin/dashboard/'+report, query=WINDOW).json['data']
    if report == 'summary':
        assert [data[key] for key in ('totalRevenue', 'totalOrders', 'totalProductsSold')] == [0, 0, 0]
        assert data['totalCustomers'] == scenario['database'].users.count_documents({'role': 'CUSTOMER'})
    elif report == 'revenue':
        assert len(data['series']) == 30 and all(x['revenue'] == x['orders'] == 0 for x in data['series'])
    elif report == 'order-status':
        assert len(data['items']) == 6 and all(x['count'] == 0 for x in data['items'])
    else:
        assert data['items'] == []


@pytest.mark.parametrize('patch', [{'from': '2026-09-01'}, {'from': 'garbage'}, {'from': '2026-02-30T00:00:00Z'},
    {'from': '2026-09-01T00:00:00+07:00'}, {'from': '2026-09-01T00:00:00'},
    {'from': WINDOW['to']}, {'to': WINDOW['from']}, {'from': '2024-01-01T00:00:00Z'},
    {'interval': 'week'}, {'timezone': 'UTC'}, {'pipeline': '{}'}, {'from': '9999-01-01T00:00:00Z'}])
def test_report_range_and_injection_validation(scenario, patch):
    scenario['call']('GET', '/admin/dashboard/revenue', query={**WINDOW, **patch}, status=422)


@pytest.mark.parametrize('report', REPORTS)
def test_report_missing_and_duplicate_params(scenario, report):
    scenario['call']('GET', '/admin/dashboard/'+report, query={'from': WINDOW['from']}, status=422)
    scenario['call']('GET', '/admin/dashboard/'+report, query=[('from', WINDOW['from']), ('from', WINDOW['from']), ('to', WINDOW['to'])], status=422)
    if report != 'revenue':
        scenario['call']('GET', '/admin/dashboard/'+report, query={**WINDOW, 'interval': 'day'}, status=422)


def test_report_utc_boundary_partial_day_month_and_leap_year(scenario):
    s = scenario
    s['order']('COMPLETED', completed=START)
    s['order']('COMPLETED', completed=END)
    series = s['call']('GET', '/admin/dashboard/revenue', query={**WINDOW, 'interval': 'month'}).json['data']['series']
    assert series == [{'bucket': '2026-09', 'revenue': 100, 'orders': 1}]
    partial = {'from': '2026-09-01T16:59:59Z', 'to': '2026-09-01T17:00:01Z'}
    assert [x['bucket'] for x in s['call']('GET', '/admin/dashboard/revenue', query=partial).json['data']['series']] == ['2026-09-01', '2026-09-02']
    leap = {'from': '2024-02-28T17:00:00Z', 'to': '2024-03-01T17:00:00Z'}
    assert [x['bucket'] for x in s['call']('GET', '/admin/dashboard/revenue', query=leap).json['data']['series']] == ['2024-02-29', '2024-03-01']
    cap = {'from': '2024-01-01T00:00:00Z', 'to': '2025-01-01T00:00:00Z'}
    assert len(s['call']('GET', '/admin/dashboard/revenue', query=cap).json['data']['series']) == 367


def test_validator_rejects_illegal_payment_pairs_and_pipeline_defensively_filters(app, scenario, database):
    valid = scenario['order']('COMPLETED')
    bad = []
    for status, payment in [('COMPLETED', 'UNPAID'), ('CANCELLED', 'PAID'), ('SHIPPING', 'PAID')]:
        doc = copy.deepcopy(valid)
        doc.update(_id=ObjectId(), orderCode='BAD-'+uuid4().hex.upper(), checkoutKey=uuid4().hex,
                   orderStatus=status, paymentStatus=payment)
        with pytest.raises(WriteError) as caught:
            database.orders.insert_one(doc)
        assert caught.value.code == 121
        bad.append(doc)
    # Real MongoDB virtual documents: no bypassDocumentValidation and no corrupt persistence.
    with app.app_context():
        pipeline = DashboardRepository().pipeline('sales-summary', ReportWindow(START, END))
    result = database.command('aggregate', 1, pipeline=[{'$documents': [valid, *bad]}, *pipeline], cursor={})
    assert result['cursor']['firstBatch'] == [{'totalRevenue': 100, 'qualifiedOrders': 1, 'totalProductsSold': 1}]


def test_canonical_pipeline_binding_and_real_aggregate_calls(app, scenario, monkeypatch):
    executed = []
    original = DashboardRepository.run
    def run(self, name, window):
        pipeline = self.pipeline(name, window)
        assert not any('$lookup' in stage for stage in pipeline)
        executed.append(name)
        return original(self, name, window)
    monkeypatch.setattr(DashboardRepository, 'run', run)
    for report in REPORTS:
        scenario['call']('GET', '/admin/dashboard/'+report, query=WINDOW)
    scenario['call']('GET', '/admin/dashboard/revenue', query={**WINDOW, 'interval': 'month'})
    assert set(executed) == {'sales-summary', 'order-count', 'customer-count', 'revenue-day', 'revenue-month', 'top-products', 'category-revenue', 'order-status'}
    with app.app_context():
        repository = DashboardRepository()
        first = repository.pipeline('top-products', ReportWindow(START, END))
        required = ['$match', '$unwind', '$group', '$sort', '$limit']
        stages = [next(iter(stage)) for stage in first]
        assert all(stage in stages for stage in required) and first[-2] == {'$limit': 5}
        first[0]['$match']['orderStatus'] = 'CANCELLED'
        assert repository.pipeline('top-products', ReportWindow(START, END))[0]['$match']['orderStatus'] == 'COMPLETED'


def test_aggregation_database_failure_is_safe_503(scenario, monkeypatch):
    def fail(*args):
        raise ServerSelectionTimeoutError('private-password-hidden')
    monkeypatch.setattr(DashboardRepository, 'run', fail)
    result = scenario['call']('GET', '/admin/dashboard/summary', query=WINDOW, status=503)
    assert 'private-password' not in result.text


def test_report_safe_integer_limit():
    with pytest.raises(ServiceUnavailableError):
        safe_report({'items': [{'revenue': Int64(9007199254740992)}]})


def test_admin_cancel_shared_once_only_stock_and_customer_retry(scenario, database):
    s = scenario
    pid = s['product']()
    order = s['order'](items=[s['item'](pid, 2), s['item'](pid, 3)])
    s['action'](order, 'cancel')
    after = database.products.find_one({'_id': pid})
    assert after['stock'] == 15 and after['version'] == 2
    s['action'](order, 'cancel')
    s['call']('POST', '/orders/'+str(order['_id'])+'/cancel', {'expectedVersion': 1}, who='customer')
    assert database.products.find_one({'_id': pid}) == after


def test_admin_cancel_stock_failure_rolls_back(scenario, database, monkeypatch):
    s = scenario
    first, second = s['product'](), s['product']()
    order = s['order'](items=[s['item'](first), s['item'](second)])
    original = ProductRepository.restore_stock
    def fail_second(self, pid, *args):
        return False if pid == second else original(self, pid, *args)
    monkeypatch.setattr(ProductRepository, 'restore_stock', fail_second)
    s['action'](order, 'cancel', status=409)
    assert database.orders.find_one({'_id': order['_id']})['orderStatus'] == 'PENDING'
    assert all(database.products.find_one({'_id': pid})['stock'] == 10 for pid in (first, second))


@pytest.mark.parametrize('action,source', [('complete', 'SHIPPING'), ('cancel', 'PENDING'), ('ship', 'CONFIRMED')])
def test_concurrent_admin_actions_no_duplicate_side_effect(scenario, database, monkeypatch, action, source):
    s = scenario
    order = s['order'](source)
    barrier = Barrier(2)
    state = local()
    original = OrderRepository.find_admin
    def find(self, *args, **kwargs):
        value = original(self, *args, **kwargs)
        if not getattr(state, 'read', False):
            state.read = True
            barrier.wait(timeout=10)
        return value
    monkeypatch.setattr(OrderRepository, 'find_admin', find)
    application = s['application']
    def request(_):
        with application.test_client() as client:
            return client.post(BASE+f"/admin/orders/{order['_id']}/{action}", json={'expectedVersion': 1}, headers=s['headers']['admin']).status_code
    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = sorted(executor.map(request, range(2)))
    assert statuses == ([200, 409] if action == 'ship' else [200, 200])
    stored = database.orders.find_one({'_id': order['_id']})
    assert stored['version'] == 2
    if action == 'cancel':
        assert database.products.find_one({'_id': order['items'][0]['productId']})['stock'] == 11


def test_admin_audit_log_is_allowlisted_and_post_commit(scenario, app):
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(SafeJSONFormatter())
    app.logger.handlers = [handler]
    app.logger.setLevel(logging.INFO)
    order = scenario['order']()
    scenario['action'](order, 'confirm')
    events = [json.loads(line) for line in stream.getvalue().splitlines()]
    audit = next(x for x in events if x['event'] == 'admin.order_action')
    assert audit['previous_order_status'] == 'PENDING' and audit['order_status'] == 'CONFIRMED'
    assert audit['action'] == 'confirm' and audit['order_id'] == str(order['_id'])
    assert 'customerSnapshot' not in stream.getvalue() and 'shippingAddress' not in stream.getvalue()


def test_admin_transition_concurrent_payment_review_write_is_not_lost(scenario, database, monkeypatch):
    order = scenario['order']('SHIPPING', 'VNPAY')
    original = OrderRepository.transition_admin
    changed = [False]
    def concurrent_write(self, snapshot, *args):
        if not changed[0]:
            changed[0] = True
            database.orders.update_one({'_id': order['_id']},
                {'$set': {'paymentReviewRequired': True}, '$inc': {'version': 1}})
        return original(self, snapshot, *args)
    monkeypatch.setattr(OrderRepository, 'transition_admin', concurrent_write)
    scenario['action'](order, 'complete', status=409)
    after = database.orders.find_one({'_id': order['_id']})
    assert after['orderStatus'] == 'SHIPPING' and after['paymentReviewRequired'] is True
    assert after['version'] == 2 and 'completedAt' not in after


def test_admin_transition_version_cap_and_json_errors(scenario, client):
    order = scenario['order'](version=2147483647)
    result = scenario['action'](order, 'confirm', status=409)
    assert result.json['error']['code'] == 'VERSION_LIMIT'
    path = BASE+f"/admin/orders/{order['_id']}/confirm"
    for content, body, status in [('application/json', '{', 400), ('text/plain', '{}', 415)]:
        assert client.post(path, data=body, content_type=content, headers=scenario['headers']['admin']).status_code == status
