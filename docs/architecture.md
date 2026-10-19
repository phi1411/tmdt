# Kiến trúc tổng thể

## Trạng thái và phạm vi

LOCKED DESIGN v1 — PHASE02/03/04 và PHASE05C đã duyệt; PHASE05A implement13 Auth/User/Admin User, PHASE05B14 Catalog, PHASE05C10 Customer Commerce và PHASE06B11 Admin Orders/Dashboard endpoints trên Flask foundation/MongoDB đã khóa, không thay mô hình DB. PHASE06B dừng để review, không tự chuyển phase; Frontend chưa làm. Mỗi feature có worker/phase evidence riêng; Payment thuộc worker06A đồng thời. Modular monolith phù hợp nhóm3SV, MongoDB là CSDL chính. Quyết định tại [foundation](foundation-decisions.md) và [ADR index](decisions/README.md); bàn giao [phase05A](phase-05a-review.md), [phase05B](phase-05b-review.md), [phase05C](phase-05c-review.md), [phase06B](phase-06b-review.md), [API contract](api-contract.md); lịch sử [phase04](phase-04-review.md), [phase03](phase-03-review.md), [phase02](phase-02-review.md). Sơ đồ dưới đây mô tả đích thiết kế, không khẳng định mọi component đã chạy.

## Luồng hệ thống

PHASE07B chỉ bổ sung performance tooling/evidence, không sửa application logic. `scripts/performance/` dùng Product query parser/repository pipeline và Dashboard canonical loader, tạo BENCHMARK DATASET riêng30.000Products/10.000Orders; dev read-only fingerprint/audit. COLLSCAN/IXSCAN, raw explain, result equality, repeated latency/storage và owned cleanup/reproduction đã đo thật; [review07B](phase-07b-performance-review.md), [feature spec](features/performance-benchmark.md). Những ghi chú chưa đo/frontend ở các phase lịch sử bên dưới không là trạng thái performance07B hiện tại; frontend completion không được nghiệm thu trong task này.

PHASE06A Payment backend thêm3method/path, initial VNPAY attempt cùng Checkout transaction, URL ký sau commit, Return verify/read-only, IPN authoritative state/version transaction và expiry worker30s/batch100. Dependencies Order detail lazy expiry/cancel, PaymentAttempt/Order/Product repos và shared Catalog transaction utility (bounded transient backoff20/40ms). Không thay schema/lifecycle/revenue, không frontend/Dashboard trong worker06A; live merchant/IPN rehearsal BLOCKED LIVE SANDBOX. [Review06A](phase-06a-review.md), [setup](payment-setup.md), [ADR010](decisions/010-payment-runtime.md). Các ghi chú05C bên dưới là lịch sử gate trước Payment.

PHASE06B thêm6Admin Orders và5Dashboard APIs, giữ lifecycle/revenue/schema đã khóa. Cancel reuse Commerce restore transaction; COD complete atomic PAID/paidAt/completedAt. DashboardRepository decode/bind8canonical EJSON pipelines, MongoDB tính metrics; Python chỉ metadata/bucket0. ZoneInfo dùng tzdata đã khóa ở DB tooling trên Windows. [Review06B](phase-06b-review.md), [contract](api-contract.md). Frontend/gateway không thuộc worker06B; không tự chuyển phase.

PHASE05C triển khai10 Customer commerce method/path: Cart→quote ký→COD checkout→snapshot history/detail/cancel. API→service→repository, reuse transaction utility Catalog hiện có (bounded snapshot/majority). CheckoutService lock ACTIVE Category/version, conditional Product stock/version write theo tổngquantity, insert Order, clear/giữ Cart+version atomic; OrderService cancel+restore+invalidate pending attempts cùng transaction. No live lookup cho history. VNPAY online creation/adapter/expiry worker bị gate503 trước write; Admin Orders/Dashboard/Frontend deferred. [Review Commerce](phase-05c-review.md), [contract](api-contract.md).

PHASE05B Catalog bổ sung14 public/Admin Category/Product method/path, API→service→repository đúng ranh giới. Product list/detail resolve Category hiện hành và kiểm tra ACTIVE bằng MongoDB lookup, không embed Category sống vào Product. catalog_schema chuyển request shape từ canonical validator, product_schema/category_schema bổ sung API rules; catalog_transaction orchestration snapshot/majority và retry hữu hạn. Product create/move/publish guarded Category version write; category archive/delete/type change cùng write guard/transaction với reference checks. Search/filter/sort/count/pagination chạy MongoDB, DTO trả attributes động. [Review PHASE05B](phase-05b-review.md). Frontend/checkout/reservation còn deferred theo phase được giao.

```mermaid
flowchart LR
  U[Guest / Customer / Admin] --> UI[React + Vite]
  UI -->|REST /api/v1| API[Flask API / JWT guards]
  API --> S[Services: validation + business rules]
  S --> R[Repositories / PyMongo]
  R --> M[(MongoDB replica set)]
  M -->|Aggregation results| R
  S --> P[VNPAY Sandbox adapter]
  P -->|Signed server IPN| API
  C[Compass / Seed / Benchmark] --> M
```

