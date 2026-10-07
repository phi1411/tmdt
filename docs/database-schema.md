# MongoDB schema — LOCKED DESIGN v1

Ngày07/10/2026: PHASE02 đã duyệt, PHASE03 apply nguyên sáu validator trên MongoDB8.0.32 local rs0, chọn14declared indexes và nạp/verify dữ liệu thật. **Không thay schema v1, chưa implement business backend.** Meaning ở file này; exact shape/type/bounds canonical tại [validators](../database/validators/README.md), ví dụ thiết kế tại [samples](../database/samples/README.md), evidence runtime tại [phase03 review](phase-03-review.md). Không copy JSON Schema sang nhiều docs/backend.

## Mục lục

1. Quy ước
2. users
3. categories
4. products — Polymorphic Schema
5. carts
6. orders — Embedded Snapshot
7. payment_attempts
8. Embed/reference và service invariants
9. Index, aggregation, schema evolution

## 1. Quy ước

Collections: users, categories, products, carts, orders, payment_attempts. reviews **DEFERRED**, không tạo collection MVP. Mỗi document có `_id:ObjectId`, `schemaVersion:int=1`, `createdAt/updatedAt:Date UTC`. Entity mutable có `version:int>=1`; User thêm tokenVersion>=0. API `_id`→id hex24, Date→ISO UTC, long→safe JSON integer.

Money: integer VND, BSON long qua `bson.int64.Int64` explicit, không double/string/bool. Quantity/stock/version BSON int, reject bool. Defaults/limits/config canonical tại [foundation-decisions](foundation-decisions.md); Root fields strict, dynamic data chỉ trong attributes. Date optional omit nếu chưa có, không null; defaultAddressId cho phép null.

Validator chỉ kiểm tra một document; reference, normalization, totals, legal transition, timestamp ordering và snapshot immutability cần service. Unique indexes enforce invariants khác shape. Source request phase02 tại [requirements-phase-02-source.txt](requirements-phase-02-source.txt).

## 2. users

Validator [users.json](../database/validators/users.json); examples [users.json](../database/samples/users.json).

| Fields | Type / meaning |
| --- | --- |
| email | string<=254, lowercase/trim, unique; không strip dot/plus |
| passwordHash | Argon2id string, private, không API response |
| role / status | CUSTOMER hoặc ADMIN / ACTIVE hoặc BLOCKED; Guest không lưu |
| tokenVersion / version | int>=0 / int>=1; mutation password/status thu hồi token và tăng version |
| name / phone | name1..100; phone string optional empty trước checkout, có dữ liệu phải8..15 digits optional+ |
| addresses[] | <=10 embedded address: _id,label?,receiverName,phone,addressLine,province,ward?,district? |
| defaultAddressId | ObjectId thuộc addresses hoặc null |

Address người dùng có label; Order snapshot không copy label/_id. Không embed Cart/Orders/Reviews trong User. Xóa default address→null; profile/address đổi không rewrite Order. Persisted arrays/defaults ghi explicit. Account/Admin restrictions tại BR-AUTH/admin-users, không thêm role.

## 3. categories

Validator [categories.json](../database/validators/categories.json); examples [categories.json](../database/samples/categories.json).

| Fields | Type / meaning |
| --- | --- |
| name / slug | string1..100 / lowercase hyphenated<=120 unique |
| productType | ELECTRONICS / FASHION / HOME_APPLIANCE |
| description | plain text<=2000, có thể empty |
| status / version | ACTIVE hoặc ARCHIVED / int>=1 |

**Một cấp, không parentId** theo ADR009: đủ3 ngành, không xây taxonomy tree chưa cần. Nhiều Category có thể cùng productType; Product.categoryId reference và productType phải khớp. Type không đổi khi đã có Product. Archive chặn browse/publish/checkout; delete chỉ khi chưa referenced, kể cả archived Product. Guarded Category version writes để serialize với create/move/publish/checkout (BR-CATALOG); slug unique không reuse.

## 4. products — Polymorphic Schema

Validator [products.json](../database/validators/products.json); examples [products.json](../database/samples/products.json); modeling ADR001.

| Fields | Type / meaning |
| --- | --- |
| sku / name / slug | unique SKU<=64 / name<=200 / unique slug<=220 |
| productType / categoryId | discriminator3 nhóm / ObjectId reference Category compatible |
| brand / description | string<=100 có thể empty / plain text<=10000 |
| nameNormalized / brandNormalized | server-derived strings phục vụ search, normalization ADR008 |
| price / stock | long1..1e9 VND / int>=0 available stock |
| images[] | <=8 absolute URL, không binary/upload; HTTP chỉ loopback dev, HTTPS bình thường |
| attributes | dynamic object1..30 keys, bounded3 mức; type-check known fields theo discriminator |
| status / version | ACTIVE / INACTIVE / ARCHIVED; version>=1 tăng cả stock mutations |

Tất cả nằm **một collection products**; không products_electronics/fashion/home. Root shared shape, oneOf branch chọn schema attributes. Field ví dụ:

