# API contract — Backend Auth/User + Catalog + Commerce

Tài liệu dành cho frontend/feature agents. PHASE04 đã duyệt; health và 13 Auth/User/Admin User endpoints IMPLEMENTED qua PHASE05A. Các phần ngoài Auth/User có worker/phases riêng; chỉ thay trạng thái khi có evidence của phần đó. Quy ước chuẩn tại [api-conventions](api-conventions.md), behavior từng feature tại docs/features. Prefix cố định `/api/v1`. [Review PHASE05A](phase-05a-review.md).

PHASE05B bổ sung14 method/path Category/Product public và Admin đã IMPLEMENTED, search/filter/sort/pagination trên MongoDB thật; [review Catalog](phase-05b-review.md). Cart/Checkout/Order/Payment/Dashboard/Frontend chưa được triển khai trong phiên Catalog.

## Endpoint IMPLEMENTED

`GET /api/v1/health`, không cần token/body.200 khi Flask chạy và MongoDB reachable, đúng rs0/writablePRIMARY/có sessions:

```json
{"data":{"status":"ok","checks":{"backend":"ok","database":"ok","replicaSet":"ok"}},"meta":{"requestId":"server-generated-id"}}
```

DB/topology không ready→503:

```json
{"error":{"code":"SERVICE_UNAVAILABLE","message":"Dịch vụ dữ liệu tạm thời không sẵn sàng","details":[]},"meta":{"requestId":"server-generated-id"}}
```

Không trả Mongo URI/DB name/host/server version/credential. Health không chứng minh API nghiệp vụ đã implement. HEAD/OPTIONS là hành vi Flask/CORS tự động, không feature endpoint riêng.

## Auth/User/Admin User IMPLEMENTED

Tất cả path bên dưới tương đối `/api/v1`, request JSON strict, không nhận query trừ list Admin. `Bearer` là access JWT. `publicUser`/`account` đúng `{id,name,email,phone,role,status,version,createdAt}`. `publicProfile` thêm `{addresses:[address],defaultAddressId,updatedAt}`; address `{id,receiverName,phone,addressLine,province,ward?,district?,label?}`. ID lowercase hex24, timestamps UTC có Z. Không trả hash/tokenVersion/schemaVersion.

| Method / path | Auth / role | Request | Response data / status | Error chính |
| --- | --- | --- | --- | --- |
| POST /auth/register | Public | `{name,email,password,phone?}` | 201 `{user:publicUser}` | 409 DUPLICATE_RESOURCE;422 fields/email/password;429 |
| POST /auth/login | Public | `{email,password}` | 200 `{accessToken,expiresIn,user:publicUser}` | 401 generic wrong/unknown/blocked;422 input;429 |
| GET /auth/me | Bearer / CUSTOMER hoặc ADMIN | Không body/query | 200 publicUser | 401 token/user invalid;422 query |
| PATCH /auth/password | Bearer / CUSTOMER hoặc ADMIN owner | `{currentPassword,newPassword}` | 200 `{reauthenticationRequired:true}` | 401 current password/token/revoke race;422 password;409 version cap;429 |
| GET /users/me | Bearer / CUSTOMER owner | Không body/query | 200 publicProfile (bao gồm list addresses) | 401/403;422 query |
| PATCH /users/me | Bearer / CUSTOMER owner | `{name?,phone?,expectedVersion}`; ít nhất một editable field | 200 publicProfile | 409 CONFLICT/version cap;422 forbidden/invalid/empty |
| POST /users/me/addresses | Bearer / CUSTOMER owner | `{receiverName,phone,addressLine,province,ward?,district?,label?,expectedVersion}` | 201 `{address,version}` | 409 stale/10-address limit;422 |
| PATCH /users/me/addresses/:id | Bearer / CUSTOMER owner | Editable address fields + expectedVersion, ít nhất một field | 200 `{address,version}` | 400 ID;404 not owned;409 stale;422 |
| DELETE /users/me/addresses/:id | Bearer / CUSTOMER owner | `{expectedVersion}` | 204 không body; đọc lại profile lấy version | 400 ID;404 not owned;409 stale;422 |
| PATCH /users/me/default-address | Bearer / CUSTOMER owner | `{addressId,expectedVersion}` | 200 `{defaultAddressId,version}` | 400 ID;404 not owned;409 stale;422 |
| GET /admin/users | Bearer / ADMIN | Query `q?,role?,status?,page?,pageSize?` | 200 data:[account], meta pagination | 401/403;400 query integer;422 enum/unknown/repeated query |
| GET /admin/users/:id | Bearer / ADMIN | Path id, không query/body | 200 account | 400 ID;401/403;404 missing;422 query |
| PATCH /admin/users/:id/status | Bearer / ADMIN | `{status:ACTIVE hoặc BLOCKED,expectedVersion}` | 200 account | 400 ID;401/403;404;409 protected Admin/stale/version cap;422 |

Mọi protected row còn có401 khi token hết hạn/invalid/User blocked/tokenVersion mismatch,403 khi current DB role thiếu quyền; mutations JSON malformed400, content type415, payload413, unavailable DB503. Details chỉ field/reason. Unique email lowercase/trim giữ dot/plus, name trim1..100, password12..128 không trim và cho Unicode/space; Argon2id m19456/t2/p1. Profile phone optional empty; nonempty/address phone8..15 digits với + tùy chọn. Address bounds theo [users](features/users.md); expectedVersion là integer strict (không bool/float).

