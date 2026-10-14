# PHASE 06AB — BACKEND INTEGRATION CHECKPOINT

Ngày 07/10/2026. **Code integration PASS:** Payment06A, Admin/Analytics06B và các feature trước cùng chạy trên source hiện tại. Full suite658pass và96HTTP checks pass. Live VNPAY chưa được nghiệm thu; có thay đổi development từ bên ngoài checkpoint cần ghi nhận riêng ở mục10/12. Không triển khai feature mới, không làm Frontend hoặc tự bắt đầu phase tiếp theo.

**Follow-up housekeeping07/10/2026:** Pending data review ở mục10/12 đã được giải quyết tại [Database Cleanup Checkpoint](phase-06ab-db-cleanup-review.md): xác định chính xác artifact E2E FE-01A, cleanup3documents và2metadata trong transaction; account người dùng yêu cầu giữ nguyên, fingerprint trở lại original41Users baseline, schema/indexes/orphans PASS. **PHASE 06AB DATABASE INTEGRITY PASS.** Phần dưới/evidence gốc giữ nguyên lịch sử trước cleanup; LIVE SANDBOX BLOCKED không đổi.

Context đã đọc: AGENTS, architecture, [API contract](api-contract.md), reviews [06A](phase-06a-review.md)/[06B](phase-06b-review.md)/[05C](phase-05c-review.md), feature Payment/Admin Orders/Dashboard và schema/business rules liên quan. Source kiểm tra trực tiếp gồm registry/config, Checkout/Order/Payment services và repositories, provider adapter, Admin state policy, Dashboard canonical pipeline loader.

Git HEAD `39998900e16daec35caee24493f7011041820c91` là checkpoint05AB; Commerce/Payment/Admin và các thay đổi worker hiện còn trong working tree. Suite chạy **source hiện tại**, không checkout HEAD cũ và không dùng lại số liệu worker. Manifest SHA256 backend/app +backend/tests +api-contract được lưu ở evidence, giữ nguyên từ lúc capture trong quá trình suite đến hết HTTP verification. Không sửa application logic, commit hoặc push trong checkpoint này. Frontend đã có từ phiên khác; checkpoint không đọc/chỉnh/triển khai frontend.

## 1. Full suite result chính thức

```powershell
Push-Location backend
../.venv/Scripts/python.exe -m pytest -q --junitxml=evidence/phase06ab-pytest.xml
Pop-Location
```

| Total | Passed | Failed | Errors | Skipped |
| ---: | ---: | ---: | ---: | ---: |
| 658 | 658 | 0 | 0 | 0 |

JUnit188.676giây, console188.69giây. Không chọn subset/exclude/skip. [JUnit mới](../backend/evidence/phase06ab-pytest.xml), [integration evidence](../backend/evidence/phase06ab-integration.json).

| Nhóm | Tests pass |
| --- | ---: |
| Foundation55 +Auth foundation25 | 80 |
| Auth/User | 133 |
| Catalog106 +bounded transaction retry6 | 112 |
| Commerce | 126 |
| Payment | 102 |
| Admin/Analytics | 105 |

Python3.12.14/Flask3.1.3/PyMongo4.15.3/pytest9.1.1/PyJWT2.15.1; MongoDB8.0.32/rs0. Tests API/transaction/concurrency dùng owned ecommerce_test thật; unit retry cases ghi rõ. Không có failure cần sửa application source hoặc chạy lại sau fix.

## 2. Startup và HTTP smoke

Factory development với cấu hình hiện tại kết nối DB thật, bind temporary localhost WSGI listener và phục vụ health200/checks backend/database/replicaSet=ok. Persistent server127.0.0.1:5001 health200, Product200, Admin Orders thiếu token401. Không bật VNPAY hoặc expiry worker trên dev.

**96/96 HTTP checks PASS**, qua network localhost và cùng app source hiện tại, không chỉ Flask test client. Mutations chạy trên ecommerce_test sau guard marker/project/topology/6collections/trống; servers tạm shutdown/close và fixture cleanup. Tất cả labels/method/path/status/provider-code trong [evidence](../backend/evidence/phase06ab-integration.json).