| Nhóm | attributes example |
| --- | --- |
| ELECTRONICS | ram8GB/storage256GB/chip/screen/battery strings |
| FASHION | sizes:[S,M,L], colors:[Black,White], material:Cotton, gender:Unisex |
| HOME_APPLIANCE | power1700W/capacity6L/voltage220V/material strings |

Known attributes optional theo thiết bị (tai nghe không cần RAM); unknown safe keys được lưu scalar/arrays/bounded objects qua patternProperties. Service validate key names/finite numeric/depth/bounds, không yêu cầu ADR để thêm key spec thông thường hợp lệ. Thêm productType mới hoặc biến thể tồn/giá riêng cần ADR. Một Product=oneSKU/oneprice/onepoolstock, sizes/colors không có stock riêng.

SKU immutable sau create để trace demo/simple links; slug/name/brand/attributes có thể sửa theo version. Category move sang type khác cần update attributes tương hợp trong cùng request/transaction, không làm snapshot cũ đổi. DELETE=archive, không hard-delete. Current Product sample điện thoại12 triệu nhưng snapshot Order10 triệu là có chủ đích.

`nameNormalized/brandNormalized` không nhận từ client: NFKD/casefold/đ→d/remove combining marks/whitespace collapse. q literal substringANDtokens theo name; brand exact normalized; không Atlas/full-text engine. Không claim name substring indexed.

## 5. carts

Validator [carts.json](../database/validators/carts.json); examples [carts.json](../database/samples/carts.json); ADR004.

| Fields | Type / meaning |
| --- | --- |
| userId / version | ObjectId owner unique / int>=1 persisted |
| items[] | <=50 embedded lines; empty allowed |
| items.lineId | lowercase SHA-256 hex64 từ canonical productId+selectedAttributes |
| items.productId / quantity | ObjectId reference current Product / int1..99 |
| items.selectedAttributes | object optional size/color strings; no price/specification payload |

lineId=SHA-256 UTF8 canonical JSON `{productId:<hex>,selectedAttributes:<sorted object>}` (keys sorted, separators comma/colon, ensure_ascii=false). Same selection merge; khác selection shared poolstock. Service bảo đảm lineId đúng/unique và sumqty/Product<=stock. Không lưu giá authoritative. GET enrich currentPrice/lineTotal/issues từ server Product/Category; Cart không reserve.

Cart tạo lazy: chưa có→API version0/items[], first add version1; unique userId guard concurrent upsert. Sau checkout/clear **giữ document**, items=[] và version+1 để version không reset. User address/password không contend cùng Cart. Request cartVersion, response version; stale409.

## 6. orders — Embedded Snapshot

Validator [orders.json](../database/validators/orders.json); examples [orders.json](../database/samples/orders.json); ADR003/006/007.

| Fields | Type / meaning |
| --- | --- |
| orderCode / userId | unique code / ObjectId owner reference |
| checkoutKey / checkoutRequestHash | key8..128 unique theo User / SHA256 request intent canonical |
| customerSnapshot | embedded name/phone/email lúc mua |
| shippingAddress | embedded receiverName/phone/addressLine/province, ward/district optional; không address reference sống |
| items[] |1..50 snapshot lines; **seed2..5** |
| subtotal / shippingFee / discount / total | BSON long; subtotal=sumlines, discount0, total=subtotal+ship |
| currency / paymentMethod | VND / COD hoặc VNPAY |
| paymentStatus / paymentReviewRequired | UNPAID/PENDING/PAID/FAILED/REVIEW_REQUIRED / required boolean |
| orderStatus / version | PENDING/CONFIRMED/SHIPPING/COMPLETED/CANCELLED/EXPIRED / int>=1 |
| paymentExpiresAt | Date required VNPAY, omit COD; deadline giữ kho cố định |
| paidAt / completedAt | actual accepted provider/COD payment time / revenue recognition event; conditional presence |
| cancelledAt / expiredAt / stockReleasedAt | Date terminal event/once-only stock restoration marker, omit trước terminal |

Mỗi items entry **required**: productId:ObjectId, sku, productName, image:URL hoặc empty, productType, categoryId:ObjectId, categoryName, attributesSnapshot:Object, selectedAttributes:Object, priceAtPurchase:long, quantity:int, lineTotal:long. categoryId/name/productType snapshot phục vụ report mà không JOIN; productId giữ trace/stock nhưng không lấy currentprice. attributesSnapshot copy specification lúc mua, selectedAttributes là size/color lựa chọn (rỗng nếu không options).

Snapshot items/customer/address và totals immutable, không generic PATCH. Cho phép state/time/version/review updates được guard. URL snapshot không copy media binary; fallback nếu tài nguyên mất. Tạo Order revalidate Product từ server, không nhận clientprice. Checkout transaction decrement conditional tổngquantity/Product+tăng version, guarded Category write, insert snapshot Order(+initialattemptVN), clear Cart đúng version cùng commit.