Access JWT HS256 với issuer/audience đã config, expiresIn mặc định1800. Guard đọc lại User ACTIVE/current role/tokenVersion mỗi request; không nhận role/status/security fields từ browser. Đổi password/status thực sự tăng version/tokenVersion nguyên tử; profile/address tăng version, giữ tokenVersion. Frontend FE-01A đã bàn giao giữ access token trong state và sessionStorage theo tab để phục hồi F5 qua GET /auth/me; logout/401 xóa cả hai, không revoke JWT; không có logout/refresh/forgot/social routes. Customer address ID của người khác→404; add không tự set default, xóa default→null cùng write. Admin status chỉ Customer; mọi Admin account được bảo vệ. Same-status200 no-op với expectedVersion đúng, không tăng version/tokenVersion.

Admin q<=100, normalized literal substring name/email, escaped regex; role CUSTOMER/ADMIN, status ACTIVE/BLOCKED; sort cố định createdAt DESC/_id DESC. Page1/pageSize20, max100. Rate limit per process/window60s: login30/IP +10/email; register10/IP; password30/IP +10/subject;429 RATE_LIMITED và Retry-After. Limiter reset khi restart, chưa phân tán qua nhiều processes. Kiểm chứng [Auth](features/auth.md), [User](features/users.md), [Admin User](features/admin-users.md), [evidence](../backend/evidence/README.md).

## Response/data contract IMPLEMENTED bằng helpers

Success200/201: data + meta.requestId;201 có thể Location.204 không body. List: dataarray và meta.requestId/page/pageSize/total/totalPages; page1/pageSize20 mặc định, max100; emptytotal→totalPages0. GET /admin/users đã kiểm tra contract pagination trên DB thật.

Error: error.code/message/detailsarray + meta.requestId. Details `{field,reason}`, không raw receivedvalue/query/traceback. ID ObjectId→id lowercasehex24; nested address _id→id; Date→UTC ISO8601 milliseconds với Z; money BSONlong→JSONinteger VND. Private password/hash/tokenVersion/checkout keys/hashes/secrets bị loại khỏi response, không trả DB entity nguyên xi làm publicDTO.

Mỗi response có `X-Request-ID` giống meta; server sinh ID mới, không tin header client. `X-Content-Type-Options: nosniff`. Log dùng requestId để tìm lỗi. Không có refresh token/cookieauth; login đã phát Bearer access JWT qua HTTP.

| HTTP | Code/quy tắc |
| --- | --- |
| 200 /201 /204 |Thành công /tạo mới /khôngbody |
| 400 |BAD_REQUEST — malformedJSON/queryinteger/ID |
| 401 |UNAUTHENTICATED — token/User invalid; WWW-Authenticate: Bearer |
| 403 |FORBIDDEN — thiếu currentDBrole |
| 404 |NOT_FOUND — route/resource/ownershipmissing |
| 405 |METHOD_NOT_ALLOWED — giữ Allowheader |
| 409 |CONFLICT /DUPLICATE_RESOURCE /BUSINESS_RULE_VIOLATION; featurecodes theo docs |
| 413 /415 |PAYLOAD_TOO_LARGE /UNSUPPORTED_MEDIA_TYPE |
| 422 |VALIDATION_ERROR — shape/value/unknown/repeatedquery |
| 429 |RATE_LIMITED; Auth limiter local đã implement, Retry-After |
| 500 /503 |INTERNAL_ERROR /SERVICE_UNAVAILABLE — safe message, log requestId |

## Catalog IMPLEMENTED — PHASE 05B

14 method/path dưới đây đã implement, dùng cùng envelope/header/error conventions. Public không cần token; mọi `/admin/categories*` và `/admin/products*` yêu cầu Bearer JWT của User ACTIVE với current DB role ADMIN (Guest401, Customer403). Detail public dùng **slug**, detail Admin dùng **id** hex24. Detail và mutations không nhận query params; unknown/repeated query hoặc body field trả422. [Review/evidence](phase-05b-review.md).

