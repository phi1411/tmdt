# PHASE 07A — Full System Hardening & End-to-End Verification

Ngày 08/10/2026. Kết luận: **FULL SYSTEM E2E PASS** trong phạm vi hệ thống local/COD, security, snapshot, polymorphic catalog và contract thanh toán. **VNPAY LIVE SANDBOX vẫn BLOCKED**, không nghiệm thu redirect/bank/public IPN thật.

Không thêm feature, redesign, đổi schema/index/collection hoặc refactor backend. Đã sửa tối thiểu 5 lỗi frontend phát hiện khi kiểm tra. Dừng để review; không commit/push hoặc tự chuyển phase.

## 1. Phạm vi và môi trường kiểm tra

Đã đọc AGENTS, architecture, API contract, business rules, review06AB, reviewFE02A và feature docs trực tiếp liên quan. MongoDB8.0.32 local rs0/WiredTiger, Python3.12.14/Flask3.1.3/PyMongo4.15.3, React/Vite6.4.4/TypeScript strict. Browser kiểm thử là Microsoft Edge headless qua Puppeteer.

- Stack development thật: MongoDB27017, Flask5001 và React5173; health200/replicaSet ok, frontend200 ở lúc bắt đầu và chốt.
- Ghi dữ liệu E2E vào **ecommerce_test** trên chính rs0 thật. Flask5002 chạy cùng source/factory; frontend5174 là Vite preview của production build, proxy5002. Không mock API trong Customer/Admin/security/snapshot/polymorphic journeys.
- Fixture là bản sao đọc-only của corpus dev ban đầu, giữ BSON ObjectId/Date/long, validators và indexes có sẵn. Không chạy reset/reseed/apply-schema, không ghi vào dev. Script kiểm tra ownership của test DB và ghi journal các ID tại ignored `.local`.
- Sáu fault-injection tests thanh toán frontend dùng API giả lập có kiểm soát và được ghi riêng; chúng không được tính là giao dịch VNPAY thật.

## 2. Kết quả kiểm thử chính thức

| Kiểm tra | Tổng | Pass | Fail/error | Skip |
| --- | ---: | ---: | ---: | ---: |
| Full backend pytest trên source hiện tại | 658 | 658 | 0/0 | 0 |
| E2E regression FE-02 Admin/contract | 22 flows | 22 | 0 | 0 |
| E2E regression Customer | 32 flows | 32 | 0 | 0 |
| Full-system bổ sung | 25 nhóm | 25 | 0 | 0 |
| Frontend Payment contract fault injection | 6 cases | 6 | 0 | 0 |
| Dashboard visual: desktop/tablet/mobile | 3 views | 3 | 0 | 0 |

Backend thực chạy toàn suite, không suy từ kết quả cũ: JUnit658tests,195.587s; console195.60s. Breakdown80foundation +133Auth/User +112Catalog +126Commerce +102Payment +105Admin/Analytics. Backend app/tests vẫn khớp toàn bộ hash tương ứng trong source manifest06AB.

`npm run build` thực chạy `tsc && vite build`; strict/noUnusedLocals/noUnusedParameters bật. Exit0,2237modules, lần build cuối16.79s. Bundle JS868.59kB/gzip237.21kB, CSS41.49kB/gzip7.48kB. Có **một cảnh báo bundle lớn hơn500kB**; không refactor/chia bundle ngoài phạm vi và không báo build không có warning.

Ba bộ E2E thật ghi nhận lần lượt61/100/258 lượt HTTP API, exit0. Không cộng các nhóm kiểm tra khác loại thành một số “tests” chung. Evidence lịch sử FE-01A/FE-02/FE-02A giữ nguyên; kết quả07A dùng tên riêng.

## 3. Customer và Admin journeys thật

**Customer PASS:** đăng ký201 → đăng nhập200 → tìm kiếm qua navbar → lọc giá → Product detail → thêm Cart → tăng quantity1→2/subtotal200.000 → thêm/chọn Address → quote có quoteToken/total230.000 → VNPAY disabled503 và trở lại COD200 → tạo Order201 → Success/code → My Orders → detail → xác nhận cancel200/CANCELLED; stock trở lại12. F5/profile/address/logout/guest route được kiểm tra thêm trong32flows regression.

**Admin PASS:** đăng nhập ADMIN → Dashboard đủ5endpoints summary/revenue/top-products/category-revenue/order-status → đọc Top5 đúng5items → Category create/read/update/delete category trống → tạo Product qua form → sửa Product → archive qua confirmation modal → User list/search/block/unblock → Order detail → confirm → ship → complete. Delete Category có Product trả409, Admin account được bảo vệ409.

Order lifecycle thật PENDING→CONFIRMED→SHIPPING→COMPLETED/PAID, có completedAt. Oracle trước/sau completion: revenue tăng đúng100.000VND, productsSold tăng1; shipping30.000 không vào revenue. Nguồn là aggregation server và item snapshot, không cộng tiền từ frontend.

