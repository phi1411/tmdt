# PHASE07C — Chuẩn bị bảo vệ NovaMart

**Bộ tài liệu, fixture, API và query đã kiểm tra xong; live Compass/Web rehearsal còn PENDING. Chưa tuyên bố PHASE 07C DEMO READINESS PASS toàn bộ.** Ngày 08/10/2026; dừng để review sau bàn giao này.

Phạm vi chỉ gồm Polymorphic Schema, Embedded Order Snapshot, MongoDB Aggregation và Index/Performance theo barem. 07C không thêm feature, redesign, schema, API hoặc business rule; chỉ tạo tài liệu, hai helper demo và fixture riêng qua API đã có. Không reset/reseed/drop, không chạy expiry worker trên seed, không commit/push.

## 1. Demo flow và acceptance

**Ba Product khác ngành → Customer đặt COD hai Product riêng → mở Order mới → Admin đổi giá A/B → Order giữ A → Dashboard → canonical pipeline → explain benchmark 07B.** Bản 5 phút ưu tiên bốn trọng tâm; bản 10 phút thêm CRUD/lifecycle hoàn thành COD và revenue delta. SV3 mở màn hình, SV1 schema/snapshot, SV2 aggregation/index.

Acceptance là kịch bản có thể làm theo, account/fixture sẵn sàng, giá khôi phục an toàn, đúng metric/window, query cùng kết quả, checklist/offline/Q&A/evidence truy tìm được. Real API/MongoDB đã kiểm tra; thao tác Compass, đầy đủ Web flow trên fixture và thời gian thực tế cần nhóm chạy thử trên máy bảo vệ trước khi ký gate cuối.

## 2. Compass từng thao tác

