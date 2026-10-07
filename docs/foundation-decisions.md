# Foundation decisions — LOCKED DESIGN v1

Ngày07/10/2026. Người dùng đã chấp nhận cấu trúc phase01 và yêu cầu phase02 khóa thiết kế; **không cho phép implementation nghiệp vụ hoặc tự chuyển phase**. Quyết định ở đây thay thế các OPEN tương ứng trong phase01. Các giá trị default là lựa chọn thiết kế có thể cấu hình, không phải yêu cầu tự nhận từ giảng viên.

## Quyết định đã khóa

| Nhóm | Quyết định | Nguồn chi tiết |
| --- | --- | --- |
| Collection names | users/categories/products/carts/orders/payment_attempts English | database-schema; reviews deferred |
| MongoDB | Local Community8.0, replica set rs0, WiredTiger; single node dev/demo | architecture; Atlas deployment deferred, không Atlas-only |
| Backend contract | Python3.12 + Flask + PyMongo; app factory/layered modular monolith | architecture; exact package patches khóa lúc bootstrap, không blocker modeling |
| Frontend contract | React + Vite + TypeScript + Tailwind CSS + Recharts | frontend do agent khác ở phase sau; shadcn/ui deferred |
| Media | Product.images[] absolute URLs; HTTPS, HTTP chỉ localhost/127.0.0.1 dev | Không upload/cloud media; Order giữ URL có fallback |
| Product | Chung products, 3 discriminator + attributes linh hoạt, price long VND | ADR001; validators/products.json |
| Category | Một cấp, không parentId; slug unique, type stable nếu referenced | ADR009; compatibility ở service |
| Cart | carts riêng, một document/User; current pricing, không reserve | ADR004 |
| Order | Snapshot embedded; transaction/quote/version/idempotency | ADR003/006; lifecycle BR-ORDER |
| Payment | COD + VNPAY Sandbox; attempts riêng có metadata/callback dedup | ADR006; không payment production/refund tự động |
| Revenue | COMPLETED+PAID, completedAt, merchandise excl ship, discount0 | ADR007, BR-REPORT |
| Search | nameNormalized substring escaped, brandNormalized equality; local Mongo | ADR008; không text/Atlas Search/fuzzy |
| Seed | 180 Product/40 User/100 Order;3 ngành,2..5 dòng/Order | seed-strategy; snapshot sinh từ Product data |

## Defaults đã khóa để backend không bị thiếu policy

| Setting | Default v1 | Rationale |
| --- | --- | --- |
| SHIPPING_FEE_VND | 30000 flat | Đủ minh họa server pricing, không engine địa lý/coupon |
| QUOTE_TTL_SECONDS | 300 | Quote5 phút; checkout luôn revalidate |
| PAYMENT_HOLD_MINUTES | 15, chỉ VNPAY | Giữ stock bounded; retry không kéo dài Order deadline |
| PAYMENT_EXPIRY_POLL_SECONDS | 30 | Explicit worker polling từ phase Payment; không TTL-delete |
| JWT_ACCESS_TTL_SECONDS | 1800 | Memory token, login lại khi hết hạn; refresh deferred |
| REPORT_TIMEZONE | Asia/Ho_Chi_Minh | Báo cáo ngày/tháng VN; BSON lưu UTC |
| REPORT_MAX_DAYS | 366 | Bounded aggregation window |
| Price / quantity / lines | 1..1e9 VND /1..99 /<=50 | Bounded document/integer arithmetic |
| Total Order | <=5e12 VND; VNPAY riêng<=9.999.999.999 VND | Safe JSON integer; provider amount12 chữ số sau×100 |
| Addresses / images / attributes | <=10 /<=8 /<=30 keys, depth<=3 | Bounded arrays/documents; linh hoạt trong attributes |

VNPAY giới hạn amount theo [contract provider](https://sandbox.vnpayment.vn/apis/docs/thanh-toan-pay/pay.html); checkout/quote reject payment VNPAY vượt cap **trước** trừ kho. COD dùng cap Order chung. Config invalid/blank phải fail khi feature cần config, không âm thầm đổi phí/TTL. Password policy12..128 ký tự; Argon2id cost default m19456/t2/p1, có thể tăng sau benchmark hashing ở runtime foundation; không cài dependencies trong phase02.

Expiry implementation contract: command/worker riêng chạy mỗi30 giây, phát hiện `paymentMethod=VNPAY,orderStatus=PENDING,paymentExpiresAt<=now,paymentStatus in [PENDING,FAILED]`, transaction expire+restore stock+invalidate pending attempt once. Checkout/payment/status reads có thể trigger cùng expiry service để state không stale khi worker chậm. Callback capture verifiedAt UTC một lần; success chỉ tự confirm nếu verifiedAt<deadline và providerPaidAt<=deadline (nếu providerPaidAt thiếu dùng verifiedAt), state PENDING. Success nhận sau deadline phải expire/restore nếu cần rồi REVIEW_REQUIRED. Quy tắc bảo thủ này cho callback đến muộn outcome giống nhau dù worker đã chạy hay chưa; không hồi sinh đơn.

## OPEN / DEFERRED

**Không còn câu hỏi thiết kế block backend.** Chưa có secrets sandbox/reachable IPN, nên kiểm chứng VNPAY sống deferred tới phase Payment; VNPAY_ENABLED=false khi bootstrap, COD và các feature khác độc lập. State/amount/metadata/idempotency contract đã khóa, không dùng credential thiếu để trì hoãn schema.

Atlas/deployment domain, cloud upload, multi-level taxonomy, variant inventory, Review, fuzzy/full-text search, refresh/forgot-password, refund automation và persistent audit store: DEFERRED, không MVP blocker. Patch versions/lockfiles, Compass version và phân công sprint thực hiện khi bootstrap/team lập kế hoạch; không được tự cài hoặc triển khai ở phase02.

Nguồn sự thật: requirement mới → AGENTS/architecture → database-schema (meaning) + validators (shape) → business-rules (behavior) → feature docs (contracts). Nếu artifacts và meaning mâu thuẫn phải sửa đồng bộ trước code, không có hai spec song song. Candidate indexes và aggregation canonical ở database/; ADR giải thích lựa chọn, không copy spec đầy đủ.
