# Hướng dẫn coding agent

## 1. Project Overview

Đồ án NoSQL cho nhóm 3 sinh viên: sàn thương mại điện tử đa ngành, giỏ hàng, đặt hàng và Dashboard Admin. MongoDB là CSDL nghiệp vụ chính. Barem và phạm vi người dùng giao là ràng buộc cao nhất của project, trong giới hạn chỉ dẫn của môi trường chạy agent.

**Trạng thái: PHASE04 đã duyệt; PHASE05A Auth/User backend hoàn thành, dừng để review.** Thiết kế MongoDB v1 giữ nguyên: local rs0,6 validators,14 declared indexes, seed180 Product/40 User/100Order. PHASE05A có13 Auth/User/Admin User endpoints,213 tests pass (80 foundation +133 Auth/User),20 HTTP checks thật; fingerprint dev documents/validators/indexes giữ nguyên. Access JWT/Argon2id/live DB role-status-tokenVersion giữ strategy cũ; refresh/logout endpoint không có, frontend chưa làm trong phiên này. Evidence backend/evidence/phase05a-*, review docs/phase-05a-review.md, contract docs/api-contract.md, setup docs/backend-setup.md; DB evidence tại database/evidence. Các feature ngoài Auth/User do phase/worker riêng xử lý, không được nghiệm thu bởi PHASE05A; chưa benchmark đầy đủ. Chỉ thực hiện phase tiếp theo khi người dùng yêu cầu.

**Bàn giao PHASE05B Catalog — hoàn thành backend, dừng để review:** 14 Category/Product public/Admin method/path, normalized Vietnamese search, filters/sorts/pagination, polymorphic attributes và guarded transactions/version patch đã IMPLEMENTED. Full workspace325 tests pass (112 Catalog +80 foundation +133 Auth/User từ phiên khác); HTTP/explain và fingerprint dev giữ nguyên ở backend/evidence/phase05b-*. Review docs/phase-05b-review.md, contract docs/api-contract.md. Không triển khai Cart/Checkout/Order/Payment/Dashboard/Frontend trong phiên này; không tự bắt đầu phase tiếp theo. PHASE05A và evidence của phiên khác được giữ nguyên.

**INTEGRATION CHECKPOINT 05AB PASS:** Full source tích hợp 325 tests pass/0 fail/error/skip,35 HTTP checks pass,7 blueprints/28 method-path không collision; Auth/User13 +Catalog14 +health1 cùng tồn tại, shared foundation duy nhất, dev fingerprint giữ nguyên. Evidence backend/evidence/phase05ab-*, review docs/phase-05ab-integration-review.md. READY FOR COMMERCE BACKEND; chưa bắt đầu Cart/Checkout/Orders/Frontend, chỉ tiếp tục khi người dùng giao. Workspace chưa có Git HEAD; source manifest được lưu trong integration evidence.

## 2. Tech Stack

- Frontend contract: React, Vite, TypeScript, Tailwind CSS, Recharts; shadcn/ui DEFERRED. Frontend do agent khác triển khai sau.
- Backend: Python, Flask, PyMongo; JWT, Argon2id cho password.
- Database: MongoDB Community8.0 local replica set rs0/WiredTiger; Compass demo. Atlas deployment DEFERRED, không dùng Atlas-only features.
- Payment: COD và VNPAY Sandbox; không tích hợp tiền thật.
- Công cụ: Git, Postman; backend pytest9.1.1 đã chọn/kiểm thử; frontend/E2E runner chưa bootstrap.
- Python target3.12; kiểm thử bằng3.12.14, MongoDB8.0.32, Flask3.1.3/PyMongo4.15.3. Backend runtime/dev locks tại backend/requirements.lock.txt và requirements-dev.lock.txt; DB tooling pins tại scripts/db/requirements.lock.txt giữ nguyên. Design/defaults khóa tại docs/foundation-decisions.md.

## 3. Architecture Rules

Modular monolith: React gọi REST `/api/v1`; Flask có API → service → repository → MongoDB. API xử lý HTTP/auth/serialization, service giữ nghiệp vụ, repository giữ truy vấn; không đặt nghiệp vụ trong component hoặc route. Aggregation chạy trong MongoDB, frontend chỉ hiển thị kết quả. Một module theo feature có thể nằm trong nhiều tầng; không tạo microservice.

## 4. MongoDB Rules

- Chung collection `products`, discriminator `productType`, thuộc tính linh hoạt trong `attributes`.
- `orders.items`, khách hàng, địa chỉ và category tại lúc mua là snapshot nhúng. Không `$lookup` Product để khôi phục giá/lịch sử hoặc tính báo cáo.
- Cart tham chiếu Product; giá hiển thị là báo giá hiện tại, chỉ snapshot khi tạo Order.
- Tiền là số nguyên VND, BSON `long`, không float; ngày BSON Date UTC, ID ObjectId.
- Không nhúng toàn bộ lịch sử đơn/review vào User/Product; không tạo collection riêng cho từng ngành.
- Mỗi index phải có query pattern và evidence; nguồn thiết kế tại ADR-005.
- MongoDB không có foreign key tự động: service kiểm tra reference và dùng transaction khi invariant trải nhiều document.
- Không thay database, collection hay schema đã thống nhất mà không cập nhật decision/migration.

## 5. Before Coding Protocol

Trước mỗi task:

