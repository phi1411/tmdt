# Order history và chi tiết đơn

**Trạng thái hiện hành20/10/2026:** API và giao diện của feature đã triển khai; các mốc phase/deferred bên dưới là lịch sử. Evidence tại [full audit](../full-project-audit-20261020.md) và [handoff](../defense-final-handoff-20261020.md). Không chạy lại toàn bộ UI suite trong lần đồng bộ tài liệu này.

## Goal

Customer đọc lịch sử bằng dữ liệu snapshot và hủy khi đủ điều kiện. **PHASE05C backend snapshot/history/cancel IMPLEMENTED**, PHASE06A thêm lazy online expiry/races; frontend OrdersPage/OrderDetailPage đã triển khai, Admin Orders có API/UI và evidence riêng. POST tạo đơn thuộc checkout. [Contract](../api-contract.md), [review](../phase-05c-review.md), [Payment](payment.md).

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

Read orders only cho history/detail; cancel write orders + products + active payment_attempts invalidation chung transaction. Source `app/api/orders.py`, `app/services/order_service.py`, `app/repositories/order_repository.py`, `app/repositories/payment_attempt_repository.py`, ProductRepository.restore_stock, `app/schemas/order_schema.py`; tests `backend/tests/test_commerce.py`. Reuse shared catalog_transaction bounded snapshot/majority orchestration; owner enforced queries, DTO allowlist. Dependency Auth live role/identity, checkout snapshot contract/payment state guard, không Product detail cho history. Frontend thực tế `frontend/src/pages/OrdersPage.tsx` và `OrderDetailPage.tsx`.

## Validation

ObjectId/filter/status/time bounds/page limits; expectedVersion positive int1..2147483647, reject bool. Mutable update allowlist chỉ states/timestamps/version, no snapshot mass assignment. Cancel reason chưa requirement, không tự bắt buộc field này. from/to UTC Z/+00:00, [from,to), from<to; page1/pageSize20/max100; no client sort/userId. History facet MongoDB count/items, summary allowlist không PII address; detail snapshot đầy đủ, private checkoutKey/hash không public.

Cancel stale409 ORDER_CHANGED, forbidden409 INVALID_TRANSITION; expectedVersion được kiểm tra sau CANCELLED replay no-op200. Guard cả paymentReviewRequired=false/absence stockReleasedAt. Restore tổng quantity/Product bằng $inc stock/version, archived vẫn restore. Missing Product/stock overflow/version exhausted→409 STOCK_RESTORE_FAILED, rollback Order và mọi Product, log event commerce.stock_restore_failed. Online cancel chuyển FAILED/invalidate attempts EXPIRED. PHASE06A detail lazy expiry dùng PaymentService, không lookup live snapshot; IPN/expiry/cancel race và late review theo [Payment](payment.md). COD cancellation giữ UNPAID; COD completion do worker Admin Orders.

## Edge Cases

Product archived/price/name changed không ảnh hưởng detail; image gone fallback. Cancel repeated, cancel vs IPN/expiry, missing Product sau manual DB corruption phải fail transaction rõ và alert, không silent stock skip. Paid late chuyển REVIEW_REQUIRED xem payment.

## Security

Ownership không dựa frontend hide button; orderId guess404. Snapshot có PII nên không public/share; log requestId thay full address. No direct patch paymentStatus/customerSnapshot.

## UI Behavior

History status badges/date/VND, loading/empty, detail snapshot kể cả Product không còn browse được; cancel chỉ render khi rule cho phép nhưng server vẫn enforce; conflict refetch state. Poll payment status hữu hạn nếu đang chờ IPN.

## Acceptance Criteria

History paginated đúng owner/date; detail độc lập live Product/User; cancel hợp lệ trả kho đúng một lần; invalid/cross-owner bị chặn; snapshot price10 triệu vẫn cũ sau update12 triệu.

## Testing Checklist

- [x] Backend history ownership/status/time boundaries/sort/pagination/input allowlist.
- [x] Snapshot after product/category/profile/address changes/archive/delete; read không dùng live Product/Category.
- [x] Cancel repeats/stale/concurrent once, CONFIRMED COD, online attempt invalidation, forbidden paid/review flag/shipping/completed/expired.
- [x] Cancel rollback missing Product/fail second restore/fail attempt invalidation trên rs0.
- [x] PHASE06A IPN/cancel/expiry race, once-only stock restore và late review trên test rs0.
- [x] Frontend Customer/Admin Orders đã triển khai; xem evidence07A và audit20/10 theo scope, không gọi lượt docs này là UI rerun.


## Cập nhật19/10/2026 — ADR013

SKU/reviews đã được người dùng yêu cầu hoàn thiện sau integration review. Product optional tierVariations/skus, root price=minSKUprice/stock=sumSKUstock; legacy không matrix giữ behavior cũ. Exact selection/SKU binding, stock reservation/restore theo SKU và Product trong cùng transaction; snapshot selectedAttributes.skuId/price immutable. Admin CRUD hỗ trợ ma trận, guard SKU_IN_USE khi đổi identity có đơn giữ kho. Reviews là collection thứ7, unique User/Order/Product, verified COMPLETED+PAID và atomic ratingSummary; public privacy/pagination/filter. Nguồn cập nhật: decisions/013-sku-review-hardening.md, features/reviews.md và mục SKU/Reviews của api-contract.md; các ghi chú DEFERRED hoặc pool Product-only trước đó là lịch sử v1, không phủ định extension này. Không đổi doanh thu/canonical pipelines hoặc Order snapshot cũ. VNPAY disabled theo lựa chọn hiện hành.
