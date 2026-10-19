"""Cross-field matrix validation in addition to the BSON-derived request shape."""
from app.errors import ValidationError


def invalid(reason):
    raise ValidationError(details=[{'field': 'skus', 'reason': reason}])


def validate_variants(payload):
    tiers, skus = payload.get('tierVariations', []), payload.get('skus', [])
    if bool(tiers) != bool(skus):
        invalid('Phân loại và ma trận SKU phải được cung cấp cùng nhau')
    if not tiers:
        return
    names = [tier['name'] for tier in tiers]
    if any(not name.strip() or name != name.strip() or name == 'skuId' or '$' in name or '.' in name for name in names) or len(set(names)) != len(names):
        invalid('Tên phân loại không được trống, trùng hoặc chứa ký tự không hợp lệ')
    for tier in tiers:
        values = tier['options']
        if len(set(values)) != len(values) or any(not value.strip() or value != value.strip() for value in values):
            invalid('Giá trị phân loại không được trống hoặc trùng')
    ids, combinations = set(), set()
    for sku in skus:
        key = sku['skuId']
        indexes = sku.get('tierIndex', [])
        if not key.strip() or key != key.strip() or key in ids:
            invalid('Mã SKU phải duy nhất và không trống')
        if len(indexes) != len(tiers) or any(not 0 <= index < len(tier['options']) for index, tier in zip(indexes, tiers)):
            invalid('Chỉ số SKU phải khớp đủ các tầng phân loại')
        if tuple(indexes) in combinations:
            invalid('Không được trùng tổ hợp phân loại')
        ids.add(key)
        combinations.add(tuple(indexes))
    if sum(sku['stock'] for sku in skus) > 2147483647:
        invalid('Tổng tồn kho vượt giới hạn')
    payload['stock'] = sum(sku['stock'] for sku in skus)
    payload['price'] = min(sku['price'] for sku in skus)
