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
    allowed = {}
    if product['productType'] == 'FASHION':
        for key, attribute in [('size', 'sizes'), ('color', 'colors')]:
            choices = product['attributes'].get(attribute, [])
            if choices:
                allowed[key] = choices
    return set(selection) == set(allowed) and all(selection[key] in choices for key, choices in allowed.items())


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
        if product is None:
            reasons.append('PRODUCT_MISSING')
        else:
            if product['status'] != 'ACTIVE':
                reasons.append('PRODUCT_UNAVAILABLE')
            if not category or category['status'] != 'ACTIVE' or category['productType'] != product['productType']:
                reasons.append('CATEGORY_UNAVAILABLE')
            if not valid_selection(product, item['selectedAttributes']):
                reasons.append('SELECTION_CHANGED')
            if quantities[item['productId']] > product['stock']:
                reasons.append('STOCK_CONFLICT')
        total = int(product['price']) * item['quantity'] if product else 0
        line = {**copy.deepcopy(item), 'name': product['name'] if product else None,
                'slug': product['slug'] if product else None,
                'image': product['images'][0] if product and product['images'] else '',
                'currentPrice': int(product['price']) if product else None,
                'stock': product['stock'] if product else 0,
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
        result.append({'productId': product['_id'], 'sku': product['sku'], 'productName': product['name'],
                       'image': product['images'][0] if product['images'] else '',
                       'productType': product['productType'], 'categoryId': category['_id'],
                       'categoryName': category['name'], 'attributesSnapshot': copy.deepcopy(product['attributes']),
                       'selectedAttributes': copy.deepcopy(line['selectedAttributes']),
                       'priceAtPurchase': Int64(product['price']), 'quantity': line['quantity'],
                       'lineTotal': Int64(int(product['price']) * line['quantity'])})
    return result
