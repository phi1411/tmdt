# Flask backend — Auth/User + Catalog + Commerce + Payment

Render preparation14/10/2026: production Waitress entrypoint `serve.py`, dependency file `requirements-render.txt`, separate Atlas config and build-time frontend API URL are ready. Full674backendtests PASS; public hosting pending. See [review](../docs/render-deployment-review.md) and [deployment guide](../docs/render-deployment-guide.md). Local runner/settings remain available; no auto-seed/expiry worker in production startup.

PHASE06A thêm3 Payment endpoints qua `api/payments.py` → PaymentService/VnpayProvider → Order/PaymentAttempt/Product repositories. Checkout VNPAY atomic initial attempt, URL sau commit, Return read-only, IPN authoritative/idempotent, expiry worker riêng30s. [Payment setup](../docs/payment-setup.md), [review06A](../docs/phase-06a-review.md). Live Sandbox thiếu merchant/IPN config; COD giữ nguyên. Không Frontend/Admin Dashboard/schema change trong worker06A; các ghi chú phase trước bên dưới là lịch sử.

PHASE06B thêm11Admin Orders/Dashboard endpoints: `api/admin_orders.py`, `admin_dashboard.py` → OrderService/DashboardService → OrderRepository/DashboardRepository; schemas `admin_order_schema.py`, `dashboard_schema.py`.8canonical pipelines chạy MongoDB thật, snapshot/no live history lookup; COD completion/cancel giữ transaction/version. [Review06B](../docs/phase-06b-review.md), [API contract](../docs/api-contract.md). Không Frontend/gateway/schema change trong worker06B; ghi chú05C dưới đây là lịch sử.

PHASE05C bổ sung10 Customer Cart/Checkout COD/Order history/detail/cancel method/path. Source `app/api/cart.py`, `checkout.py`, `orders.py` → `app/services/cart_service.py`, `checkout_service.py`, `order_service.py`, `commerce_pricing.py` → Cart/Order/Product/Category/User/PaymentAttempt repositories. Strict request schemas trong `app/schemas/cart_schema.py`, `checkout_schema.py`, `order_schema.py`; reuse Catalog transaction utility và foundation. [Review Commerce](../docs/phase-05c-review.md). VNPAY503 trước write; Admin Orders/Dashboard/Frontend deferred, không tự tiến phase.

Foundation đã duyệt; health và13 Auth/User/Admin User endpoints IMPLEMENTED,213 scoped tests pass và20 HTTP checks thật. Frontend chưa triển khai trong phiên này; các module ngoài Auth/User có worker riêng. [Hướng dẫn chạy](../docs/backend-setup.md), [API contract](../docs/api-contract.md), [review](../docs/phase-05a-review.md), [evidence](evidence/README.md).

| Module | Trách nhiệm hiện tại |
| --- | --- |
| app/__init__.py, config.py | Factory, config env, middleware/CORS/logging |
| app/api/health.py | HTTP health dưới /api/v1 |
| app/api/categories.py, products.py, admin_products.py | PHASE05B:14 public/Admin Catalog method/path |
| app/services/category_service.py, product_service.py, catalog_transaction.py | Catalog business/type/version rules và bounded snapshot/majority transactions |
| app/repositories/category_repository.py, product_repository.py | MongoDB filter/search/sort/facet pagination, current Category lookup, conditional writes |
| app/schemas/catalog_schema.py, category_schema.py, product_schema.py | Request adapter từ canonical validators, polymorphic attributes, URL/query allowlists |
| tests/test_catalog.py, test_catalog_transaction.py |112 Catalog cases, real rs0 races/rollback và commit retry bounds |
| app/services/health_service.py | Readiness orchestration |
| app/db | Client pool/process lifecycle, primary rs0 readiness |
| app/api/auth.py, users.py, admin_users.py | Auth, owner profile/addresses, minimal Admin accounts HTTP |
| app/services/auth_service.py, user_service.py | Credentials, revocation, ownership/address limits/defaults, status/version rules |
| app/repositories/user_repository.py | Strict projections, User queries và atomic conditional writes |
| app/auth | JWT, current User/role guards, Argon2id, bounded per-process rate limiter |
| app/errors | Error hierarchy và global safe response mapping |
| app/schemas | JSON Schema request validation, pagination/query allowlists |
| app/utils | BSON serialization, response helpers, IDs, structured logging |
| tests/test_auth_users.py |133 Auth/User cases cùng foundation tests, DB thật và race conditions |
| run.py | Local development entrypoint, debugger/reloader off |

Feature agent đọc AGENTS + architecture + API contract + đúng feature doc; schema/business-rules khi liên quan. Inspect module trực tiếp theo routing trong architecture, không cần đọc toàn backend. Dùng các helpers hiện có; API gọi service, service giữ transaction boundary, repository nhận session. Không tạo validator/index/seed từ factory. Khi implement feature thật, cập nhật API contract từ PLANNED sang IMPLEMENTED cùng tests và feature doc.

Dependency runtime được khóa trong requirements.lock.txt; development gồm pytest ở requirements-dev.lock.txt. Không chứa secret trong source. Test probe routes chỉ đăng ký trong test, không thuộc app thường.

PHASE05B backend Catalog đã implement, frontend chưa làm. Full workspace325 tests pass (112 Catalog +213 foundation/Auth/User từ phiên khác); giữ nguyên database/schema/index strategy. [Review Catalog](../docs/phase-05b-review.md), [contract](../docs/api-contract.md), evidence `phase05b-pytest.xml`/`phase05b-runtime.json`. Request adapter cần các canonical files `database/validators/categories.json` và `products.json` đi cùng project khi chạy, không tự apply schema từ app.
