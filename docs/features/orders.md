# Order history và chi tiết đơn

## Goal

Customer đọc lịch sử bằng dữ liệu snapshot và hủy khi đủ điều kiện. P0 snapshot, P1 history/cancel; chưa implement. POST tạo đơn thuộc checkout.

## Actors

Customer owner; Admin dùng admin-orders, không customer endpoint để đọc người khác.

## Functional Requirements

History paginated/filter trạng thái/ngày tạo, detail Order đầy đủ snapshot/totals/payment/state, cancel owner trước khi thanh toán/giao. Không sửa items/address/totals sau tạo.

## Business Rules

BR-ORDER: snapshot immutable; cancel PENDING/CONFIRMED khi chưa PAID/REVIEW_REQUIRED; không SHIPPING/COMPLETED. Transaction status predicate/version + stock restore tổng qty/Product và stockReleasedAt once. Already CANCELLED replay action trả Order hiện hành200, không trả thêm kho; EXPIRED/các trạng thái khác409.

## Permission

Customer đọc/hủy chính mình; JWT owner trong repository filter. Unknown/other owner404; Admin management route riêng.

## API

| Method / path | Request | Response data | Error |
| --- | --- | --- | --- |
| GET /orders | status?,from?,to?,page,pageSize | 200 own summaries + meta | 401/403/422 |
| GET /orders/:id | Bearer, id | 200 Order snapshot/version/status | 404 owner/missing;401/403 |
| POST /orders/:id/cancel | {expectedVersion} | 200 Order state | 404;409 INVALID_TRANSITION/stale |

List dateBasis=createdAt, stable sort createdAt desc/_id desc. Không trả raw payment payload/hash/idempotency digest trong public detail.

## Data

Read orders only cho history/detail; cancel write orders + products + active payment_attempts invalidation chung transaction. Source `api/orders.py`, `services/order_service.py`, `repositories/order_repository.py`, product/attempt methods khi cancel, `schemas/order_schema.py`, `features/orders/`. Dependency checkout snapshot contract/payment state guard, không Product detail cho history.

## Validation

ObjectId/filter/status/time bounds/page limits; expectedVersion positive int. Mutable update allowlist chỉ states/timestamps/version, no snapshot mass assignment. Cancel reason chưa requirement, không tự bắt buộc field này.

## Edge Cases

Product archived/price/name changed không ảnh hưởng detail; image gone fallback. Cancel repeated, cancel vs IPN/expiry, missing Product sau manual DB corruption phải fail transaction rõ và alert, không silent stock skip. Paid late chuyển REVIEW_REQUIRED xem payment.

## Security

Ownership không dựa frontend hide button; orderId guess404. Snapshot có PII nên không public/share; log requestId thay full address. No direct patch paymentStatus/customerSnapshot.

## UI Behavior

History status badges/date/VND, loading/empty, detail snapshot kể cả Product không còn browse được; cancel chỉ render khi rule cho phép nhưng server vẫn enforce; conflict refetch state. Poll payment status hữu hạn nếu đang chờ IPN.

## Acceptance Criteria

History paginated đúng owner/date; detail độc lập live Product/User; cancel hợp lệ trả kho đúng một lần; invalid/cross-owner bị chặn; snapshot price10 triệu vẫn cũ sau update12 triệu.

## Testing Checklist

- [ ] History ownership/status/time boundaries/sort/pagination.
- [ ] Snapshot after product/category/profile/address changes/archive.
- [ ] Cancel repeats/stale/race IPN/expiry, forbidden paid/shipping/completed.
