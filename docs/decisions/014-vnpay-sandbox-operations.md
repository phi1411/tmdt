# ADR014 — VNPAY Sandbox trên Render demo

Ngày19/10/2026. Người dùng cung cấp merchant Sandbox và yêu cầu hoàn tất tích hợp, rà soát/sửa lỗi thực tế. Không payment production, không phát sinh dịch vụ trả phí mới.

## Vấn đề và quyết định

Entrypoint Render trước đây chỉ Waitress; worker expiry riêng chưa chạy. Enabling VNPAY mà thiếu worker sẽ giữ kho các đơn bỏ thanh toán nếu không ai đọc Order. Thêm supervisor vào entrypoint hiện hữu: API và expiry là hai process riêng; khi VNPAY enabled cả hai là bắt buộc. Giữ PAYMENT_EXPIRY_WORKER_ENABLED=true khi tắt creation để xử lý holds đã có. Một process dừng bất thường thì stop process còn lại, exit nonzero để Render restart; SIGTERM/SIGINT stop cả hai với bounded wait/kill. Không chạy worker bằng Flask import hoặc mỗi request, không thêm collection/index/dependency.

Atlas có5online PENDING seed đã quá hạn, merchantDEMO0001. Lần vận hành Sandbox mới dùng mốc `PAYMENT_EXPIRY_CREATED_AFTER` cố định khi enable lần đầu, UTC có timezone; scanner lọc createdAt>=mốc cùng due predicates. Không thay mốc sau restart/redeploy. Default không có mốc giữ behavior cũ; lazy expiry và IPN vẫn áp dụng invariant hiện hữu. Không expire/reseed các fixture lịch sử chỉ vì bật worker cho demo mới.

ReturnUrl là SPA `/payment/return`, forward nguyên query tới backend readonly verifier; IPN URL backend `/api/v1/payments/vnpay/ipn` đăng ký trong SIT. IPN đã verify và commit mới set paid; Return/query trình duyệt không tự set paid. Secret chỉ backend env/private files, không VITE_/source/evidence/log.

Rà soát FE phát hiện Return page giữ PENDING cũ sau khi poll Order đã FAILED/EXPIRED và cảnh báo đối soát chỉ đọc Return ban đầu. Sửa view từ Order hiện hành đúng id, giữ signature guard; lỗi mạng verify phải hiển thị chưa xác minh và cho retry, không báo bank failure. Guard async bỏ kết quả truy vấn cũ khi URL/verification đổi.

## Acceptance và kiểm tra

Real child-process supervision shutdown/failure tests; real rs0 cutoff/stock restore-once; full backend suite và strict/build, FE status tests; provider redirect/test card/IPN/Return nếu provider reachable; kiểm tra duplicate/amount tamper, hết hạn và COD regression. Cleanup exact owned fixtures, fingerprint corpus trước/sau; không fake callback rồi claim provider live PASS. Callback provider và file log phải được xử lý riêng vì Render request logs có thể lưu query; không commit signed URL/raw callback/secret.


Verification20/10/2026: hai real NCB Sandbox/testOTP/automaticIPN/Return PAID PASS, gồm WebSKU/Cart/quote/createOrder journey; replay02/tamper97/readonlyReturn digest unchanged/Adminship-complete/revenue100k exclude30kship/exactcleanup PASS. Bộ SIT provider riêng chưa hoàn tất do emptylist/extraUIerrors, không gán deterministic cases thành SIT PASS. Xem docs/vnpay-sandbox-final-review.md và backend/evidence/vnpay-*-20261020.json.
