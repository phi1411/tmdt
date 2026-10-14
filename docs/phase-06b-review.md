# PHASE06B — Admin Orders + Analytics Dashboard API

Ngày07/10/2026. PHASE05C đã được người dùng duyệt. Worker06B hoàn thành backend Admin/Analytics và dừng để review; không tự bắt đầu phase tiếp theo. Frontend/gateway không được triển khai bởi worker này; giữ schema/validators/indexes/revenue definition v1. Workspace đồng thời có worker06A Payment, thay đổi của worker đó được giữ nguyên.

## 1. Admin Order endpoints

6routes dưới `/api/v1`: GET `/admin/orders`; GET `/admin/orders/:id`; POST `/admin/orders/:id/confirm`, `/ship`, `/complete`, `/cancel`. ADMIN ACTIVE/current DB role only (Guest401/Customer403), không owner restriction với Admin. List filter status/paymentStatus/from/to/exact orderCode/page/pageSize; fixed createdAt DESC/_id DESC, Mongo facet count/items, không Python filtering. Không alias/filter/sort ngoài locked feature contract.

Admin detail/action trả immutable Commerce snapshot DTO + allowedActions. Body mutation chỉ expectedVersion strict; không generic PATCH/state/timestamps/totals/snapshot. COD PENDING→CONFIRMED→SHIPPING→COMPLETED; complete chuyển PAID và paidAt/completedAt cùng atomic write/transaction. VNPAY chỉ ship/complete khi PAID, giữ paidAt; không manual confirm/pay. Cancel dùng cùng Commerce once-only stock restore/pending-attempt invalidation transaction. Complete/CANCELLED retry200 current snapshot, không ghi version/ngày/stock lần nữa; wrong state/payment/stale409.

## 2–6. Dashboard endpoints/metrics

| Endpoint GET dưới `/api/v1/admin/dashboard` | Response data |
| --- | --- |
| /summary | totalRevenue,totalOrders,totalProductsSold,totalCustomers + metadata |
| /revenue | series[{bucket,revenue,orders}],interval day/month + metadata |
| /top-products | items[{productId,productName,quantity,revenue}] max5 + metadata |
| /category-revenue | items[{categoryId,categoryName,revenue}] + metadata |
| /order-status | items[{status,count}] đủ6states,count0 nếu trống,dateBasis:createdAt + metadata |

Metadata currencyVND/timezoneAsia/Ho_Chi_Minh/from/to/revenueBasisPAID_COMPLETED_MERCHANDISE/fetchedAt; times UTC milliseconds Z. from/to bắt buộc full ISO UTC, from<to, max366×24h; default interval day, chỉ day/month. Year<=9998 để calendar không overflow. Bucket day YYYY-MM-DD/month YYYY-MM; fill0 chỉ bucket giao window, max367day buckets khi partial-day. Unknown/repeated/raw pipeline params422, no raw Orders/PII. Integers ngoài2^53-1→503 thay vì rounding.

Payment method/payment status charts chưa có dashboard endpoint/semantics trong design nên không tự thêm. Các report queries độc lập, không BI snapshot xuyên HTTP calls. Total Customers là global CUSTOMER kể cả BLOCKED, không khoảng ngày.

## 7. Aggregation usage

DashboardRepository load/decode8canonical EJSON artifacts từ database/aggregations, deep-copy/cache templates và bind Date vào initial match. Không sửa pipeline JSON hoặc copy stages vào backend. Summary chạy sales-summary/order-count/customer-count; Revenue day/month, Top5, CategoryRevenue, OrderStatus đúng artifacts còn lại. maxTimeMS10000/allowDiskUse=false; MongoDB cộng/group/sort, backend chỉ ghép metadata/default/calendar buckets.

Top5 stages: `$match` qualified/date → `$sort` completedAt/_id latest → `$unwind` items → `$group` productId → `$sort` quantity DESC/revenue DESC/ID ASC → `$limit:5` → `$project`. Latest sort phục vụ snapshot label gần nhất, không Product lookup. Category group snapshot ID/name, không Category sống. Đủ `$match/$unwind/$group/$sort` trong API runtime, không chỉ seed script.

