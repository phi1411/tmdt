# PHASE 07D — Final Demo Rehearsal & Readiness Review

Ngày kiểm tra: **12/10/2026**, Asia/Bangkok. **Chưa đủ điều kiện FINAL PASS: có một lỗi chặn bước đổi giá bằng Web, cùng các gate MANUAL PENDING. Dừng để review.**

**Follow-up14/10/2026:** lỗi form ảnh rỗng đã sửa và kiểm tra lại trên production Web/real rs0:11checksPASS/147HTTP, Web đổi10→12triệu/snapshot giữ10 không còn API fallback. [Review bản sửa và evidence mới](phase-07d-price-editor-fix-review.md). Nội dung12/10bên dưới giữ nguyên lịch sử; FAIL price editor đã đóng, các gate Compass/timing/offlineOS vẫn PENDING, chưa FINAL PASS.

## 1. Executive Summary

Đã chạy kiểm tra mới trên MongoDB thật/local rs0 và production bundle frontend hiện tại. Readiness fixture 07C, Products/Cart/Orders, snapshot A→B qua API, lifecycle COD bằng Web, revenue delta, aggregation và explain đều có bằng chứng mới. Browser run cuối có **10 check PASS, 1 check FAIL, 140 HTTP response đều 2xx**; FAIL là form Admin chặn lưu Product có images rỗng trước khi gửi PATCH.

Luồng COD chạy thành công với browser tắt cache và chặn mọi HTTP(S) ngoài loopback. Đây là PASS cho phạm vi kiểm thử browser cô lập, **không** phải đã ngắt mạng hệ điều hành/backend. Compass GUI, rehearsal 5/10 phút do ba sinh viên thực hiện và offline bằng ngắt mạng thật vẫn MANUAL PENDING. VNPAY LIVE SANDBOX BLOCKED tiếp tục là giới hạn ngoài flow COD bắt buộc.

## 2. Scope & Safety

Đã đọc đầy đủ 10 tài liệu được yêu cầu, AGENTS/architecture, phần schema/business rules và API/feature/source trực tiếp của checkout/orders/admin/dashboard. Kiểm tra Git cho thấy repo đã có HEAD **3999890 — PHASE 05AB - Auth Users and Catalog integration pass**, với nhiều thay đổi/untracked từ các phase sau; không coi chúng là thay đổi của 07D, không checkout/reset/commit/push.

**Dev và benchmark chỉ đọc trong toàn phiên 07D.** Để không làm mất baseline stock 20 và lịch sử 07C, clone đúng sáu collection hiện tại sang **owned ecommerce_test** sau khi kiểm tra marker, schema và collection rỗng. Browser chạy cùng Flask source trên 5002 và production bundle trên 5174; nguồn demo chính vẫn ecommerce_dev/backend 5001/frontend 5173. Không thay backend/frontend application code, schema/index/business rule hoặc evidence 07B/07C.

Mutation chỉ xảy ra trong clone kiểm thử. Journal private ghi exact ID trước insert; cleanup bằng transaction chỉ xóa các clone IDs và Order/Cart/Attempt thuộc đúng Customer demo được journal nhận diện. Test listener đã dừng, sáu collection test cuối cùng rỗng; không drop/reset/reseed DB. Mật khẩu/token không được đưa vào evidence; credentials 07C giữ nguyên private.

## 3. Environment Verification