Bao phủ loginCustomer/OtherCustomer/Admin, Product, Cart, COD/online quote +checkout +idempotency replay, payment-attempt ownership/tamper/retry/replay, signed Return trước/sau IPN, success/failure/duplicate IPN, Admin lifecycle/invalid transitions/cancel, expiry/late review, toàn bộ5Dashboard endpoints, authorization và historical dev oracle. Response envelope/requestId/private redaction đúng; IPN ngoại lệ provider envelope được kiểm tra riêng. Các status401/403/404/409/422/503 kỳ vọng và IPN02/99 không là test failure.

## 3. Route audit

**13 blueprints/52 method-path**, nhất quán `/api/v1`, không duplicate/collision/shadowing. Không tính HEAD/OPTIONS tự động. Concrete path matching được kiểm tra ngoài canonical method/path comparison; mỗi path sample dispatch đúng endpoint.

| Nhóm | Method/path |
| --- | ---: |
| Health | 1 |
| Auth/User/Admin User | 13 |
| Catalog | 14 |
| Cart/Checkout/Orders | 10 |
| Payment | 3 |
| Admin Orders | 6 |
| Admin Dashboard | 5 |

Factory và api/__init__.py giữ registration của cả hai worker. Shared error/JWT/auth decorators/validation/ObjectId/serialization/pagination/config/MongoClient chỉ có một nguồn; AST/import/source inspection không thấy implementation cạnh tranh. Payment và Commerce/Admin dùng cùng catalog_transaction snapshot/majority/retry hữu hạn; không thêm callback-side external request.

## 4. Payment/Commerce compatibility

Online checkout tạo PENDING/PENDING Order +initial attempt +conditional grouped stock decrement +Category guard +Cart clear trong một transaction; immutable Order snapshot/amount từ server. Signed paymentUrl dựng sau commit, HMAC vector/URLamount được verify offline trong smoke. `vnp_Amount=Order.total×100`, gồm shipping; retry không nhận client amount/owner.

POST `/orders/:id/payment-attempts` giữ CUSTOMER ACTIVE owner404 với owner khác, payload thêm amount422, expectedVersion/idempotency scope theo Order. Sau failed IPN, retry201/replay200 cùng attempt; amount bằng Order.total, deadline không đổi, không giữ/trừ stock lần nữa. Initial pending link lấy từ checkout, không tạo retry cạnh tranh. Quote/Checkout/Catalog shared helpers vẫn hoạt động.

COD vẫn PENDING/UNPAID, không attempt/deadline; replay same key/body không trừ stock thêm. Customer cancel/replay trả kho once và giữ UNPAID. Order history/detail giữ snapshot sau live Product name/price đổi. Full126Commerce cases vẫn pass, gồm atomic rollback/ambiguous commit/idempotency/races;102Payment bổ sung initial attempt/IPN/expiry/cancel concurrency thật. Không dùng mock alone để nghiệm thu transaction.

## 5. Payment/Admin compatibility

| Trạng thái/trigger | Admin và Payment đã xác minh |
| --- | --- |
| VNPAY PENDING/PENDING hoặc FAILED | Không manual confirm/ship/complete; failed retry giữ deadline/stock |
| Valid timely IPN success | CONFIRMED/PAID; Admin ship→complete được, paidAt provider giữ nguyên |
| COD PENDING/UNPAID | confirm→ship→complete; PAID/paidAt/completedAt cùng write |
| PAID | Customer/Admin cancel bị409; không create payment attempt mới |
| CANCELLED online +late success | Giữ CANCELLED, REVIEW_REQUIRED/review flag, không revive/trừ kho; Admin ship/complete409 |
| EXPIRED +late success | Giữ EXPIRED/REVIEW_REQUIRED, restoreonce; mọi Admin action409 |
| COMPLETED | Repeat complete200 current snapshot, không rewrite timestamps/version; duplicateIPN02 không write |

