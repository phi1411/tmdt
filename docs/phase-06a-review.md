# PHASE06A — VNPAY Sandbox Payment backend

Ngày07/10/2026. PHASE05C đã được người dùng duyệt; worker06A chỉ triển khai Payment và dependency trực tiếp. Backend implementation hoàn thiện; **BLOCKED LIVE SANDBOX**, không tuyên bố đã thanh toán/nhận IPN từ VNPAY thật. Dừng để review, không bắt đầu phase tiếp theo.

## 1. Payment endpoints

Prefix `/api/v1`: POST `/orders/:id/payment-attempts` CUSTOMER ACTIVE owner, `{expectedVersion}` +Idempotency-Key; GET `/payments/vnpay/return` public verify/read-only; GET `/payments/vnpay/ipn` public signed provider callback. GET `/orders/:id` existing owner status poll/lazy expiry. Giữ route retry đã khóa, không thêm alias `/payments/vnpay/create`; Return API bổ sung đúng yêu cầu hiện hành, ghi ADR010.

## 2. VNPAY URL generation

Checkout VNPAY initial Order/attempt/stock/Cart commit atomic; Order PENDING/PENDING, deadline15phút. URL dựng **sau commit** từ immutable paymentRequest metadata, Sandbox2.1.0, backend total×100, VND, txnRef unique, OrderInfo server, peer socket IP, date UTC+7. Không browser amount/URL/merchant/state. Fault URL trả retryRequired và replay cùng key/body; không tạo Order lại. Retry tạo attempt trên existing Order khi eligible, không giữ/trừ stock lại hoặc gia hạn deadline. COD vẫn `{method:COD}`, không online attempt/deadline.

## 3. Signature strategy