| Hạng mục | Kết quả mới |
| --- | --- |
| MongoDB | 8.0.32, localhost:27017, rs0 PRIMARY; lúc bắt đầu chưa chạy, đã start bằng script project với cùng dbPath |
| Backend demo | 5001, health 200; start bằng script có sẵn |
| Frontend demo | 5173, Vite proxy `/api` → 5001; dependencies local đã có |
| Browser test | Headless Edge/Puppeteer, production bundle 5174 → same-source Flask 5002 → ecommerce_test |
| Frontend build | `npm run build` PASS: TypeScript + Vite 6.4.4, 2237 modules, build 18,42 s; JS 868,59 kB/gzip 237,21 kB, có chunk-size warning |
| Compass | Installed/running **1.52.0**; không cập nhật/cài mới trong 07D; native capture thất bại |
| Dev counts trước và sau | users 42, categories 5, products 182, carts 1, orders 101, payment_attempts 30 |
| Dev integrity | Full fingerprint trước/sau bằng nhau, gồm documents/options/validators/indexes và fixture 07C |
| Schema/reference | 6 canonical validators, 14 declared + 6 `_id_` indexes; orphan checks bằng 0 |
| Benchmark | ecommerce_benchmark riêng: 30.000 Products/10.000 Orders; full fingerprint trước/sau bằng nhau |

Baseline gồm seed 40 User/180 Product/100 Order, User được giữ ở 06AB và fixture 07C có chủ đích. Không ép counts hiện tại về seed. Hash toàn bộ app source/canonical DB artifacts/API contract/evidence 07B/07C được so trước/sau, **không có protected file thay đổi**; chi tiết ở [environment](../database/evidence/phase07d-environment.json) và [integrity](../database/evidence/phase07d-integrity.json).

## 4. API/MongoDB Test Results

| Kiểm tra | Status | Phạm vi / bằng chứng |
| --- | --- | --- |
| Local health, Admin/Customer login | PASS | Real HTTP demo 5001, credentials private |
| Products search/detail, Cart rỗng, Orders owner | PASS | Read-only ecommerce_dev; Product fixture ACTIVE, category ACTIVE, phone/address sẵn sàng |
| 5 Dashboard endpoints | PASS | Real demo API trả 200: summary/revenue/top-products/category-revenue/order-status |
| Hai Product → Cart → COD Order | PASS | Browser production bundle trên clone test, quantity 1 mỗi SKU, áo M/Black |
| Hủy COD/hoàn tồn | PASS | Browser Customer cancel hợp lệ; stock clone về 20 sau bản 5 phút; Cart rỗng |
| Confirm → ship → complete | PASS | Browser Admin actions hợp lệ, cuối COMPLETED/PAID, completedAt có thật |
| Hoàn thành và revenue | PASS | Cùng window tháng 10: revenue +10.200.000, units +2, không cộng ship 30.000 |
| Cleanup / bảo toàn fixture | PASS | Exact test cleanup; dev/benchmark fingerprint giữ nguyên, test rỗng |

11 HTTP preflight calls và query assertions chạy trực tiếp; browser run cuối ghi 140 HTTP response đều 2xx, không có pageerror. Không chạy lại toàn bộ 658 pytest vì không sửa application; evidence 07A/06AB vẫn là lịch sử riêng. [Browser receipt](../database/evidence/phase07d-browser.json), [MongoDB test outcomes](../database/evidence/phase07d-test-outcomes.json).

## 5. Compass GUI Readiness

**MANUAL PENDING.** Đã mở Compass thật và tìm được cửa sổ 1.52.0. Capture lần đầu lỗi `FrameArrived timed out: timed out waiting on channel`; làm mới window selection và retry một lần lỗi `window capture timed out: timed out waiting on channel`. Không gửi input dựa trên state/tọa độ cũ; không có thao tác Documents/aggregation/explain GUI thành công để đánh dấu PASS.

Filter/pipeline/explain đã chạy bằng PyMongo trên DB thật và có output kiểm chứng; điều này chỉ chứng minh query dùng được, không nghiệm thu GUI Compass. Hướng dẫn hiện có là [Compass từng click](compass-demo-steps.md); exact manual actions ở mục 13. Không tái dùng kết quả 07B như phép đo GUI 07D.

## 6. Snapshot Demonstration