## 4. Snapshot và Polymorphic Product

**Snapshot PASS:** Order được tạo với tên Product ban đầu/priceAtPurchase100.000; Admin UI đổi tên Product và giá hiện tại120.000. GET Order vẫn trả toàn bộ `items` deep-equal với trước mutation, total130.000 và UI vẫn hiển thị tên lịch sử. Sau archive Product, public detail404 nhưng Order vẫn giữ snapshot. Live Product giữ battery5000mAh và nested customSpecification khi chỉ đổi tên/giá.

**Polymorphic PASS:** cùng collection/API, mở ba Product detail và đối chiếu API với các scalar attributes trên UI; FASHION còn kiểm tra các option sizes/colors.

| productType | Ví dụ attributes đã đối chiếu |
| --- | --- |
| ELECTRONICS | warrantyMonths, ram, battery; nested customSpecification được giữ khi edit/snapshot |
| FASHION | sizes, colors, material, gender, sole |
| HOME_APPLIANCE | material, capacity, dishwasherSafe, useCase, care |

Nested metadata không được yêu cầu render thành chuỗi; kiểm tra bảo toàn trong API/Order snapshot. Không tạo collection riêng theo ngành.

## 5. Security và browser

| Trường hợp | Kết quả |
| --- | --- |
| Guest vào Admin | UI về login; API401 |
| Customer vào Admin | UI403; API403 |
| Customer A đọc Order của B | API404, không lộ dữ liệu |
| Invalid JWT | auth/me401 |
| Account BLOCKED | login401 và access token cũ401 ngay; mở khóa vẫn không làm token cũ hợp lệ |
| Mass assignment/payload tampering | register role ADMIN, Cart client price, Order client total, Admin action paymentStatus đều422 |
| Admin tự khóa/Admin account |409 |

Kiểm tra browser cuối:0page errors,0unexpected console errors,0console warnings,0unexpected HTTP failures,0failed assets,0unexpected request failures. Có17console messages từ HTTP âm tính dự kiến và2`net::ERR_ABORTED` do navigation hủy request đang đọc; được ghi rõ, không gọi toàn bộ raw console/network là0. Legacy suites có2messages401/409 và2messages503 Return tương ứng các scenario cố ý.

Deep links Customer7route/Admin6route hoạt động; đường dẫn không tồn tại hiển thị trang404 của SPA, HTTPdocument200 theo SPA fallback. Không có routeAPI collision:13blueprints/52method-path, prefix/api/v1 nhất quán.

Responsive21lượt:1440×900,900×768,390×844 trên Catalog/Order detail/Dashboard/Admin Products/Categories/Users/Orders. Root không tràn ngang; Catalog được scroll qua từng card để thật sự tải ảnh lazy, kiểm tra complete/naturalWidth và assetHTTP. Chart visual audit chờ animation, kiểm tra SVG Pie sectors/Area paths/Bars và chụp Pie đang trong viewport; đã xem ảnh desktop/mobile. Ảnh full-page đầu có thể bắt animation/offscreen paint, không dùng ảnh đó để kết luận biểu đồ trống.

## 6. Lỗi phát hiện và sửa tối thiểu

| Lỗi thực tế | Sửa | Kiểm chứng cuối |
| --- | --- | --- |
| Admin sửa tên/giá gửi attributes thiếu field, làm mất battery/nested metadata | Giữ originalAttributes và chỉ thay các key có ô chỉnh sửa | Browser edit thật +API +snapshot deep-equal |
| Checkout thiếu URL sau commit không replay đúng request; mỗi lần click sinh key mới | Giữ payload/key cho cùng intent; initial URL fault replay đúng POST/orders, bounded một lần/lượt; giữ intent nếu chưa khôi phục được | COD journey thật và2fault-injection cases cùng key/body |
| Retry attempt URL fault/network sinh key mới | Giữ key theo orderId/expectedVersion tới khi nhận URL/terminal hoặc bị từ chối4xx |2requests cùng key/body trong deterministic case |
| UI mời retry khi initial PENDING, COD hoặc cần review | Điều kiện VNPAY/PENDINGorder/FAILEDpayment/noReview/còn deadline ở detail/Return |3negative UI contract cases; backend102Payment tests |
| Category filter Admin Products tràn trang mobile429px tại viewport390px | Giới hạn container/select, cho select co lại |21responsive checks, root390px |

Application files sửa: `frontend/src/pages/AdminProductFormPage.tsx`, `AdminProductsPage.tsx`, `CheckoutPage.tsx`, `OrderDetailPage.tsx`, `PaymentReturnPage.tsx`, `frontend/src/api/paymentApi.ts`. Backend logic, tests và DB architecture không đổi.