## 8. Revenue verification

Giữ `orderStatus=COMPLETED AND paymentStatus=PAID`, dateBasis completedAt `[from,to)`, revenue subtotal-discount (discount0), không shipping. Units sum quantities; Top/category tiền item.lineTotal sau unwind, không nhân order.total. TotalOrders/status theo createdAt, gồm CANCELLED/EXPIRED; Customers global.

Fixture thật: A250VND/3units, B200VND/5units, tổng450VND/8units; SHIPPING PAID/CANCELLED/EXPIRED/PENDING không vào revenue. Date basis khác giữa createdAt/completedAt được kiểm tra. COD completion tăng đúng subtotal, không30000ship. Giá/tên live Product thay đổi và Product bị xóa vẫn cùng historical output.

Canonical validator không cho persist COMPLETED UNPAID/CANCELLED PAID/PENDING VNPAY PAID; tests kiểm tra reject121. Defensive filtering của pipeline chạy trên Mongo `$documents` với các virtual bad pairs, không bypassDocumentValidation/schema relaxation/persist corrupt fixtures.

Dev seed read-only oracle từ PHASE03: range2026-07-03T00:00Z→2026-10-01T00:00Z, revenue10.103.259.022VND/434units/100Orders/39Customers. HTTP evidence xác minh số này, không đổi dataset để ép kết quả.

## 9. Index/explain

[ExecutionStats/winning plans](../backend/evidence/phase06b-explain.json): reuse ix_orders_qualified_completed cho sales/revenue day/month/Top5/category,60docs/60keys trong seed cohort60/100orders. CreatedAt count/status scan100docs/0keys, globalCustomer scan40/0. Named-index Top5 và natural scan cùng output; natural100docs/0keys. Admin latest scan/sort khi chưa apply candidate admin-status/created-at. Không tạo index mới, không drop index, không đổi manifest14declared+6_id_. Không full benchmark/median/p95/speedup claim; executionTimeMillis là observation từng explain.

`nReturned` trong artifact là executionStats của `$cursor` nếu có, nếu pipeline được optimizer gộp thì là root plan; không mặc định là số dòng cuối Dashboard. Top5 API vẫn tối đa5items, được kiểm tra bằng fixture/rank/limit tests. Revenue explains quan sát5–10ms, natural Top5 lần này2ms; dataset nhỏ không chứng minh index nhanh hơn.

## 10–11. Tests và runtime evidence

- Worker:105 passed/0 fail/error/skip, real MongoDB8.0.32/rs0 và canonical validators/indexes; [JUnit](../backend/evidence/phase06b-worker-pytest.xml).
- Full backend: **658 total/658 pass/0 fail/0 error/0 skip**,211.41s; [JUnit cuối](../backend/evidence/phase06b-pytest.xml). Breakdown80foundation +133Auth/User +112Catalog +126Commerce +105Admin/Analytics +102Payment từ worker06A. Initial integrated648/657pass đã được thay bằng lần source cuối này sau các thay đổi code/test của worker06A; không skip subset để né regression.
- [Runtime HTTP/fingerprint](../backend/evidence/phase06b-runtime.json): **46 HTTP checks pass** qua temporary threaded servers/current source, Admin/Customer login thật, all11endpoint security matrix, COD lifecycle/dashboard delta/cancel replay; dev chỉ read reports/explain. Persistent server5001 đã reload đúng project process:3checks health200/AdminOrders401/Dashboard401. Registry tích hợp13blueprints/52method-path/0collision;11routes06B khớp contract và feature docs.
- Backend source/test hashes giữ nguyên từ trước scoped/full tests đến cuối runtime. Worker06A cập nhật `docs/api-contract.md` trong lúc tests chạy; current contract được audit riêng, cả tested/runtime manifests và `contractUpdatedSinceTests:true` lưu trong evidence. Không tuyên bố contract hash không đổi hoặc gán Payment implementation cho06B.
- Cases: validation/status matrix/stale/immutable timestamps/snapshot/role/query injection, atomic COD completion, concurrent ship/complete/cancel one state change, restore rollback, concurrent payment-review DB write not lost, post-commit audit. Audit formatter allowlist requestId/actor/order/action/trước-sau status/version, không PII/secrets.
- Asia/Ho_Chi_Minh dùng ZoneInfo/tzdata2025.2 đã có từ DB tooling locks; không dependency mới. Python3.12.14/Flask3.1.3/PyMongo4.15.3/pytest9.1.1.

