# VNPAY Sandbox — cấu hình và vận hành PHASE06A

Backend đã có adapter/attempt/Return/IPN/expiry. Follow-up19/10/2026: người dùng đã cung cấp merchant Sandbox, đăng ký IPN trong SIT và cấu hình backend Render riêng. Follow-up20/10/2026 đã kiểm thử hai giao dịch NCB/OTP test, automaticIPN và Return PAID, gồm checkout từ Web; [review](vnpay-sandbox-final-review.md) ghi phạm vi PASS và giới hạn SIT riêng; các phase cũ BLOCKED không là trạng thái cấu hình hiện tại. [Contract](api-contract.md), [review](phase-06a-review.md), [VNPAY protocol chính thức](https://sandbox.vnpayment.vn/apis/docs/thanh-toan-pay/pay.html).

## Environment

Cấu hình `.env` ignored tại project, không gửi secret vào chat/source/Frontend/VITE_ env. `.env.example` chỉ placeholders. Không dùng tên credential VNPAY_* cũ làm alias.

| Variable | Giá trị cần cung cấp |
| --- | --- |
| VNPAY_ENABLED | false mặc định; true chỉ khi đủ cấu hình hợp lệ và worker sẵn sàng |
| VNP_TMN_CODE | Merchant Sandbox8ký tự alphanumeric |
| VNP_HASH_SECRET | Hash secret Sandbox, giữ riêng ở backend |
| VNP_PAYMENT_URL | https://sandbox.vnpayment.vn/paymentv2/vpcpay.html |
| VNP_RETURN_URL | HTTPS backend `/api/v1/payments/vnpay/return` hoặc SPA forward query tới handler; loopback HTTP cho local tests |
| VNP_IPN_URL | Public HTTPS `/api/v1/payments/vnpay/ipn`, đăng ký với merchant Sandbox; không thêm vào payment URL |
| PAYMENT_HOLD_MINUTES | 15 cố định theo design |
| PAYMENT_EXPIRY_POLL_SECONDS | 30 cố định theo design |

Enabled với thiếu/placeholder/sai config fail startup với message an toàn. Disabled+thiếu config giữ COD và từ chối tạo online503 trước write. Giữ credentials hợp lệ nếu tắt creation trong khi còn attempts để IPN cũ tiếp tục verify. URL ngoài loopback cần HTTPS, không credentials/fragment; adapter chỉ Sandbox, không production. API port máy hiện5001; example5000 phải thay theo env khi cấu hình Return. Không đặt secret trong URL.

## Chạy API và expiry worker

Từ project dùng `.\scripts\backend\start.ps1`. Sau khi thay env/source cần restart đúng process backend của project để đọc config mới. Worker là process riêng, không tự start từ Flask, không TTL xóa Order/attempt:

```powershell
.\scripts\payment\start-expiry.ps1
# Hoặc foreground (Ctrl+C để dừng):
.\.venv\Scripts\python.exe -X utf8 scripts/payment/expire_pending.py
# Một batch, exit1 khi có failure:
.\.venv\Scripts\python.exe -X utf8 scripts/payment/expire_pending.py --once
```

Worker quét tối đa100 eligible Orders mỗi30s; state/restore/invalidate cùng transaction. Safe stdout chỉ scanned/expired/failed; log/PID ở ignored `.local/payment`, script kiểm tra PID thuộc đúng worker trước reuse. Worker **ghi vào database được cấu hình** và sẽ expire online holds cũ đủ điều kiện, kể cả creation đang disabled. Verification PHASE06A chỉ chạy worker trên owned ecommerce_test; chưa bật worker nền trên ecommerce_dev để bảo toàn seeded database/fingerprint. Khi demo online, khởi động worker cho DB demo đã được cho phép vận hành. Detail/retry/IPN dùng cùng lazy expiry service; Return không expire.

## Luồng tích hợp Frontend

CUSTOMER login→Cart→GET quote paymentMethod=VNPAY→POST /orders với nguyên quote và Idempotency-Key→nhận Order/initial attempt/paymentUrl→redirect URL. Return verify trả safe envelope nhưng không xác nhận paid; poll Bearer owner GET /orders/:id. IPN server provider verify+transaction mới authoritative. Retry POST /orders/:id/payment-attempts với expectedVersion mới và key cho ý định mới khi failure/no pending và trước deadline; timeout replay nguyên key/body. Không gửi client price/state/merchant/URL.

Deadline15phút không gia hạn. Late/second success chỉ review, không hồi sinh đơn; không refund/resolve-review endpoint. Provider retry trả02 sau receipt đã commit; lỗi processing99, không falsely acknowledge00. Public HTTPS ingress/proxy phải chuyển nguyên provider query, không ghi full URL/query; backend không tin X-Forwarded-For. Ghi chú PHASE06A lịch sử: tunnel/merchant registration chưa cấu hình trong worker đó. Hiện IPN đã lưu ở SIT; bank/automatic IPN phải theo [review follow-up](vnpay-sandbox-final-review.md), không suy ra từ việc lưu URL.

## Verification

```powershell
Set-Location backend
..\.venv\Scripts\python.exe -X utf8 -m pytest -q tests/test_payment.py --junitxml=evidence/phase06a-payment-pytest.xml
..\.venv\Scripts\python.exe -X utf8 -m pytest -q --junitxml=evidence/phase06a-pytest.xml
Set-Location ..
.\.venv\Scripts\python.exe -X utf8 scripts/backend/verify_payment_runtime.py
```

Test writes chỉ owned ecommerce_test rs0; không reset/reseed/drop dev. Runtime real localhost HTTP dùng fixture credentials giả rõ ràng, không gửi signed fixture URL tới provider. Dev fingerprint trước/sau gồm documents/options/validators/indexes, cleanup exact fixture IDs. Live rehearsal chỉ có thể ghi PASS sau khi dùng merchant thật, mở gateway/redirect, thanh toán Sandbox và nhận IPN server thật; offline signed callback không phải evidence live.


## VNPAY operations19/10/2026 — ADR014

Merchant Sandbox đã cung cấp; IPN đăng ký trên SIT tại backend public `/api/v1/payments/vnpay/ipn`, Return tới SPA `/payment/return`. Runtime `backend/serve.py` supervises API/expiry ở hai process riêng trên dịch vụ hiện hữu, bật tự động khi VNPAY enabled. Giữ `PAYMENT_EXPIRY_WORKER_ENABLED=true` kể cả khi tắt creation để giải phóng holds đang có. Fixed `PAYMENT_EXPIRY_CREATED_AFTER` UTC loại fixture lịch sử khỏi auto-scan; không thay mốc sau restart. Không TTL/reset/reseed. Khi một child chết supervisor dừng child còn lại và exit nonzero; shutdown bounded. Source `backend/service_supervisor.py`, `scripts/payment/expire_pending.py`; ADR014 khóa cutover/verification. Return UI lấy trạng thái Order mới đúng id, cảnh báo review sau poll, lỗi mạng hiện chưa xác minh và có retry. Chỉ evidence provider redirect/bank/IPN thực mới đóng live gate; cấu hình đủ hoặc signed fixture không thay thế live PASS.
