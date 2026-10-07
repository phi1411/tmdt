# API contract — Backend PHASE 05A Auth/User + PHASE 05B Catalog

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

Access JWT HS256 với issuer/audience đã config, expiresIn mặc định1800. Guard đọc lại User ACTIVE/current role/tokenVersion mỗi request; không nhận role/status/security fields từ browser. Đổi password/status thực sự tăng version/tokenVersion nguyên tử; profile/address tăng version, giữ tokenVersion. Logout UI chỉ xóa memory token, không revoke JWT; không có logout/refresh/forgot/social routes. Customer address ID của người khác→404; add không tự set default, xóa default→null cùng write. Admin status chỉ Customer; mọi Admin account được bảo vệ. Same-status200 no-op với expectedVersion đúng, không tăng version/tokenVersion.

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

## API nghiệp vụ PLANNED

| Nhóm | Method/path tương đối `/api/v1` | Contract chi tiết |
| --- | --- | --- |
| Cart |GET /cart, item mutations/clear |[cart](features/cart.md) |
| Checkout |GET /checkout/quote,POST /orders |[checkout](features/checkout.md) |
| Orders |GET /orders,GET /orders/:id, cancellationaction |[orders](features/orders.md) |
| Payment |attempt creation,status,providercallbacks |[payment](features/payment.md) |
| Admin Order |order management |[admin-orders](features/admin-orders.md) |
| Dashboard |GET /admin/dashboard/* |[admin-dashboard](features/admin-dashboard.md) |

Bảng này là danh mục planning, không thêm endpoint thay contract feature. Reviews DEFERRED, không endpoint. IPN envelope ngoại lệ theo provider chỉ triển khai ở phasePayment. Các path chưa implemented hiện404; không stub200 giả thành công.

## Development usage

Máy hiện tại chạy `http://127.0.0.1:5001/api/v1/health`; API_PORT trong .env quyết định port, example mặc định5000. CORS mặc định FRONTEND_ORIGIN từ env (http://localhost:5173), exactallowlist, supportscredentials=false; Authorization/Content-Type/Idempotency-Key được phép. Payload tối đa1MiB configurable. [Cách chạy](backend-setup.md), [review/evidence](phase-04-review.md). Không cần đọc backend internals để hiểu status/body/params.
