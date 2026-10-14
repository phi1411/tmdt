"""Owner cart mutations with canonical lines, shared stock and version guards."""
import copy
from datetime import datetime, timezone
from pymongo.errors import DuplicateKeyError
from app.errors import ConflictError, NotFoundError, ValidationError
from app.repositories.cart_repository import CartRepository
from app.services.commerce_pricing import line_id, resolve_cart


class CartService:
    def __init__(self):
        self.carts = CartRepository()

    def get(self, user_id):
        return resolve_cart(self.carts.find(user_id))[0]

    def mutate(self, user_id, version, action, product_id=None, quantity=None, selection=None, target=None):
        cart = self.carts.find(user_id)
        if (cart['version'] if cart else 0) != version:
            raise ConflictError(code='CART_CHANGED')
        if version >= 2147483647:
            raise ConflictError(code='VERSION_LIMIT')
        items = copy.deepcopy(cart['items']) if cart else []
        if action == 'add':
            selection = selection or {}
            target = line_id(product_id, selection)
            existing = next((line for line in items if line['lineId'] == target), None)
            if existing:
                existing['quantity'] += quantity
                if existing['quantity'] > 99:
                    raise ValidationError(details=[{'field': 'quantity', 'reason': 'Tối đa 99 mỗi dòng'}])
            else:
                if len(items) >= 50:
                    raise ConflictError(code='CART_LIMIT')
                items.append({'lineId': target, 'productId': product_id, 'quantity': quantity,
                              'selectedAttributes': selection})
        elif action in {'update', 'remove'}:
            existing = next((line for line in items if line['lineId'] == target), None)
            if existing is None:
                raise NotFoundError()
            product_id = existing['productId']
            if action == 'update':
                existing['quantity'] = quantity
            else:
                items.remove(existing)
        elif action == 'clear':
            items = []
        else:
            raise ValueError('Unknown cart action')
        if action in {'add', 'update'}:
            resolved = resolve_cart({'version': version, 'items': items})[0]
            relevant = [line for line in resolved['items'] if line['productId'] == product_id]
            reasons = {reason for line in relevant for reason in line['issues']}
            if 'PRODUCT_MISSING' in reasons:
                raise NotFoundError()
            if 'SELECTION_CHANGED' in reasons:
                raise ValidationError(details=[{'field': 'selectedAttributes', 'reason': 'Lựa chọn không phù hợp sản phẩm hiện tại'}])
            if reasons:
                raise ConflictError(code='STOCK_CONFLICT' if 'STOCK_CONFLICT' in reasons else 'PRODUCT_UNAVAILABLE')
        now = datetime.now(timezone.utc)
        if not cart:
            if action == 'clear':
                return resolve_cart(None)[0]
            try:
                cart = self.carts.create(user_id, items, now)
            except DuplicateKeyError:
                raise ConflictError(code='CART_CHANGED') from None
        else:
            cart = self.carts.replace_items(user_id, version, items, now)
            if cart is None:
                raise ConflictError(code='CART_CHANGED')
        return resolve_cart(cart)[0]
