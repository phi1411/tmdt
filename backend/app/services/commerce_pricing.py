"""Current cart resolution and immutable checkout snapshots, never stored prices in Cart."""
import copy
import hashlib
import json
from collections import Counter
from bson.int64 import Int64
from app.repositories.product_repository import ProductRepository
from app.repositories.category_repository import CategoryRepository


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False).encode('utf-8')).hexdigest()


def line_id(product_id, selection):
    return canonical_hash({'productId': str(product_id), 'selectedAttributes': selection})


def valid_selection(product, selection):
    # Case 1: Product has tierVariations
    tier_variations = product.get('tierVariations')
    if tier_variations and len(tier_variations) > 0:
        expected_keys = {t['name'] for t in tier_variations}
        user_keys = {k for k in selection if k != 'skuId'}
        if user_keys != expected_keys:
            return False
        for tier in tier_variations:
            val = selection.get(tier['name'])
            if val not in tier['options']:
                return False
        return True

    # Case 2: Legacy fallback for FASHION
    allowed = {}
    if product['productType'] == 'FASHION':
        for key, attribute in [('size', 'sizes'), ('color', 'colors')]:
            choices = product['attributes'].get(attribute, [])
            if choices:
                allowed[key] = choices
    user_keys = {k for k in selection if k != 'skuId'}
    return set(user_keys) == set(allowed) and all(selection[key] in choices for key, choices in allowed.items())


def resolve_cart(cart, session=None):
    items = cart['items'] if cart else []
    quantities = Counter()
    for line in items:
        quantities[line['productId']] += line['quantity']
    products = {p['_id']: p for p in ProductRepository().find_many(quantities, session)}
    categories = {}
    for product in products.values():
        category_id = product['categoryId']
        if category_id not in categories:
            categories[category_id] = CategoryRepository().find({'_id': category_id}, session)
    lines, issues = [], []
    subtotal = 0
    for item in items:
        product = products.get(item['productId'])
        category = categories.get(product['categoryId']) if product else None
        reasons = []
        active_price = product['price'] if product else 0
        active_stock = product['stock'] if product else 0

        if product and product.get('skus'):
            sku_id = item['selectedAttributes'].get('skuId')
            matched_sku = next((s for s in product['skus'] if s['skuId'] == sku_id), None)
            if not matched_sku and product.get('tierVariations'):
                matched_sku = next((s for s in product['skus'] if s.get('tierIndex') and all(
                    product['tierVariations'][tier_idx]['options'][opt_idx] == item['selectedAttributes'].get(product['tierVariations'][tier_idx]['name'])
                    for tier_idx, opt_idx in enumerate(s['tierIndex']) if tier_idx < len(product['tierVariations'])
                )), None)
            if matched_sku:
                active_price = matched_sku['price']
                active_stock = matched_sku['stock']

        if product is None:
            reasons.append('PRODUCT_MISSING')
        else:
            if product['status'] != 'ACTIVE':
                reasons.append('PRODUCT_UNAVAILABLE')
            if not category or category['status'] != 'ACTIVE' or category['productType'] != product['productType']:
                reasons.append('CATEGORY_UNAVAILABLE')
            if not valid_selection(product, item['selectedAttributes']):
                reasons.append('SELECTION_CHANGED')
            if quantities[item['productId']] > active_stock:
                reasons.append('STOCK_CONFLICT')

        total = int(active_price) * item['quantity'] if product else 0
        line = {**copy.deepcopy(item), 'name': product['name'] if product else None,
                'slug': product['slug'] if product else None,
                'image': product['images'][0] if product and product['images'] else '',
                'currentPrice': int(active_price) if product else None,
                'stock': active_stock,
                'available': not reasons, 'issues': reasons, 'lineTotal': total}
        lines.append(line)
        if reasons:
            issues.append({'lineId': item['lineId'], 'codes': reasons})
        else:
            subtotal += total
    response = {'version': cart['version'] if cart else 0, 'items': lines, 'subtotal': subtotal,
                'currency': 'VND', 'issues': issues, 'checkoutAllowed': bool(items) and not issues}
    return response, products, categories, quantities


def snapshot_items(cart, products, categories):
    result = []
    for line in cart['items']:
        product = products[line['productId']]
        category = categories[product['categoryId']]
        price = product['price']
        if product.get('skus'):
            sku_id = line['selectedAttributes'].get('skuId')
            matched_sku = next((s for s in product['skus'] if s['skuId'] == sku_id), None)
            if not matched_sku and product.get('tierVariations'):
                matched_sku = next((s for s in product['skus'] if s.get('tierIndex') and all(
                    product['tierVariations'][tier_idx]['options'][opt_idx] == line['selectedAttributes'].get(product['tierVariations'][tier_idx]['name'])
                    for tier_idx, opt_idx in enumerate(s['tierIndex']) if tier_idx < len(product['tierVariations'])
                )), None)
            if matched_sku:
                price = matched_sku['price']
        result.append({'productId': product['_id'], 'sku': product['sku'], 'productName': product['name'],
                       'image': product['images'][0] if product['images'] else '',
                       'productType': product['productType'], 'categoryId': category['_id'],
                       'categoryName': category['name'], 'attributesSnapshot': copy.deepcopy(product['attributes']),
                       'selectedAttributes': copy.deepcopy(line['selectedAttributes']),
                       'priceAtPurchase': Int64(price), 'quantity': line['quantity'],
                       'lineTotal': Int64(int(price) * line['quantity'])})
    return result
