from collections import Counter
from app.services.product_selection import resolve_selection
"""Signed quotes and atomic COD/VNPAY checkout; provider URL only after commit."""
import hashlib
import re
from datetime import datetime, timedelta, timezone
import jwt
from bson import ObjectId
from bson.int64 import Int64
from flask import current_app
from pymongo.errors import DuplicateKeyError
from app.errors import AuthenticationError, ConflictError, NotFoundError, ServiceUnavailableError, ValidationError
from app.repositories.cart_repository import CartRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.user_repository import UserRepository
from app.schemas.order_schema import order_response
from app.services.catalog_transaction import catalog_transaction
from app.services.commerce_pricing import canonical_hash, resolve_cart, snapshot_items
from app.utils.serialization import to_api
from app.services.payment_service import PaymentService
from app.services.coupon_service import require_coupon, allocate_discount

ADDRESS_FIELDS = ('receiverName', 'phone', 'addressLine', 'province', 'ward', 'district')


def quote_key():
    # Domain separation prevents a checkout quote from being an access JWT.
    return hashlib.sha256(('checkout-quote-v1\0' + current_app.config['JWT_SECRET']).encode()).digest()


def sign_quote(bindings, expires_at):
    return jwt.encode({**bindings, 'exp': int(expires_at.timestamp()), 'aud': 'checkout-quote-v1'},
                      quote_key(), algorithm='HS256')


def read_quote(token):
    try:
        return jwt.decode(token, quote_key(), algorithms=['HS256'], audience='checkout-quote-v1',
                          options={'require': ['exp', 'aud', 'userId', 'cartVersion', 'addressId',
                                               'addressHash', 'paymentMethod', 'pricingHash'], 'strict_aud': True})
    except jwt.ExpiredSignatureError:
        raise ConflictError(code='QUOTE_EXPIRED') from None
    except jwt.InvalidTokenError:
        raise ValidationError(details=[{'field': 'quoteToken', 'reason': 'Báo giá không hợp lệ'}]) from None