| Method / path (sau `/api/v1`) | Auth | Query / JSON body | Thành công | Lỗi riêng |
| --- | --- | --- | --- | --- |
| GET /categories | Public | `page?,pageSize?` | 200 Category[] ACTIVE + pagination | 400 integer syntax;422 unknown/range |
| GET /categories/:slug | Public | Không query/body | 200 Category | 404 missing/ARCHIVED |
| GET /admin/categories | ADMIN | `status?=ACTIVE hoặc ARCHIVED,page?,pageSize?` | 200 mọi status hoặc filter + pagination | 422 enum |
| GET /admin/categories/:id | ADMIN | Không query/body | 200 Category | 400 ID;404 |
| POST /admin/categories | ADMIN | `{name,slug,productType,description?}` | 201 Category + Location | 409 DUPLICATE_RESOURCE;422 |
| PATCH /admin/categories/:id | ADMIN | `{expectedVersion,name?,slug?,productType?,description?,status?}` | 200 Category/version mới | 400 ID;404;409 CATEGORY_CHANGED/CATEGORY_IN_USE/VERSION_LIMIT/DUPLICATE_RESOURCE;422 |
| DELETE /admin/categories/:id | ADMIN | `{expectedVersion}` | 204 hard delete **chỉ chưa referenced** | 400 ID;404;409 CATEGORY_CHANGED/CATEGORY_IN_USE/VERSION_LIMIT |
| GET /products | Public | Bộ filters/sort/pagination bên dưới | 200 Product[] + pagination | 400 ID/integer syntax;422 |
| GET /products/:slug | Public | Không query/body | 200 Product detail | 404 Product missing/INACTIVE/ARCHIVED hoặc Category ARCHIVED/missing |
| GET /admin/products | ADMIN | Cùng public filters + `status?=ACTIVE hoặc INACTIVE hoặc ARCHIVED` | 200 mọi status nếu bỏ status + pagination | 400/422 |
| GET /admin/products/:id | ADMIN | Không query/body | 200 Product detail mọi status | 400 ID;404 |
| POST /admin/products | ADMIN | Product create payload dưới đây, tất cả fields bắt buộc | 201 Product + Location | 409 DUPLICATE_RESOURCE/CATEGORY_UNAVAILABLE;422 |
| PATCH /admin/products/:id | ADMIN | Editable Product fields + `expectedVersion` | 200 Product/version mới | 400 ID;404;409 PRODUCT_CHANGED/CATEGORY_UNAVAILABLE/INVALID_TRANSITION/VERSION_LIMIT/DUPLICATE_RESOURCE;422 |
| DELETE /admin/products/:id | ADMIN | `{expectedVersion}` | 204 logical archive | 400 ID;404;409 PRODUCT_CHANGED/VERSION_LIMIT |

Mọi mutation còn có400 malformed JSON,415 non-JSON,413 payload limit; mọi endpoint503 DB unavailable. Duplicate SKU/slug do unique index enforce (kể cả archived); details không echo input. Category create mặc định `description:"",status:"ACTIVE",version:1`; không nhận `status` ở create vì contract đã khóa. PATCH ít nhất một editable field, expectedVersion integer strict1..2147483647; version tăng cùng write. Category order `_id ASC` ổn định. Product create/move/publish tăng Category.version trong transaction, vì vậy Admin phải đọc lại Category trước update/delete.

Category data: `{id,name,slug,productType,description,status,version,createdAt,updatedAt}`. Name1..100 không whitespace-only; slug lowercase hyphenated1..120; description<=2000; productType ELECTRONICS/FASHION/HOME_APPLIANCE. Một cấp, không `parentId`. Type không đổi nếu có bất kỳ Product reference; delete bị chặn kể cả Product archived. Archive bằng PATCH status ARCHIVED; có thể phục hồi bằng ACTIVE. Rename/archive không rewrite Order snapshot.

Product data cho cả list/detail: `{id,sku,name,slug,categoryId,category,productType,brand,description,price,stock,images,attributes,version,createdAt,updatedAt}`. `category:{id,name,slug,productType}` resolve current Category; Admin có thêm `status`. Public **không trả status**, normalized fields/schemaVersion không expose. Price JSON integer VND, stock numeric; dates UTC ISO8601 với Z. Attributes object động, giữ nguyên keys/nested values hợp lệ, không reshape theo Electronics. Admin category=null chỉ khi có dữ liệu reference thiếu bất thường.

Ví dụ body POST Product ELECTRONICS:

```json
{"sku":"PHONE_DEMO_01","name":"Điện thoại Demo","slug":"dien-thoai-demo","categoryId":"000000000000000000000101","productType":"ELECTRONICS","brand":"Demo","description":"Mô tả dạng văn bản","price":12000000,"stock":20,"images":["https://example.com/phone.png"],"attributes":{"ram":"8GB","storage":"256GB","chip":"Demo"},"status":"ACTIVE"}
```

categoryId trong ví dụ phải thay bằng ID Category ACTIVE phù hợp từ API. SKU1..64 uppercase `[A-Z0-9][A-Z0-9_-]*`; name1..200 không blank; slug1..220 lowercase hyphenated; brand<=100/description<=10000 có thể empty; price integer1..1e9 (bool/float reject); stock integer0..2147483647; images0..8 URLs<=2048 HTTPS hoặc HTTP localhost/127.0.0.1, không credentials/scheme khác/relative/URL malformed. Không tải ảnh, descriptions là văn bản cần escape khi UI render.

Attributes1..30 safe keys mỗi object, key `[A-Za-z][A-Za-z0-9_]{0,63}`; tối đa3 object levels; scalar string<=500/finite BSON-range number/bool/null, scalar arrays<=30. Known fields optional, nếu có phải đúng schema canonical: ELECTRONICS ram/storage/chip/screen/battery strings1..100; FASHION sizes/colors unique nonempty string arrays<=30 (item1..50), material1..100/gender1..50; HOME_APPLIANCE power/capacity/voltage/material strings1..100. Ví dụ Fashion `{"sizes":["S","M"],"colors":["Black"],"material":"Cotton"}`; gia dụng `{"power":"1700W","capacity":"6L","voltage":"220V"}`. Unknown safe keys được hỗ trợ có bounds; không bắt buộc field của ngành khác.

