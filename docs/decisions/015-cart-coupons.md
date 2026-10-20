# ADR015 — Mã giảm giá tại giỏ hàng

Ngày: 20/10/2026. Phạm vi do người dùng yêu cầu, thay thế quy định discount=0 của v1.

## Vấn đề và lựa chọn

Ô ưu đãi trên cổng VNPAY thuộc nhà cung cấp, không phải giao diện Novamart. Bổ sung mã của sàn ở Cart, áp dụng độc lập phương thức COD/VNPAY. Người dùng chọn giới hạn mức giảm, chưa bổ sung giá vốn; không tuyên bố bảo đảm lợi nhuận thực tế.

Chiến dịch duy nhất NOVA25: tiền hàng hợp lệ từ 500.000 VND, giảm 25%, tối đa 50.000 VND/đơn, không giảm phí giao hàng. Chỉ các dòng Product/Category ACTIVE, lựa chọn và tồn kho hợp lệ được tính. Không cộng dồn mã; chưa giới hạn lượt/người hoặc thêm quản trị chiến dịch. Không thêm collection/index/dependency.

## Dữ liệu, API và nhất quán

- Cart thêm couponCode tùy chọn; PATCH /cart/coupon nhận code (chuỗi rỗng để bỏ) và cartVersion, dùng CAS như thay đổi số lượng. Mã chuẩn hóa trim/uppercase. Không nhận client discount/total.
- GET Cart tính lại điều kiện; mã đã chọn nhưng giỏ giảm dưới ngưỡng được giữ và báo couponIssue, discount=0, chặn checkout đến khi bỏ mã hoặc đủ điều kiện. Clear/checkout xóa mã cùng Cart.items.
- Quote ký cả pricing/coupon snapshot. Checkout tính lại trong transaction; đổi mã làm đổi cartVersion; đổi giá/điều kiện làm báo giá cũ không còn hợp lệ. Payment amount lấy Order.total đã giảm.
- Order thêm coupon snapshot tùy chọn (code, percent, minSubtotal, maxDiscount). Items của đơn mới có discountAllocated BSON long. Chia tỷ lệ theo lineTotal, lấy phần nguyên rồi phân bổ phần dư theo thứ tự dòng, tổng luôn bằng discount. lineTotal và priceAtPurchase vẫn là giá gốc tại lúc mua.
- Top Product/Category dùng lineTotal - ifNull(discountAllocated, 0); báo cáo ngày/tháng/summary dùng subtotal-discount. Dữ liệu cũ discount=0 đọc nguyên trạng, không backfill/reseed.
- Validators carts/orders mở rộng theo hướng cộng thêm; cần áp dụng trước khi chạy source mới. Migration chỉ collMod hai collection, kiểm tra toàn bộ document hợp lệ, lưu schema cũ và không thay document/index. Không tự chạy trên Atlas trong task phát triển.

## Kiểm tra bắt buộc

Ngưỡng 499.999/500.000, mã sai, cap, tiền nguyên, phân bổ chính xác, CAS/ownership, stale quote, payload tampering, COD và VNPAY amount/IPN, snapshot, hủy/retry, báo cáo doanh thu đồng nhất; full backend suite và frontend build. Test DB riêng rs0; không sửa dữ liệu development/Atlas.