AllowedActions từ schemas/admin_order_schema.py là policy dùng bởi Admin service và DTO; Admin không có rule mark-paid VNPAY thứ hai. Admin cancel reuse đúng OrderService.cancel đã dùng cho Customer, same transaction/stockReleasedAt/invalidate attempts. Payment state writes và Admin writes có CAS status/payment/version guard, không lost concurrent review. Terminal/paid states không bị mở lại.

## 6. Revenue verification

Fixture qua checkout và HTTP Admin/IPN, price120000VND, ship30000/Order:

- Online2units chỉ PAID/CONFIRMED: revenue0. Sau Admin complete:240000VND.
- COD1unit hoàn tất giao/thu tiền: thêm120000VND.
- Tổng qualified **360000VND/3units**, không cộng **60000VND shipping**.
- Return/duplicate IPN/repeat complete/retry-paid chưa completed/cancelled/expired/late REVIEW_REQUIRED không tăng revenue.
- Live Product price đổi130000 và name đổi: snapshot và historical revenue vẫn360000; không lookup current Product để phục hồi giá.

Summary, day revenue, Top Products và Category Revenue cùng số kỳ vọng. Order Status đủ states/counts, TotalOrders fixture6 theo createdAt. Query window trên completedAt cho revenue, không paidAt/createdAt. Pipeline chạy MongoDB thật từ8canonical EJSON, không duplicate pipeline logic vào backend/frontend. Historical dev range2026-07-03→2026-10-01 vẫn10.103.259.022VND/434units; Customers là global, tính cả các tài khoản thử mới ngoài39seedCustomers.

## 7. API contract status

Auth/User13, Catalog14, Commerce10, Payment3, Admin/Analytics11 và Health1 trong api-contract hiện đầy đủ, tất cả IMPLEMENTED tương ứng source thật. Sets được đối chiếu chính xác với route registry và feature docs; Payment feature GET own Order poll là endpoint existing, không tính thành Payment thứ4.

Không còn gate503 vô điều kiện từ PHASE05C: online đã IMPLEMENTED với điều kiện `VNPAY_ENABLED=true` +valid Sandbox config; **disabled/missing config vẫn503 trước hold/write**, đúng implementation. Nội dung05C review/gate cũ là evidence lịch sử, không contract frontend hiện tại. Current api-contract giữ nguyên trong checkpoint; no worker section overwrite phát hiện được. Frontend flow đầy đủ tại mục8 và [payment setup](payment-setup.md).

## 8. FRONTEND HANDOFF

Mọi endpoint tương đối `/api/v1`, JSON envelope `{data,meta:{requestId}}`, trừ IPN provider. Bearer accessJWT và current DB role/status enforced; token ở memory theo Auth contract. API base development hiện `http://127.0.0.1:5001/api/v1`. Frontend cần đọc contract này/API contract, không phải implementation.

### Payment — create, redirect và result

| Method / path | Request và quyền | Response / behavior |
| --- | --- | --- |
| GET /checkout/quote | CUSTOMER owner; query addressId,paymentMethod=VNPAY | 200 `{cartVersion,items,subtotal,shippingFee,discount,total,currency,quoteToken,expiresAt,issues}`; không giữ stock |
| POST /orders | CUSTOMER; `{cartVersion,addressId,paymentMethod:"VNPAY",quoteToken}`; Idempotency-Key | 201 `{order,payment}`; replay200 cùng key/body. payment=`{method:"VNPAY",attemptId,attemptStatus,expiresAt,paymentUrl?,retryRequired?}` |
| POST /orders/:id/payment-attempts | CUSTOMER owner; `{expectedVersion}` +Idempotency-Key; không query | 201 `{attemptId,attemptStatus,expiresAt,orderVersion,paymentUrl?,retryRequired?}`; same key/body200. Chỉ eligible pending Order/no pending attempt/trước deadline |
| GET /payments/vnpay/return | Public; forward nguyên provider query, không sửa/thêm keys | 200 safe result dưới đây; read-only, **không HTTP redirect tự động và không xác nhận paid** |
| GET /orders/:id | Bearer CUSTOMER owner, không query/body | 200 snapshot với paymentStatus/orderStatus/paymentReviewRequired/version; owner status poll, lazy expiry |
| GET /payments/vnpay/ipn | Provider server signed query; frontend không gọi để tự mark paid | HTTP200 `{RspCode,Message}`; authoritative transaction sau verification |

