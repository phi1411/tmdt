# Examples schema v1 — Extended JSON

Sáu file JSON chứa **19 document minh họa**, không phải bộ Dummy Data180 Product/100 Order. Canonical numeric wrappers `$numberInt`/`$numberLong`, ObjectId `$oid`, ngày `$date` được giữ để phân biệt BSON khi kiểm tra/import ở phase sau.

- users:2 (Customer/Admin), hash minh họa shape Argon2id, không tài khoản login thật.
- categories:3 (Điện tử/Thời trang/Gia dụng), một cấp.
- products:3 cùng collection, attributes khác; Product điện thoại hiện tại12 triệu.
- carts:1, một dòng tham chiếu Product, không persist giá.
- orders:6, mỗi đơn2 dòng snapshot; điện thoại lúc mua10 triệu, COD/VNPAY completed, online confirmed, cancelled, expired và late-payment review.
- payment_attempts:4, liên kết các đơn VNPAY; provider IDs/callback metadata là fixture, không giao dịch sandbox thật.

URL ảnh `https://assets.example.test/...` chỉ minh họa URL syntax, không cam kết có ảnh online. Seed sau này dùng URL tới asset demo ổn định. Idempotency hashes là fixture deterministic; quoteToken mẫu không token checkout hợp lệ. Không nhúng token/secret hoặc paymentUrl đã ký vào samples.

Fixtures qualified có merchandise revenue21.900.000 VND, units5; Top quantities điện thoại2/áo2/nồi1, tie revenue làm điện thoại đứng trước áo. Shipping mỗi Order30.000 VND không vào revenue. Có3 Product nhưng19 documents tổng không đáp ứng định mức seed; không ghi nhận điểm Dummy Data từ examples này.

Kiểm tra bằng script validation thiết kế. Chưa import vào MongoDB/Compass, chưa validate runtime authentication/payment.
