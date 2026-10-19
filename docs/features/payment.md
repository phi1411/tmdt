# COD và VNPAY Sandbox

## Goal

PHASE06A Payment backend IMPLEMENTED; COD giữ nguyên. Follow-up19/10/2026 có merchant Sandbox và IPN cấu hình riêng; runtime/FE đã harden theo ADR014. Provider rehearsal chỉ nghiệm thu theo evidence live mới; không gán deterministic tests thành live PASS. [Contract](../api-contract.md), [review](../phase-06a-review.md), [setup](../payment-setup.md).

## Actors

Customer owner tạo/retry link; VNPAY server gửi IPN; browser Return; Admin đọc trạng thái/đối soát, không fake paid online.

## Functional Requirements

Checkout online tạo Order/initial attempt/hold stock/clear Cart atomic; dựng signed URL sau commit. Retry existing Order idempotent trong deadline; Return verify/read-only; IPN authoritative transaction và duplicate-safe; expiry worker30s trả kho once. COD payment thuộc existing Admin complete flow; không payment production/refund tự động.

## Business Rules

BR-PAYMENT/BR-ORDER/ADR006 và [ADR010 runtime](../decisions/010-payment-runtime.md). Amount=Order.total×100. Success cả response/status00, nonzero transactionNo, verifiedAt trước deadline và providerPaidAt<=deadline: Order PENDING→CONFIRMED/PAID, attempt SUCCEEDED. Failure→attempt FAILED/Order PENDING+FAILED, hold tới deadline. Retry không gia hạn. Expiry→EXPIRED/FAILED +stockReleasedAt/expiredAt, invalidate pending; cancel giữ CANCELLED/FAILED. Late success sau terminal/deadline→REVIEW_REQUIRED, không revive. Second distinct success khi đã PAID giữ PAID/orderStatus/paidAt, chỉ review flag và attempt REVIEW_REQUIRED. Duplicate hoặc failure sau success không write. Revenue definition giữ nguyên, không cộng revenue trong IPN.

## Permission

CUSTOMER ACTIVE owner tạo link/poll Order, Guest401/Admin403/khác owner404. IPN/Return public nhưng bắt buộc provider verification; Return không PII. Không endpoint set-paid, không Admin override owner.

## API

| Method / path | Request | Response data | Error |
| --- | --- | --- | --- |
| POST /orders/:id/payment-attempts | Bearer CUSTOMER; {expectedVersion}, Idempotency-Key, không query | 201 {attemptId,attemptStatus,expiresAt,orderVersion,paymentUrl?,retryRequired?};200 replay | 400 ID/JSON;401/403;404 owner;409 ORDER_CHANGED/INVALID_TRANSITION/PAYMENT_ATTEMPT_PENDING/IDEMPOTENCY_CONFLICT/VERSION_LIMIT;422;503 |
| GET /payments/vnpay/return | Signed provider query | 200 envelope safe result SUCCESS/FAILED/PENDING/INVALID_SIGNATURE/INVALID_RESPONSE, authoritative:false | 503 config/DB |
| GET /payments/vnpay/ipn | Signed provider query | HTTP200 provider {RspCode,Message}, không envelope | 00 committed;02 duplicate;01 relation;04 amount;97 signature;99 processing |
| GET /orders/:id | Bearer CUSTOMER owner, không query | 200 Order paymentStatus/orderStatus/review flag; lazy expiry | 400/401/403/404/422/503 |

Shape/parameters/errors đầy đủ tại [API contract Payment](../api-contract.md). ReturnUrl trỏ handler backend hoặc SPA `/payment/return` forward nguyên query tới handler. Return trước IPN chỉ PENDING dù provider success; persisted PAID mới SUCCESS. Client poll own Order. Replay same attempt key/body trả current state, không paymentUrl cho terminal attempt/order; đổi body409. Initial link lấy từ checkout, retry endpoint chỉ khi không pending attempt.

## Data

Read/write payment_attempts/orders; expiry/cancel products stock/version transaction. Paths `backend/app/api/payments.py`, `services/payment_service.py`, `services/vnpay_provider.py`, `repositories/payment_attempt_repository.py`, Order/Product repositories; dependencies Checkout initial attempt, Order detail expiry/cancel, shared `catalog_transaction.py`, foundation config/guards/DTO/errors. Worker `scripts/payment/expire_pending.py` poll30s/batch100, `start-expiry.ps1`; tests `backend/tests/test_payment.py`, runtime `scripts/backend/verify_payment_runtime.py`. PaymentRequest immutable metadata theo canonical validator, money BSON long, date UTC, ObjectId, partial unique pending/order +txnRef/attemptKey/providerTransactionNo indexes có sẵn. Không schema/index/collection mới.

## Validation

HMAC-SHA512 canonical sorted UTF-8 form URL encoding, constant-time compare, exclude signature fields; callback allowlist/repeated/missing keys reject, bounds/protocol verification. Merchant/ref/order/owner/payment method và amount khớp cả attempt/Order/request metadata. Order total1..9.999.999.999VND, version strict integer1..2147483647, key printable ASCII8..128 không spaces. Valid config VNP_* và VNPAY_ENABLED; Sandbox host allowlist, HTTPS ngoài loopback; IP lấy peer socket, không tin forwarded header. Provider date UTC+7 strictly14digits, missing payDate dùng verifiedAt.

## Edge Cases

