# Đối chiếu barem đồ án Novamart

Barem gốc là nguồn yêu cầu, không phải cam kết điểm do agent tự chấm. Tài liệu này chốt trạng thái kỹ thuật20/10/2026; báo cáo lịch sử giữ nguyên kết quả từng lần chạy.

| Mục | Điểm tối đa | Phần đã có | Evidence trực tiếp | Việc còn cần nhóm thực hiện |
| --- | ---: | --- | --- | --- |
| Giải trình ưu điểm MongoDB cho sản phẩm thuộc tính khác nhau |1.0| Báo cáo phân tích document/attributes, trade-off so với cột cố định;3ngành chung products | [Báo cáo §3](final-project-report.md#3-lựa-chọn-mongodb), [schema](database-schema.md), [ADR001](decisions/001-mongodb-modeling.md) | SV1 trình bày và chỉ document trong Compass |
| JSON Schema đa hình và Order nhúng |1.5| Canonical products discriminator/oneOf, orders.items/customer/address/category snapshots; BSONlong/Date/ObjectId | [products validator](../database/validators/products.json), [orders validator](../database/validators/orders.json), [snapshot receipt](../backend/evidence/defense-demo-final-20261020.json) | SV3 mở GUI, SV1 giải thích snapshot không lấy giá Product sống |
| CRUD Category/Product và tạo Order |2.5| Public/Admin API+UI, validation/auth/version guards, COD checkout transaction | [API contract](api-contract.md), [66HTTPSchecks](../backend/evidence/full-audit-20261020-public.json), [714tests](../backend/evidence/full-audit-20261020-tests.json) | Nhóm demo đúng tài khoản/luồng và thao tác được CRUD |
| Snapshot và Aggregation thời gian/Top5 |2.5| Immutable snapshot;8canonical pipelines; match/unwind/group/sort, doanh thu qualified theo completedAt, không shipping | [Top5](../database/aggregations/top-products.json), [revenue-day](../database/aggregations/revenue-day.json), [audit DB/query](../backend/evidence/full-audit-20261020-final-integrity.json) | SV2 chạy/giải thích đúng range; demo Product đổi giá không đổi Order |
| Dummy data |1.0| Seed180Products/3ngành,100Orders mỗi2–5items,40Users; live có thêm fixture được giữ có chủ đích | [seed strategy](seed-strategy.md), [manifest](../database/evidence/seed-manifest-ecommerce_dev.json), [current counts](../backend/evidence/defense-final-integrity-20261020.json) | Phân biệt seed theo định mức và live counts, không reset để ép count |
| Demo sống |1.5| Web/API/journeys, Dashboard, local fallback, benchmark và export/import PyMongo đã có evidence | [5phút](demo-script-5min.md), [10phút](demo-script-10min.md), [performance](phase-07b-performance-review.md), [export/import](../backend/evidence/defense-export-import-20261020.json) | **Còn Compass GUI và rehearsal3SV có bấm giờ**; PyMongo không thay thao tác GUI |

Phần bổ sung ngoài barem gốc nhưng người dùng đã giao: Auth/User/address/search/order management, VNPAY Sandbox, SKU stock/price và verified reviews. Đã có implementation và evidence; không tự thêm Seller/Shipper/Staff/refund/coupon hoặc payment tiền thật.

Kết luận: **các chức năng kỹ thuật chính đã triển khai và kiểm thử; chưa thể gọi toàn bộ hồ sơ nộp và phần bảo vệ của nhóm hoàn tất** khi chưa điền thông tin báo cáo/định dạng nộp và chưa thực hiện các bước người thật. [Checklist nộp](submission-checklist.md) là danh sách còn lại.