## 12. Contract/docs

[API contract](api-contract.md) đánh dấu11endpoints IMPLEMENTED với method/path/auth/role/request/response/errors để UI đọc trực tiếp. [Admin Orders](features/admin-orders.md), [Dashboard](features/admin-dashboard.md) cập nhật đủ13sections/behavior/source/testing. Architecture/context/setup/evidence/index/pipeline README/demo-plan cập nhật06B, giữ evidence/history05A/05B/05AB/05C và rule/schema v1.

## 13. ecommerce_dev integrity

Baseline ignored `.local/phase06b-before.json` captured trước implementation, mở exclusive không overwrite; khớp immutable05C/05AB/phase04. Digest full documents/options/validators/indexes trước/sau `3cb02b86dae359fe469356c818205b8ddc2e83768862d9f3c47776a79657c6a6`. Counts40User/3Category/180Product/0Cart/100Order/30attempts giữ nguyên. Destructive cases chỉ ecommerce_test sau marker/project/topology guards; cleanup exact fixture IDs, không drop/reset/seed. Runtime refuse write khi test DB có data từ worker khác; sáu collections rỗng sau cleanup.

## 14. Files tạo/sửa bởi worker06B

- Tạo `backend/app/api/admin_orders.py`, `admin_dashboard.py`; `schemas/admin_order_schema.py`, `dashboard_schema.py`; `services/dashboard_service.py`; `repositories/dashboard_repository.py`.
- Sửa trực tiếp `api/__init__.py` (2blueprints, giữ registration worker khác), `services/order_service.py` (Admin lifecycle và shared cancel owner policy/audit), `repositories/order_repository.py` (Admin find/list/CAS), `utils/logging.py` (sanitized audit keys).
- Tạo `backend/tests/test_admin_analytics.py`, `scripts/backend/verify_admin_runtime.py`, `docs/phase-06b-review.md`; evidence `backend/evidence/phase06b-worker-pytest.xml`, `phase06b-pytest.xml`, `phase06b-runtime.json`, `phase06b-explain.json`; local baseline/source manifest ignored.
- Docs cập nhật: `docs/api-contract.md`, `docs/features/admin-orders.md`, `admin-dashboard.md`, `docs/demo-plan.md`, `docs/architecture.md`, `docs/backend-setup.md`, `docs/testing-strategy.md`, `AGENTS.md`, `backend/README.md`, `backend/evidence/README.md`, `database/aggregations/README.md`, `database/indexes/README.md`.
- Không tạo Git repo/commit vì workspace chưa có Git HEAD. Source manifest lưu hashes để review; không gán các thay đổi Payment/shared retry utility của worker06A cho worker06B.

## 15. Bugs/DEFERRED và điểm dừng

Không có runtime bug đã biết trong phạm vi06B đã kiểm tra. Frontend Dashboard/rehearsal, full benchmark/deployment, payment method/status chart chưa có design, gateway/IPN/expiry validation thuộc worker khác. Simulated payment-review write chỉ chứng minh Admin CAS không lost update, không nghiệm thu gateway race. Shared workspace có Payment worker; source mới được giữ nguyên và full suite bao gồm module đó,06B không implement/review gateway.

**Không làm Frontend/VNPAY gateway, không đổi MongoDB schema/index/revenue rule. Aggregation chạy thật trong Admin API. Dừng để review, không tự tiến phase.**
