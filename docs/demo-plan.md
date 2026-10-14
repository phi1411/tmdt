# Kịch bản bảo vệ trực tiếp

## Kịch bản hiện hành — PHASE07C

Ưu tiên [bản 5 phút](demo-script-5min.md); [bản 10 phút](demo-script-10min.md) thêm lifecycle COD và Dashboard delta. [Compass từng click](compass-demo-steps.md), [checklist](pre-demo-checklist.md), [20 Q&A](defense-qa.md), [evidence index](defense-evidence-index.md), [readiness và giới hạn](phase-07c-demo-readiness.md).

Web/API đã có sau các phase ứng dụng. Dùng Customer `defense07c@example.test`, Admin `admin@example.test` và hai Product **riêng** `DEFENSE-07C-ELE/FAS`; password chỉ local private. Polymorphic demo chọn seed `DEMO-ELE-001`, `DEMO-FAS-001`, **DEMO-HOM-019** để có power/capacity/voltage. Luồng COD → Order mới → đổi price A/B → snapshot giữ A → Dashboard/pipeline → benchmark index 07B. Bản 5 phút giữ PENDING và hủy sau proof; không làm thay đổi seed, không reset/reseed.

07C đã kiểm tra real API/MongoDB và fixture ảnh rỗng trên Web; native Compass capture/input lỗi nên GUI/timed Web rehearsal còn gate thủ công. Đoạn dưới là lịch sử chuẩn bị PHASE03/06B/07B, không dùng câu “chưa có API login/Web” làm mô tả hệ thống hiện tại.

## Lịch sử chuẩn bị PHASE03 và bổ sung các phase sau

**PHASE03: dữ liệu/validator/aggregation/index/roundtrip đã kiểm thử trực tiếp. Chưa rehearsal UI Compass hoặc Web.** MongoDB local chạy với DB ecommerce_dev. Kịch bản Web/API bên dưới dành cho phase ứng dụng sau; không dùng fixture seed để tuyên bố checkout đã chạy.

## Demo DB có thể thực hiện ngay

Kết nối Compass `mongodb://localhost:27017/?replicaSet=rs0`, chọn ecommerce_dev. Không reset giữa demo. Các bộ lọc ObjectId dưới đây dùng trong Compass; count products180/orders100. Bản schema/validator giữ nguyên v1.

1. SV3 mở Products với `sku: DEMO-ELE-001`, `sku: DEMO-FAS-001`, `sku: DEMO-HOM-001`. Electronics có ram/storage/chip, Fashion sizes/colors/material, Home material/assemblyRequired/dimensions; chung collection. Đây là spec demo được biên soạn từ dataset, không phải thông số hãng đã xác minh.
2. SV1/SV3 mở Order `orderCode: DEMO-2026-0001`; xem items/customerSnapshot/shippingAddress embedded. Product DEMO-ELE-001 hiện12triệu, item lịch sử10triệu; snapshots sinh từ Product thật trong seed transaction. Không nói đây là đơn vừa checkout trên Web.
3. SV2 chạy [demo-queries.mongodb.js](../database/evidence/demo-queries.mongodb.js) qua mongosh hoặc shell Compass; file sinh từ pipeline canonical với ISODate. Range2026-07-03T00:00:00Z đến2026-10-01T00:00:00Z exclusive; cohort COMPLETED+PAID/completedAt, timezone Việt Nam. Revenue10.103.259.022VND,60Order,434units; không gồm1.800.000ship. Top5 có match/unwind/group/sort/limit. Canonical JSON trong database/aggregations dùng khoảng tháng9 minh họa. Shell/UI chưa rehearsal; PyMongo đã thực thi pipeline trên DB.
4. SV2/SV3 mở indexes:14declared +6_id_; xem baseline `database/evidence/explain-baseline.json`. Query category/price/sort/limit10: planner và named IXSCAN xem10docs/10keys, natural COLLSCAN xem180docs/0keys. Cả hai0ms ở độ phân giải đồng hồ; không khẳng định benchmark tốc độ.
5. SV3 xuất Product/Order rồi import vào ecommerce_roundtrip bằng commands trong [setup](mongodb-setup.md);180/100, exact BSON equality. DB roundtrip chỉ là slice, User/Category refs trace về DB gốc. DB ecommerce_test trống sau probe rollback.

Tài khoản development nằm trong `.local/demo-credentials.md`; chưa có API đăng nhập. VNPAY attempts là fixture, chưa gọi provider. Pending fixture hợp lệ tại anchor1/10; ở thời điểm demo sau anchor, expiry worker phase sau sẽ cần reseed scenario mới thay vì đổi clock.

## Chuẩn bị

PHASE06B có thể demo bằng Postman/HTTP khi chưa có Web: ADMIN gọi `/admin/orders/:id/confirm`, `/ship`, `/complete` với expectedVersion mới mỗi bước; revenue tăng sau complete đúng subtotal/units, không shipping. Chọn from/to UTC bao phủ completedAt mới, kiểm tra day/month/Top5/category/status. Seed read-only `[2026-07-03T00:00:00Z,2026-10-01T00:00:00Z)` kỳ vọng10.103.259.022VND/434units/100Orders/39Customers. [Review06B](phase-06b-review.md); HTTP evidence dùng ecommerce_test và cleanup fixtures, không sửa seed permanent/completedAt thủ công. UI/gateway không nghiệm thu bởi worker06B.