Product PATCH cho phép `name,slug,categoryId,productType,brand,description,price,stock,images,attributes,status` + expectedVersion; **sku immutable**. Chỉ supplied fields được `$set`; attributes/images là replacement toàn bộ object/array của field đó, omitted fields giữ nguyên. Đổi productType phải gửi attributes tương hợp cùng request và Category đúng type. Name/brand normalized do server derive cùng write. Create/move/publish cần Category ACTIVE; sửa metadata/ẩn Product đã nằm trong Category archived vẫn được, nhưng publish lại bị409. Product ARCHIVED chỉ PATCH `{status:"ACTIVE",expectedVersion}`; sửa field khác409 INVALID_TRANSITION. DELETE archived lần nữa204 với body version hợp lệ, không tăng version hoặc đổi stock; không hard delete Product. Không nhận `_id`, version trực tiếp, normalized fields/timestamps/schemaVersion/operator keys từ client.

Ví dụ PATCH giá: `{"price":12500000,"expectedVersion":1}` →200 version2, stock/attributes giữ nguyên. Nếu một request khác đã tăng version, trả409 PRODUCT_CHANGED; UI reload/review rồi gửi version mới. CATEGORY_UNAVAILABLE nghĩa là Category thiếu/archived/type mismatch (hoặc không còn version để guarded increment). Failed transaction rollback cả Category guard và Product write.

## Filter/sort contract IMPLEMENTED cho Product

Tên đã khóa: `q,categoryId,productType,brand,minPrice,maxPrice,size,color,ram,capacity,sort,page,pageSize`. Không dùng aliases search/category/limit. Sort `latest` (default)=createdAt/_id DESC; `price_asc`=price/_id ASC; `price_desc`=price/_id DESC. Không `newest/name_asc` hoặc raw sort object. Page1/pageSize20 mặc định, max100; total/count sau khi lọc Category ACTIVE; page vượt cuối trả[] nhưng giữ total/totalPages, empty total→0 pages.

`q` trim<=100 ký tự, <=8 normalized tokens: NFKD/casefold/đ→d/remove combining marks/collapse spaces; escaped literal substring **AND tokens** trên nameNormalized trong MongoDB, không search description/brand/relevance. q rỗng sau normalize bỏ filter. Brand<=100, exact normalized; empty brand bỏ filter. categoryId hex24 lowercase; productType enum đúng schema. minPrice/maxPrice unsigned query integer0..1e9 inclusive, min<=max. size/color membership trong attributes.sizes/colors (nonempty<=50), ram/capacity exact string<=100. Mọi filters intersection; category/type mismatch trả empty. Admin cùng behavior + status allowlist; public status query422, Product/Category ACTIVE bắt buộc. [Search strategy](decisions/008-local-vietnamese-search.md), [query usage/evidence](phase-05b-review.md).

Ví dụ `GET /api/v1/products?q=dien+thoai&productType=ELECTRONICS&minPrice=1000000&maxPrice=20000000&sort=price_asc&page=1&pageSize=20` → `{"data":[...],"meta":{"requestId":"...","page":1,"pageSize":20,"total":60,"totalPages":3}}` (total minh họa, phụ thuộc dữ liệu). Query chạy MongoDB aggregation; không tải toàn bộ Product về Python để lọc. Index category/price được giữ nguyên; type-price candidate chưa applied, latest cần đánh giá ở phase performance. Không claim substring/brand/attributes được index tăng tốc.

## Commerce IMPLEMENTED — PHASE 05C

10 method/path, tất cả Bearer JWT **CUSTOMER ACTIVE**, owner lấy từ live User guard. Guest401, Admin403, User blocked/tokenVersion cũ401. Không nhận userId/price/totals/state từ client. Error envelope và requestId dùng foundation; malformed ObjectId400, JSON sai400/content type415, allowlist/type/range422. [Cart](features/cart.md), [Checkout](features/checkout.md), [Orders](features/orders.md), [review](phase-05c-review.md).

| Method / path | Request | Response data / status | Errors |
| --- | --- | --- | --- |
| GET /cart | Không body/query | 200 Cart hiện tại | 401/403/503 |
| POST /cart/items | {productId,quantity,selectedAttributes?:{},cartVersion} | 200 Cart cập nhật | 404 Product;409 CART_CHANGED/STOCK_CONFLICT/PRODUCT_UNAVAILABLE/CART_LIMIT/VERSION_LIMIT;422 selection/quantity |
| PATCH /cart/items/:lineId | {quantity,cartVersion} | 200 Cart cập nhật | 404 line;409 như add;422 |
| DELETE /cart/items/:lineId | JSON {cartVersion} | 204 không body | 404 line;409 CART_CHANGED/VERSION_LIMIT |
| DELETE /cart | JSON {cartVersion} | 204 không body | 409 CART_CHANGED/VERSION_LIMIT |
| GET /checkout/quote | Query addressId,paymentMethod=COD hoặc VNPAY | 200 quote có chữ ký | 404 address;409 CART_EMPTY/PRODUCT_UNAVAILABLE/STOCK_CONFLICT/PRICE_CHANGED/VERSION_LIMIT;422;503 PAYMENT_UNAVAILABLE |
| POST /orders | {cartVersion,addressId,paymentMethod,quoteToken}; Idempotency-Key | 201 {order,payment}; cùng key/body replay200 | 404 address;409 CART_CHANGED/CART_EMPTY/STOCK_CONFLICT/PRICE_CHANGED/QUOTE_CHANGED/QUOTE_EXPIRED/IDEMPOTENCY_CONFLICT/CATEGORY_UNAVAILABLE/VERSION_LIMIT;422;503 |
| GET /orders | status?,from?,to?,page?,pageSize? | 200 own summaries, pagination meta | 422 filters/bounds;401/403/503 |
| GET /orders/:id | Không body/query | 200 immutable Order snapshot | 404 missing/khác owner;401/403/503 |
| POST /orders/:id/cancel | {expectedVersion} | 200 Order trạng thái mới; CANCELLED replay200 | 404 missing/khác owner;409 ORDER_CHANGED/INVALID_TRANSITION/STOCK_RESTORE_FAILED/VERSION_LIMIT;422;503 |