Checkout replay hash=SHA256 canonical original `{cartVersion,addressId,paymentMethod,quoteToken}`; check existing Order first trước Cart/quoteexpiry, same key/hash200 Order cũ, differentintent409. Không expose hash/key trong public responses. Quote signature gắn owner/cartVersion/addressId/addressHash/prices/fees/selections/payment/TTL; default5min. Không persist quotes collection.

Lifecycle/money/revenue nguồn chuẩn BR-ORDER/BR-PAYMENT/BR-REPORT. VNPAY total<=9.999.999.999 VND để scaled amount<=12digits; COD Order total<=5e12. Validator enforce legal at-rest combos/timestamp presence; service enforce transitions/chronology/arithmetic/sideeffects.

## 7. payment_attempts

Validator [payment_attempts.json](../database/validators/payment_attempts.json); examples [payment_attempts.json](../database/samples/payment_attempts.json).

| Fields | Type / meaning |
| --- | --- |
| orderId / userId | ObjectId Order reference/owner; nhiều attempts cùng Order |
| attemptKey / requestHash | idempotency scoped Order / SHA256 canonical create intent, checkout initial intent derived |
| txnRef / provider | unique alphanumeric<=100 / VNPAY only |
| amount / currency | long amount=Order.total <=provider cap / VND |
| status / version | PENDING/SUCCEEDED/FAILED/EXPIRED/REVIEW_REQUIRED / int>=1 |
| expiresAt | fixed deadline bằng Order.paymentExpiresAt; retry không kéo dài |
| paymentRequest | minimal immutable request metadata đủ tái dựng URL, camelCase mapping ở dưới |
| providerTransactionNo? | nonzero digits1..15, omit missing/0/failure placeholder; partial unique khi real string |
| responseCode? / transactionStatus? / bankCode? | allowlisted callback codes/meta, không raw query |
| verifiedAt? / providerPaidAt? / callbackFingerprint? | server verification time / providerDate UTC / SHA256 canonical verified callback |
| expiredAt? | server expiry/cancel-invalidate event |

paymentRequest required: version2.1.0,commandpay,tmnCode8chars,amountScaled long=amount×100,currencyVND,txnRef,orderInfo chữ/số/khoảng trắng không dấu<=255,orderTypeother,localevn,returnUrl absolute URL<=255,clientIp,createdAt,expiresAt. Adapter mapping sang provider vnp_ fields, provider times format GMT+7 yyyyMMddHHmmss; original values giữ nguyên khi tái dựng URL để retries cùng attempt không đổi intent. No hashSecret/JWT/card/billing details, no stored signedpaymentUrl. Request fields server-derived; secrets env. providerPaidAt có thể vắng theo provider protocol; service dùng verifiedAt làm paidAt/deadline fallback (BR-PAYMENT).

COD không tạo attempts. Online Order status là summary nghiệp vụ, attempts giữ lịch sử riêng. Unique txnRef+order/attemptKey+partial pendingOrder+providerTxnNo enforce idempotency/concurrency. Same callback no-op, failure sau success không downgrade, late/second distinct success review theo BR-PAYMENT. Không TTL-delete chứng từ. Seed attempts được ghi là fixtures, không giả mạo payment thật.

## 8. Embed/reference và service invariants

| Relationship | Strategy / reason |
| --- | --- |
| User→addresses | bounded embed cùng lifecycle |
| User→Orders | reference qua orders.userId; pagination, không growing User array |
| Product→Category | reference dữ liệu catalog sống có quản trị riêng |
| Cart→lines/Product | embed bounded lines + Product reference/current pricing |
| Order→items/customer/address/category | historical embedded snapshot independent current entities |
| Order→productId/userId | trace/ownership/stock bổ sung, không nguồn giá/nội dung history |
| Attempt→Order/User | reference lifecycle payment/history riêng |

MongoDB không foreignkey tự động. Service kiểm tra category.type/status và ownerrefs, Productselection membership, unique IDs trong addresses/Cart, normalizedfields, integerpricing/overflow/sum, orderedtimestamps, snapshotsimmutable, state+version, stockreleasedonce. Indexes và JSONSchema không thay thế transaction. Local replica set required, primary reads/snapshottransaction/majority commit; retries không external sideeffects.

## 9. Index, aggregation, evolution

[Candidate index manifest](../database/indexes/candidate-indexes.json) là exact key/options/query/ESR; [aggregation designs](../database/aggregations/README.md) là canonical pipeline, không copy trong feature docs. No lookup Product/Category để tính history. Báo cáo từ snapshot Completed+Paid theo completedAt, Top5 group productId, Categorygroup snapshotcategoryId.

SchemaVersion1 locked; phase03 đã create/load/test sáu validator thật, seed/aggregation/index/roundtrip và baseline explain. JSON canonical v1 không cần correction/ADR mới. Schema change về sau cần ADR/versioned migration/dryrun/invariant verification; không backfill snapshot từ currentProduct. Full benchmark và business API chưa triển khai. Deferred scopes tại foundation-decisions, không còn modeling OPEN block backend.
