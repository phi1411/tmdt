# Phạm vi và truy vết yêu cầu

## Nguồn

Đề gốc người dùng gửi trong chat: thang 10 điểm, MongoDB, nhóm 3 SV. Yêu cầu phase01 được giữ nguyên tại [requirements-source.txt](requirements-source.txt); phase02 tại [requirements-phase-02-source.txt](requirements-phase-02-source.txt). Ngày lập tài liệu: 07/10/2026. Các lựa chọn thiết kế bổ sung được gắn ADR hoặc OPEN; không phải yêu cầu mới từ giảng viên.

## Barem → thiết kế → bằng chứng cần làm

| Mục | Điểm | Tài liệu | Bằng chứng ở phase implementation |
| --- | --- | --- | --- |
| Giải thích MongoDB/thuộc tính không cố định | 1.0 | database-schema, ADR-001 | Hai sản phẩm khác ngành trong một collection; giải thích trade-off |
| Polymorphic JSON Schema + Order embedded | 1.5 | database-schema, ADR-002/003 | Validator và document Compass; đơn có mảng snapshot |
| CRUD Category/Product + tạo Order | 2.5 | categories, products, admin-products, checkout | API/Postman và Web quản lý/tạo đơn |
| Snapshot giá và pipeline | 2.5 | orders, admin-dashboard, ADR-003/005 | Đổi giá không đổi đơn cũ; `$match/$unwind/$group/$sort`, doanh thu và Top 5 |
| Dummy Data | 1.0 | seed-strategy | >=100 Product, >=3 ngành; 50–100 Order, mỗi đơn 2–5 item |
| Demo sống | 1.5 | demo-plan, testing-strategy | Compass + checkout Web + Dashboard; đo/index, import/export |

Đề gốc gọi `sanpham`/`hoadon`; người dùng phase02 đã khóa tên vật lý English `products`/`orders` cùng bốn collection MVP khác. Ánh xạ thuật ngữ đề được ghi rõ; OQ-01 RESOLVED theo chỉ dẫn mới, không tạo duplicate collections.

## Phạm vi ưu tiên

- **P0 — bám barem:** Category/Product CRUD, dữ liệu đa hình, Cart/Checkout COD, Order snapshot, Dashboard doanh thu theo thời gian/Top 5, seed, index/explain, Compass và demo.
- **P1 — sản phẩm người dùng yêu cầu:** JWT, profile/địa chỉ, search/filter, lịch sử/hủy đơn, quản lý User/Order, các metric Dashboard bổ sung và VNPAY Sandbox. Đây vẫn là phần dự kiến phải hoàn thành, chỉ làm sau P0.
- **Follow-up hiện hành:** Reviews và tồn kho/giá theo SKU đã được người dùng giao bổ sung, triển khai và kiểm thử theo [ADR013](decisions/013-sku-review-hardening.md) và [review](sku-review-hardening-review.md); shadcn/ui vẫn DEFERRED. Quyết định không tạo reviews ở phase02 là lịch sử, không là kiến trúc hiện tại.
- **Ngoài phạm vi hiện tại:** Seller/Shipper/Staff, marketplace nhiều người bán, payment production, refund tự động, coupon, guest checkout, tải media lên dịch vụ ngoài.

Target seed: 180 Product (60 mỗi ngành), 40 User (1 Admin + 39 Customer), đúng 100 Order với 2–5 item; chọn trong mức yêu cầu, không biến 180 thành định mức giảng viên mới. Demo tạo thêm đơn làm count live tăng; định mức áp dụng bộ seed sạch.

## Trách nhiệm nhóm

| Người | Chịu trách nhiệm | Bàn giao |
| --- | --- | --- |
| SV1 | Schema, Category/Product API, tạo Order | Validator/CRUD, snapshot và checkout transaction phối hợp SV3 |
| SV2 | Aggregation, compound index | Pipeline, metric contract, explain/benchmark với SV3 |
| SV3 | Seed, Compass import/export, Web/Dashboard, hiệu năng, demo | Fixture reproducible, frontend, bằng chứng và điều phối |

Auth/Cart/Payment cần phân công bổ sung khi lập sprint, không tự thay vai trò 3 SV. Feature có API/UI hai phần phối hợp cùng contract, không chia ownership dữ liệu khác nhau.

## Trạng thái

Hiện20/10/2026: các nhómP0/P1 có API/UI/evidence, SKU/reviews theo ADR013; VNPAY Sandbox realWeb/testOTP/automaticIPN và bộ SIT chính thức6/6Đạt. Xem [audit](full-project-audit-20261020.md), [payment review](vnpay-sandbox-final-review.md) và [báo cáo tổng hợp](final-project-report.md). Compass GUI và rehearsal3SV có bấm giờ vẫn cần người thật; offlineOS là kiểm tra dự phòng chưa thực hiện, không phải yêu cầu mới của barem. Các đoạn theo phase bên dưới là lịch sử.

PHASE07B nghiệm thu performance evidence riêng: real MongoDB explain/compound index/cardinality/repeated latency, benchmark dataset tách dev, index audit/storage và reproducible scripts. [Review07B](phase-07b-performance-review.md), [evidence](evidence/performance/README.md). Không thay barem/scope/schema/business rules; đây là bằng chứng đo mới, không claim feature/UI/deployment hoặc Compass07C completion. Các DEFERRED/NOT_MEASURED ở đoạn lịch sử05C bên dưới giữ ngữ cảnh thời điểm đó.

Phase01 tạo docs/thư mục; phase02 khóa thiết kế và tạo declarative artifacts/checker tĩnh. Các phase tiếp theo có evidence riêng: PHASE03 MongoDB/seed, PHASE04 foundation, PHASE05A Auth/User, PHASE05B Catalog và PHASE05AB integration đã pass. PHASE05C triển khai backend Cart/Checkout COD/Order snapshot/history/cancel theo yêu cầu hiện hành, [review](phase-05c-review.md). VNPAY gateway/online creation, Admin Orders/Dashboard/Frontend/demo Web và full benchmark vẫn DEFERRED/NOT MEASURED. Barem/scope không đổi; backend completion không đồng nghĩa hoàn thành đồ án hoặc frontend.