Cart `{version,items,subtotal,currency:"VND",issues,checkoutAllowed}`; mỗi item `{lineId,productId,name,slug,image,currentPrice,quantity,selectedAttributes,stock,available,issues,lineTotal}`. Missing Product: name/slug/currentPrice=null, image="", stock/lineTotal=0, issue PRODUCT_MISSING. Các issue còn lại PRODUCT_UNAVAILABLE/CATEGORY_UNAVAILABLE/SELECTION_CHANGED/STOCK_CONFLICT. Subtotal chỉ cộng dòng available; empty hoặc có issue→checkoutAllowed=false. GET không tự xóa dòng. Quantity integer1..99 (reject bool/float), <=50 lines; Fashion có sizes/colors phải chọn đúng membership, tổng quantity mọi selection cùng Product<=stock. Cart không lưu giá và không reserve stock.

lineId SHA256 hex64 canonical productId+selectedAttributes do server tạo; keys order không đổi identity. Cart chưa có version0/items[], clear version0 là no-op; first add tạo version1. Mọi mutation Cart tồn tại tăng version1, stale409 CART_CHANGED; remove/clear/checkout giữ document nên version không reset. DELETE dùng JSON body, sau204 frontend GET lại để lấy version. Không query ở Cart mutations/detail/cancel, không client sort/raw filter ở Orders.

Quote `{cartVersion,items,subtotal,shippingFee,discount:0,total,currency:"VND",quoteToken,expiresAt,issues:[]}`. Items dùng shape snapshot Order phía dưới. Không giữ hàng. Address phải thuộc User; profile phone phải hợp lệ8..15 digits optional+, nếu thiếu→422 field phone. Fee default30000, TTL300s; quote ký HS256 bằng key domain-separated SHA256 từ JWT_SECRET và audience checkout-quote-v1. Token bind owner/cartVersion/addressId/addressHash/paymentMethod/full snapshot pricingHash/expiry. Đây là token báo giá, không phải access JWT. Chữ ký thiếu/sai→422; expired409 QUOTE_EXPIRED; address cùng ID đổi→QUOTE_CHANGED; giá/fee/snapshot/selection đổi→PRICE_CHANGED; yêu cầu quote mới và khách xác nhận lại. Không có collection quote.

POST Idempotency-Key opaque ASCII không khoảng trắng8..128, scope User. Hash canonical nguyên body gồm quoteToken; check Order existing trước Cart/expiry. Cùng key/body trả Order hiện hành200, kể cả Cart đã clear/quote hết hạn/Order đã hủy; khác body409 IDEMPOTENCY_CONFLICT. Chỉ tạo key mới khi ý định đổi.201 có Location=/api/v1/orders/:id. Transaction snapshot/majority, bounded retry chung Catalog, lock Category ACTIVE bằng guarded version write, conditional stock decrement theo tổng quantity/Product+version, insert Order và clear Cart+version cùng session. Không external side effect trong callback; lỗi rollback toàn bộ, ambiguous commit503→retry nguyên key/body.

Order detail `{id,orderCode,userId,customerSnapshot,shippingAddress,items,subtotal,shippingFee,discount,total,currency,paymentMethod,paymentStatus,paymentReviewRequired,orderStatus,version,createdAt,updatedAt,...state timestamps}`. Item `{productId,sku,productName,image,productType,categoryId,categoryName,attributesSnapshot,selectedAttributes,priceAtPurchase,quantity,lineTotal}`; không lookup live Product/User để dựng history. Address snapshot không id/label. Tiền JSON integer/BSON long; discount0, total=subtotal+ship. Checkout COD tạo PENDING/UNPAID/version1, payment `{method:"COD"}`, không paidAt/paymentExpiresAt/attempt. Thu COD→PAID/COMPLETED thuộc Admin Orders phase sau.

Order summaries `{id,orderCode,orderStatus,paymentStatus,paymentMethod,paymentReviewRequired,total,currency,version,createdAt,updatedAt}`, không shippingAddress. Filter status allowlist6 enums; from/to ISO UTC `[from,to)` theo createdAt, from<to; page1/pageSize20/max100. Sort createdAt desc/_id desc cố định; facet matching count/items tại MongoDB. Detail/cancel của owner khác trả404.

