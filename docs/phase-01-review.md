# Review PHASE01 — lịch sử đã được chấp nhận

**ARCHIVED CONTEXT:** Người dùng đã chấp nhận cấu trúc phase01. Các OPEN/bước tiếp bên dưới phản ánh trạng thái cũ, không chỉ dẫn đang hiệu lực. Xem [foundation decisions](foundation-decisions.md) và [phase02 review](phase-02-review.md) cho resolved/deferred/current state.

## Inventory

Repo ban đầu trống, không có source hay Git. Tạo AGENTS/README/env/gitignore, docs nền tảng + schema/rules/REST/test/seed/demo, 6 ADR và 14 feature docs; skeleton app/database/scripts/tests với `.gitkeep`. Giữ root `tmdt/` thay vì lồng thư mục ecommerce không cần thiết. Không cài dependency, chạy DB, seed hoặc implement business API/UI.

## Quyết định được chọn cho bộ thiết kế

MongoDB + Flask/PyMongo modular monolith, React/Vite/Tailwind/Recharts; Product discriminator/attributes chung collection; Order embedded immutable snapshot; Cart riêng/User; payment_attempts riêng; tiền integer VND; checkout replica-set transaction/quote/idempotency; index theo query và benchmark tách; source-of-truth và đọc context theo feature. Không Seller/Shipper/Staff. Reviews tùy chọn. “Chọn” ở đây là baseline tài liệu, chưa tuyên bố người dùng đã review/approve.

## OPEN QUESTIONS / DECISION PENDING

| ID | Cần quyết định | Đề xuất để review | Ảnh hưởng / cần trước bước |
| --- | --- | --- | --- |
| OQ-01 | Tên vật lý products/orders hay sanpham/hoadon theo đề gốc? | Theo request mới products/orders; xác nhận giảng viên chấp nhận ánh xạ | Bootstrap collections/Compass, không tạo hai bộ |
| OQ-02 | Mongo local replica set hay Atlas, versions Python/Node/Mongo/packages? | Local replica set để demo offline; Atlas nếu đã có tài khoản | Bootstrap/transaction/CI; không pin đoán versions |
| OQ-03 | Frontend TypeScript/JavaScript, shadcn/ui? | TypeScript; shadcn/ui nếu thực cần | Scaffold/frontend conventions |
| OQ-04 | Search token hay substring; yêu cầu dấu/không dấu? | Chọn text/token baseline sau test tiếng Việt; không hứa fuzzy | Search query/index/acceptance |
| OQ-05 | VNPAY merchant secrets, IPN công khai, URL return, scheduler expiry và xử lý tiền về muộn? | Sandbox credentials riêng; explicit periodic expiry script; manual review late success | Payment implementation/rehearsal; COD độc lập |
| OQ-06 | Phí ship/quote TTL/giữ hàng TTL và giới hạn arrays/price/report window? | Shipping flat configurable; giới hạn ở schema là đề xuất; không gán phí/TTL khi chưa rõ | Quote/checkout validator/policy |
| OQ-07 | Có triển khai Review? | Làm sau P0/P1 nếu thời gian đủ | Tạo collection/routes/tests Review |
| OQ-08 | Doanh thu theo completedAt của COMPLETED+PAID, excl ship có đáp ứng cách giảng viên đánh giá? | Dùng baseline đã mô tả; UI ghi rõ dateBasis/revenueBasis | Dashboard acceptance/seed expected results |
| OQ-09 | Media local hay dịch vụ ngoài? Ai phụ trách Auth/Cart/Payment trong 3 SV? | Local assets/fallback, nhóm bổ sung ownership sprint | Admin form/seed/UI/tiến độ |

Không cần chốt tất cả để review docs, nhưng không implement phần phụ thuộc quyết định chưa có. Agent sau ưu tiên thông tin mới nhất của người dùng và cập nhật ADR/docs khi chốt.

## Phase kế tiếp sau review

1. Resolve OQ-01/02/03, bootstrap và khóa dependencies, config validation, health endpoint/test DB.
2. Apply/test JSON Schema/index; create seed/verify reproducible và account demo bảo mật.
3. Auth/User + Category/Product CRUD, public catalogue/search theo OQ-04.
4. Cart/Quote/Checkout/Order transaction, snapshot, COD và cancellation/concurrency tests.
5. Aggregation Dashboard, benchmark evidence, Compass import/export, rehearsal barem.
6. VNPAY theo OQ-05/06; User/Order admin hoàn thiện, UI/E2E; Review nếu chọn.

Task nhỏ nên giao theo feature doc, ghi acceptance criteria và chỉ inspect source paths trực tiếp. Không bắt đầu phase 02 tự động vì docs đã đủ.

## Definition of Done phase tài liệu

- [x] Barem truy vết, stack/scope/roles rõ.
- [x] Mô hình dữ liệu có fields/types/invariants/JSON Schema đa hình và embedded.
- [x] Snapshot, stock/callback/idempotency, metric semantics có baseline rõ.
- [x] 14 feature docs cùng format, endpoints và test checklist thiết thực.
- [x] Trade-off Cart/embed/reference/index có ADR; uncertain decisions được gắn OPEN.
- [x] Seed/performance/demo là kế hoạch, không claim đã chạy.
- [x] Người dùng đã review và chấp nhận cấu trúc phase01, yêu cầu phase02 lock design.

Kiểm tra tĩnh đã thực hiện: đủ14 feature docs theo đúng13 section/order;32 file Markdown;21 liên kết tương đối hợp lệ;4 JSON code blocks parse được;26 thư mục skeleton; bản copy requirement trùng SHA-256 với file người dùng; không có file implementation Python/JS/TS. Runtime validator/pipeline, benchmark và test ứng dụng **chưa được xác minh** ở phase này. Những kiểm tra này chỉ xác nhận cấu trúc/cú pháp tài liệu, không thay thế test MongoDB.
