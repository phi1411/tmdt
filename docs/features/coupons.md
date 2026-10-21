# Mã giảm giá tại giỏ hàng

## Goal / Actors

Customer nhập hoặc bỏ mã tại Cart trước checkout. Guest phải đăng nhập; Admin không được mua thay Customer. Ô ưu đãi của cổng VNPAY do nhà cung cấp quản lý.

## Functional Requirements / Business Rules

NOVA25 giảm 25% tiền hàng từ 500.000 VND, tối đa 50.000 VND/đơn; không giảm phí vận chuyển. Một mã mỗi giỏ/đơn. Điều kiện tính trên các dòng hợp lệ, không dựa vào số tiền client gửi. Chưa có giá vốn, hạn lượt sử dụng, chiến dịch theo sản phẩm riêng hoặc quản trị mã; không cam kết lợi nhuận. Xem ADR015.

## Permission / API

`PATCH /api/v1/cart/coupon` IMPLEMENTED: CUSTOMER owner từ JWT. Body `{code:"NOVA25",cartVersion:1}`; code rỗng để bỏ. Response Cart như GET, thêm discount, coupon và couponIssue (null nếu không có lỗi). Coupon metadata gồm code, percent, minSubtotal, maxDiscount.

422 cho shape/code sai hoặc giỏ chưa đủ điều kiện; 409 CART_CHANGED cho version cũ, VERSION_LIMIT, CART_EMPTY nếu apply giỏ rỗng; 401/403 theo auth chung. Không cho chọn userId/discount/percent/maxDiscount từ request.

## Data / Dependencies

Cart.couponCode tùy chọn; Order.coupon snapshot tùy chọn; items.discountAllocated là long (legacy không có tương đương 0). Không có collection mới. Dùng Product/Category hiện hành để tính Cart, sau checkout chỉ dùng snapshot. Nguồn: services/coupon_service.py, commerce_pricing.py, cart_service.py, checkout_service.py, CartRepository, schemas/cart_schema.py, api/cart.py và database/validators/{carts,orders}.json; FE CartContext/CartPage, CheckoutPage và Order detail. Dashboard dùng canonical pipelines.

## Validation / Edge Cases / Security

Code tối đa 32 ký tự, ASCII chữ/số, trim/uppercase; allowlist đúng NOVA25, DEMO10, DEMO15. Backend tính min(subtotal*25//100, 50000), integer và không vượt subtotal. Mã chỉ apply nếu mọi dòng đang hợp lệ. Giảm số lượng dưới ngưỡng sau apply: hiện lý do, giảm 0, chặn quote cho đến khi bỏ mã hoặc tăng lại. Không tự đổi tiền đơn lịch sử. Quote bind snapshot và Cart.version; retry cùng intent không áp mã hai lần; hủy không tạo credit/voucher tự động.

## UI Behavior

Chỉ Cart có ô nhập và nút Áp dụng/Bỏ mã, hiện rõ ngưỡng/tỷ lệ/trần. Checkout và Order hiển thị số giảm thực tế; không có ô nhập ở phương thức VNPAY. Chuyển COD/VNPAY giữ cùng mã. Clear/checkout xóa mã cùng Cart. Không dùng frontend tính số tiền thanh toán.

## Acceptance Criteria / Testing Checklist

- Test biên ngưỡng/cap/mã sai và tổng không âm; server reject sửa giá, mức giảm.
- Cart CAS/ACL; thay đổi giỏ hoặc giá sau quote không dùng được báo giá cũ.
- COD/VNPAY cùng totals; attempt amount/signature/IPN dùng total sau giảm.
- Snapshot/discount allocation bất biến; tổng doanh thu theo sản phẩm/danh mục khớp tổng doanh thu.
- Validator legacy và mới đều hợp lệ; migration không sửa documents/indexes; full backend và strict production build pass.


## Deploy/demo21/10/2026

Người dùng yêu cầu deploy và thêm mã để nhìn thấy trên Compass. Bổ sung DEMO10: từ100k,10%,max20k; DEMO15: từ300k,15%,max40k; NOVA25 giữ nguyên. Một mã/đơn, không ship. Allowlist server và validators snapshot theo đúng từng mã, giữ lịch sử cũ; không thêm collection. Giữ có chủ đích3CODCANCELLEDOrders và1Customer/Cart demo quaAPI, stock trả đúng một lần, không fakepaid hoặc cộng doanh thu. Trạng thái deploy/nghiệm thu phải có receipt mới; các ghi chú chưadeploy trước đây là lịch sử.