Cancel PENDING/CONFIRMED, chưa PAID/REVIEW_REQUIRED và paymentReviewRequired=false, version đúng. Transaction guard Order state/version/absence stockReleasedAt, trả tổng quantity/Product+tăng Product.version, invalidate PENDING attempts→EXPIRED. Order CANCELLED+cancelledAt+stockReleasedAt/version+1; COD giữ UNPAID, online chuyển FAILED. CANCELLED replay200 không viết/hoàn kho lần nữa (kể cả có review flag sau này); EXPIRED/SHIPPING/COMPLETED409. Product archived vẫn hoàn kho được; missing/overflow/version-limit Product→STOCK_RESTORE_FAILED409, rollback và log event commerce.stock_restore_failed.

**VNPAY IMPLEMENTED — PHASE06A:** chỉ tạo quote/Order online khi VNPAY_ENABLED=true và đủ cấu hình Sandbox hợp lệ; disabled trả503 PAYMENT_UNAVAILABLE trước hold/write. Checkout tạo PENDING/PENDING/version1, paymentExpiresAt=createdAt+15phút và initial attempt cùng transaction stock/Order/Cart. Payment `{method:"VNPAY",attemptId,attemptStatus,expiresAt,paymentUrl? ,retryRequired?}`; dựng URL sau commit. Lỗi dựng URL sau commit trả retryRequired:true, retry nguyên checkout key/body để nhận lại attempt; không tạo Order khác. Total online1..9.999.999.999 VND, backend tính toàn bộ. COD giữ nguyên. [Payment setup](payment-setup.md).

## Payment IMPLEMENTED — PHASE 06A

Ba method/path mới; frontend chưa triển khai, live Sandbox cần merchant credentials/IPN reachable riêng. [Feature](features/payment.md), [ADR010](decisions/010-payment-runtime.md), [review](phase-06a-review.md).

| Method / path (sau `/api/v1`) | Auth | Request | Thành công / response | Lỗi |
| --- | --- | --- | --- | --- |
| POST /orders/:id/payment-attempts | CUSTOMER owner | JSON `{expectedVersion}` + Idempotency-Key; không query | 201 `{attemptId,attemptStatus,expiresAt,orderVersion,paymentUrl?,retryRequired?}`;200 cùng key/body replay | 400 ID/JSON;401/403;404 owner;409 ORDER_CHANGED/INVALID_TRANSITION/PAYMENT_ATTEMPT_PENDING/IDEMPOTENCY_CONFLICT/VERSION_LIMIT;422 fields/key;503 PAYMENT_UNAVAILABLE/DB |
| GET /payments/vnpay/return | Public, signed provider query | VNPAY callback query | 200 normal envelope với safe Return result bên dưới; không ghi DB | 503 PAYMENT_UNAVAILABLE/DB; invalid provider data trả safe result |
| GET /payments/vnpay/ipn | Public, signed provider query | VNPAY callback query | HTTP200 `{RspCode,Message}` theo provider, **không** data/meta envelope; có X-Request-ID | Provider codes bên dưới; không acknowledge00 khi DB chưa commit |

GET /orders/:id vẫn CUSTOMER owner, dùng để poll paymentStatus/orderStatus/paymentReviewRequired; không thêm public status/mark-paid endpoint. Detail chạy lazy expiry nếu đủ điều kiện, Return chỉ đọc. Retry cần Order VNPAY/PENDING, payment PENDING hoặc FAILED, chưa review/trả kho, trước deadline, expectedVersion hiện tại và không còn attempt PENDING. Scope Idempotency-Key theo Order; body hash gồm expectedVersion, cùng key/body200 trả attempt hiện hành ngay cả đã terminal nhưng không có paymentUrl; khác body409. Retry không kéo dài deadline hoặc trừ kho/tạo Order lần nữa. Initial attempt server key riêng; frontend sử dụng paymentUrl từ checkout, không gọi retry ngay khi initial đang PENDING. Lỗi URL sau commit giữ attempt và trả retryRequired; với retry endpoint, gửi lại nguyên key/body. Các mutation giữ JSON/content type/payload/error conventions chung.

URL chỉ host `sandbox.vnpayment.vn/paymentv2/vpcpay.html`, protocol2.1.0/command pay, amount=Order.total×100, currencyVND, txnRef unique alphanumeric, server OrderInfo/peer IP, create/expire date `yyyyMMddHHmmss` UTC+7. Parameters sort tăng dần, form URL encoding UTF-8 (space→+), HMAC-SHA512; bỏ vnp_SecureHash/vnp_SecureHashType khỏi signature input, constant-time compare. IPN URL đăng ký với merchant, không là parameter payment URL. Callback bắt buộc vnp_TmnCode,vnp_Amount,vnp_TxnRef,vnp_OrderInfo,vnp_ResponseCode,vnp_TransactionStatus,vnp_BankCode,vnp_TransactionNo,vnp_SecureHash; optional vnp_PayDate,vnp_BankTranNo,vnp_CardType,vnp_SecureHashType. Unknown/repeated/missing keys bị từ chối; signature/merchant kiểm tra trước dữ liệu nghiệp vụ. Không trả/lưu card data, raw callback/query/URL hoặc secret; callback metadata chỉ allowlist và fingerprint.