Sorted form URL encoding UTF-8, space→+, HMAC-SHA512, loại SecureHash/SecureHashType, constant-time compare; callback keys allowlist/unique/bounds và merchant check. Golden fixed HMAC vector + independent stdlib fixture signing kiểm tra escaping/Unicode/amount/time. [Protocol VNPAY](https://sandbox.vnpayment.vn/apis/docs/thanh-toan-pay/pay.html), [ADR010](decisions/010-payment-runtime.md). Fixtures dùng merchant/secret giả, không gửi tới provider.

## 4. Return behavior

Normal envelope safe result SUCCESS/FAILED/PENDING/INVALID_SIGNATURE/INVALID_RESPONSE; verified/confirmed/authoritative:false và only non-PII IDs/current state nếu verified. Provider success trước authoritative IPN→PENDING; DB PAID mới SUCCESS. Không ghi attempt/Order/expire/stock, kể cả hold quá hạn. Frontend cần Bearer owner poll Order, UI chưa triển khai. Review flag giữ để đối soát, không dùng browser query tự set paid.

## 5. IPN behavior

Signature/merchant/format→lookup attempt/Order relation→check amount cả attempt+Order+request→state/version/deadline→transaction metadata/state. HTTP200 provider `{RspCode,Message}` ngoại lệ envelope; requestId header vẫn có. Codes00 committed receipt,02 duplicate,01 missing relation,04 amount mismatch,97 verification invalid,99 processing/config/DB/version/unique constraint failure. Không return00 trước commit, không log raw callback/query/secret/error message. Success require responseCode00 AND transactionStatus00 +nonzero provider transactionNo; payDate strict UTC+7, missing date dùng captured verifiedAt UTC.

## 6. Idempotency strategy

Checkout key scope User, retry key scope Order/body expectedVersion hash, txnRef unique, partial unique PENDING/order và unique provider transactionNo hiện hữu. Replay cùng key/body200 với current attempt; terminal không paymentUrl, khác body409. Transaction state/version guards bảo vệ race. Duplicate success/review hoặc repeated failure receipt→02/no write; failure sau success không downgrade. Unknown commit retry chỉ commit; request/IPN retry đọc persisted receipt, không tạo thêm Order/stock/revenue.

## 7. State transitions và expiry

| Trigger | Attempt | Order/payment | Stock |
| --- | --- | --- | --- |
| Checkout online | PENDING | PENDING/PENDING | Hold/decrement trong checkout |
| Timely valid IPN success | SUCCEEDED | CONFIRMED/PAID +paidAt | Không decrement thêm |
| Valid failure | FAILED | PENDING/FAILED | Giữ hold, retry trước deadline |
| Deadline expiry | PENDING→EXPIRED | EXPIRED/FAILED +expiredAt/stockReleasedAt | Restore grouped quantity once |
| Customer cancel | PENDING→EXPIRED | CANCELLED/FAILED | Restore once |
| Success sau cancel/expiry/deadline | REVIEW_REQUIRED | Giữ terminal, payment REVIEW_REQUIRED +paidAt/review flag | Không revive/decrement |
| Second distinct success sau PAID | REVIEW_REQUIRED | Giữ PAID/orderStatus/paidAt, review flag=true | Không thay stock |

verifiedAt phải trước deadline, providerPaidAt không vượt deadline. Provider late date khi server clock chậm vẫn expire/restore trước review. Worker30s/batch100 và lazy detail/create/IPN dùng cùng expiry service; --once checked trên test DB, failure exit1, loop tiếp tục sau scan failure. Worker chưa bật trên dev để bảo toàn seed. No new enums/lifecycle/revenue definition/schema/index/collection.

## 8. Sandbox live status

**BLOCKED LIVE SANDBOX:** kiểm tra presence-only `.env` cho thấy VNP_TMN_CODE/HASH_SECRET/PAYMENT_URL/RETURN_URL/IPN_URL đều chưa có, VNPAY_ENABLED=false. Không có real payment URL/redirect/bank transaction hoặc provider server IPN evidence. Deterministic tests/localhost HTTP chỉ xác nhận implementation. Cần merchant Sandbox và public HTTPS IPN registration +rehearsal để nghiệm thu live; không dùng config giả để đánh PASS. Không sửa `.env` chứa credentials người dùng.

## 9. Payment tests

102 tests PASS,0fail/error/skip trong [Payment JUnit](../backend/evidence/phase06a-payment-pytest.xml). Bao phủ creation ownership/roles/state/idempotency/payloads, signature/URL/tamper/missing/repeated params, Return safe readonly, IPN success/failure/duplicate/amount/ref/transaction uniqueness, retry fixed deadline, version caps/no leak, atomic rollback, ambiguous real commit, initial checkout/attempt/IPN/cancel/expiry concurrency trên MongoDB rs0 thật và expiry CLI once/error handling. [Commerce regression](../backend/evidence/phase06a-commerce-regression.xml):126 pass trong lần kiểm tra dependency sau core implementation; full final suite là bằng chứng source cuối.

## 10. Full suite và HTTP evidence

**658/658 PASS,0fail/0error/0skip**,187.99s trong [full JUnit](../backend/evidence/phase06a-pytest.xml):451 existing (80foundation+133Auth/User+112Catalog+126Commerce)+102Payment+105Admin/Analytics của worker06B riêng. Không gán implementation06B cho06A. Payment scoped102pass/27.60s; source backend/tests/API contract manifest chụp trước final tests và giữ nguyên đến sau HTTP verification, lưu ignored `.local/phase06a-source-before-tests.json` và runtime evidence. Không Git HEAD nên dùng manifest, không tạo commit/PR giả.

[Runtime evidence](../backend/evidence/phase06a-runtime.json): **50 current-source real HTTP checks PASS** qua temporary threaded localhost listener/owned ecommerce_test rs0. Actual Customer/Admin login→Catalog→Cart→online quote/atomic checkout/replay→signed Return pending/invalid→IPN amount/ref/signature/security→success/duplicate/paid poll→failure/retry/replay/success→readonly expired Return/expiry/late review→COD checkout/cancel.13blueprints/52method-path không collision,3Payment routes khớp contract/feature docs; các Admin/Dashboard registrations được giữ nguyên từ06B. Provider fixture URL chỉ verify offline, không giả live redirect.

Full dev fingerprint documents/collection options/validators/indexes trước/sau trùng immutable phase05C/phase04: `3cb02b86dae359fe469356c818205b8ddc2e83768862d9f3c47776a79657c6a6`; users40/categories3/products180/carts0/orders100/payment_attempts30. Cleanup exact test IDs:6collections đều0, không reset/reseed/drop/index creation. PowerShell expiry starter parsed PASS, CLI --once/scan failure checked trong tests. Persistent localhost5001 hiện health200/IPN200+99/Return503 PAYMENT_UNAVAILABLE đúng missing config; routes đã đăng ký, không restart/enable credentials giả hoặc chạy dev expiry.

## 11. API contract update

[API contract](api-contract.md) có3 Payment method/path IMPLEMENTED, response URL/retry shape, Return safe results, owner status poll, exact IPN codes/envelope, amount/signature/metadata/deadline/late/replay rules. Checkout VNPAY gate chuyển thành enabled/config có điều kiện; disabled vẫn503 trước write. Feature Payment/Checkout/Orders và architecture/module/testing docs đồng bộ; frontend không phải đọc backend internals.

## 12. Config và vận hành

[Payment setup](payment-setup.md), [.env.example](../.env.example): canonical VNP_TMN_CODE,VNP_HASH_SECRET,VNP_PAYMENT_URL,VNP_RETURN_URL,VNP_IPN_URL, flagVNPAY_ENABLED; enabled thiếu/sai fail startup, Sandbox-only URLs, HTTPS ngoài loopback, hold15m/poll30s. Secret ở backend ignored env, không hardcode/log/Frontend. IPN URL đăng ký với provider, không là payment URL parameter. Khởi động worker riêng chỉ khi được phép vận hành DB đó; không chạy dev expiry trong verification vì seed có holds lịch sử.

## 13. Files sửa/tạo

- Backend mới: `app/api/payments.py`, `app/services/payment_service.py`, `app/services/vnpay_provider.py`, `tests/test_payment.py`.
- Backend dependency sửa: `app/api/__init__.py`, `app/api/checkout.py`, `app/services/checkout_service.py`, `app/services/order_service.py`, `app/repositories/order_repository.py`, `app/repositories/payment_attempt_repository.py`, `app/services/catalog_transaction.py`, `app/config.py`, `app/utils/serialization.py`.
- Scripts mới: `scripts/payment/expire_pending.py`, `scripts/payment/start-expiry.ps1`, `scripts/backend/verify_payment_runtime.py`.
- Config/docs: `.env.example`, `docs/decisions/010-payment-runtime.md`, ADR index, `docs/payment-setup.md`, `docs/phase-06a-review.md`, `docs/api-contract.md`, Payment/Checkout/Orders feature docs, architecture/testing/AGENTS/backend README/evidence index. Evidence mới `backend/evidence/phase06a-*`; giữ nguyên evidence05A/05B/05AB/05C/06B.

## 14. Bugs/correction/DEFERRED

Real race IPN vs expiry từng có1 failure trong100 cases: three immediate transaction retries hết trước contender commit. Sửa tối thiểu utility chung thêm20/40ms backoff sau abort TransientTransactionError, vẫn3attempts, uncertain commit vẫn chỉ retry commit. ADR010 ghi rõ correction; rerun102 Payment đã pass, full suite kiểm tra dependency chung. Worker scan failure giờ safe log/continue hoặc --once exit1; callback success không kế thừa stale providerPaidAt từ receipt failure thiếu date.

Không lỗi backend đã biết trong checks pass; live merchant/IPN/redirect rehearsal, Frontend Payment Result/poll UI, refund/resolve review/tunnel/full benchmark DEFERRED. User asked Payment nên worker06A **không sửa Frontend hoặc Admin Dashboard**, không đổi MongoDB design, không thêm Product/Cart/Auth. **COD không regression:**126 Commerce và toàn bộ658 final tests PASS, actual HTTP COD checkout/replay/cancel/restore PASS. Các feature Admin/Analytics do worker06B riêng cung cấp, không gán cho06A. Dừng để review.