1. Lấy quote online, cho người dùng xác nhận giá/địa chỉ, POST Order với quoteToken và key ổn định.
2. Checkout **đã tạo initial attempt**; dùng paymentUrl từ response, không gọi retry endpoint ngay khi attempt còn PENDING.
3. Frontend chuyển browser tới paymentUrl do backend trả. Backend không trả302 từ create/retry. Không tự dựng URL/amount/chữ ký/merchant hoặc đưa secret vào VITE_ env.
4. Sau Sandbox Return, SPA result route forward query tới GET Return handler. VNP_RETURN_URL có thể trỏ SPA `/payment/return`; nếu trỏ backend Return API thì browser nhận JSON, handler không tự điều hướng về SPA. Cần thống nhất Return URL khi có merchant config.
5. IPN là callback server-provider riêng, publicHTTPS/merchant registered; Return query thành công chưa đủ để đánh dấu đã trả tiền.
6. Result page đọc safe Return result và poll own GET Order hữu hạn với Bearer. Qua full browser redirect, token memory có thể mất; người dùng cần login lại cho owner poll, không đổi sang persistent token store tùy tiện.

Return verified data: `{result,providerResult,verified:true,confirmed,authoritative:false,orderId,attemptId,paymentStatus,orderStatus,paymentReviewRequired}`. `result=SUCCESS` chỉ khi DB PAID; provider success trước IPN→PENDING. FAILED dựa state/provider failure; invalid signature/merchant/missing/duplicate query→`{result:"INVALID_SIGNATURE",verified:false,confirmed:false,authoritative:false}`, signed invalid relation/amount/format→INVALID_RESPONSE. Không PII.

Result UI: PENDING hiển thị đang xác minh; SUCCESS/confirmed=true dùng trạng thái backend, không coi đó là đã giao/COMPLETED; FAILED thông báo thanh toán chưa thành công; INVALID_* không xác nhận thanh toán. Khi paymentStatus=REVIEW_REQUIRED hoặc paymentReviewRequired=true, báo cần đối soát; Return result có thể vẫn PENDING, không có result enum REVIEW_REQUIRED. Poll có giới hạn, không giả SUCCESS khi timeout. Retry chỉ theo current Order eligibility, dùng expectedVersion từ Order mới đọc. Giá/quote/address409 cần đọc/xác nhận lại đúng contract.

POST create/retry không nhận query. Idempotency-Key là nguyên chuỗi ASCII in được không khoảng trắng8..128 ký tự; expectedVersion là integer1..2147483647. Retry errors:400 ID/JSON,401 Guest,403 role/status,404 missing/other owner,409 ORDER_CHANGED/INVALID_TRANSITION/PAYMENT_ATTEMPT_PENDING/IDEMPOTENCY_CONFLICT/VERSION_LIMIT,422 payload/key,503 PAYMENT_UNAVAILABLE/DB. IPN luôn HTTP200:00 receipt committed,02 duplicate,01 relation missing,04 amount mismatch,97 signature/merchant invalid,99 config/processing failure.

Timeout/URL fault sau commit: giữ Order, `retryRequired:true`; gửi lại **nguyên request/key** để nhận lại URL/attempt, không tạo Order mới/key mới chỉ vì network retry. Terminal attempt/order replay không có paymentUrl. Deadline15phút cố định, retry không gia hạn. Disabled/unconfigured503 PAYMENT_UNAVAILABLE là trạng thái khả dụng, không feature chưa implement.

### Admin Orders

| Method / path | Request | Response data |
| --- | --- | --- |
| GET /admin/orders | ADMIN; optional status,paymentStatus,from,to,orderCode,page,pageSize | summaries[] + meta page/pageSize/total/totalPages |
| GET /admin/orders/:id | ADMIN, no query/body | Immutable Order snapshot + allowedActions |
| POST /admin/orders/:id/confirm | ADMIN; `{expectedVersion}` | Updated AdminOrder |
| POST /admin/orders/:id/ship | ADMIN; `{expectedVersion}` | Updated AdminOrder |
| POST /admin/orders/:id/complete | ADMIN; `{expectedVersion}` | AdminOrder với completedAt; COD cùng PAID/paidAt |
| POST /admin/orders/:id/cancel | ADMIN; `{expectedVersion}` | AdminOrder CANCELLED, stock restore once |