VNPAY ReturnUrl là kênh điều hướng về Web; chỉ server IPN đã xác minh mới cập nhật kết quả theo policy ở payment. Backend không gọi dịch vụ ngoài bên trong transaction có thể retry. COD hoàn tất không phụ thuộc VNPAY.

## Ranh giới các tầng

| Path | Trách nhiệm | Không làm |
| --- | --- | --- |
| backend/app/api | Flask Blueprint, HTTP, guard, parse/serialize | Trực tiếp tính doanh thu/tồn kho |
| backend/app/services | Use case, pricing, state transition, transaction orchestration | Phụ thuộc React/HTTP request toàn cục |
| backend/app/repositories | Mongo query/aggregate, nhận session từ service | Tự commit transaction nhiều repository |
| backend/app/schemas | Request/response validation, allowlists, type conversion | Thay thế DB validator hoàn toàn |
| backend/app/auth | JWT/hash/role/ownership guard | Tin role từ client |
| backend/app/db | MongoClient lifecycle/readiness, truy cập DB/session | Business rule; tự setup validator/index/seed trong factory |
| backend/app/errors | Error hierarchy/global HTTP envelope mapping | Leak traceback/received input |
| backend/app/utils | Lỗi/time/money/serialization dùng chung có nhu cầu thật | Gom tất cả logic vào utils |
| frontend/src/api | HTTP client/token/error, typed contracts | Tự xác nhận thanh toán |
| frontend/src/features | UI/state theo feature | Truy cập trực tiếp MongoDB |
| frontend/src/pages/layouts/routes | Ghép trang, layout shop/admin, điều hướng | Authorization duy nhất ở frontend |
| database | Artifacts validator/index/pipeline/sample được review | CSDL thứ hai, duplicate source of truth |
| scripts | Seed, import/export, đo hiệu năng | Lách rule để tạo data sai schema |
| tests | E2E liên Web/API; test tầng dưới ở từng ứng dụng | Dataset/secret production |

Module dự kiến dùng cặp `api/products.py`, `services/product_service.py`, `repositories/product_repository.py`, `schemas/product_schema.py`; các feature docs chỉ ra file liên quan. `checkout_service.py` sở hữu transaction chung; repository không mở transaction độc lập. Dashboard repository khi implementation load/decode Extended JSON pipeline canonical từ `database/aggregations`, bind range đã validate, không sao chép hai bản khác nhau.

Foundation thực tế tại `backend/app`: create_app/config; api/health.py → services/health_service.py → db readiness; auth JWT/Argon2/guards; schemas validation/pagination/query constants; errors handlers; utils BSON/responses/IDs/logging. PHASE05A thêm api/auth.py, users.py, admin_users.py → auth_service.py/user_service.py → user_repository.py với strict DTO/schema và local rate limiter. Profile/address/password/status chỉ sửa một User document, atomic conditional writes giữ version/default/tokenVersion; không tạo Cart hoặc cascade Order. MongoClient một instance/app/process, không đóng mỗi request; atexit và test fixture explicit close. Health và Auth/User blueprints được đăng ký trong app thường; các feature khác có registration của worker riêng. Feature agent dùng factory/register blueprint theo prefix, service gọi repository qua get_db(), session do service điều phối; cập nhật api-contract và feature docs khi endpoint thực sự implement. [Backend setup](backend-setup.md), [module map](../backend/README.md).

## Mô hình MongoDB và tính nhất quán

Product chung collection có discriminator. User/Category được reference ở tài liệu sống. Cart riêng (ADR-004). Order là aggregate lịch sử nhúng snapshot item/customer/address/category; Product reference chỉ phục vụ trace/link và trả tồn kho. Payment attempts riêng vì nhiều lần thử/callback có vòng đời khác Order. Review DEFERRED, không tạo collection/endpoint ở MVP.

