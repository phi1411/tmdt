# PHASE05A — Authentication + Users review

Ngày07/10/2026. PHASE04 đã được người dùng duyệt. Auth/User backend hoàn thành trong phạm vi worker này và **dừng để review**, không tự triển khai phase tiếp theo. Frontend chưa làm. Thiết kế MongoDB v1/JWT foundation/Argon2id/roles giữ nguyên.

## 1. Endpoint đã implement

13 endpoints dưới `/api/v1`, đã chạy test với rs0 thật và HTTP server thật:

| Nhóm | Method / path |
| --- | --- |
| Auth | POST /auth/register; POST /auth/login; GET /auth/me; PATCH /auth/password |
| Profile | GET /users/me; PATCH /users/me |
| Address | POST /users/me/addresses; PATCH /users/me/addresses/:id; DELETE /users/me/addresses/:id; PATCH /users/me/default-address |
| Admin User | GET /admin/users; GET /admin/users/:id; PATCH /admin/users/:id/status |

Chi tiết request/response/auth/role/error từng endpoint trong [API contract](api-contract.md).

## 2. Business rules áp dụng

- Register chỉ CUSTOMER ACTIVE; email trim/lowercase, unique index xử lý cả signup đồng thời; không strip dot/plus. Name/phone chuẩn hóa và strict required/unknown-field validation; không nhận role/status/hash/security fields từ client.
- Password12..128 ký tự, Unicode/space được giữ nguyên, Argon2id m19456/t2/p1; không plaintext hoặc hash trong response/log.
- Login wrong/unknown/blocked/corrupt hash cùng generic401. Unknown account verify dummy hash. Body không hợp lệ422; malformed JSON400/content type415 theo foundation.
- Ownership lấy subject; Customer chỉ quản lý dữ liệu mình, địa chỉ của người khác404. Admin không sử dụng Customer profile API.
- Mutation User version tăng nguyên tử với expectedVersion strict; CAS còn check role/status/tokenVersion, không lost update khi race. Bounds BSON int không overflow.
- Profile/address/status không ghi lại Order snapshot. Test fixture Order giữ nguyên sau đổi profile/address và block.

## 3. Auth/token strategy cuối cùng

JWT access HS256 dùng issuer/audience/config/claims foundation; TTL mặc định1800s. Không role browser/JWT-only authorization: mỗi request guard đọc lại ACTIVE/current role/tokenVersion từ DB. Đổi password và status thực sự tăng tokenVersion/version cùng write, vô hiệu mọi token cũ. Unblock không làm token cũ hợp lệ trở lại. Đổi password trả `{reauthenticationRequired:true}`, login lại; concurrent password changes chỉ một thành công, block giữa verify/write ngăn đổi password.

Logout UI chỉ xóa token memory; không server logout/revoke endpoint, không refresh/forgot/email verification/social login theo baseline đã khóa. publicUser/account chỉ id/name/email/phone/role/status/version/createdAt; internal tokenVersion/passwordHash/schemaVersion không lộ.

Rate limit local per-process/thread-safe, window60s: login30/IP+10/email; register10/IP; password30/IP+10/subject. Input malformed vẫn tính IP, normalized credential dùng chung account bucket; không tin X-Forwarded-For. Keys HMAC/random process secret, max10.000 active buckets,429 với Retry-After. Restart reset limits; production/distributed limiter chưa triển khai.

## 4. Profile/address

GET profile chứa addresses/version/defaultAddressId/updatedAt; PATCH chỉ name/phone và phải có ít nhất một editable field. Phone profile có thể empty; nonempty/address phone8..15 digits với + tùy chọn. Address add/update/delete/default bounded10; ID do server tạo, không collection riêng. Add không tự chọn default, xóa default reset null cùng write. CRUD/default increments version, không revoke JWT. DELETE204 không body, client refetch version. Concurrent add khi9 địa chỉ chỉ một winner; race default vs delete không tạo dangling reference.

## 5. Admin User

ADMIN list/detail public-safe, search q<=100 normalized literal substring name/email, escaped regex; role/status allowlist, pagination1/20 max100 và stable createdAt/_id DESC. Không địa chỉ/hash/security fields trong response. Customer endpoints Admin luôn403. List count/page là hai reads, không snapshot transaction; không thêm index.

Status chỉ đổi Customer ACTIVE/BLOCKED. Mọi Admin target (kể cả self/same-status)409, không create Admin/role mutation/reset-password hộ/xóa account. Same-status200 no-op với expectedVersion đúng, giữ version/tokenVersion/updatedAt. Stale409; concurrent status changes chỉ một winner, không cascade Order.

## 6. Test/result và evidence

