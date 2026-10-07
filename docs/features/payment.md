# COD và VNPAY Sandbox

## Goal

COD phục vụ demo barem; VNPAY Sandbox mô phỏng thanh toán online an toàn. P0/P1; chưa implement. Design/state/metadata/TTL đã khóa; secrets/reachable IPN deferred tới phasePayment, không blocker modeling/COD.

## Actors

Customer initiates; VNPAY server IPN; Admin xem trạng thái/đối soát, không fake paid online.

## Functional Requirements

COD payment status tại Order completion; VNPAY signed payment URL, attempt retry/idempotency, signed IPN validation, ReturnUrl UX/poll server state, explicit expiry/late payment review. Không payment production/refund tự động.

## Business Rules

BR-PAYMENT/BR-ORDER và ADR-006. Amount=Order.total ×100 theo [VNPAY chính thức](https://sandbox.vnpayment.vn/apis/docs/thanh-toan-pay/pay.html), txnRef unique/attempt, merchant/hash server config. URL không đồng nghĩa đã trả tiền. Chỉ success IPN chữ ký/merchant/amount/reference/status valid cập nhật PAID và CONFIRMED trong transaction. Duplicate same txn no side effects; failure after success no downgrade. Late success sau cancel/expiry→Order REVIEW_REQUIRED. Second-success txn khác trên Order đã PAID→attempt REVIEW_REQUIRED và Order.paymentReviewRequired=true nhưng giữ paymentStatus PAID/orderStatus, không tăng hay xóa doanh thu trước đó/trừ stock lại.

## Permission

Customer owner tạo link/read status qua Order detail; IPN public network nhưng bắt buộc provider verification. Admin chỉ read/review baseline, không gọi endpoint set-paid VNPAY. Return trang public không lộ Order PII, cần đăng nhập để fetch detail.

## API

| Method / path | Request | Response data | Error |
| --- | --- | --- | --- |
| POST /orders/:id/payment-attempts | {expectedVersion}, Idempotency-Key | 201 {attemptId,paymentUrl,expiresAt};200 replay | 404 owner;409 paid/terminal/pending attempt/expired/stale;503 config;422 |
| GET /payments/vnpay/ipn | Provider signed query | HTTP200 provider {RspCode,Message}, không JSON envelope | Signature/amount/ref/state response theo protocol provider |
| GET /orders/:id | Bearer | 200 Order paymentStatus | 404/401/403 |

Frontend `/payment/return` là SPA route được cấu hình ReturnUrl; không API trust browser params. IPN codes/method/canonical encoding đã khóa theo BR-PAYMENT và provider2.1.0; implementation sau này phải có provider fixtures xác minh contract, không mở lại quyết định đã khóa. IPN chỉ acknowledge sau DB commit; DB outage cần provider-compatible retry response, không falsely acknowledge thành công.

## Data

Read/write payment_attempts + orders; expiry/cancel write products stock trong transaction. Paths `api/payments.py`, `services/payment_service.py`, `services/vnpay_provider.py`, `repositories/payment_repository.py`, Order/Product repos state operations, `features/payment/`; future `scripts/payment/expire_pending.py` worker đã khóa poll30giây, file chỉ tạo khi phasePayment được yêu cầu. Checkout tạo initial attempt, payment endpoint retry cùng existing state. Canonical paymentRequest/callback metadata tại database-schema và validator, partial unique PENDING/orderId chống concurrent attempts.

## Validation

Query allowlist + signature canonical sorted params theo provider, exclude signature fields đúng protocol; compare digest constant time. txnRef existing, provider/code/amount/time/transaction status; amount integer bound (Order.total<=9.999.999.999 VND); configured absolute return/IPN URLs. Success require both responseCode00 và transactionStatus00, deadline guard theo BR-PAYMENT. Không nhận user amount/provider secret/URL tùy ý.

## Edge Cases

Double-click/timeout URL, callbacks out of order/duplicate, lost return, server clock offset, payment after expiry/cancel, failed attempt retry, simultaneous expiry/success, unavailable IPN public access. Không refund hoặc hồi sinh đơn tự động; manual reconciliation ngoài ứng dụng; refund automation DEFERRED. Deadline15phút/expiry30giây, provider amount cap và late success rules tại foundation-decisions/BR-PAYMENT.

## Security

HTTPS cho IPN/return bên ngoài localhost; secret không vào frontend/repo/log. Signature mandatory kể cả IP allowlist; không tin IP header từ proxy chưa cấu hình. Rate limit không cản retry hợp lệ; request replay state guarded. No card data capture/storage.

## UI Behavior

Payment choice/fee đúng quote; redirect allowlisted provider URL; Return page hiển thị “đang xác minh”, poll own Order hữu hạn, rồi paid/failed/pending/review message từ backend. Retry chỉ khi đủ điều kiện, không tạo Order mới. Admin có badge cần đối soát.

## Acceptance Criteria

COD PAID khi completion; VNPAY sandbox success real IPN test, invalid/duplicate/late callbacks an toàn; external redirect không tự set paid; expiry trả kho once. Không đánh feature DONE khi chưa có credentials/reachable IPN/rehearsal.

## Testing Checklist

- [ ] Signed URL amount/encoding/expiry and secret absence.
- [ ] Invalid hash/amount/merchant/ref, provider response codes.
- [ ] Duplicate/out-of-order/late/second-success + transaction rollback.
- [ ] Retry idempotency, expiry concurrency, Return poll and actual sandbox rehearsal.