Return data hợp lệ `{result,providerResult,verified:true,confirmed,authoritative:false,orderId,attemptId,paymentStatus,orderStatus,paymentReviewRequired}` không chứa PII. result=SUCCESS chỉ khi DB đã PAID; signed provider success trước IPN→PENDING; failed/cancelled/expired không review→FAILED; review→PENDING (hoặc SUCCESS với confirmed=true khi đã PAID và review flag). providerResult=SUCCESS hoặc FAILED phản ánh hai provider codes. Invalid signature/merchant/missing/duplicate params→`{result:"INVALID_SIGNATURE",verified:false,confirmed:false,authoritative:false}`; signed invalid amount/reference/format→INVALID_RESPONSE cùng shape. Frontend hiển thị kết quả, đăng nhập và poll own Order hữu hạn; Return không xác nhận paid, expire hay restore stock.

| IPN RspCode | Message | Ý nghĩa |
| --- | --- | --- |
| 00 | Confirm Success | Receipt và state/metadata đã commit; gồm failure/review receipt hợp lệ |
| 02 | Order already confirmed | Attempt success/review hoặc failure receipt đã xử lý; không write/downgrade |
| 01 | Order not found | txnRef/Order/owner/payment method relation không hợp lệ |
| 04 | Invalid amount | Callback không khớp attempt/Order/request metadata |
| 97 | Invalid signature | Signature/merchant/unknown/duplicate/missing parameters không hợp lệ |
| 99 | Unable to process | Malformed signed data, thiếu config, DB/transaction/version/unique constraint failure; provider có thể retry |

IPN success require **responseCode00 AND transactionStatus00**, providerTransactionNo khác0; verifiedAt trước deadline và providerPaidAt (nếu có) không vượt deadline. Attempt SUCCEEDED, Order CONFIRMED/PAID +paidAt cùng transaction; invalidate các attempt pending khác, không trừ stock lần nữa. Nếu thiếu payDate hợp lệ thì dùng verifiedAt (UTC). Failure attempt FAILED/Order PENDING+FAILED; không trả kho ngay, có thể retry trong deadline. Expiry worker30s/batch100 hoặc lazy expiry chuyển Order EXPIRED/FAILED, stockReleasedAt/expiredAt, trả tổng quantity/Product đúng một lần, invalidate PENDING attempts. Success sau cancel/expiry/ngoài deadline→attempt REVIEW_REQUIRED và terminal Order REVIEW_REQUIRED +paidAt/review flag; không hồi sinh/trừ kho. Provider paidAt vượt deadline cũng expire/restore trước review nếu Order còn pending. Second distinct success khi Order đã PAID giữ PAID/orderStatus/paidAt, chỉ attempt REVIEW_REQUIRED +Order.paymentReviewRequired=true. Duplicate/failure sau success trả02, không tăng revenue/stock/Order. Revenue definition giữ nguyên; IPN không tạo ledger/revenue entry.

## Admin Orders và Dashboard IMPLEMENTED — PHASE 06B

11 method/path dưới `/api/v1`, tất cả Bearer JWT **ADMIN ACTIVE/current DB role**; Guest401/Customer403. Bad IDs400, JSON malformed400/content type415/payload413, strict input422, DB unavailable503 theo envelope chung. [Review06B](phase-06b-review.md).

| Method / path | Auth / role | Request | Response data / status | Error chính |
| --- | --- | --- | --- | --- |
| GET /admin/orders | Bearer / ADMIN | status?,paymentStatus?,from?,to?,orderCode?,page?,pageSize? | 200 summaries[] + meta pagination | 401/403;400 page syntax;422 query |
| GET /admin/orders/:id | Bearer / ADMIN | Path id, không body/query | 200 AdminOrder | 400 ID;401/403;404;422 query |
| POST /admin/orders/:id/confirm | Bearer / ADMIN | `{expectedVersion}` | 200 AdminOrder | 401/403;404;409 state/version/payment;422 |
| POST /admin/orders/:id/ship | Bearer / ADMIN | `{expectedVersion}` | 200 AdminOrder | 401/403;404;409 state/version/payment;422 |
| POST /admin/orders/:id/complete | Bearer / ADMIN | `{expectedVersion}` | 200 AdminOrder with completedAt | 401/403;404;409 state/version/payment;422 |
| POST /admin/orders/:id/cancel | Bearer / ADMIN | `{expectedVersion}` | 200 AdminOrder | 401/403;404;409 state/version/paid/stock;422 |
| GET /admin/dashboard/summary | Bearer / ADMIN | from,to UTC | 200 `{totalRevenue,totalOrders,totalProductsSold,totalCustomers,...reportMetadata}` | 401/403;422 window/query;503 |
| GET /admin/dashboard/revenue | Bearer / ADMIN | from,to,interval?=day hoặc month | 200 `{series:[{bucket,revenue,orders}],interval,...reportMetadata}` | 401/403;422 window/query;503 |
| GET /admin/dashboard/top-products | Bearer / ADMIN | from,to | 200 `{items:[{productId,productName,quantity,revenue}],...reportMetadata}` max5 | 401/403;422;503 |
| GET /admin/dashboard/category-revenue | Bearer / ADMIN | from,to | 200 `{items:[{categoryId,categoryName,revenue}],...reportMetadata}` | 401/403;422;503 |
| GET /admin/dashboard/order-status | Bearer / ADMIN | from,to | 200 `{items:[{status,count}],dateBasis:"createdAt",...reportMetadata}` | 401/403;422;503 |

