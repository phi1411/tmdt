# Review PHASE02 — Lock MongoDB Design & Foundation Decisions

## Trạng thái và phạm vi

**Hoàn thành khóa thiết kế v1 và kiểm tra tĩnh, dừng để review.** Cấu trúc phase01 đã được người dùng chấp nhận. Phase02 không cài dependency/server, không khởi tạo MongoDB, không apply validators/indexes, không seed đầy đủ và không implement Auth/Product/Cart/Checkout/Order/Payment/Frontend.

Có một script kiểm tra thiết kế độc lập, không API/service nghiệp vụ. Các artifact JSON là validator/pipeline/index specification và schema examples; không phải ứng dụng chạy được. Source requirement phase02 giữ nguyên tại requirements-phase-02-source.txt.

## 1. Các quyết định đã khóa

English collection names; local MongoDB Community8.0 single-node replica set rs0/WiredTiger; Python3.12/Flask/PyMongo backend contract; React/Vite/TypeScript/Tailwind/Recharts frontend contract do agent khác triển khai về sau. Atlas chỉ deployment option, không Atlas-only feature. Product images URL-only; no upload/cloud media. Reviews DEFERRED.

Category một cấp, không parentId; Product một collection với discriminator+attributes. Cart riêng/User. Order embedded snapshot và transaction/version/quote/idempotency. COD+VNPAY Sandbox và attempts metadata/callback guards. Revenue và Vietnamese search local đã khóa ở ADR007/008. Defaults chi tiết canonical tại [foundation-decisions](foundation-decisions.md).

## 2. Collections và schema chính thức

Meaning ở [database-schema](database-schema.md), exact validator ở [database/validators](../database/validators/README.md). Common fields _id/schemaVersion/createdAt/updatedAt không lặp trong bảng.

| Collection | Fields/aggregate chính | Quan hệ |
| --- | --- | --- |
| users | email/passwordHash/role/status/tokenVersion/version/name/phone/addresses/defaultAddressId | addresses embed bounded; Orders/Cart không embed vào User |
| categories | name/slug/productType/description/status/version | một cấp; Product reference type-compatible |
| products | sku/name/slug/productType/categoryId/brand/description/nameNormalized/brandNormalized/price/stock/images/attributes/status/version | một collection, Category reference, attributes đa hình |
| carts | userId/version/items(lineId/productId/quantity/selectedAttributes) | một document/User; line embed + Product reference, không giá persist |
| orders | orderCode/userId/checkoutKey/checkoutRequestHash/customerSnapshot/shippingAddress/items/subtotal/shippingFee/discount/total/currency/paymentMethod/paymentStatus/paymentReviewRequired/orderStatus/version/timestamps | snapshot Product/category/customer/address embedded, history không lookup giá sống |
| payment_attempts | orderId/userId/attemptKey/requestHash/txnRef/provider/amount/currency/status/version/expiresAt/paymentRequest/verified callback metadata | nhiều attempts/Order, một PENDING active, COD không tạo attempt |

## 3. Product Polymorphic

Fields chung và oneOf productType: ELECTRONICS, FASHION, HOME_APPLIANCE. Electronics có RAM/storage/chip, Fashion sizes/colors/material, Gia dụng power/capacity/voltage. Không collection theo ngành hoặc bảng thuộc tính kiểu SQL. Known keys type-check, extension safe keys/scalar/array/object tối đa3 mức được phép; không buộc mọi Electronics có RAM.

## 4. Order embedded/snapshot

customerSnapshot, shippingAddress và items embedded immutable. Mỗi item có productId/sku/productName/image/type/categoryId/categoryName/attributesSnapshot/selectedAttributes/priceAtPurchase/quantity/lineTotal. Price lấy server; long integer VND. Product sample điện thoại12 triệu, Order snapshot10 triệu. Totals/history/Top/Category revenue không JOIN Product/User/Category sống.

Lifecycle: PENDING→CONFIRMED→SHIPPING→COMPLETED. CANCELLED chỉ PENDING/CONFIRMED khi chưa PAID/REVIEW_REQUIRED; EXPIRED chỉ VNPAY PENDING quá deadline. Không PROCESSING vì không cần stage riêng cho MVP. Restore stock once, version guard, terminal timestamps bắt buộc đúng branch. Không hủy paid/shipping/completed hoặc tự refund.

## 5. Cart

carts riêng unique userId; versioned bounded items, không reserve stock hoặc persist authoritative price. Current prices backend enrich. Same Product/selection merge, nhiều selection dùng chung stock. Clear/checkout giữ Cart document, items=[]/version+1. Checkout atomic stock+snapshotOrder+Cart(+initial online attempt) trên local replica set.

## 6. Payment

COD UNPAID khi đặt, PAID cùng COMPLETED. VNPAY IPN valid mới PAID/CONFIRMED; ReturnUrl chỉ UX/poll. Attempts có unique txnRef/orderKey/providerTxnNo và partial unique PENDING/order; request metadata đủ tái dựng URL, callback allowlist/fingerprint, không secret/card/raw PII.

