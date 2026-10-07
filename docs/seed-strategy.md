# Seed strategy — LOCKED DESIGN v1

PHASE02 đã khóa kế hoạch; PHASE03 triển khai tại [seed.py](../scripts/seed/seed.py) và [live verifier](../scripts/validation/verify_database.py). 19 document tại database/samples vẫn là ví dụ thiết kế riêng. Target/RNG/anchor giữ nguyên; nguồn cache giúp seed không phụ thuộc API sống. Kết quả chạy thực tại [evidence](../database/evidence/README.md).

## Target

| Collection | Target | Quy tắc |
| --- | --- | --- |
| categories |3 | Điện tử, Thời trang, Gia dụng; một cấp |
| products |180 |60 mỗi productType, SKU/slug unique, attributes khác nhau |
| users |40 |1 Admin +39 Customer, email example.test và địa chỉ giả lập |
| orders |100 |2–5 dòng Product khác nhau mỗi đơn, quantity1–3 |
| carts |0 lúc seed | Tạo khi Customer thêm hàng; fixture riêng nếu cần |
| payment_attempts |Theo đơn VNPAY | Metadata/history giả lập hợp lệ, không gọi provider |
| reviews |Không tạo | DEFERRED, không phụ thuộc MVP |

Phân bố trạng thái: 60 COMPLETED, 10 PENDING, 10 CONFIRMED, 10 SHIPPING, 5 CANCELLED, 5 EXPIRED. Trong 100 đơn có 70 COD và30 VNPAY: completed40/20, pending5/5, confirmed10/0, shipping10/0, cancelled5/0, expired0/5. Đây là lựa chọn seed để demo, không phải định mức mới của giảng viên.

COMPLETED luôn PAID; COD pending/confirmed/shipping/cancelled giữ UNPAID; VNPAY pending là PENDING, expired là FAILED. Timestamp và payment attempt theo schema/rules. Tạo fixtures thanh toán phải ghi rõ trong manifest, không gọi chúng là giao dịch sandbox thật.

## Product source và normalization

Nguồn PHASE03 là [DummyJSON Products](https://dummyjson.com/docs/products), cache194 Product đầu vào ở database/sources/dummyjson-products.json, checksum/mapping/provenance tại [provenance.json](../database/sources/provenance.json). Chọn38 nguồn Electronics,46 nguồn Fashion và35 nguồn Home/Household; mỗi ngành dựng60 document, thêm biến thể catalog demo rõ tên khi nguồn chưa đủ60. Thuộc tính ngành được biên soạn phù hợp nhóm thiết bị/quần áo/giày/phụ kiện/nội thất/dụng cụ bếp. Không tuyên bố thông số demo là thông số hãng đã xác minh. Giá VND giả lập dùng USD×25.000 cố định, thêm5% cho vòng biến thể; không phải tỷ giá/giá thị trường hiện tại. Product demo đầu tiên dùng10triệu rồi cập nhật12triệu sau snapshot. Không import reviews/rating/PII/raw dataset nguyên xi.

Chuẩn hóa field chung/discriminator/attributes theo database-schema; nameNormalized/brandNormalized theo ADR008. IDs/SKU/slug deterministic. Images giữ HTTPS URL CDN của nguồn, không dùng localhost tạm hoặc download media hàng loạt. Kiểm tra URL nonempty/HTTPS trên toàn bộ180 Product; probe mạng đại diện chỉ chứng minh URL tại thời điểm kiểm tra. Availability CDN về sau cần fallback ở frontend. Giá BSON long, stock BSON int, category/type tương hợp.

## Sinh Order từ chính Product data

Tạo các version Product cơ sở trước. Chọn2–5 ID khác nhau từ tập180 Product, copy sku/name/image/productType/categoryId/categoryName/attributes và selections hợp lệ. priceAtPurchase lấy từ version Product tại purchase event; tính quantity×price, lineTotal, subtotal. Shipping mặc định30.000 VND, discount long0; total theo công thức server.

Sau snapshot có thể tăng current price của một số Product để demo10→12triệu; không sửa Order cũ. Manifest lưu timeline/version đã dùng để chứng minh snapshot có nguồn, không sinh productId hoặc giá lịch sử tùy ý. Một SKU dùng chung price/stock; Fashion size/color chọn trong attributes lúc mua.

## Reproducibility và tồn kho

RNG seed20261007, anchor UTC2026-10-01T00:00:00Z, event window90 ngày trước anchor. Dates/IDs/SKU/orderCode/key/hash và nội dung deterministic; không dùng now để tạo lịch sử.

Các đơn VNPAY PENDING đặt trong15 phút trước anchor và deadline chưa quá anchor. Khi dùng demo thực ở thời điểm sau anchor, expiry service có thể làm chúng hết hạn đúng rule; không sửa clock ứng dụng để giữ trạng thái giả. Completed có paidAt<=completedAt; cancelled/expired có stockReleasedAt và timestamp terminal đúng.

Password nhận từ env lúc seed, hash Argon2id có salt ngẫu nhiên; nghiệp vụ reproducible không có nghĩa hash giống từng byte. Không commit password/secrets thật; export chia sẻ bỏ credential/PII cần bảo vệ. Hash trong schema examples chỉ minh họa shape, không phải account dùng để login demo.

Initial stock được đặt đủ, giảm cho đơn đã bán và đơn còn giữ hàng, trả lại đơn cancelled/expired đúng một lần. Manifest ghi initial/sold/reserved/released/final; final stock>=0. Cart không giữ stock. Verify đối chiếu references, chronology, statuses, selections, normalization, money types, arithmetic và stock reconciliation.

## Scripts PHASE03

Đã có scripts/seed/seed.py; scripts/validation/verify_database.py và verify_reproducibility.py; scripts/export/export_data.py và scripts/import/import_data.py. [Setup](mongodb-setup.md) ghi command/config/guard. scripts/validation/validate_design.py vẫn chỉ kiểm thiết kế tĩnh, không thay kiểm thử DB thật.

Mặc định dry-run, không reset/drop ngầm. `--reset` chỉ trên DB local allowlist có filesystem ownership marker; từ chối document ngoài tập deterministic IDs. Giữ validator/index, không drop. Trong transaction snapshot/majority: xóa fixture cũ → Category/User/Product cơ sở → đọc lại Product/Category/User bằng PyMongo → Order/Attempts snapshots → update Product current version/stock → commit. Transaction retries không gọi dịch vụ ngoài. Verify reseed so SHA-256 nội dung cả6collection trước/sau, loại passwordHash có salt ngẫu nhiên; counts không tăng.

## Compass import/export và acceptance

Extended JSON bảo toàn ObjectId/Date/Long. Export documents không mang validator/index, nên roundtrip dùng DB test riêng và apply lại chúng. Hướng dẫn Compass theo phiên bản thực cài ở phase demo; chưa cần chốt UI version để khóa modeling.

Verify target180 Product/3 nhóm/40 User/100 Order/2–5 item,11 unique constraints/type branches, references/snapshot origins/password hashes/provider cap/chronology/status/payment/totals/stock/normalization; so kết quả8pipeline MongoDB với phép tính độc lập. Temporarily đổi Product trong transaction rồi chạy lại báo cáo, sau đó rollback để chứng minh snapshot độc lập giá hiện tại. Stress dataset và benchmark đầy đủ thuộc phase performance riêng; không đổi100Order seed chuẩn. Không có checkout/payment/expiry service chạy ở phase03; các state/stock marker là fixture phù hợp schema, không chứng minh workflow ứng dụng.