Verify seed 180 Product/100 Order/3 ngành/2–5 item. Chuẩn bị 1 Customer +1 Admin, Cart trống, Product demo điện thoại giá10 triệu stock đủ, một áo thun. Khóa browser timezone hiển thị Việt Nam, report khoảng bao phủ dữ liệu seed và demo hiện tại. Kết nối replica set trước; không reset giữa kịch bản. Dự kiến VNPAY ở phần bổ sung khi có merchant sandbox/IPN, không thay COD trong demo barem.

## Luồng chính theo 3 SV

1. **SV3 — Compass:** chỉ rõ `products` (tên English đã khóa phase02), document Electronics và Fashion cùng collection; fields chung và attributes ram/storage khác sizes/colors. Cho xem validator `oneOf/productType`; count tối thiểu và count items seed. Giải thích MongoDB tránh bảng con/cột NULL, vẫn validation/index.
2. **SV1 — Web checkout:** Customer thêm điện thoại +áo, chọn address/COD, xem server quote và đặt đơn. Ghi orderCode/ID; không dùng Admin sửa DB để làm giả checkout.
3. **SV3 — Compass snapshot:** mở Order mới: items.productName/sku/priceAtPurchase/attributesSnapshot/selectedAttributes/category snapshot; customer/address embedded. Giá điện thoại10 triệu nằm trong Order. Admin sửa giá Product12 triệu; reload Order Web/Compass vẫn10 triệu. Stock giảm đúng quantity. Không `$lookup` để lấy giá lịch sử.
4. **SV1/SV3 — hoàn tất COD:** Admin đi PENDING→CONFIRMED→SHIPPING→COMPLETED; chuyển PAID hợp lệ. Chưa COMPLETED thì revenue không tăng theo policy thiết kế. Ghi subtotal/ship của Order để so sánh metric.
5. **SV2 — Dashboard:** refresh khoảng ngày gồm hôm nay; Revenue tăng đúng **subtotal** (không shipping), units tăng đúng quantity, Top5 tính từ snapshot. Cho xem pipeline `$match`, `$unwind`, `$group`, `$sort` và network API nhận kết quả aggregate. UI không tải toàn bộ Orders để tự cộng.

Thời gian demo tại Việt Nam; DB timestamps UTC. Nếu hôm nay ngoài dataset anchor, chọn khoảng phù hợp; không sửa completedAt thủ công để ép báo cáo.

## Bằng chứng bổ sung

PHASE07B performance đã pass: dùng database **ecommerce_benchmark** riêng30.000Products/10.000Orders, [bảng BEFORE/AFTER](evidence/performance/benchmark-summary.md) và [talk track30–60s](phase-07b-performance-review.md#defense-talk-track). Natural COLLSCAN vs named/unhinted IXSCAN, docs/keys và exact same results; Category selector30.000→20docs, Revenue/Top510.000→152. Full Product repository có lookup/count khác selector, không lấy20docs làm latency toàn API. Giữ dev180Products/100Orders/41Users, không demo drop index dev. Rehearsal Compass screenshots thuộc07C;07B chỉ tạo JSON/text evidence và để benchmark dataset sẵn. [Script setup/run/reproduce/cleanup](../scripts/performance/README.md).

- CRUD: tạo/sửa/ẩn Product; tạo Category, duplicate validation; thử DELETE referenced Category→409. Show Postman API contract nếu được hỏi.
- **SV2+SV3 — performance:** query thật trên collection benchmark riêng; baseline natural scan và compound index; show winningPlan/COLLSCAN/IXSCAN, totalDocsExamined/totalKeysExamined/executionTimeMillis, client p50/p95. Không hứa thời gian giảm trên data100; explain cardinality là evidence.
- **SV3 — Compass roundtrip:** export Product/Order Extended JSON, import vào DB test riêng, verify type/count và reapply validators/indexes.
- **VNPAY bổ sung:** sandbox thành công, browser return chỉ chờ backend/IPN; callback repeat không double-update. Nếu credentials/IPN chưa có, ghi rõ chưa demo được, không nói đã hoàn thành.

## Tình huống dự phòng

Chuẩn bị seed/asset local và script verify, không phụ thuộc internet cho COD/Compass/aggregation. Nếu stock thiếu/quote đổi, UI báo lấy quote mới; dùng scenario đã rehearsal. Nếu fail topology/API, dừng ghi evidence lỗi và khắc phục, không thay bằng ảnh rồi gọi demo sống. Backup recording chỉ hỗ trợ giải thích, không thay yêu cầu demo trực tiếp.

## Checklist rehearsal

- [ ] Web/API/Compass trỏ cùng DB demo, account/permissions đúng.
- [ ] Dữ liệu tối thiểu và validators pass, index/pipeline có artifacts.
- [ ] Đặt đơn2 item, snapshot proof giá10→12 triệu pass.
- [ ] Transition COD đúng, Dashboard delta chính xác, Top5 và ngày/tháng hoạt động.
- [ ] Explain/index và latency đã đo, results metadata lưu artifacts.
- [ ] Import/export BSON roundtrip pass, không xóa data đang demo.
- [ ] Mỗi SV giải thích được phần mình, giải thích ánh xạ tên đề sanpham/hoadon sang products/orders đã khóa.
