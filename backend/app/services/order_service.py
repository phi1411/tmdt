"""Snapshot-only history and transactionally guarded once-only cancellation."""
from collections import Counter
from datetime import datetime, timezone
from flask import current_app, g
from app.errors import ConflictError, NotFoundError
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.payment_attempt_repository import PaymentAttemptRepository
from app.schemas.order_schema import order_response
from app.schemas.admin_order_schema import admin_order_response, allowed_actions
from app.services.catalog_transaction import catalog_transaction


class OrderService:
    def __init__(self):
        self.orders = OrderRepository()
        self.products = ProductRepository()
        self.attempts = PaymentAttemptRepository()

    def list(self, user_id, filters, pagination):
        return self.orders.list(user_id, filters, pagination)

    def detail(self, user_id, order_id):
        order = self.orders.find(user_id, order_id)
        if order is None:
            raise NotFoundError()
        if order['paymentMethod'] == 'VNPAY':
            from app.services.payment_service import PaymentService
            order = PaymentService().expire(order_id, user_id)
        return order_response(order)

    def cancel(self, user_id, order_id, expected_version, *, admin=False, audit=None):
        now = datetime.now(timezone.utc)

        def write(session):
            order = self.orders.find_admin(order_id, session) if admin else self.orders.find(user_id, order_id, session)
            if order is None:
                raise NotFoundError()
            if audit is not None:
                audit['previous_order_status'] = order['orderStatus']
            if order['orderStatus'] == 'CANCELLED':
                return order_response(order)
            if order['version'] != expected_version:
                raise ConflictError(code='ORDER_CHANGED')
            if (order['orderStatus'] not in {'PENDING', 'CONFIRMED'} or
                order['paymentStatus'] in {'PAID', 'REVIEW_REQUIRED'} or order['paymentReviewRequired'] or
                'stockReleasedAt' in order):
                raise ConflictError(code='INVALID_TRANSITION')
            if order['version'] >= 2147483647:
                raise ConflictError(code='VERSION_LIMIT')
            payment_status = 'UNPAID' if order['paymentMethod'] == 'COD' else 'FAILED'
            changed = self.orders.cancel(order, payment_status, now, session)
            if changed is None:
                raise ConflictError(code='ORDER_CHANGED')
            quantities = Counter()
            for item in order['items']:
                quantities[item['productId']] += item['quantity']
            for product_id in sorted(quantities):
                if not self.products.restore_stock(product_id, quantities[product_id], now, session):
                    current_app.logger.error('Stock restoration failed', extra={'event': 'commerce.stock_restore_failed'})
                    raise ConflictError(code='STOCK_RESTORE_FAILED', message='Không thể hoàn tồn kho; cần kiểm tra dữ liệu')
            self.attempts.invalidate_pending(order_id, now, session)
            return order_response(changed)

        return catalog_transaction(write)

    def admin_list(self, filters, pagination):
        return self.orders.list_admin(filters, pagination)

    def admin_detail(self, order_id):
        order = self.orders.find_admin(order_id)
        if order is None:
            raise NotFoundError()
        return admin_order_response(order)

    def admin_action(self, order_id, action, expected_version, actor_id):
        now = datetime.now(timezone.utc)
        audit = {}
        if action == 'cancel':
            order = self.cancel(None, order_id, expected_version, admin=True, audit=audit)
            result = admin_order_response(order)
        else:
            target = {'confirm': 'CONFIRMED', 'ship': 'SHIPPING', 'complete': 'COMPLETED'}[action]

            def write(session):
                order = self.orders.find_admin(order_id, session)
                if order is None:
                    raise NotFoundError()
                audit['previous_order_status'] = order['orderStatus']
                # Same-terminal retry returns the committed snapshot, never rewrites timestamps.
                if action == 'complete' and order['orderStatus'] == 'COMPLETED':
                    return admin_order_response(order)
                if order['version'] != expected_version:
                    raise ConflictError(code='ORDER_CHANGED')
                if order['version'] >= 2147483647:
                    raise ConflictError(code='VERSION_LIMIT')
                if action not in allowed_actions(order) or now < order['createdAt'] or now < order.get('paidAt', order['createdAt']):
                    raise ConflictError(code='INVALID_TRANSITION')
                fields = {'orderStatus': target}
                if action == 'complete':
                    fields['completedAt'] = now
                    if order['paymentMethod'] == 'COD':
                        fields.update(paymentStatus='PAID', paidAt=now)
                changed = self.orders.transition_admin(order, fields, now, session)
                if changed is None:
                    raise ConflictError(code='ORDER_CHANGED')
                return admin_order_response(changed)

            result = catalog_transaction(write)
        current_app.logger.info('Admin order action', extra={
            'request_id': getattr(g, 'request_id', None),
            'event': 'admin.order_action', 'actor_id': str(actor_id), 'order_id': str(order_id),
            'action': action, 'order_status': result['orderStatus'], 'order_version': result['version'], **audit,
        })
        return result