AdminOrder = Commerce detail `{id,orderCode,userId,customerSnapshot,shippingAddress,items,subtotal,shippingFee,discount,total,currency,paymentMethod,paymentStatus,paymentReviewRequired,orderStatus,version,createdAt,updatedAt}` + `allowedActions:[confirm|ship|complete|cancel]`. Các timestamp tùy trạng thái:paymentExpiresAt,paidAt,completedAt,cancelledAt,expiredAt,stockReleasedAt; field chưa tồn tại được omit. Snapshot objects/items theo [Commerce DTO contract](api-contract.md#commerce-implemented--phase-05c), không live Product. Summary chính xác `{id,orderCode,orderStatus,paymentStatus,paymentMethod,paymentReviewRequired,total,currency,version,createdAt,updatedAt}`. Render actions từ server; không generic state/paid mutation. Review badge không tự resolve/refund. Stale409 ORDER_CHANGED→refresh; wrong state/payment409 INVALID_TRANSITION; Customer403/Guest401. Repeat complete/cancel200 snapshot không viết lại.

List filter status6states, paymentStatus UNPAID/PENDING/PAID/FAILED/REVIEW_REQUIRED, exact orderCode uppercase/alphanumeric/-1..64, optional from/to theo createdAt `[from,to)` UTC. page1/pageSize20 mặc định, max100; fixed latest. Không alias sort/paymentMethod/customer/email/orderStatus.

### Admin Dashboard

Tất cả GET/Bearer ADMIN. Query **from,to bắt buộc** full ISO UTC seconds Z hoặc+00:00; from<to, tối đa366×24h. Revenue thêm interval=day(default)/month. UI ngày Việt Nam chuyển thành UTC, end-date inclusive chuyển sang to-exclusive. Không gửi pipeline hoặc tự cộng raw Orders ở frontend.

| Path | Response data |
| --- | --- |
| /admin/dashboard/summary | `{totalRevenue,totalOrders,totalProductsSold,totalCustomers,...reportMetadata}` |
| /admin/dashboard/revenue | `{series:[{bucket,revenue,orders}],interval,...reportMetadata}` |
| /admin/dashboard/top-products | `{items:[{productId,productName,quantity,revenue}],...reportMetadata}` tối đa5 |
| /admin/dashboard/category-revenue | `{items:[{categoryId,categoryName,revenue}],...reportMetadata}` |
| /admin/dashboard/order-status | `{items:[{status,count}],dateBasis:"createdAt",...reportMetadata}` đủ6states |

reportMetadata=`{currency:"VND",timezone:"Asia/Ho_Chi_Minh",from,to,revenueBasis:"PAID_COMPLETED_MERCHANDISE",fetchedAt}`; date UTCmillisecondsZ. Day bucketYYYY-MM-DD/monthYYYY-MM theo Việt Nam, bucket trống0. Revenue/units/top/category chỉCOMPLETED+PAID theo completedAt, không ship. TotalOrders/status theo createdAt; Customers toàn hệ thống CUSTOMER gồmBLOCKED. Panels query độc lập, không cam kết snapshot xuyên HTTP. Loading/error/empty riêng; không hiển thị0 giả khi API fail. Các metric vượt số nguyên an toàn trả503, validation422, role401/403.

## 9. Live VNPAY status

**LIVE SANDBOX BLOCKED.** Development VNPAY_ENABLED=false và thiếu effective VNP_TMN_CODE,VNP_HASH_SECRET,VNP_PAYMENT_URL,VNP_RETURN_URL,VNP_IPN_URL/public registered IPN. Không cấu hình/bật merchant giả trên dev, không gọi provider/bank, không claim live redirect hoặc provider IPN. Deterministic fixtures trên owned test listener chứng minh implementation/code integration, không thay live rehearsal.

## 10. ecommerce_dev integrity

Dev từ worker baseline40Users/0Cart/100Orders khác trạng thái hiện tại do thử ứng dụng từ bên ngoài checkpoint. Ban đầu41Users: thêm tài khoản khachtest_1791374905461@example.test; người dùng đã xác nhận chủ động tạo và yêu cầu giữ. Loại riêng document này khỏi phép tính trong memory thì toàn bộ phần còn lại khớp historical digest3cb02b86...; không xóa DB.

Trong lúc suite/audit chạy, thêm khach_muy2lxi4@example.test,1Cart,1Order và stock/version liên quan. **Nguồn gốc/ý định của đợt thay đổi này còn chờ xác nhận từ người dùng**; giữ nguyên dữ liệu, không xóa/reset/reseed hoặc nhận định rằng full dev fingerprint vẫn bằng baseline worker.

| Collection | Baseline worker | Ban đầu checkpoint | Trước/sau HTTP smoke |
| --- | ---: | ---: | ---: |
| users | 40 | 41 | 42 |
| categories | 3 | 3 | 3 |
| products | 180 | 180 | 180 |
| carts | 0 | 0 | 1 |
| orders | 100 | 100 | 101 |
| payment_attempts | 30 | 30 | 30 |

Original historical baseline giữ nguyên. Initial checkpoint digestf8c36f... khác historical do User đã xác nhận. Pre-smoke runtime digest **347c71bdc799e828bceeb197d9a9f3ea45624449a387aca239abb18538792f73**, **trùng hoàn toàn sau96HTTP checks** cho toàn documents/options/validators/indexes. Không nói dev không thay đổi trong cả phiên vì đợt ghi ngoài checkpoint đã được phát hiện. Checkpoint scripts/API dev chỉ đọc; không start expiry hoặc own-Order detail lazy expiry trên seeded online holds.

6validators strict/error và14declared indexes +6_id_ kiểm tra khớp canonical validator/index artifacts, không thêm/drop/rebuild/schema change. Sau suite và HTTP,6collections ecommerce_test rỗng; cleanup exact fixture IDs/userIds, servers đóng. Local baselines/delta/schema audit ở ignored .local; public evidence không chứa raw docs/hash/password/merchant secret.

## 11. Conflicts/fixes/files

Không phát hiện application conflict/regression cần sửa; không refactor business logic/shared state/revenue/schema. API contract và backend/app/tests giữ nguyên manifest đã kiểm tra. Script đã chủ động fail integrity khi dev khác initial baseline; không che khác biệt bằng reset hoặc ghi đè baseline. Runtime baseline bổ sung cho riêng smoke, giữ original baseline và ghi external delta rõ.

Tạo `scripts/backend/verify_integration_06ab.py`, `backend/evidence/phase06ab-pytest.xml`, `backend/evidence/phase06ab-integration.json` và báo cáo này; thêm liên kết/trạng thái checkpoint vào AGENTS.md và backend/evidence/README.md. Local .local/phase06ab-* là dữ liệu audit private. Evidence các worker/phase cũ giữ nguyên. Chưa tạo commit/push; không sửa frontend từ phiên khác. Không re-run full suite sau application fix vì không có application fix.

## 12. Blockers và điểm dừng

Không có code integration blocker cho Frontend Admin/Payment. **Live Sandbox blocker:** merchant/config/public registered IPN và rehearsal thật chưa có. **Development data review pending:** cần xác nhận đợt User/Cart/Order mới từ bên ngoài và tạm ổn định DB nếu cần đối chiếu checkpoint xuyên toàn phiên; không phải failure của Payment/Admin code.

Kết luận về code đã chạy: **PHASE 06AB BACKEND INTEGRATION PASS**; **READY FOR FRONTEND ADMIN + PAYMENT INTEGRATION** ở mức API/backend implementation. Live provider chưaPASS; data-delta approval nêu ở trên vẫn pending. Dừng checkpoint, không tự bắt đầu phase tiếp theo.
