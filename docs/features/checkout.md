# Checkout

## Goal

Từ Cart/address tới Order snapshot, pricing/tồn kho nhất quán. **PHASE05C COD +PHASE06A VNPAY backend IMPLEMENTED** khi đủ cấu hình; frontend deferred, live Sandbox chưa rehearsal. Đây là transaction orchestration owner. [Contract](../api-contract.md), [review05C](../phase-05c-review.md), [Payment](payment.md).

## Actors

Customer active; Admin không tạo đơn thay Customer.

## Functional Requirements

Server quote, Customer xác nhận, POST Order idempotent, check stock/selection/address/price, atomic stock+order+cart, trả hướng dẫn COD/VNPAY sau commit.

## Business Rules

BR-CHECKOUT/BR-ORDER; quoteToken signed binds owner/cartVersion/addressId/addressHash/payment/price/fee/selection/expiry. Address cùng ID đổi nội dung→QUOTE_CHANGED409. Quote không giữ hàng. Checkout revalidate server data, compare confirmed quote, group qty/Product, guarded category write and conditional Product decrement. Stock/order/clear Cart items và tăng version (giữ document)/initial payment attempt cùng transaction. Repricing409 không tạo Order. Replay key/body check existing Order trước Cart/quote expiry.

## Permission

CUSTOMER owner Cart/Address; no client userId, price, orderStatus. Role/Admin override không thuộc baseline.

## API

| Method / path | Request | Response data | Error |
| --- | --- | --- | --- |
| GET /checkout/quote | addressId,paymentMethod; Bearer | 200 quote contract + quoteToken/expiresAt/issues | 404 address;409 cart/product issue;422 |
| POST /orders | {cartVersion,addressId,paymentMethod,quoteToken}, Idempotency-Key | 201 {order,payment};200 same replay | 409 CART_CHANGED/STOCK_CONFLICT/PRICE_CHANGED/QUOTE_CHANGED/QUOTE_EXPIRED/IDEMPOTENCY_CONFLICT;404;422;503 |

Order creation thuộc feature này; Orders doc chỉ detail/history/cancel, không API POST khác.

## Data

Read User/Cart/Category/Product; write Product stock/version, Category guard version, Order, Cart version/clear và initial payment_attempts nếu online. Paths `app/api/checkout.py`, `app/services/checkout_service.py`, `app/services/commerce_pricing.py`, cart/order/category/product/user repositories, `app/schemas/checkout_schema.py`; PHASE06A dependency trực tiếp `PaymentService.initial_attempt/checkout_result`, `VnpayProvider` và PaymentAttemptRepository. Reuse `app/services/catalog_transaction.py` snapshot/majority, tối đa3 transaction attempts/3 commit attempts, finite transient backoff20/40ms; unknown commit chỉ retry commit. Dependencies Auth live identity, Cart, Orders immutable/state contract, shared errors/validation/serialization. Tests `backend/tests/test_commerce.py`, `test_payment.py`; HTTP `scripts/backend/verify_commerce_runtime.py`, `verify_payment_runtime.py`; frontend `features/checkout/` chưa tạo.

## Validation

Address owner/current, User active/tokenVersion/role current, profile phone8..15 digits optional+ (empty→422), Cart correct version/nonempty, quote valid/reprice consistent, price/qty integer/overflow, category/type/selection. Fees/TTLs config SHIPPING_FEE_VND default30000/range0..1000000, QUOTE_TTL_SECONDS default300/range1..3600; invalid/blank fail startup. COD cap5e12, VNPAY cap9999999999VND. PHASE06A cho phép VNPAY_ENABLED=true chỉ với valid VNP_* Sandbox config; false→503 PAYMENT_UNAVAILABLE trước hold/write. Online Order PENDING/PENDING, deadline15phút và initial attempt cùng transaction; URL ký sau commit, fault trả retryRequired, replay không tạo lại đơn. [Setup](../payment-setup.md).

Quote HS256 audience checkout-quote-v1 dùng SHA256 key domain-separated từ JWT_SECRET; placeholder QUOTE_SIGNING_SECRET cũ không được dùng. Token bind user/cart/address hash/payment/full item snapshot pricing hash/expiry, không lưu collection. Chữ ký sai422, expiry409, address đổi QUOTE_CHANGED, price/fee/snapshot/selection đổi PRICE_CHANGED, stale Cart CART_CHANGED. Same-key same-body replay đọc Order trước quote/cart và trả trạng thái hiện hành200. Idempotency-Key opaque printable ASCII không khoảng trắng8..128; hash canonical nguyên body (không lowercase/trim).201 có Location. Unknown commit response503 cần retry nguyên key/body.

## Edge Cases

Concurrent stock1, duplicate key race, Cart changed, quote expired, address removed, price increased/decreased, rollback after second item, commit response lost; URL failure after committed VNPAY Order trả retryRequired thay vì tạo lại đơn.

## Security

Server key/hash/quote signatures, canonicalization allowlist; no transaction external side effect; no trust client amount; protect ownership/role. Do not log full quoteToken/address/secrets.

## UI Behavior

Address/payment picker, quote summary, total server, confirm submit disabled đang xử lý. 409 fetch quote mới để Customer xác nhận; network retry dùng cùng key/body, chỉ tạo key mới khi thay ý định. Sau success clear Cart UI từ server và đi Order/detail/provider URL.

PHASE07A đã kiểm tra frontend production. Intent đặt hàng giữ nguyên key/body khi mất response hoặc503. Với initial VNPAY attempt đã commit nhưng URL lỗi, gửi lại đúng POST /orders tối đa một lần trong mỗi lượt xác nhận; nếu vẫn retryRequired thì giữ intent để người dùng xác nhận lại, không gọi payment-attempts cạnh tranh với initial PENDING attempt. Intent chỉ đổi khi payload/ý định thay đổi hoặc request bị từ chối rõ ràng4xx.

## Acceptance Criteria

Đặt COD snapshot đầy đủ, one transaction/no partial data, same replay one Order/one stock decrement. Changed quote không âm thầm charge khác, rollback/concurrency đúng; VNPAY adapter chỉ sau commit.

## Testing Checklist

- [x] Quote signature/expiry/binding/price tăng-giảm/fee/address change và reject client totals.
- [x] Ownership/version/selection/shared stock; stock1 concurrency và Category archive race trên rs0.
- [x] Rollback fail product thứ2/insert/Cart clear; duplicate checkout race; real commit mất response503 rồi replay200.
- [x] COD snapshot10→12 triệu và tên/attributes/category/profile/address/image độc lập.
- [x] VNPAY503 không hold/Order/attempt hoặc fake PAID.
- [x] PHASE06A VNPAY adapter/atomic initial attempt/post-commit URL/rollback/races/expiry worker trên test rs0.
- [ ] Live merchant/IPN rehearsal và frontend deferred.
