# ADR-010 — VNPAY Sandbox runtime và Return API

## Status

PHASE06A — implementation decision07/10/2026. Người dùng yêu cầu Payment backend, giữ schema/lifecycle/BR-PAYMENT/ADR006. Không migration, enum/index/collection mới.

## Decision

Giữ POST /orders/:id/payment-attempts +expectedVersion/Idempotency-Key, không thêm alias create-payment. Checkout VNPAY tạo initial attempt cùng Order/stock/Cart transaction; dựng signed URL sau commit, lỗi URL trả retryRequired. Initial attemptKey server-derived từ Order ID; retry endpoint hash nguyên body, scope Order. Deadline15phút không kéo dài khi retry.

User yêu cầu Return handler: thêm GET /payments/vnpay/return, trả safe JSON envelope cho result page, không ghi DB/expire/paid từ browser return. Config ReturnUrl có thể trỏ handler backend hoặc SPA chuyển nguyên query sang handler này. Signature+amount/reference verified; provider success trước IPN trả PENDING, persisted PAID mới SUCCESS; invalid signature có safe result INVALID_SIGNATURE, không lộ Order PII. Customer poll GET /orders/:id để xác nhận owner state.

Env primary theo yêu cầu hiện hành: VNP_TMN_CODE,VNP_HASH_SECRET,VNP_PAYMENT_URL,VNP_RETURN_URL,VNP_IPN_URL; VNPAY_ENABLED mặc địnhfalse. Không nhận merchant secret/amount từ browser, không silent alias VNPAY_* credential names cũ. Bật với config thiếu/sai phải fail startup; disabled giữ COD hoạt động. Payment URL chỉ VNPAY Sandbox. IPN config là URL đăng ký server-to-server phía merchant, không parameter trong payment URL. HTTP loopback dùng local tests, HTTPS bắt buộc ngoài loopback.

Signature2.1.0: HMAC-SHA512, parameters sort+form URL encoding UTF-8, exclude SecureHash/SecureHashType, constant-time compare. Callback allowlist/bounds/duplicate key reject trước verification; only IPN đã verified cập nhật metadata allowlist và state. No stored card/billing/raw query/secret/signed URL.

Expiry worker CLI poll30s/once mode, transaction Order EXPIRED+restore grouped stock+invalidate pending attempts once. Detail/create/IPN có thể gọi cùng expiry service; Return tuyệt đối read-only. Callback capture verifiedAt một lần trước retry; amount check cả attempt và Order. Success ngoài deadline/terminal cần review, không hồi sinh; second distinct success giữ PAID/orderStatus, chỉ review flag. Theo BR-PAYMENT, late providerPaidAt vượt deadline cũng trigger expire/restore trước review khi Order còn pending dù server clock đang chậm; không tạo lifecycle mới.

## Validation và giới hạn

Correction trực tiếp ở shared transaction utility: real IPN/expiry race cho thấy retry3lần ngay lập tức có thể exhausted khi writer kia chưa commit. Thêm backoff20/40ms **sau abort** cho TransientTransactionError, vẫn tối đa3attempts; unknown commit chỉ retry commit như cũ. Không đổi schema/lifecycle hoặc replay uncertain commit, full-suite regression bắt buộc.

Real ecommerce_test rs0: COD regression, online atomic initial attempt/rollback, signature fixtures, idempotent callback/retry, cancel/expiry/IPN races, ambiguous commit retry, late/second success, no secret leakage. Dev fingerprint giữ nguyên, không chạy expiry trên dev trong verification. Live Sandbox chỉ xác nhận khi có credentials/network/reachable IPN thực; thiếu cấu hình ghi BLOCKED LIVE SANDBOX, không fake rehearsal. Source provider: https://sandbox.vnpayment.vn/apis/docs/thanh-toan-pay/pay.html.
