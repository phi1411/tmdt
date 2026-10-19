from app.services.product_selection import snapshot_stock_groups
"""VNPAY attempts, authoritative IPN and once-only expiry with locked states."""
from datetime import datetime, timezone
from bson import ObjectId
from bson.int64 import Int64
from flask import current_app
from pymongo.errors import DuplicateKeyError
from app.errors import ConflictError, NotFoundError, ServiceUnavailableError, ValidationError
from app.repositories.order_repository import OrderRepository
from app.repositories.payment_attempt_repository import PaymentAttemptRepository
from app.repositories.product_repository import ProductRepository
from app.services.catalog_transaction import catalog_transaction
from app.services.commerce_pricing import canonical_hash
from app.services.vnpay_provider import ProviderValidationError, VnpayProvider


class PaymentService:
    def __init__(self):
        self.orders = OrderRepository()
        self.attempts = PaymentAttemptRepository()
        self.products = ProductRepository()
        self.provider = VnpayProvider()

    def new_attempt(self, order, key, request_hash, client_ip, now, attempt_id):
        total = order['total']
        if isinstance(total, bool) or not isinstance(total, int) or not 1 <= total <= 9999999999:
            raise ValidationError(details=[{'field': 'total', 'reason': 'Tổng tiền không phù hợp VNPAY'}])
        txn_ref = 'VN' + str(attempt_id).upper()
        return {'_id': attempt_id, 'schemaVersion': 1, 'createdAt': now, 'updatedAt': now,
                'orderId': order['_id'], 'userId': order['userId'], 'attemptKey': key, 'requestHash': request_hash,
                'txnRef': txn_ref, 'provider': 'VNPAY', 'amount': Int64(total), 'currency': 'VND',
                'status': 'PENDING', 'version': 1, 'expiresAt': order['paymentExpiresAt'],
                'paymentRequest': self.provider.payment_request(order, txn_ref, client_ip, now)}

    def initial_attempt(self, order, client_ip, now, attempt_id, session):
        attempt = self.new_attempt(order, 'checkout-' + str(order['_id']),
            canonical_hash({'orderId': str(order['_id']), 'checkoutRequestHash': order['checkoutRequestHash']}),
            client_ip, now, attempt_id)
        self.attempts.insert(attempt, session)
        return attempt

    def attempt_result(self, order, attempt):
        result = {'attemptId': attempt['_id'], 'attemptStatus': attempt['status'], 'expiresAt': attempt['expiresAt']}
        payable = (attempt['status'] == 'PENDING' and order['orderStatus'] == 'PENDING' and
                   order['paymentStatus'] in {'PENDING', 'FAILED'} and not order['paymentReviewRequired'] and
                   datetime.now(timezone.utc) < attempt['expiresAt'])
        if payable:
            try:
                result['paymentUrl'] = self.provider.payment_url(attempt)
            except ServiceUnavailableError:
                result['retryRequired'] = True
        return result

    def checkout_result(self, order):
        # Replays reuse an existing attempt and its immutable request; never create another Order/attempt here.
        attempt = self.attempts.pending(order['_id']) or self.attempts.latest(order['_id'])
        result = {'method': 'VNPAY', 'expiresAt': order['paymentExpiresAt']}
        if attempt:
            result.update(self.attempt_result(order, attempt))
        else:
            result['retryRequired'] = True
        return result

    def create(self, user_id, order_id, payload, key, client_ip):
        owned = self.orders.find(user_id, order_id)
        if owned is None:
            raise NotFoundError()
        self.provider.require_config(creation=True)
        now = datetime.now(timezone.utc)
        # Expiry commits independently before refusing a new attempt on an expired hold.
        self.expire(order_id, user_id, now)
        request_hash = canonical_hash(payload)
        attempt_id = ObjectId()

        def write(session):
            order = self.orders.find(user_id, order_id, session)
            if order is None:
                raise NotFoundError()
            existing = self.attempts.replay(order_id, key, session)
            if existing:
                if existing['requestHash'] != request_hash:
                    raise ConflictError(code='IDEMPOTENCY_CONFLICT')
                return order, existing, False
            if (order['paymentMethod'] != 'VNPAY' or order['orderStatus'] != 'PENDING' or
                order['paymentStatus'] not in {'PENDING', 'FAILED'} or order['paymentReviewRequired'] or
                'stockReleasedAt' in order or now >= order['paymentExpiresAt']):
                raise ConflictError(code='INVALID_TRANSITION')
            if order['version'] != payload['expectedVersion']:
                raise ConflictError(code='ORDER_CHANGED')
            if self.attempts.pending(order_id, session):
                raise ConflictError(code='PAYMENT_ATTEMPT_PENDING')
            attempt = self.new_attempt(order, key, request_hash, client_ip, now, attempt_id)
            self.attempts.insert(attempt, session)
            changed = self.orders.patch_payment(order, {'paymentStatus': 'PENDING'}, now, session)
            return changed, attempt, True

        try:
            order, attempt, created = catalog_transaction(write)
        except DuplicateKeyError:
            order = self.orders.find(user_id, order_id)
            attempt = self.attempts.replay(order_id, key)
            if not attempt:
                raise ConflictError(code='PAYMENT_ATTEMPT_PENDING') from None
            if attempt['requestHash'] != request_hash:
                raise ConflictError(code='IDEMPOTENCY_CONFLICT') from None
            created = False
        return {**self.attempt_result(order, attempt), 'orderVersion': order['version']}, created

    def due(self, order, now):
        return (order['paymentMethod'] == 'VNPAY' and order['orderStatus'] == 'PENDING' and
                order['paymentStatus'] in {'PENDING', 'FAILED'} and now >= order['paymentExpiresAt'])

    def expire_in_session(self, order, now, session, force=False):
        eligible = (order['paymentMethod'] == 'VNPAY' and order['orderStatus'] == 'PENDING' and
                    order['paymentStatus'] in {'PENDING', 'FAILED'} and 'stockReleasedAt' not in order)
        if not eligible or (not force and not self.due(order, now)):
            return order
        changed = self.orders.patch_payment(order, {'orderStatus': 'EXPIRED', 'paymentStatus': 'FAILED',
            'expiredAt': now, 'stockReleasedAt': now}, now, session)
        quantities, sku_counts = snapshot_stock_groups(order['items'])
        for product_id in sorted(quantities):
            extra = {'sku_quantities': sku_counts[product_id]} if sku_counts.get(product_id) else {}
            if not self.products.restore_stock(product_id, quantities[product_id], now, session, **extra):
                current_app.logger.error('Stock restoration failed', extra={'event': 'payment.stock_restore_failed'})
                raise ConflictError(code='STOCK_RESTORE_FAILED')
        self.attempts.invalidate_pending(order['_id'], now, session)
        return changed

    def expire(self, order_id, user_id=None, now=None):
        now = now or datetime.now(timezone.utc)

        def write(session):
            order = self.orders.find(user_id, order_id, session) if user_id is not None else self.orders.find_payment(order_id, session)
            if order is None:
                if user_id is not None:
                    raise NotFoundError()
                return None
            return self.expire_in_session(order, now, session)
        return catalog_transaction(write)

    def expire_due(self, limit=100):
        now = datetime.now(timezone.utc)
        result = {'scanned': 0, 'expired': 0, 'failed': 0}
        for order_id in self.orders.due_ids(now, limit):
            result['scanned'] += 1
            try:
                changed = self.expire(order_id, now=now)
                if changed and changed['orderStatus'] == 'EXPIRED':
                    result['expired'] += 1
            except Exception as error:
                from app.utils.logging import log_failure
                log_failure(current_app, 'payment.expiry_failed', error)
                result['failed'] += 1
        return result

    def verified_relation(self, callback, session=None):
        attempt = self.attempts.by_reference(callback['txnRef'], session)
        if attempt is None:
            raise ProviderValidationError('01')
        order = self.orders.find_payment(attempt['orderId'], session)
        if order is None or order['userId'] != attempt['userId'] or order['paymentMethod'] != 'VNPAY':
            raise ProviderValidationError('01')
        if (callback['amountScaled'] != int(attempt['amount']) * 100 or callback['amountScaled'] != int(order['total']) * 100 or
            attempt['paymentRequest']['amountScaled'] != callback['amountScaled'] or
            attempt['paymentRequest']['txnRef'] != callback['txnRef'] or attempt['expiresAt'] != order['paymentExpiresAt']):
            raise ProviderValidationError('04')
        if attempt['paymentRequest']['tmnCode'] != current_app.config['VNP_TMN_CODE']:
            raise ProviderValidationError('97')
        return order, attempt

    def return_result(self, args):
        try:
            callback = self.provider.verify(args)
            order, attempt = self.verified_relation(callback)
        except ProviderValidationError as error:
            return {'result': 'INVALID_SIGNATURE' if error.code == '97' else 'INVALID_RESPONSE',
                    'verified': False, 'confirmed': False, 'authoritative': False}
        confirmed = order['paymentStatus'] == 'PAID'
        failed = order['paymentStatus'] == 'FAILED' or order['orderStatus'] in {'CANCELLED', 'EXPIRED'} or not callback['success']
        result = 'SUCCESS' if confirmed else 'FAILED' if failed and not order['paymentReviewRequired'] else 'PENDING'
        return {'result': result, 'providerResult': 'SUCCESS' if callback['success'] else 'FAILED',
                'verified': True, 'confirmed': confirmed, 'authoritative': False, 'orderId': order['_id'],
                'attemptId': attempt['_id'], 'paymentStatus': order['paymentStatus'],
                'orderStatus': order['orderStatus'], 'paymentReviewRequired': order['paymentReviewRequired']}

    def ipn(self, args):
        # One captured verification timestamp, reused across any transaction retries.
        verified_at = datetime.now(timezone.utc)
        callback = self.provider.verify(args)

        def write(session):
            order, attempt = self.verified_relation(callback, session)
            if attempt['status'] in {'SUCCEEDED', 'REVIEW_REQUIRED'}:
                return '02'
            if not callback['success'] and 'callbackFingerprint' in attempt:
                return '02'
            paid_at = callback['providerPaidAt'] or verified_at
            late = verified_at >= order['paymentExpiresAt'] or paid_at > order['paymentExpiresAt']
            order = self.expire_in_session(order, verified_at, session,
                force=callback['success'] and (late or order['paymentReviewRequired']))
            attempt = self.attempts.find(attempt['_id'], session)
            metadata = {k: callback[k] for k in ('responseCode', 'transactionStatus', 'bankCode', 'callbackFingerprint')}
            metadata['verifiedAt'] = verified_at
            if callback['providerTransactionNo']:
                metadata['providerTransactionNo'] = callback['providerTransactionNo']
            if callback['providerPaidAt']:
                metadata['providerPaidAt'] = callback['providerPaidAt']
            if callback['success']:
                confirm = (order['orderStatus'] == 'PENDING' and order['paymentStatus'] in {'PENDING', 'FAILED'} and
                           not order['paymentReviewRequired'] and 'stockReleasedAt' not in order and not late)
                self.attempts.patch(attempt, {**metadata, 'status': 'SUCCEEDED' if confirm else 'REVIEW_REQUIRED'}, verified_at, session)
                if confirm:
                    self.orders.patch_payment(order, {'orderStatus': 'CONFIRMED', 'paymentStatus': 'PAID',
                        'paidAt': paid_at, 'paymentReviewRequired': False}, verified_at, session)
                elif order['paymentStatus'] == 'PAID':
                    self.orders.patch_payment(order, {'paymentReviewRequired': True}, verified_at, session)
                else:
                    self.orders.patch_payment(order, {'paymentStatus': 'REVIEW_REQUIRED', 'paymentReviewRequired': True,
                        'paidAt': paid_at}, verified_at, session)
                self.attempts.invalidate_pending(order['_id'], verified_at, session)
            else:
                status = 'EXPIRED' if attempt['status'] == 'EXPIRED' else 'FAILED'
                self.attempts.patch(attempt, {**metadata, 'status': status}, verified_at, session)
                if (order['orderStatus'] == 'PENDING' and order['paymentStatus'] in {'PENDING', 'FAILED'} and
                    not self.attempts.pending(order['_id'], session) and order['paymentStatus'] != 'FAILED'):
                    self.orders.patch_payment(order, {'paymentStatus': 'FAILED'}, verified_at, session)
            return '00'
        return catalog_transaction(write)