- Python3.12.14, pytest9.1.1, Flask3.1.3, PyMongo4.15.3, MongoDB8.0.32/rs0; không đổi dependency/locks.
- **213 passed,0 failed/error/skipped**:80 foundation+133 Auth/User. [JUnit](../backend/evidence/phase05a-pytest.xml).
- **20 HTTP checks thật**, temporary threaded server trên owned ecommerce_test, bao phủ13 endpoints và block/unblock/password revocation. [HTTP evidence](../backend/evidence/phase05a-runtime-verification.json).
- Test fixtures guard database suffix/marker/project/topology; cleanup đúng ID/email, không drop/reset. ecommerce_test6 collections rỗng sau cleanup.
- Dev fingerprint toàn bộ documents/options/validators/indexes trước/sau trùng; counts users40/categories3/products180/carts0/orders100/payment_attempts30. Baseline immutable ignored `.local/phase05a-db-before.json`; evidence không chứa secrets/hashes/raw documents.
- Không claim frontend/checkout/payment transaction/E2E/full benchmark pass. [Cách chạy lại](backend-setup.md).

## 7. API contract/documentation

[api-contract](api-contract.md) đánh dấu13 endpoints IMPLEMENTED, mỗi row có method/path/auth/role/request/response/error. [auth](features/auth.md), [users](features/users.md), [admin-users](features/admin-users.md) cập nhật behavior/source paths/checklists. Context AGENTS/architecture/backend README/setup/testing/API conventions cập nhật status; evidence PHASE04 giữ nguyên.

## 8. Files tạo/sửa bởi worker này

Paths dưới đây tương đối project root; source cùng API → service → repository, schema/DTO allowlist:

- Tạo: `backend/app/api/auth.py`, `users.py`, `admin_users.py`.
- Tạo: `backend/app/services/auth_service.py`, `user_service.py`.
- Tạo: `backend/app/schemas/auth_schema.py`, `user_schema.py`, `admin_user_schema.py`, `user_response.py`.
- Tạo: `backend/app/auth/rate_limit.py`, `backend/tests/test_auth_users.py`, `scripts/backend/verify_auth_users.py`, `docs/phase-05a-review.md`, `backend/evidence/phase05a-pytest.xml`, `phase05a-runtime-verification.json`.
- Sửa dependency trực tiếp: `backend/app/__init__.py` (dummy hash/limiter init), `backend/app/api/__init__.py` (register3 Auth/User blueprints, giữ registration từ worker khác), `backend/app/repositories/user_repository.py`, `backend/app/auth/passwords.py` (docstring).
- Sửa docs: `AGENTS.md`, `docs/architecture.md`, `docs/api-contract.md`, `docs/api-conventions.md`, `docs/backend-setup.md`, `docs/testing-strategy.md`, `docs/features/auth.md`, `users.md`, `admin-users.md`, `backend-foundation.md` (historical foundation scope), `backend/README.md`, `backend/evidence/README.md`.
- Local ignored evidence mới: `.local/phase05a-db-before.json` chỉ digest/counts, không credentials.

## 9. Issues/deferred và workspace phối hợp

Không có lỗi runtime đã biết trong phạm vi đã kiểm tra. UI/frontend, distributed limiter/production proxy, refresh/forgot/email verification/social login, full benchmark/deployment và các feature khác không thuộc PHASE05A.

Workspace có thay đổi Catalog/Product của worker khác xuất hiện trong lúc chạy test; phiên này giữ nguyên và không review/claim DONE cho chúng. Scoped JUnit chỉ chạy3 test modules foundation/auth, tránh phụ thuộc test chưa nghiệm thu của worker khác. Không có Git repository trong workspace hiện tại, nên không có commit/diff Git; manifest trên ghi các paths worker này đã chỉnh.

Backend development trên127.0.0.1:5001 đã restart đúng process có command line trỏ `backend/run.py`; health200 và `/api/v1/auth/me` thiếu token401. Kiểm tra links của review/features Auth/User đạt; một số docs dùng chung được worker Catalog cập nhật đồng thời và tham chiếu `phase-05b-review.md` chưa có tại thời điểm kiểm tra. Đây là tài liệu ngoài phạm vi worker này, không tự tạo hoặc thay nội dung review Catalog.

## 10. Xác nhận phạm vi

Worker này **không sửa implementation Product/Category/Cart/Checkout/Order/Payment/Dashboard/Frontend**, không schema/validator/index/dependency change, không reset ecommerce_dev. Shared factory/blueprint registry và context docs được sửa vì dependency trực tiếp; các registration Catalog từ worker khác giữ nguyên. Order chỉ được đọc seed và clone fixture vào test DB để kiểm tra snapshot; không implement hoặc sửa Order module.

PHASE05A dừng để review. Không bắt đầu feature tiếp theo.
