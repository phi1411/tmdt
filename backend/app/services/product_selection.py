"""Resolve server-owned variant identity; never trust a client SKU price."""
from collections import Counter, defaultdict


def resolve_selection(product, selection):
    tiers = product.get('tierVariations') or []
    if tiers:
        if set(selection) - {'skuId'} != {tier['name'] for tier in tiers}:
            return False, None
        matches = [sku for sku in product.get('skus', []) if len(sku.get('tierIndex', [])) == len(tiers)
                   and all(0 <= index < len(tier['options']) and tier['options'][index] == selection[tier['name']]
                           for tier, index in zip(tiers, sku['tierIndex']))]
        if len(matches) != 1 or ('skuId' in selection and selection['skuId'] != matches[0]['skuId']):
            return False, None
        return True, matches[0]
    allowed = {}
    if product['productType'] == 'FASHION':
        for key, field in [('size', 'sizes'), ('color', 'colors')]:
            if product['attributes'].get(field):
                allowed[key] = product['attributes'][field]
    return set(selection) == set(allowed) and all(selection[key] in values for key, values in allowed.items()), None


def snapshot_stock_groups(items):
    totals, skus = Counter(), defaultdict(Counter)
    for item in items:
        totals[item['productId']] += item['quantity']
        sku_id = item['selectedAttributes'].get('skuId')
        if sku_id:
            skus[item['productId']][sku_id] += item['quantity']
    return totals, skus
