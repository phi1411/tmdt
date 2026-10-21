"""Server-owned campaign and integer allocation; never trust client totals."""
from bson.int64 import Int64
from app.errors import ValidationError

COUPONS = {
    'NOVA25': {'code': 'NOVA25', 'percent': 25, 'minSubtotal': 500000, 'maxDiscount': 50000},
    'DEMO10': {'code': 'DEMO10', 'percent': 10, 'minSubtotal': 100000, 'maxDiscount': 20000},
    'DEMO15': {'code': 'DEMO15', 'percent': 15, 'minSubtotal': 300000, 'maxDiscount': 40000},
}


def normalize_code(code):
    return code.strip().upper()


def coupon_pricing(code, subtotal, available=True):
    if not code:
        return {'discount': 0, 'coupon': None, 'couponIssue': None}
    code = normalize_code(code)
    coupon = COUPONS.get(code)
    issue = None
    if coupon is None:
        issue = 'Mã giảm giá không hợp lệ.'
    elif not available:
        issue = 'Vui lòng xử lý sản phẩm không hợp lệ trong giỏ trước khi dùng mã.'
    elif subtotal < coupon['minSubtotal']:
        minimum = f"{coupon['minSubtotal']:,}".replace(',', '.')
        issue = f'Mã {code} áp dụng cho tiền hàng từ {minimum}đ, không gồm phí giao hàng.'
    discount = min(subtotal * coupon['percent'] // 100, coupon['maxDiscount'], subtotal) if not issue else 0
    return {'discount': discount, 'coupon': dict(coupon) if coupon else None,
            'couponIssue': issue}


def require_coupon(pricing):
    if pricing['couponIssue']:
        raise ValidationError(details=[{'field': 'code', 'reason': pricing['couponIssue']}])


def allocate_discount(items, discount):
    """Largest remainder, stable line order for ties, no floating-point rounding."""
    subtotal = sum(int(item['lineTotal']) for item in items)
    if discount < 0 or discount > subtotal or not subtotal:
        raise ValueError('Invalid discount allocation')
    amounts = [discount * int(item['lineTotal']) // subtotal for item in items]
    remaining = discount - sum(amounts)
    order = sorted(range(len(items)), key=lambda i: (-(discount * int(items[i]['lineTotal']) % subtotal), i))
    for i in order[:remaining]:
        amounts[i] += 1
    for item, amount in zip(items, amounts):
        item['discountAllocated'] = Int64(amount)