class CheckoutService:
    def __init__(self):
        self.carts = CartRepository()
        self.users = UserRepository()
        self.products = ProductRepository()
        self.categories = CategoryRepository()
        self.orders = OrderRepository()

    def payment_available(self, method):
        if method == 'VNPAY':
            PaymentService().provider.require_config(creation=True)

    def current(self, identity, address_id, method, session=None, cart_version=None):
        self.payment_available(method)
        user = self.users.find_checkout_user(identity, session)
        if user is None:
            raise AuthenticationError()
        address = next((a for a in user['addresses'] if a['_id'] == address_id), None)
        if address is None:
            raise NotFoundError()
        shipping_address = {key: address[key] for key in ADDRESS_FIELDS if key in address}
        if not re.fullmatch(r'\+?[0-9]{8,15}', user.get('phone', '')):
            raise ValidationError(details=[{'field': 'phone', 'reason': 'Cần số điện thoại hồ sơ hợp lệ trước checkout'}])
        cart = self.carts.find(identity['_id'], session)
        if cart_version is not None and (cart['version'] if cart else 0) != cart_version:
            raise ConflictError(code='CART_CHANGED')
        if not cart or not cart['items']:
            raise ConflictError(code='CART_EMPTY')
        if cart['version'] >= 2147483647:
            raise ConflictError(code='VERSION_LIMIT')
        response, products, categories, quantities = resolve_cart(cart, session)
        if response['issues']:
            codes = {code for issue in response['issues'] for code in issue['codes']}
            code = ('STOCK_CONFLICT' if 'STOCK_CONFLICT' in codes else
                    'PRICE_CHANGED' if 'SELECTION_CHANGED' in codes else 'PRODUCT_UNAVAILABLE')
            raise ConflictError(code=code, details=response['issues'])
        require_coupon(response)
        items = snapshot_items(cart, products, categories)
        subtotal = sum(int(item['lineTotal']) for item in items)
        fee = current_app.config['SHIPPING_FEE_VND']
        discount = response['discount']
        total = subtotal - discount + fee
        if total > (9999999999 if method == 'VNPAY' else 5000000000000):
            raise ValidationError(details=[{'field': 'total', 'reason': 'Tổng tiền vượt giới hạn'}])
        pricing = {'items': items, 'subtotal': subtotal, 'shippingFee': fee, 'discount': discount,
                   'total': total, 'currency': 'VND'}
        if response['coupon']:
            pricing['coupon'] = response['coupon']
            allocate_discount(items, discount)
        bindings = {'userId': str(identity['_id']), 'cartVersion': cart['version'],
                    'addressId': str(address_id), 'addressHash': canonical_hash(shipping_address),
                    'paymentMethod': method, 'pricingHash': canonical_hash(to_api(pricing))}
        return user, shipping_address, cart, products, quantities, pricing, bindings

    def quote(self, identity, address_id, method):
        *_, pricing, bindings = self.current(identity, address_id, method)
        expires = datetime.fromtimestamp(int(datetime.now(timezone.utc).timestamp()), timezone.utc) + timedelta(
            seconds=current_app.config['QUOTE_TTL_SECONDS'])
        return {**pricing, 'cartVersion': bindings['cartVersion'], 'quoteToken': sign_quote(bindings, expires),
                'expiresAt': expires, 'issues': []}

    def replay(self, existing, request_hash):
        if existing['checkoutRequestHash'] != request_hash:
            raise ConflictError(code='IDEMPOTENCY_CONFLICT')
        return self.result(existing), False

    def result(self, order):
        payment = {'method': order['paymentMethod']}
        if order['paymentMethod'] == 'VNPAY':
            payment = PaymentService().checkout_result(order)
        return {'order': order_response(order), 'payment': payment}

    def create(self, identity, payload, key, address_id, client_ip='127.0.0.1'):
        request_hash = canonical_hash(payload)
        existing = self.orders.replay(identity['_id'], key)
        if existing:
            return self.replay(existing, request_hash)
        self.payment_available(payload['paymentMethod'])
        # Stable identity/time across retry; callback has only DB side effects.
        order_id = ObjectId()
        attempt_id = ObjectId()
        now = datetime.now(timezone.utc)

        def write(session):
            existing = self.orders.replay(identity['_id'], key, session)
            if existing:
                if existing['checkoutRequestHash'] != request_hash:
                    raise ConflictError(code='IDEMPOTENCY_CONFLICT')
                return existing, False
            confirmed = read_quote(payload['quoteToken'])
            if any(confirmed[field] != value for field, value in {
                'userId': str(identity['_id']), 'cartVersion': payload['cartVersion'],
                'addressId': str(address_id), 'paymentMethod': payload['paymentMethod'],
            }.items()):
                raise ConflictError(code='QUOTE_CHANGED')
            user, address, cart, products, quantities, pricing, bindings = self.current(
                identity, address_id, payload['paymentMethod'], session, payload['cartVersion'])
            if bindings['addressHash'] != confirmed['addressHash']:
                raise ConflictError(code='QUOTE_CHANGED')
            if bindings['pricingHash'] != confirmed['pricingHash']:
                raise ConflictError(code='PRICE_CHANGED')
            # Lock each depended-on Category once, consistently ordered to bound contention.
            for category_id in sorted({p['categoryId'] for p in products.values()}):
                product_type = next(p['productType'] for p in products.values() if p['categoryId'] == category_id)
                if self.categories.guard_active(category_id, product_type, now, session) is None:
                    raise ConflictError(code='CATEGORY_UNAVAILABLE')
            for product_id in sorted(quantities):
                product = products[product_id]
                sku_counts = Counter()
                if product.get('tierVariations'):
                    for line in cart['items']:
                        if line['productId'] == product_id:
                            sku_counts[resolve_selection(product, line['selectedAttributes'])[1]['skuId']] += line['quantity']
                extra = {'sku_quantities': sku_counts} if sku_counts else {}
                if not self.products.decrement_stock(product, quantities[product_id], now, session, **extra):
                    raise ConflictError(code='STOCK_CONFLICT')
            order = {'_id': order_id, 'schemaVersion': 1, 'createdAt': now, 'updatedAt': now,
                     'orderCode': 'ORD-' + str(order_id).upper(), 'userId': identity['_id'],
                     'checkoutKey': key, 'checkoutRequestHash': request_hash,
                     'customerSnapshot': {field: user[field] for field in ('name', 'phone', 'email')},
                     'shippingAddress': address, **pricing,
                     'paymentMethod': payload['paymentMethod'],
                     'paymentStatus': 'PENDING' if payload['paymentMethod'] == 'VNPAY' else 'UNPAID', 'paymentReviewRequired': False,
                     'orderStatus': 'PENDING', 'version': 1}
            for field in ('subtotal', 'shippingFee', 'discount', 'total'):
                order[field] = Int64(order[field])
            if 'coupon' in order:
                for field in ('minSubtotal', 'maxDiscount'):
                    order['coupon'][field] = Int64(order['coupon'][field])
            if order['paymentMethod'] == 'VNPAY':
                order['paymentExpiresAt'] = now + timedelta(minutes=current_app.config['PAYMENT_HOLD_MINUTES'])
            self.orders.insert(order, session)
            if order['paymentMethod'] == 'VNPAY':
                PaymentService().initial_attempt(order, client_ip, now, attempt_id, session)
            if self.carts.replace_items(identity['_id'], cart['version'], [], now, session) is None:
                raise ConflictError(code='CART_CHANGED')
            return order, True

        try:
            order, created = catalog_transaction(write)
            return self.result(order), created
        except DuplicateKeyError:
            existing = self.orders.replay(identity['_id'], key)
            if existing:
                return self.replay(existing, request_hash)
            raise