Unknown commit→retry nguyên key/body, acknowledge IPN00 chỉ sau commit. Initial insert/stock restoration/Order patch fault rollback toàn bộ. URL fault sau commit→retryRequired. Same/different attempt key race, duplicate IPN, cancel/expiry vs IPN dùng real rs0 state/version guards. Expiry/retry không trừ kho lần nữa, version cap không overflow. Old failure callback không downgrade paid; success sau failure vẫn được xử lý theo deadline. Missing Product/restore cap giữ transaction fail và safe log. Worker scan fail tiếp tục poll, --once exit1; per-order failure không ngăn batch còn lại.

## Security

Secret chỉ backend env, không hardcode/live credential trong tests, không lưu signed URL/raw query/card/billing/secret, không log exception message. Metadata allowlist+SHA256 callback fingerprint; IPN không tin browser amount/state. HTTPS/IPN registration cần reachable public endpoint; signature mandatory. Không external HTTP call trong transaction callback. Disabled creation vẫn cho receipt/expiry hiện hữu khi retained valid config.

## UI Behavior

Frontend đã được kiểm tra ở PHASE07A và harden19/10/2026. Merchant/Render env/SIT IPN đã cấu hình; bank OTP/automatic IPN còn PENDING_USER_TERMS_CONFIRMATION theo [review hiện hành](../vnpay-sandbox-final-review.md). Dùng paymentUrl từ checkout/retry để redirect Sandbox; Return hiển thị đang xác minh trước IPN, người dùng chủ động poll Order, failed/invalid/review message từ server. Retry trên UI chỉ dành cho VNPAY/PENDING order, payment FAILED, chưa review và còn deadline; không mời tạo attempt mới khi initial attempt đang PENDING. Retry URL fault/network503 giữ cùng Idempotency-Key/expectedVersion để khôi phục attempt đã commit. Initial URL recovery dùng nguyên checkout key/body theo Checkout, không tạo attempt mới. Review flag cần đối soát thủ công ngoài ứng dụng. Không tự set paid từ query browser. Evidence giả lập contract frontend được ghi riêng và không thay thế provider rehearsal.

## Acceptance Criteria

Backend atomic checkout/attempt, valid URL/signature, Return read-only, IPN idempotent/amount-safe, expiry/cancel return stock once và COD regression pass; dev fingerprint giữ nguyên. Full feature live DONE cần credentials, reachable registered IPN và rehearsal provider thật; deterministic fixtures không thay thế live check.

## Testing Checklist

- [x] Signed URL/golden canonical UTF-8 vector/amount/expiry/config/secret absence.
- [x] Valid/invalid/tampered/missing/duplicate signature parameters, protocol codes, owner/role/payload tampering.
- [x] Return pending/success/failed/invalid/review read-only, no PII.
- [x] IPN duplicate/out-of-order/late/second-success, version caps, unique transactionNo, rollback/ambiguous commit.
- [x] Retry idempotency/deadline/creation race và expiry/cancel/IPN concurrency trên real rs0; worker --once/failure handling.
- [x] Real Sandbox signed redirect tới gateway và biểu mẫu NCB, cấu hình IPN lưu thành công tại SIT.
- [ ] Bank OTP/automatic IPN: PENDING_USER_TERMS_CONFIRMATION, chưa claim Live Sandbox PASS; credentials hiện đã có, không còn blocker thiếu merchant.
- [ ] Frontend Payment Result page/poll UI: deferred theo phạm vi.


## Cập nhật19/10/2026 — ADR013

SKU/reviews đã được người dùng yêu cầu hoàn thiện sau integration review. Product optional tierVariations/skus, root price=minSKUprice/stock=sumSKUstock; legacy không matrix giữ behavior cũ. Exact selection/SKU binding, stock reservation/restore theo SKU và Product trong cùng transaction; snapshot selectedAttributes.skuId/price immutable. Admin CRUD hỗ trợ ma trận, guard SKU_IN_USE khi đổi identity có đơn giữ kho. Reviews là collection thứ7, unique User/Order/Product, verified COMPLETED+PAID và atomic ratingSummary; public privacy/pagination/filter. Nguồn cập nhật: decisions/013-sku-review-hardening.md, features/reviews.md và mục SKU/Reviews của api-contract.md; các ghi chú DEFERRED hoặc pool Product-only trước đó là lịch sử v1, không phủ định extension này. Không đổi doanh thu/canonical pipelines hoặc Order snapshot cũ. VNPAY disabled theo lựa chọn hiện hành.


## VNPAY operations19/10/2026 — ADR014

Merchant Sandbox đã cung cấp; IPN đăng ký trên SIT tại backend public `/api/v1/payments/vnpay/ipn`, Return tới SPA `/payment/return`. Runtime `backend/serve.py` supervises API/expiry ở hai process riêng trên dịch vụ hiện hữu, bật tự động khi VNPAY enabled. Giữ `PAYMENT_EXPIRY_WORKER_ENABLED=true` kể cả khi tắt creation để giải phóng holds đang có. Fixed `PAYMENT_EXPIRY_CREATED_AFTER` UTC loại fixture lịch sử khỏi auto-scan; không thay mốc sau restart. Không TTL/reset/reseed. Khi một child chết supervisor dừng child còn lại và exit nonzero; shutdown bounded. Source `backend/service_supervisor.py`, `scripts/payment/expire_pending.py`; ADR014 khóa cutover/verification. Return UI lấy trạng thái Order mới đúng id, cảnh báo review sau poll, lỗi mạng hiện chưa xác minh và có retry. Chỉ evidence provider redirect/bank/IPN thực mới đóng live gate; cấu hình đủ hoặc signed fixture không thay thế live PASS.