1. Đọc `AGENTS.md` và `docs/architecture.md`.
2. Chỉ đọc `docs/database-schema.md` nếu task liên quan dữ liệu.
3. Chỉ đọc `docs/business-rules.md` nếu task liên quan nghiệp vụ.
4. Đọc `docs/api-contract.md` khi task liên quan API và đúng `docs/features/<feature>.md`; xem bảng routing trong architecture. Foundation có docs/features/backend-foundation.md và backend/README.md.
5. Inspect source trực tiếp được file feature chỉ ra; nếu chưa tồn tại, xác định file dự kiến cần tạo.
6. Xác định dependency trực tiếp và contract ảnh hưởng; chỉ mở thêm module có dependency thật.
7. Nêu phạm vi, acceptance criteria và cách kiểm tra rồi mới code, khi phase đã được phép.

Task thuần docs áp dụng bước đọc theo nội dung cần sửa. Nếu task chưa có feature doc, viết doc trước implementation.

## 6. Context Management Rules

Không đọc toàn bộ repo theo thói quen. Search có mục tiêu trong module; không dump lockfile, build, dataset hay tất cả feature docs. Chỉ đọc phần schema/business rule cần thiết qua mục lục. Ghi rõ dependency vừa phát hiện. Nếu tài liệu và source mâu thuẫn, phân tích và sửa nguồn đúng; không mặc định source thắng.

Thứ tự nguồn sự thật: requirement/barem trong `docs/requirements.md` + chỉ dẫn người dùng hiện hành → AGENTS → architecture → database-schema → business-rules → feature docs → implementation. `docs/requirements-source.txt` và `docs/requirements-phase-02-source.txt` giữ nguyên yêu cầu từng phase. Người dùng phase02 đã chốt English collection names; các OQ phase01 đã resolve/defer theo docs/foundation-decisions.md. Không tạo lại OPEN đã được chốt.

## 7. Feature Documentation Rules

Mỗi feature có đủ: Goal, Actors, Functional Requirements, Business Rules, Permission, API, Data, Validation, Edge Cases, Security, UI Behavior, Acceptance Criteria, Testing Checklist. API ghi method/path/request/response/error; dùng envelope từ api-conventions. Ghi dependencies và source path dự kiến trong Data. Ghi `OPEN QUESTION`/`DECISION PENDING` cho điều chưa chốt; không dùng placeholder chung chung. Behavior đổi phải sửa tài liệu cùng change.

## 8. Naming Conventions

- Collection: plural English `snake_case`; field BSON/JSON: `camelCase`; enum: `UPPER_SNAKE_CASE`.
- Python: `snake_case`, class `PascalCase`; React component `PascalCase`, hook `useX`, TypeScript field `camelCase`.
- File tài liệu: `kebab-case.md`; module Python `snake_case.py`; route URL: plural `kebab-case`.
- API ID là `id` chuỗi hex 24 ký tự; DB `_id` là ObjectId. Không đổi tên cùng một field giữa API và DB ngoài `_id` → `id`.
- Tiếng Việt dùng cho nội dung UI/docs; tên kỹ thuật thống nhất English.

## 9. API Conventions

Theo `docs/api-conventions.md`: `/api/v1`, JSON envelope, HTTP status đúng, pagination giới hạn, allowlist filter/sort, Bearer JWT. Ownership enforced ở backend. Không nhận client price trong luồng mua hàng hoặc role/orderStatus tùy ý; Admin Product price mutation theo allowlist/version contract. Trạng thái endpoint đã IMPLEMENTED/PLANNED theo `docs/api-contract.md`; Health/Auth/User/Catalog đã có API thực. Không đánh dấu feature IMPLEMENTED chỉ vì đã có auth/validation primitives.

## 10. Testing Rules

Theo `docs/testing-strategy.md`. Kiểm tra contract, validation, authorization, ownership; snapshot sau đổi giá; checkout đồng thời, retry/idempotency, callback trùng, rollback tồn kho; aggregation bằng fixture có số kỳ vọng. Test transaction trên replica set thật, không chỉ mock. Không báo DONE nếu test fail hoặc chưa chạy mà không nêu rõ.

## 11. Change Policy

Không refactor ngoài phạm vi, thêm role/dependency/collection hoặc đổi API tùy tiện. Với thay đổi lớn: mô tả vấn đề → phương án và trade-off → ADR và tác động dữ liệu/API/tests → thực hiện khi yêu cầu hiện hành cho phép. Không tự sinh yêu cầu Seller/Shipper/Staff, coupon, refund, guest checkout hay quản lý tồn theo biến thể. Sửa lỗi nhất quán nội bộ nhỏ không cần hỏi lại; ghi decision nếu ảnh hưởng contract.

## 12. Definition of Done

Feature DONE khi code chạy, API và UI hoạt động, validation/authorization đúng, test liên quan pass, edge case chính được kiểm tra, docs cập nhật, không lỗi runtime đã biết. Nêu checks thực chạy và giới hạn còn lại. Phase02 DONE là khóa thiết kế/kiểm tra tĩnh; phase03 DONE là local rs0 + validators/indexes + seed/aggregation/constraint/roundtrip/reseed trên DB thật. Phase04 DONE là foundation startup/HTTP health + pytest thật + DB contract/data giữ nguyên + API/context docs; không đồng nghĩa business app/auth/payment/frontend hoặc benchmark đầy đủ DONE.