[compass-demo-steps.md](compass-demo-steps.md) hướng dẫn kết nối local, Documents/Filter/Find, mở nested fields, tìm orderCode từ Web, Aggregations → Text → paste array → Run, Indexes → Explain/Raw Output và shell read-only forced plans. Các bước editor/explain dựa trên [hướng dẫn MongoDB Compass](https://www.mongodb.com/docs/compass/create-agg-pipeline/) và [Explain chính thức](https://www.mongodb.com/docs/compass/query-plan/); cần xác nhận trên bản Compass của máy bảo vệ.

Ba SKU seed đã đọc thật: `DEMO-ELE-001` (ram/storage/chip), `DEMO-FAS-001` (sizes/colors/material), **`DEMO-HOM-019` Hand Blender** (power/capacity/voltage). Cùng sáu field name/price/categoryId/productType/stock/images, collection products và validator v1. Không dùng giường DEMO-HOM-001 để minh họa power/voltage.

## 3. Accounts, fixture và integrity

Customer **defense07c@example.test**, Admin **admin@example.test** đều login qua API thành công. Password chỉ local private tại `.local/phase07c/demo-credentials.md`; recovery và lệnh prepare/check/restore ở [checklist](pre-demo-checklist.md). Customer có phone/địa chỉ tổng hợp; dùng hai browser/profile và login ngay trước demo. Frontend source hiện lưu token trong sessionStorage, có phục hồi khi reload; vẫn login lại khi hết hạn/401.

Hai Category và Product fixture riêng giúp checkout không tăng version hay thay stock của seed. Điện thoại `DEFENSE-07C-ELE`, slug `defense-07c-dien-thoai`, giá A **10.000.000**, B **12.000.000**, stock 20; áo `DEFENSE-07C-FAS`, slug `defense-07c-ao-thun`, giá **200.000**, stock 20, M/Black. Cả hai images rỗng, không cần URL ảnh để demo core.

| Collection | Baseline trước 07C | Sau fixture/rehearsal |
| --- | ---: | ---: |
| users | 41 | 42 |
| categories | 3 | 5 |
| products | 180 | 182 |
| carts | 0 | 1, items rỗng |
| orders | 100 | 101 |
| payment_attempts | 30 | 30 |

41 User baseline gồm 40 seed và User được người dùng giữ tại 06AB. Dữ liệu gốc/documents/options/validators/indexes có fingerprint giữ nguyên khi loại **đúng fixture sở hữu** qua IDs/User ID trong journal; toàn dev fingerprint có thay đổi hợp lệ do fixture mới, không tuyên bố dev bất biến toàn phiên. Snapshot baseline trước prepare và exact fixture IDs nằm trong evidence public, password không có trong đó.

Order rehearsal **ORD-6AC7A53587E692850A155388** được tạo bằng **real HTTP API, chưa phải Web checkout**. Hai item quantity 1; subtotal 10.200.000, ship 30.000, total 10.230.000. API replay cùng key trả cùng ID; Product đổi A→B và Order/items/customer/address vẫn giữ nguyên. Order sau đó CANCELLED/UNPAID qua API, tồn mỗi Product trở về 20, giá điện thoại về A và Cart rỗng. Không sửa timestamps, snapshot hoặc hoàn kho thủ công.

Helper restore chỉ hủy COD PENDING/CONFIRMED của Customer riêng, restore riêng price và clear Cart; giữ mọi document/lịch sử. Bản 10 phút hoàn thành COD thì giữ Order COMPLETED, doanh thu và mỗi stock 19 sau một lần bán quantity 1 mỗi Product; không giả rollback terminal Order.

## 4–5. Kịch bản 5 phút và 10 phút

[demo-script-5min.md](demo-script-5min.md) có 8 đoạn liên tục từ 0:00 đến 5:00 và lời giải thích snapshot khoảng 30 giây. [demo-script-10min.md](demo-script-10min.md) có 12 đoạn đến 10:00, thêm Admin confirm/ship/complete và revenue tăng đúng merchandise subtotal 10.200.000/units +2, không cộng ship. Timeline là ngân sách rehearsal, chưa phải thời gian người thật đã đo.

## 6. Phân công ba sinh viên

| Người | Nói và thao tác | Điểm chuyển lời |
| --- | --- | --- |
| SV1 | Schema, CRUD, Order snapshot, transaction checkout; điều khiển Customer/Admin nghiệp vụ | Sau giới thiệu SV3; xong snapshot chuyển SV3 mở Dashboard/SV2 giải thích |
| SV2 | Pipeline/stages, metric, compound index/field order, performance/evidence limits | Nhận lời ở Dashboard, kết thúc index chuyển SV3 tổng kết |
| SV3 | Dummy Data, Compass, frontend/Dashboard, giữ thời gian, offline/evidence | Mở và kết thúc; điều khiển Compass xuyên suốt |

## 7. Bộ phản biện

[defense-qa.md](defense-qa.md) có **20 câu**, mỗi đáp án 2–5 câu. Bao phủ MongoDB/SQL, polymorphic, collection chung, embed/reference, snapshot, unwind/group, compound/prefix/field order, COLLSCAN/IXSCAN, transaction/rs0/concurrency, reference integrity, frontend revenue, money/date và VNPAY/offline.

## 8. Offline fallback

COD/API/MongoDB đều local; frontend/dependencies đã có, không tải package trong phòng. Browser fixture detail đã quan sát được tên/giá/stock/attributes và “Hình ảnh không có sẵn” với images rỗng. Ảnh seed chỉ là phụ trợ/cache; không hứa URL ngoài luôn online, không thay architecture/assets.

Lưu trước pipeline/raw explain/benchmark summary và Order rehearsal làm standby; gọi đúng là evidence API/seed nếu live lỗi. Nếu Compass không thao tác được, mở raw artifacts để giải thích nhưng không gọi đó là Compass live PASS. Chưa thực hiện thử ngắt internet toàn hệ thống trong 07C; gate offline và rehearsal người thật vẫn có trong checklist.

## 9. VNPAY demo status

**LIVE SANDBOX BLOCKED**, VNPAY_ENABLED=false trên môi trường máy. Backend integration đã implement và có 102 Payment tests lịch sử; thiếu merchant VNP_* và public registered IPN, chưa chứng minh real redirect/bank/IPN. Không giả giao dịch live; dùng COD làm luồng bắt buộc, VNPAY chỉ trình bày code/tests và Return readonly/IPN authoritative khi được hỏi.

## 10. Checks thực chạy và evidence index

| Kiểm tra 07C | Kết quả / giới hạn |
| --- | --- |
| Prepare qua API | 12 HTTP checks PASS, fixtures và credentials private sẵn sàng |
| API snapshot rehearsal | 20 HTTP checks PASS, COD/replay/A→B/snapshot/cancel/stock restore |
| Readiness check cuối | 3 HTTP checks PASS + DB assertions phone/address/price/stock/Cart/original digest |
| Canonical MongoDB pipelines | Top5/revenue-day/revenue-month/sales-summary PASS; seed fixed range doanh thu **10.103.259.022**, units **434**, Top5 5 rows |
| Dashboard hiện tại | Admin login + 5 endpoint summary/revenue/top-products/category-revenue/order-status đều 200; query checks không đổi dev fingerprint |
| Dev explain | Natural COLLSCAN 182 docs/0 keys, indexed IXSCAN 10 docs/10 keys, cùng nReturned 10 và ordered IDs; 0–1 ms không phải benchmark latency |
| Replay evidence 07B | Query riêng ecommerce_benchmark: natural 30.000/0, named 20/20, cùng nReturned 20/ordered IDs; không build/drop index, không đo lại latency |
| Browser | Quan sát Product fixture detail/ảnh rỗng thành công; chưa thực hiện đầy đủ checkout/Admin bằng GUI trong 07C |
| Native Compass | Đã mở Compass 1.49.15; capture/input lỗi, chưa kết nối local hoặc chạy document/pipeline/explain trên GUI |

[defense-evidence-index.md](defense-evidence-index.md) tập hợp phase reports, validators/seed, aggregation output, raw performance plans/samples, backend pytest và frontend E2E. **658 backend tests/96 HTTP tại 06AB và 22 FE02 flows/32 Customer flows là evidence lịch sử**, không chạy lại trong docs-only 07C. PHASE07B report xuất hiện trong lúc làm; đã cập nhật kịch bản sang benchmark 30.000/10.000 và replay query read-only, giữ dev 182/10 làm fallback.

Nguồn app/API được so với manifest 141 file đầu phiên: 7 file thay đổi trong workspace chung (`paymentApi.ts`, `AdminProductFormPage.tsx`, `AdminProductsPage.tsx`, `CheckoutPage.tsx`, `OrderDetailPage.tsx`, `PaymentReturnPage.tsx`, `docs/api-contract.md`). 07C không sửa các file này; worker 07A đang kiểm tra hệ thống riêng. Vì vậy không tuyên bố toàn shared source unchanged hoặc gán nghiệm thu app của worker khác cho 07C. Chi tiết current hashes/checks/link audit tại [final receipt](../database/evidence/phase07c-final-verification.json).

## 11. Rủi ro và gate còn lại

Native tool trả `FrameArrived timed out` / `window capture timed out` và `coordinate input geometry is unavailable`; đã thử lại theo hướng dẫn công cụ, không dùng tọa độ cũ. Nhóm cần tự chạy Compass guide và Web COD → đổi giá → Order cũ, đo 5/10 phút và tick checklist; chưa đủ điều kiện gọi live readiness toàn bộ PASS. Không có ảnh/screenshot Compass thành công được dùng làm bằng chứng.

MongoDB dừng bất ngờ trong final checks (chưa xác định nguyên nhân); đã dùng start-mongo.ps1 của project khởi động lại **cùng dữ liệu trên đĩa**, rs0 PRIMARY và tất cả checks sau đó PASS, original digest giữ nguyên. Helper check từng lỗi đọc address `id` thay vì BSON `_id`, đã sửa helper và chạy lại PASS; application không đổi. Cần check health/PRIMARY sát giờ, bảo đảm các worker không cùng thao tác Customer fixture, không reset để xử lý lỗi.

Các KPI cần cùng from/to khi đối chiếu, seed window khác range live; Customers hiện toàn cục 41, không dùng số 39 seed làm current count. Fixture/history giữ lại có chủ đích để lần demo sau dùng; không có housekeeping pending cần tự xóa. VNPAY live là giới hạn đã ghi nhận. **Dừng tại checkpoint để review; gate GUI/timing/offline chưa ký.**
