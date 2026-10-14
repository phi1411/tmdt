# Admin Order Management

## Goal

Admin xử lý vòng đời Order, hoàn tất COD và kiểm tra thanh toán. Backend PHASE06B IMPLEMENTED; frontend/gateway không thuộc worker này. [Review06B](../phase-06b-review.md).

## Actors

ADMIN; không có role Staff/Shipper.

## Functional Requirements

List/detail all Orders với filters, confirm/ship/complete/cancel khi hợp lệ; thấy payment review required. Không sửa snapshot/totals/địa chỉ, không set VNPAY paid hoặc refund.

## Business Rules

BR-ORDER transition table, BR-PAYMENT. PENDING COD confirm được, VNPAY cần IPN PAID; shipping only CONFIRMED; complete only SHIPPING, COD mark PAID cùng transaction. Cancel chỉ chưa PAID/REVIEW_REQUIRED và PENDING/CONFIRMED. ExpectedVersion/state guard, stock restore once. COMPLETED không reopen. Manual late-money resolution ngoài ứng dụng, refund automation DEFERRED; list badge chỉ báo paymentReviewRequired/REVIEW_REQUIRED, không tự giải quyết tiền.

## Permission

All routes ADMIN. Customer dùng own orders endpoints và không nhận admin list, hidden UI không đủ quyền.

## API

| Method / path | Request | Response data | Error |
| --- | --- | --- | --- |
| GET /admin/orders | status?,paymentStatus?,from?,to?,orderCode?,page/pageSize | 200 summaries + meta | 401/403/422 |
| GET /admin/orders/:id | id | 200 snapshot/status/version | 404/401/403 |
| POST /admin/orders/:id/confirm | {expectedVersion} | 200 Order | 409 transition/stale/payment |
| POST /admin/orders/:id/ship | {expectedVersion} | 200 Order | 409 transition/stale |
| POST /admin/orders/:id/complete | {expectedVersion} | 200 Order with completedAt | 409 transition/stale |
| POST /admin/orders/:id/cancel | {expectedVersion} | 200 Order | 409 transition/stale/paid |

No generic PATCH orderStatus/paymentStatus/snapshot. Complete khi đã COMPLETED và cancel khi đã CANCELLED trả200 current snapshot, kể cả expectedVersion cũ, không ghi timestamps/version/stock. Confirm/ship không replay sau tiến trạng thái: stale409 ORDER_CHANGED, wrong state/payment409 INVALID_TRANSITION. Mọi action yêu cầu expectedVersion hợp lệ. Detail/action thêm `allowedActions:[confirm|ship|complete|cancel]`; terminal/version cap trả[]. List dùng Commerce summaries, không customer/address/items PII.

## Data

Source dưới `backend/app`: `api/admin_orders.py` → `services/order_service.py` → `repositories/order_repository.py`; `schemas/admin_order_schema.py`. Read/write orders; products/payment_attempts khi cancel. Reuse Customer cancel với server admin policy, cùng session/restore code. COD complete chỉ atomic Order payment/state/timestamps. Direct dependencies auth, Commerce transaction/cancel/DTO, validation/pagination/errors/envelopes và allowlisted audit formatter; test `backend/tests/test_admin_analytics.py`. Frontend vẫn dự kiến.

## Validation

IDs lowercase hex24; expectedVersion strict1..2147483647, không bool/float; version cap409 VERSION_LIMIT. Query chỉ `status,paymentStatus,from,to,orderCode,page,pageSize`; status map6orderStatus, paymentStatus5enum. Exact orderCode uppercase alphanumeric/-1..64; optional createdAt `[from,to)` full ISO UTC seconds/Z/+00:00/fractional1..6, năm tối đa9998; nếu đủ from<to. Pagination1/20,max100, fixed createdAt DESC/_id DESC, MongoDB facet. Không alias orderStatus/paymentMethod/customer/email/sort. Action body chỉ expectedVersion, không client timestamps/snapshot/money. Server UTC clock không ghi trước createdAt/paidAt.

Confirm chỉ COD PENDING UNPAID; VNPAY confirm thuộc verified IPN. Ship/complete VNPAY cần PAID, giữ paidAt. COD SHIPPING complete set PAID/paidAt/completedAt cùng write. Transaction/CAS check state/payment/version, snapshot bất biến, không overwrite concurrent payment-review DB write. Audit sau commit gồm requestId/actor/order/action/trước-sau state/version, không PII/secrets.

## Edge Cases

Stale page/IPN arrived meanwhile, repeat complete/cancel, expired VNPAY, paid late REVIEW_REQUIRED, Product archived still restorable. Double complete không ghi ngày lại/cộng revenue hai lần.

## Security

Admin auth hiện hành; PII projection chỉ đủ quản lý, no provider secrets/hash/raw token. Audit log requestId/actor/action/orderId/trước-sau sanitized; không cần thêm collection audit khi chưa quyết định persistence.

## UI Behavior

Table filter/details/status timeline, buttons từ allowedActions server, conflict refresh. COD completion ghi rõ đã giao/thu tiền trước xác nhận; pending online có thanh toán badge, review required cảnh báo đối soát.

## Acceptance Criteria

Workflow hợp lệ, COD completion phản ánh Dashboard khi qualify; invalid transitions/unauthorized blocked; cancel once; immutable snapshot, no fabricated VNPAY paid.

## Testing Checklist

- [x] Transition matrix COD/VNPAY/stale/role, filters/detail/pagination/validation.
- [x] Repeat/concurrent complete/cancel/ship, grouped restore once/rollback; simulated payment-review DB race.
- [x] Revenue qualifies after COD completion; immutable snapshot/timestamps và audit.
- [ ] Real gateway IPN/expiry race và frontend thuộc worker khác; không claim test gateway.
