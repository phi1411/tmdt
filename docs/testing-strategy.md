# Chiến lược kiểm thử

**PHASE03 kiểm tra MongoDB thật; PHASE04 có80 foundation tests pass; PHASE05A có213 scoped tests pass (80 foundation +133 Auth/User),20 HTTP checks thật với pytest9.1.1/rs0.** Evidence [backend](../backend/evidence/README.md), [database](../database/evidence/README.md); setup [backend](backend-setup.md). Auth/User backend được nghiệm thu riêng; các ca feature ngoài phạm vi/frontend/E2E dưới đây chỉ đánh dấu pass khi có evidence worker tương ứng. Full benchmark chưa chạy. Backend runner đã khóa; Vitest/Testing Library và Playwright là hướng frontend/E2E chưa bootstrap.

## Tầng kiểm tra

PHASE05B Catalog đã kiểm tra backend thật:112 Catalog cases +80 foundation +133 Auth/User hiện có=325 workspace tests pass. Evidence riêng [JUnit](../backend/evidence/phase05b-pytest.xml), [HTTP/explain/fingerprint](../backend/evidence/phase05b-runtime.json), [review](phase-05b-review.md). Các tests Catalog chỉ ghi owned test DB fixtures/xóa exact IDs, thực chạy transaction rollback/create-move-publish vs Category archive/delete và concurrent Product version patch. Checkout/payment/frontend/benchmark cases vẫn kế hoạch, không suy ra pass từ Catalog tests.

| Tầng | Cần chứng minh | Môi trường |
| --- | --- | --- |
| Unit service | integer pricing, selection, state policy, request hash | Fixture deterministic |
| API integration | HTTP contract, validation/role/ownership, unique/validator | Flask test client + Mongo replica set test DB |
| Mongo integration | transactions, rollback, conditional stock, indexes, aggregation | DB thật cùng topology/features với dev |
| Frontend | loading/error/empty, stock/price conflicts, accessibility form | Component/API fixture đúng contract |
| E2E | shop→cart→checkout→history và Admin→dashboard | Web/API/test DB, provider sandbox hoặc adapter giả rõ ràng |
| Demo/manual | Compass polymorphism/snapshot/import-export/explain | Database demo riêng |

Mock không chứng minh behavior transaction/index; integration không chạy trên standalone. Setup/teardown chỉ DB test có suffix `_test` và marker fixture; không xóa DB từ URI bất kỳ. Không gọi payment thật trong CI. Tests không phụ thuộc giá thị trường/public API sống.

## Ca bắt buộc có giá trị

- Guest/Admin/Customer matrix; Customer A không đọc/sửa Cart/Order/Address của B; register payload role ADMIN bị reject.
- Hai Product khác ngành pass validator; discriminator sai, long sai, quantity bool/float, attribute key/operator sai bị reject.
- Create/read/update/archive Category/Product; duplicate SKU/slug; category đang referenced không hard-delete; archive race với checkout/create không tạo sale sai rule.
- Cart tổng quantity cùng Product qua nhiều selections <=stock; stale version 409, inactive Product vẫn hiển thị issue.
- Checkout price tampering/quote tampering/expired quote; reprice→409 trước commit; address không thuộc User→404.
- **Snapshot test:** mua Product giá 10 triệu → sửa giá 12 triệu/tên/category/profile/address → Order cũ vẫn đủ snapshot và totals. Archive Product vẫn đọc Order bằng Order document, không lookup.
- **Concurrency:** stock=1, hai checkout cùng lúc chỉ một thành công; stock không âm. Order/cart/payment attempt không tồn tại nửa chừng khi fail item thứ hai.
- **Idempotency:** mất response retry cùng key/body vẫn một Order, trừ stock một lần; cùng key khác body 409; retry sau Cart clear vẫn lấy Order cũ.
- Hủy đơn lặp và race hủy/hết hạn→trả kho một lần; không hủy PAID/SHIPPING/COMPLETED; state/version stale bị 409.
- VNPAY invalid signature/amount/merchant/txnRef; callback success trùng; failure sau success; success sau expiry; retry nhiều attempt và success muộn. Không ReturnUrl nào tự set paid.
- Chỉ Admin có Dashboard/User management; không khóa/demote Admin cuối, kể cả hai request đồng thời.
- Search q có `$`, regex, Unicode/tiếng Việt; filter/sort/pagination allowlist; không leak fields nhạy cảm.

## Fixture aggregation có số kỳ vọng

Tạo 4 Orders với ngày đã biết (không phải toàn bộ seed):

| Order | completedAt | Trạng thái | Items | Subtotal / ship |
| --- | --- | --- | --- | --- |
| A | 2026-09-01T01:00Z | COMPLETED+PAID | P1 100×2, P2 50×1 | 250 / 20 |
| B | 2026-09-02T01:00Z | COMPLETED+PAID | P1 100×1, P3 25×4 | 200 / 30 |
| C | không có | CANCELLED+UNPAID | P1 100×3 | 300 / 0 |
| D | không có | CONFIRMED+PAID | P2 50×2 | 100 / 0 |

Khoảng chứa A/B/C/D theo ngày tạo: Total Orders=4. Qualified revenue=450, products sold=8 (3+5), Top quantities P3=4/P1=3/P2=1. Category mapping P1→Điện tử, P2/P3→Gia dụng: revenues 300/150. Collected amount của A/B=500 nhưng không được dùng làm revenue. Ngày 01/09=250, 02/09=200, ngày trống=0. C/D không vào revenue. Test from inclusive/to exclusive, boundary 17:00Z (00:00 VN), month boundary, tie Top 5, hai snapshot names cùng Product/Category ID vẫn group chung.

## Hiệu năng

Theo ADR-005: collection benchmark riêng; baseline `hint({$natural:1})`, candidate index bằng hint tên index, thêm unhinted planner. Giữ dataset/filter/projection/sort kết quả như nhau; warm-up và lặp >=30 lượt **đề xuất**. Báo p50/p95 client monotonic latency riêng với executionTimeMillis của explain; 0ms trên data nhỏ là có thể. Đo docs/keys examined, winningPlan và cardinality; lưu version/topology/index/seed/query.

Không claim “nhanh hơn X lần” trước đo; index không bảo đảm tăng tốc khi predicate chọn phần lớn 100 Order. Bộ stress riêng có thể 10.000+ Order, không thay target seed 100 hoặc đưa dữ liệu stress vào demo. Không drop index unique trên DB dev/demo để tạo so sánh.

## Exit criteria

Checks liên quan pass; failed/skipped và môi trường ghi rõ; không lỗi runtime đã biết; docs/contract khớp behavior. Validation phase tài liệu: file đủ, liên kết đúng, đủ 13 section feature, không endpoint triển khai giả. Schema/pipeline artifacts kiểm tra tĩnh phase02; DB apply/aggregate/constraint/reseed/roundtrip đã chạy thật phase03; startup/health/config/envelopes/auth primitives/validation và an toàn DB đã pass phase04. Transaction nghiệp vụ và frontend/E2E chỉ đánh dấu pass sau khi implement và thực chạy ở phase được giao.
