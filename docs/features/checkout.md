# Checkout

## Goal

Từ Cart/address tới Order snapshot, pricing/tồn kho nhất quán. P0 COD + P1 VNPAY. Chưa implement. Đây là transaction orchestration owner.

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

Read User/Cart/Category/Product; write Product stock/version, Category guard version, Order, Cart version/clear, payment_attempts initial nếu VNPAY. Paths `api/checkout.py`, `services/checkout_service.py`, relevant repository methods/session; `schemas/checkout_schema.py`; `features/checkout/`. Dependencies Cart, Orders immutable/state contract, payment adapter only; không Dashboard/Review.

## Validation

Address owner/current, User active, Cart correct version/nonempty, quote valid/reprice consistent, price/qty integer/overflow, category/type/selection. paymentMethod COD/VNPAY và feature VNPAY_ENABLED. Fees/TTLs/limits đã khóa ở foundation-decisions; VNPAY amount cap kiểm tra trước stock write. Chưa triển khai config/service.

## Edge Cases

Concurrent stock1, duplicate key race, Cart changed, quote expired, address removed, price increased/decreased, rollback after second item, commit response lost; URL failure after committed VNPAY Order trả retryRequired thay vì tạo lại đơn.

## Security

Server key/hash/quote signatures, canonicalization allowlist; no transaction external side effect; no trust client amount; protect ownership/role. Do not log full quoteToken/address/secrets.

## UI Behavior

Address/payment picker, quote summary, total server, confirm submit disabled đang xử lý. 409 fetch quote mới để Customer xác nhận; network retry dùng cùng key/body, chỉ tạo key mới khi thay ý định. Sau success clear Cart UI từ server và đi Order/detail/provider URL.

## Acceptance Criteria

Đặt COD snapshot đầy đủ, one transaction/no partial data, same replay one Order/one stock decrement. Changed quote không âm thầm charge khác, rollback/concurrency đúng; VNPAY adapter chỉ sau commit.

## Testing Checklist

- [ ] Quote signature/expiry/price/fee change and no trusted client totals.
- [ ] Ownership/version/selection/shared stock; stock1 concurrency.
- [ ] Rollback fault injection và duplicate/idempotency network replay.
- [ ] COD snapshot10→12 triệu, VNPAY post-commit failure contract.
