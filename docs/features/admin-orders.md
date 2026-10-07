# Admin Order Management

## Goal

Admin xử lý vòng đời Order, hoàn tất COD và kiểm tra thanh toán. P1 và hỗ trợ demo P0; chưa implement.

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

No generic PATCH orderStatus/paymentStatus/snapshot. Same-terminal action retry có thể trả current Order nếu đã đạt cùng target và không tạo side effect; transition khác vẫn409. Implementation chốt action idempotency tests cùng service.

## Data

Read/write orders; products stock và payment_attempts khi cancel; COD complete chỉ Order atomic payment/state/timestamps. Paths `api/admin_orders.py` → `order_service.py`, order/product/payment repos methods, `features/admin-orders/`. Reuse Customer cancel service với role policy, không hai logic restore stock.

## Validation

IDs, expectedVersion, filters enums/time ranges; state predicates và payment readiness. Không nhận completedAt/paidAt từ client; server clock UTC. Snapshot/money immutable allowlist.

## Edge Cases

Stale page/IPN arrived meanwhile, repeat complete/cancel, expired VNPAY, paid late REVIEW_REQUIRED, Product archived still restorable. Double complete không ghi ngày lại/cộng revenue hai lần.

## Security

Admin auth hiện hành; PII projection chỉ đủ quản lý, no provider secrets/hash/raw token. Audit log requestId/actor/action/orderId/trước-sau sanitized; không cần thêm collection audit khi chưa quyết định persistence.

## UI Behavior

Table filter/details/status timeline, buttons từ allowedActions server, conflict refresh. COD completion ghi rõ đã giao/thu tiền trước xác nhận; pending online có thanh toán badge, review required cảnh báo đối soát.

## Acceptance Criteria

Workflow hợp lệ, COD completion phản ánh Dashboard khi qualify; invalid transitions/unauthorized blocked; cancel once; immutable snapshot, no fabricated VNPAY paid.

## Testing Checklist

- [ ] Transition matrix COD/VNPAY/stale/role.
- [ ] Repeat complete/cancel và concurrent IPN/cancel/expiry.
- [ ] Revenue qualifies after completion; snapshot unchanged.