Docs được đồng bộ: Admin Products/Checkout/Payment; Auth/API/architecture/foundation ghi nhận state+sessionStorage theo tab đã bàn giao và kiểm thử F5 tại FE-01A, thay mô tả memory-only cũ. Không thay JWT access-only/TTL/live DB guards hoặc thêm refresh token. Review lịch sử không bị ghi đè.

Test tooling được sửa để lấy seed password từ private env, results riêng và fail đúng khi thiếu flow/fatal error; bổ sung API-aware waits, chờ modal/actionable controls và foreground tab cho Edge. Có những lần chạy chưa đạt do lỗi ứng dụng trước sửa, wait/selector của harness, hoặc MongoDB được restart trong phiên dùng chung. Kết quả chính thức ở bảng trên là các lần chạy hoàn tất sau sửa; không coi lần gián đoạn là PASS.

## 7. VNPAY status

**Contract/disabled/deterministic/Return-IPN implementation PASS; LIVE SANDBOX BLOCKED.** Env máy VNPAY_ENABLED=false; quote online503 trước write/hold, UI chuyển COD được. Return không xác nhận PAID từ query browser; disabled handler503 được hiển thị an toàn, IPN thiếu config trảHTTP200/RspCode99.102backend Payment tests bao phủ ký URL/Return readonly/IPN authoritative/duplicate/late/expiry/rollback/idempotency trên rs0 thật.6frontend tests giả lập chứng minh recovery/eligibility của bundle production, không có bank/provider/public callback thật.

Thiếu merchant VNP_* và public IPN đăng ký/reachable; không bật expiry worker trên dev seed, không claim real redirect/bank/IPN PASS.

## 8. Cleanup và database integrity

Đã dừng riêng hai listener test5002/5174, xóa theo journal/exactID/owned fixture trong transaction snapshot/majority.6collections ecommerce_test đều rỗng; validators6/indexes14+6_id_ của cả test/dev giữ nguyên.0global orphan Cart/Order/Payment Attempt/reference mismatch. Không reset/reseed/drop collection/index hoặc sửa seed để khôi phục counts.

**PHASE07A dev writes=0.** Dev ban đầu41Users/3Categories/180Products/0Cart/100Orders/30Attempts, digest `f8c36f1872e7de3b42ae7e949e16e6f2a81fbdca20a24eeb3789033c358b50ce`. Trong phiên có worker07C tạo fixture demo có chủ ý; đối chiếu [evidence07C](../database/evidence/phase07c-rehearse.json) và ownership journal riêng, giữ nguyên `defense07c@example.test` +2Category +2Product +1Cart +1CODOrder, không có attempt thêm.

Counts dev cuối42Users/5Categories/182Products/1Cart/101Orders/30Attempts; full digest `0a3ebe55d3ff069259a892eb80fbce25a8cb9db00c24ecbec3b97c6f795197cf`. Loại đúng các fixture07C khi đối chiếu, corpus gốc vẫn khớp nguyên digest/counts f8c36f…; không có thay đổi ngoài nguồn đã xác định. `khachtest_1791374905461@example.test` vẫn được giữ theo người dùng. DB sạch đối với artifact07A; không claim full dev fingerprint bất biến toàn phiên hoặc xóa fixture của worker khác.

## 9. Evidence và tái kiểm tra

- [Full backend JUnit](../backend/evidence/phase07a-pytest.xml), [system/build/routes/source manifest](../backend/evidence/phase07a-system.json), [DB integrity/cleanup](../backend/evidence/phase07a-db-integrity.json).
- [Customer32](../frontend/tests/phase07a-customer-results.json), [Admin22](../frontend/tests/phase07a-fe-02-results.json), [full-system25/HTTP258/browser](../frontend/tests/phase07a-full-system-results.json).
- [Payment contract6](../frontend/tests/phase07a-payment-contract-results.json), [chart visual3views](../frontend/tests/phase07a-chart-visual-results.json); pre-fix attributes/payment/mobile evidence nằm cùng directory, tên before-fix/failure riêng.
- Runner chính: `scripts/backend/verify_full_system_07a.py`; browser scripts trong frontend/tests/phase07a-*.mjs. Screenshots tại ignored `.local/phase07a-shots`; Pie desktop/tablet/mobile đã chụp sau animation và scroll vào viewport.

Reproduction: MongoDB rs0 ready → full pytest khi test DB rỗng → `npm run build` → helper `prepare` → chạy helper `serve` và preview runner ở hai tiến trình riêng → helper `legacy-admin`, `legacy-customer`, `full-journey`, `chart-visual`; payment contract runner dùng E2E_BASE_URL5174 → dừng listener test → helper `cleanup`. Không build lại khi browser đang chạy. Helper từ chối cleanup/reset dữ liệu không có ownership; secrets/credentials chỉ ignored env/.local.

Services development5001/5173 và MongoDB được giữ cho review. Không commit/push. **FULL SYSTEM E2E PASS — dừng để review.**