Admin list DTO dùng Commerce summaries, không customer/address/items PII. Detail/action `AdminOrder`=Order snapshot DTO Commerce + `allowedActions` chứa các action hợp lệ hiện tại (confirm/ship/complete/cancel). Snapshot/totals bất biến; Admin đọc mọi owner, Customer vẫn own APIs. Query list chỉ `status` map6orderStatus, paymentStatus5enum, exact orderCode uppercase alphanumeric/-1..64, optional `[from,to)` **createdAt** UTC, page/pageSize. Sort cố định createdAt DESC/_id DESC; Mongo facet count/items, pagination1/20,max100, page ngoài cuối data[], emptytotal→totalPages0. Không alias orderStatus/paymentMethod/email/customer/sort; unknown/repeated query422.

Action expectedVersion strict integer1..2147483647, không client state/time/money/snapshot. Stale409 ORDER_CHANGED, wrong state/payment409 INVALID_TRANSITION, cap409 VERSION_LIMIT, restore failure409 STOCK_RESTORE_FAILED và rollback. COD PENDING UNPAID→confirm→CONFIRMED→ship→SHIPPING→complete→COMPLETED/PAID; server set completedAt/paidAt nguyên tử. VNPAY ship/complete chỉ khi đã PAID, giữ paidAt, Admin không manual confirm/pay VNPAY. Cancel reuse Commerce transaction cho PENDING/CONFIRMED chưa PAID/REVIEW_REQUIRED/no review flag, restore stock + invalidate pending attempts once. Complete đã COMPLETED/cancel đã CANCELLED→200 current snapshot với expectedVersion hợp lệ dù cũ, không ghi timestamps/version/stock lần nữa; confirm/ship sau tiến state409. Không generic PATCH Order/refund/resolve review.

Dashboard from/to **bắt buộc**, full ISO UTC có seconds/Z hoặc +00:00/fractional1..6, năm tối đa9998; `from<to`, window<=366×24h. Admin list dates cùng format nhưng optional bounds và không report window cap. Revenue interval default day, chỉ day/month. reportMetadata=`{currency:"VND",timezone:"Asia/Ho_Chi_Minh",from,to,revenueBasis:"PAID_COMPLETED_MERCHANDISE",fetchedAt}`; times UTC milliseconds Z. Day/month bucket YYYY-MM-DD/YYYY-MM theo local calendar, điền0 bucket giao window (max367day buckets khi partial-day). Status đủ6states, missing count0. Empty summary0 trừ Customers global; Top/category[], revenue bucket0. Values vượt2^53-1→503, không rounding.

Revenue/units/Top5/category dùng **COMPLETED AND PAID**, `[from,to)` **completedAt**, revenue merchandise subtotal-discount, không shipping. TotalOrders/status dùng createdAt gồm cancelled/expired; totalCustomers global CUSTOMER gồm BLOCKED. Top5 group productId, rank quantity DESC/revenue DESC/productId ASC, snapshot label gần nhất; Category group snapshot categoryId.8canonical EJSON pipelines được decode/deep-copy/bind, chạy MongoDB aggregate thật; không lookup Product/Category hiện tại hoặc cộng/group raw Orders trong Python/frontend. Các report queries độc lập, không cam kết snapshot xuyên HTTP. Payment method/status charts chưa có contract nên không thêm endpoint. [Admin Order](features/admin-orders.md), [Dashboard](features/admin-dashboard.md), [evidence](../backend/evidence/README.md).

## Phạm vi DEFERRED

Frontend, Reviews/refund/resolve payment review và live Sandbox rehearsal chưa nghiệm thu bởi worker Payment. Không thêm endpoint ngoài contract. IPN dùng provider envelope ngoại lệ đã IMPLEMENTED ở PHASE06A. Các path ngoài contract hiện404.

## Development usage

Production deployment retains the same `/api/v1` contract. `APP_ENV=production` uses an explicit Atlas SRV URI, expected `MONGODB_REPLICA_SET`, separate JWT secret and exact HTTPS frontend origin; it does not auto-load the local `.env`. React reads build-time `VITE_API_BASE_URL` (backend URL + `/api/v1`); local default remains `/api/v1`. See [deployment](features/deployment.md) and [ADR012](decisions/012-render-production-runtime.md). This configuration does not imply that a public Render deployment has passed verification.

Máy hiện tại chạy `http://127.0.0.1:5001/api/v1/health`; API_PORT trong .env quyết định port, example mặc định5000. CORS mặc định FRONTEND_ORIGIN từ env (http://localhost:5173), exactallowlist, supportscredentials=false; Authorization/Content-Type/Idempotency-Key được phép. Payload tối đa1MiB configurable. [Cách chạy](backend-setup.md), [review/evidence](phase-04-review.md). Không cần đọc backend internals để hiểu status/body/params.
