# Flask backend — PHASE 05A Auth/User

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