Browser tạo Order **ORD-6ACCA500676156E90EDA3738** trên **ecommerce_test**, hai item, subtotal 10.200.000/ship 30.000/total 10.230.000. Form Admin không đổi được giá trên fixture images rỗng, nên phần còn lại dùng **PATCH API chỉ price + expectedVersion**: điện thoại 10.000.000 → 12.000.000. Đọc lại qua API và Web Customer xác nhận items/customerSnapshot/shippingAddress không đổi, priceAtPurchase vẫn 10.000.000; không có field sống khác bị sửa trong PATCH fallback.

[Screenshot snapshot sau đổi giá](../database/evidence/phase07d-browser/snapshot-A-after-B.png) và receipt ghi rõ channel `REAL_HTTP_API_FALLBACK_UI_PRICE_EDITOR_FAILED`. Sau proof, Customer hủy đơn qua Web; giá clone về A, stock clone 20. Đây là snapshot PASS với API mutation + Web read; **không** gọi Admin Web price edit PASS. Đơn này thuộc test và đã cleanup, không thể tìm trong ecommerce_dev sau phiên; standby dev vẫn là Order 07C đã CANCELLED.

Lỗi Web được tái hiện bằng click Submit thực tế: toast **“Vui lòng cung cấp ít nhất một đường dẫn hình ảnh hợp lệ (http:// hoặc https://).”**, không phát sinh PATCH. Source `frontend/src/pages/AdminProductFormPage.tsx` chặn `images.length === 0` dù API/fixture cho phép images rỗng. [Screenshot lỗi](../database/evidence/phase07d-browser/admin-price-blocked-empty-image.png). Không thêm ảnh, sửa fixture hay sửa source để che lỗi; bước này chặn cả hai kịch bản hiện hành.

## 7. Dashboard / Aggregation / Index Verification

Order **ORD-6ACCA506676156E90EDA373A** được browser đặt và Admin confirm/ship/complete trong clone test. Cùng range **[2026-10-01T00:00:00Z, 2026-11-01T00:00:00Z)**: revenue từ 0 lên **10.200.000**, products sold 0→2, paymentStatus PAID và orderStatus COMPLETED. Giá Product B không thay đổi snapshot A; Order total 10.230.000 không dùng làm merchandise revenue. Mỗi stock clone còn 19 sau một lần bán; không cố hoàn kho Order COMPLETED.

Dashboard Web trả đủ 5 reports; visual check bổ sung chờ animation xong, xác nhận **5 pie sectors/2 area paths/6 bars**, desktop 1440 không overflow ngang. [Chart receipt](../database/evidence/phase07d-chart-visual.json), [screenshot đã ổn định](../database/evidence/phase07d-browser/desktop-dashboard-settled.png). Screenshot `dashboard.png` của lượt đầu chụp sớm trong animation, không dùng để kết luận chart bị mất dữ liệu.

Query mới trên ecommerce_dev chạy 4 canonical pipelines Top5/revenue-day/revenue-month/sales-summary trong seed window **[2026-07-03, 2026-10-01) UTC**: tổng **10.103.259.022 VND**, **434 units**, Top5 5 rows. Top5 có match/pre-sort snapshot label/unwind/group/rank-sort/limit/project; không lookup giá Product hiện tại. Range này khác Dashboard 30 ngày và tháng 10 của delta test; phải bind cùng from/to khi đối chiếu.

| Replay explain mới 07D | Natural docs/keys/nReturned | Named docs/keys/nReturned |
| --- | --- | --- |
| Dev category-price, limit 10 | 182 / 0 / 10 | 10 / 10 / 10 |
| Benchmark category-price 07B, limit 20 | 30.000 / 0 / 20 | 20 / 20 / 20 |

Ordered IDs giữa natural/named/planner bằng nhau; raw winningPlan/executionStats ở [phase07d-queries.json](../database/evidence/phase07d-queries.json). Natural hint nghĩa là **không dùng index cho truy vấn**, không drop index. 07D không đo lại 720 latency samples; số Revenue/Top5 10.000→152 và p50/p95 vẫn dẫn về evidence **07B**, không gọi là kết quả GUI hay latency mới của 07D.

## 8. Demo 5-minute Rehearsal

Đối chiếu [script 5 phút](demo-script-5min.md): ba loại Product render đúng attributes; Customer thêm điện thoại và áo M/Black, Cart/quote/COD/Order thành công, Order snapshot hiển thị đúng, Dashboard và query có bằng chứng. Reset clone bằng hủy/restore giá hoàn tất; dev fixture không ghi.

**FAIL bước đổi giá bằng Web trên fixture images=[];** phần snapshot chỉ hoàn tất qua API fallback đã nêu rõ. Compass GUI và **thời gian 5 phút người thật** MANUAL PENDING. automationSeconds trong receipt là thời gian từng test, không gồm lời nói, chuyển người/Compass và xử lý tình huống; không dùng tổng vài giây này làm thời lượng bảo vệ.

## 9. Demo 10-minute Rehearsal

Đối chiếu [script 10 phút](demo-script-10min.md): browser thêm đủ hai item/checkout, Admin lifecycle thực, COMPLETED/PAID và revenue delta đúng business rules. Giá đổi qua API fallback; không thực hiện optional description CRUD vì cùng form ảnh rỗng chặn submit.

Phần completion chạy trên clone test để giữ fixture live stock 20. Order COMPLETED test được cleanup trong phạm vi fixture kiểm thử; đây không phải hủy/rollback một Order nghiệp vụ live. Kịch bản end-to-end nguyên bản chưa PASS do price editor/Compass; **thời gian 10 phút người thật MANUAL PENDING**.

## 10. Offline Readiness

Source cho thấy browser gọi API tương đối `/api/v1`, proxy localhost; COD không gọi VNPAY/provider trong checkout. MongoDB, Python, Node và frontend dependencies hiện có local; build đã chạy thành công. Hai fixture images=[] và fallback văn bản đã hiển thị thực. Trang có **Google Fonts** bên ngoài và ảnh seed bên ngoài: là dependency trình bày phụ trợ, không hứa tất cả ảnh/font online.

Đã thử an toàn trong browser test: **tắt cache, chặn mọi request HTTP(S) có host ngoài localhost/127.0.0.1/::1**, mở mới browser page, login, tải hai fixture, Cart, Checkout COD, Order success và hủy qua Web. Request probe `https://example.invalid` bị interceptor chặn trước khi đi ra mạng; request font ngoài cũng bị chặn, các request local vẫn hoạt động. [offline-cancelled.png](../database/evidence/phase07d-browser/offline-cancelled.png) và `offline` trong browser receipt là bằng chứng mới.

**PASS scoped browser external-network denial; MANUAL PENDING actual host internet disconnect.** Không đổi network adapter/firewall/settings của máy vì đang có ứng dụng khác và đây không phải phạm vi cần tác động hệ thống. Backend không bị network-deny trong drill; không dùng kết quả này để khẳng định đã thử mọi dependency cấp OS. Nhóm cần ngắt mạng thật trên máy bảo vệ trong thời điểm phù hợp, vẫn giữ services local, rồi thực hiện mục 13.

## 11. Remaining Risks / Blockers

- **Chặn demo:** form Admin yêu cầu ảnh, không lưu được price-only trên fixture images=[]; cả script 5/10 phút cần xử lý điểm này trước khi nghiệm thu Web flow nguyên bản.
- **Chưa nghiệm thu GUI:** native Compass capture lỗi; thao tác Text/Run, Documents/Order và Explain vẫn cần người dùng làm trực tiếp trên Compass 1.52.0.
- **Chưa đo người thật/offline OS:** timeline là ngân sách, không phải số đo; browser deny không thay thế thử ngắt mạng thực.
- **Ổn định máy/test:** lượt browser đầu có Customer login 401; kiểm tra hash/password dev/test đều hợp lệ và login sau đó PASS. Có các timeout khi tự động mở lại Order; lượt cuối cancel/lifecycle PASS. Log test listener ghi một `MemoryError` ở Werkzeug request teardown, chưa xác định nguyên nhân; không sửa application và không khẳng định đã giải quyết tận gốc. Cần login/check health sát buổi bảo vệ.
- **Giới hạn đã biết:** build cảnh báo bundle lớn; VNPAY LIVE SANDBOX BLOCKED; ranges/cohort metric khác nhau. Không suy ra SLA production hoặc gate VNPAY live PASS.

Receipts thất bại lưu [attempt1](../database/evidence/phase07d-browser-attempt1.json), [attempt2](../database/evidence/phase07d-browser-attempt2.json), [attempt3](../database/evidence/phase07d-browser-attempt3.json). Chúng là lần thử không hoàn tất; receipt browser cuối và chart check mới là nguồn cho các hạng mục PASS sau retry. Screenshots thư mục browser là captures của lượt cuối/visual check; không dùng tên lặp của lần đầu để khẳng định hai ảnh khác nhau.

## 12. Final PASS / FAIL / PENDING Matrix

| Gate | Trạng thái | Kết luận |
| --- | --- | --- |
| Environment/API/MongoDB | PASS | Real local services/PRIMARY/accounts/read APIs |
| Fixture 07C và dữ liệu gốc | PASS | Dev full fingerprint unchanged; giá A, stock 20, Cart rỗng |
| Validators/indexes/benchmark preservation | PASS | Canonical match; dev/benchmark/evidence protected unchanged |
| Frontend TypeScript/production build | PASS, warning | Chunk-size warning còn lại |
| Browser Products/Cart/COD/cancel | PASS trên clone | Test cùng dữ liệu/source, không claim dev write rehearsal |
| Snapshot API mutation + Web read | PASS | A→B giữ historical A/customer/address |
| **Admin Web price edit trên fixture 07C** | **FAIL** | Form yêu cầu ảnh, chặn PATCH |
| Admin COD completion/revenue delta | PASS trên clone | COMPLETED+PAID, +10.200.000/+2, ship excluded |
| Dashboard charts/aggregation/query equality | PASS | 5 endpoint, chart paths/sectors, raw outputs/explain mới |
| Compass GUI | MANUAL PENDING | Không capture/thao tác GUI thành công |
| Human 5-minute / 10-minute timing | MANUAL PENDING | Chưa có rehearsal ba sinh viên theo đồng hồ |
| Offline browser external deny | PASS scoped | Cold cache/local COD/cancel, không phải host disconnected |
| Actual internet-disconnected rehearsal | MANUAL PENDING | Chưa ngắt mạng máy thật |
| VNPAY live | BLOCKED, ngoài COD gate | Thiếu merchant/public IPN, không giả live |
| **PHASE07D FINAL PASS** | **CHƯA ĐẠT — FAIL + PENDING** | Không chuyển phase |

## 13. Exact Manual Actions Required

**Compass trên ecommerce_dev — chỉ đọc:**

1. Mở Compass → Add new connection → URI `mongodb://localhost:27017/?replicaSet=rs0` → Connect → **ecommerce_dev**. Không chọn saved Atlas/test/benchmark để xem đơn demo.
2. products → Documents → Filter `{sku:{$in:["DEMO-ELE-001","DEMO-FAS-001","DEMO-HOM-019"]}}` → Find. Mở attributes/field chung ở ba document; chụp kết quả và ghi thời điểm.
3. orders → Documents → Filter `{orderCode:"ORD-6AC7A53587E692850A155388"}` → Find. Đây là **standby API rehearsal 07C đã CANCELLED**, không phải đơn vừa tạo 07D. Mở items/category/customerSnapshot/shippingAddress; không Edit/Insert/Delete. Khi demo sống sau này phải thay bằng orderCode vừa copy từ Web.
4. orders → Aggregations → **Text** → paste toàn array từ `database/evidence/phase07c-top-products.compass.txt` → **Run**, không chỉ xem preview sample. Kỳ vọng 5 rows/top quantity 12; chụp output. Thử tương tự `phase07c-revenue-day.compass.txt`; tổng fixed seed window 10.103.259.022/434 units ở evidence. Muốn so Dashboard, copy đúng from/to của API vào Date match rồi Run lại.
5. products → Indexes → xem `ix_products_category_price`. Documents Filter `{categoryId:ObjectId("4ad126c3ebc4fb3918f084d4"),status:"ACTIVE",price:{$gte:1000000,$lte:20000000}}`, Sort `{price:1,_id:1}`, Limit 10 → Find → Explain → Visual Tree/Raw Output. Trong embedded MONGOSH chạy file **read-only** `database/evidence/phase07c-index.mongodb.js`: nReturned 10, docs 182→10, keys 0→10 ở dữ liệu hiện tại; không drop index.
6. Chỉ cho phần performance, chuyển **ecommerce_benchmark → products**, filter status ACTIVE/productType ELECTRONICS/categoryId `9f279f9b19426a6a465cfd3a`/price 2–5 triệu, sort price/id ASC, limit 20; xem Explain hoặc chạy `phase07c-benchmark-index.mongodb.js`. So COLLSCAN 30.000/0 và IXSCAN 20/20, cùng 20 results. Nói rõ dataset benchmark riêng và quay lại dev sau phần này; không chạy setup/run/reproduce/cleanup 07B trong buổi demo.
7. Ghi người kiểm tra/ngày giờ/version Compass và ảnh Documents/Order/pipeline/explain vào checklist. Chỉ đổi GUI gate sang PASS sau khi thực hiện được thật.

**Web/timing/offline:**

8. Login Customer/Admin từ private note ở hai browser/profile; check health/Cart/giá A/stock trước demo. Hiện tại **không bấm lưu form Product images rỗng rồi kỳ vọng thành công**. Review lỗi form trước; phương án tạm là Admin price-only API với expectedVersion mới và nói rõ đây là API fallback. Không thêm external ảnh hoặc sửa schema/seed để che lỗi.
9. Sau khi có quyết định cho price editor/fallback, ba SV chạy đúng script và bấm đồng hồ từ mở đầu đến kết thúc; ghi số đo thật cho 5/10 phút. Bản 5 phút hủy đúng Order riêng sau proof và restore A qua API/Web đã được kiểm tra; không cộng stock thủ công.
10. Bản 10 phút nếu hoàn thành trên live dev sẽ giữ lịch sử COMPLETED/revenue và mỗi stock 19 sau một lần bán, không thể restore baseline stock 20 bằng cancel. Nếu cần giữ nguyên fixture 07C, tiếp tục rehearsal completion trên clone test có ownership như phiên này; không giả số liệu/đổi completedAt.
11. Khi phù hợp để ngắt internet thật trên máy bảo vệ: giữ Mongo/backend/frontend local, mở browser mới/tắt cache, login, tải Product fixture, thêm hai item, COD, xem Order và hủy hợp lệ. Ghi ảnh/trạng thái/giá/tồn/Cart; font/ảnh ngoài có thể mất nhưng core phải chạy. Kết nối lại mạng sau thử; chưa thực hiện bước này trong 07D.

## 14. Final Recommendation

**Không duyệt PHASE07D FINAL PASS ở trạng thái hiện tại.** Chấp nhận evidence mới cho các gate đã PASS theo phạm vi, giữ FAIL của form ảnh rỗng và MANUAL PENDING của Compass/timing/offline OS. Cần review và xử lý điểm chặn price editor hoặc chốt lại kịch bản API fallback minh bạch, rồi thực hiện exact manual actions và ghi số đo thật trước khi duyệt cuối.

07D chỉ thêm helper kiểm thử, evidence và tài liệu. Live fixture 07C/data gốc, backend/frontend application, schema/business rules và benchmark/evidence 07B đều giữ nguyên; ecommerce_test đã cleanup rỗng. **Dừng để review, không tự chuyển phase.**