Duplicate callback không trừ kho/tạo doanh thu lặp. Deadline guard và cancel/expiry race chung transaction; late success→REVIEW_REQUIRED, không hồi sinh Order. Distinct second success trên Order đã PAID giữ doanh thu hợp lệ trước đó và bật review flag. Amount×100 tối đa12 chữ số nên online cap riêng; reject trước stock write. Credentials/IPN reachable là cấu hình vận hành phasePayment, không design blocker.

## 7. Revenue definition

Chỉ COMPLETED+PAID qualify, merchandise=subtotal-discount (discount0), **loại shipping**. Cả COD và VNPAY tính theo completedAt, không theo checkout hoặc online paid sớm. Cancelled/expired/review-required excluded. Day/month/Top5/Category cùng cohort `[from,to)` và timezone Asia/Ho_Chi_Minh. OrderCount/Status theo createdAt; Customers global role CUSTOMER gồm blocked. ADR007/BR-REPORT là nguồn chuẩn.

## 8. Candidate indexes

[Manifest](../database/indexes/candidate-indexes.json) có18 entries:11 unique invariant +7 workload candidates, mỗi entry ghi equality/sort/range/reason/options. Workload gồm Product category/type+price, User Order history, Admin status/latest, global createdAt, qualified completedAt và online deadline. No name substring/text/wildcard/reviews index. Chưa tạo hoặc đo; chuẩn bị explain COLLSCAN/IXSCAN/docs/keys/time ở DB benchmark riêng sau này.

## 9. Aggregations dự kiến

Canonical [database/aggregations](../database/aggregations/README.md): Revenue Day/Month, Top5, Category Revenue, Sales Summary, Order Count, Status Distribution, Customer Count. Revenue match/group/sort; Top5 match/unwind/group/sort/limit. Concrete EJSON date range minh họa, bind runtime params sau review; field paths khớp schema. Không copy pipeline trong frontend/feature docs; không sum Order.total sau unwind.

## 10. Seed target

180 Product (60 mỗi ngành),40 User (1Admin+39Customer),100 Order/2–5 Product lines, tối thiểu3ngành. Generate Order snapshot từ chính Product/version pool, RNG20261007/anchor2026-10-01UTC, deterministic IDs/content/timeline/stock reconciliation. Public source optional cached/normalized; synthetic baseline không phụ thuộc internet. **19 schema examples hiện có không thay bộ Dummy Data.**

## 11. Files tạo/sửa

- Tạo: foundation-decisions.md, phase-02-review.md, phase-02-validation.json, bản source requirement phase02; ADR007/008/009.
- Tạo:6validator JSON +6sample JSON +candidate-indexes.json +8aggregation JSON, README tại bốn thư mục database; scripts/validation/validate_design.py.
- Sửa: AGENTS, README, .env.example, backend/requirements.txt (comments status), requirements/architecture/database-schema/business-rules/api-conventions/testing/seed/demo, phase01-review (archived); ADR001–006/index.
- Sửa feature docs chịu ảnh hưởng: auth/users/products/search-filter/cart/checkout/payment/reviews/admin-products/admin-orders/admin-dashboard. Categories/orders/admin-users giữ contract phù hợp baseline, không rewrite module không liên quan.

## 12. Validation và giới hạn

Command: `python scripts/validation/validate_design.py --write-report`. Evidence tại [phase-02-validation.json](phase-02-validation.json). JSON Schema draft4 keywords kiểm tra qua jsonschema, custom BSON type markers từ EJSON; samples/reference/money/normalization/status/index paths/pipeline references có check tĩnh. Có positive extension và legal state variants, negative cases. Checker không kết nối MongoDB, không chạy aggregate hoặc benchmark; không chứng minh production auth/payment/runtime.

Kết quả cuối:6 validators/19 samples hợp lệ,21 negative cases bị từ chối,8 legal status variants bổ sung pass, polymorphic extension pass,18 index specs/8 pipeline designs kiểm tra field paths. Documentation audit:14 feature docs đúng13 sections,41 Markdown/22 JSON parse được,65 relative links hợp lệ,2 bản source requirement khớp SHA-256, backend/app và frontend/src chưa có implementation.

Fixture qualified kỳ vọng21.900.000 VND và5units/2Order;60.000 VND shipping excluded. Chỉ tính độc lập từ fixture để kiểm tra định nghĩa, không nói đây là kết quả MongoDB chạy. Phase runtime sau phải apply validators/indexes trên8.0 replica set, chạy pipeline/integration/concurrency và explain thật.

## 13. OPEN / DEFERRED

**Không còn OPEN QUESTION về thiết kế block backend.** OQ01 names resolved; OQ02 local/major contract resolved (exact patch pins bootstrap); OQ03 TypeScript resolved/shadcn deferred; OQ04 search resolved; OQ05 state/TTL/worker/manual policy resolved, credentials/IPN deferred; OQ06 defaults/limits resolved; OQ07 Reviews deferred; OQ08 revenue resolved; OQ09 URL media resolved, sprint ownership deferred theo nhóm.

Atlas/domain/cloud media, taxonomy tree, variant stock, Review, fuzzy search, refresh/forgot-password, automated refund và persistent audit deferred. Không đưa chúng làm dependency bắt buộc cho MVP. Không tự bắt đầu phase tiếp theo; dừng để người dùng review.