Checkout cần transaction: conditional decrement tổng quantity/Product + insert Order + clear items và tăng đúng version Cart (giữ document), tạo payment attempt đầu nếu VNPAY. Snapshot, tiền và tồn kho phải commit cùng nhau. Hủy/hết hạn trả kho đúng một lần trong transaction có state guard. Môi trường chính đã khóa MongoDB Community8.0 local single-node replica set rs0/WiredTiger; standalone không đáp ứng transaction. Atlas chỉ deployment option về sau. Test startup phải nhận ra topology không phù hợp, không bỏ transaction âm thầm. [Nguồn MongoDB](https://www.mongodb.com/docs/manual/core/transactions/).

Giới hạn retry hữu hạn; callback transaction không gửi email/payment request. Index/validator tạo trước checkout. Đọc primary, transaction snapshot read concern và majority commit theo khả năng deployment; không tuyên bố local một node chịu lỗi như production.

## Auth và frontend

Guest là truy cập không đăng nhập, không phải persisted role. User chỉ `CUSTOMER`/`ADMIN`. Register chỉ tạo Customer; Admin bootstrap qua seed riêng. Access JWT thời hạn hữu hạn, frontend giữ trong state và sessionStorage theo tab (hành vi F5 đã kiểm tra ở FE-01A), logout/401 xóa cả hai, hết hạn đăng nhập lại; chưa thiết kế refresh token. Mỗi protected request kiểm tra User đang ACTIVE và `tokenVersion`, role hiện hành từ DB để khóa/đổi role có hiệu lực. Argon2id baseline m19456 KiB/t2/p1 theo foundation-decisions; benchmark hashing có thể tăng cost khi bootstrap, không thay database/schema.

Các trang shop: catalogue, chi tiết, đăng nhập/đăng ký, profile/addresses, Cart, Checkout, Order history/detail. Admin: Dashboard, Category/Product CRUD, Order/User management. Frontend route guard giúp UX; backend luôn enforce. UI tiền VND và ngày giờ Việt Nam; API trả UTC.

## Bản đồ đọc context theo task

Luôn đọc AGENTS + architecture; thêm schema/business-rules chỉ khi liên quan. Bảng bên dưới chỉ là dependency trực tiếp, không yêu cầu đọc toàn bộ docs của dependency nếu chỉ dùng contract.

| Task | Feature doc | Code dự kiến inspect | Dependency trực tiếp |
| --- | --- | --- | --- |
| Backend foundation | backend-foundation | app factory/config/db/errors/utils/schemas/auth, tests | API contract/conventions, auth User projection |
| Auth | auth | app/auth, api/auth.py, user repository; features/auth | users, API conventions |
| Profile/addresses | users | api/users.py, user service/repository; features/users | auth |
| Category | categories | category API/service/repository/schema; features/categories | products khi archive/delete |
| Product/read | products | product API/service/repository/schema; features/products | categories |
| Search/filter | search-filter | product repository/schema; features/search-filter | products, index ADR |
| Cart | cart | cart API/service/repository/schema; features/cart | Product current read, auth |
| Checkout | checkout | checkout service/API; cart/product/order repositories | cart, orders, payment adapter |
| Orders/customer | orders | order API/service/repository; features/orders | auth, immutable snapshots |
| Payment | payment | payment API/service/repository/provider; features/payment | orders state contract, checkout |
| Review | reviews | review API/service/repository; features/reviews | orders eligibility, products, auth |
| Admin Product | admin-products | admin product/category routes; features/admin-products | products/categories |
| Admin Order | admin-orders | admin order API, order service; features/admin-orders | orders/payment state contract |
| Admin User | admin-users | admin user API, user service; features/admin-users | auth tokenVersion |
| Dashboard | admin-dashboard | dashboard API/service/repository, aggregations; features/admin-dashboard | orders snapshot, users count |

## Những lựa chọn chưa triển khai

Deployment follow-up (14/10/2026): user authorized Atlas demo migration and Render preparation. Local/testing topology remains rs0; production requires the configured Atlas replica set, verified TLS and separate environment settings. Waitress serves the existing Flask app; React uses a build-time API URL and static SPA rewrite. See [deployment](features/deployment.md), [ADR012](decisions/012-render-production-runtime.md). Historical deferred status below describes earlier phases; public hosting is still pending verification.

Frontend contract React/Vite/TypeScript/Tailwind/Recharts đã khóa; frontend agent khác làm sau. Images là URL-only, không upload/cloud. Ship/quote/payment TTL/limits đã khóa tại foundation-decisions. Search local normalized substring theo ADR008; không Atlas Search. Reviews/shadcn/ui/deployment deferred. DB tooling/backend foundation/Auth User đã triển khai; phần ngoài Auth/User theo worker riêng, full benchmark chưa chạy. Auth rate limit hiện local per process, chưa deployment/distributed limiter. Không cần Redis/queue/Elasticsearch/SQL cho MVP.


## Cập nhật19/10/2026 — ADR013

SKU/reviews đã được người dùng yêu cầu hoàn thiện sau integration review. Product optional tierVariations/skus, root price=minSKUprice/stock=sumSKUstock; legacy không matrix giữ behavior cũ. Exact selection/SKU binding, stock reservation/restore theo SKU và Product trong cùng transaction; snapshot selectedAttributes.skuId/price immutable. Admin CRUD hỗ trợ ma trận, guard SKU_IN_USE khi đổi identity có đơn giữ kho. Reviews là collection thứ7, unique User/Order/Product, verified COMPLETED+PAID và atomic ratingSummary; public privacy/pagination/filter. Nguồn cập nhật: decisions/013-sku-review-hardening.md, features/reviews.md và mục SKU/Reviews của api-contract.md; các ghi chú DEFERRED hoặc pool Product-only trước đó là lịch sử v1, không phủ định extension này. Không đổi doanh thu/canonical pipelines hoặc Order snapshot cũ. VNPAY disabled theo lựa chọn hiện hành.
