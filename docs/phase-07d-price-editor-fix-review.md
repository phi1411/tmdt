# Follow-up PHASE07D — sửa form Product ảnh rỗng

Ngày14/10/2026. **WEB PRICE EDITOR FIX PASS; functional rehearsal PASS. PHASE07D FINAL PASS vẫn chờ các gate thủ công.**

## Vấn đề và sửa tối thiểu

Rehearsal12/10 phát hiện form Admin không lưu được Product fixture07C có `images=[]`, dù contract/validator cho phép0–8ảnh. Luồng đổi giá bằng Web bị chặn; snapshot chỉ được chứng minh qua API fallback ở lần đó.

Sửa duy nhất application file `frontend/src/pages/AdminProductFormPage.tsx`:

- Cho textarea ảnh trống và gửi `images:[]` khi tạo/sửa; bỏ dấu bắt buộc và cập nhật hướng dẫn0–8ảnh.
- Chỉ loại các dòng trắng, không âm thầm loại URL sai. Backend canonical validation vẫn xử lý URL schemes/host/bounds và trả422.
- Không đổi API/backend/schema/index/collection, không thêm ảnh vào fixture để né lỗi. Attributes preservation và expectedVersion vẫn dùng implementation hiện hữu.

Feature doc Admin Products đã cập nhật cùng behavior. Không refactor hoặc thêm feature.

## Kiểm chứng mới

Production build thực: `npm run build` = TypeScript strict + Vite, exit0,2237modules,15.58s; JS868.37kB/gzip237.16kB, CSS41.49kB/gzip7.48kB. Còn cảnh báo chunk lớn hơn500kB.

Browser Edge headless, production bundle5174 → same-source Flask5002 → owned ecommerce_test/rs0 thật. Dữ liệu clone chính xác từ dev, không mock API và không ghi dev. Runner follow-up dùng tên riêng, giữ nguyên evidence07D12/10.

**11 checks PASS /0FAIL**,147HTTP:146phản hồi2xx và đúng1phản hồi422 cố ý cho URL ảnh sai;0page errors. Bao gồm:

1. Customer/Admin login, health và Cart readiness.
2. Kiểm tra không có interrupted Order cần recovery trên clone mới.
3. Nhập URL ảnh sai qua Web → PATCH422, payload vẫn chứa input sai; Product GET trước/sau deep-equal.
4. Render3ProductType ELECTRONICS/FASHION/HOME_APPLIANCE.
5. Hai Product fixture → Cart → CODOrder,2items/quantity1,subtotal10.200.000/ship30.000/total10.230.000.
6. **Admin Web edit giá10.000.000→12.000.000 với images=[]**, nhận PATCH200, stock giữ nguyên; existing attributes giữ nguyên. Order items/customerSnapshot/shippingAddress deep-equal; Web Order vẫn hiện10.000.000. **Không có API fallback cho mutation.**
7. Customer cancel hợp lệ và Admin Web restore giáA; stock clone20mỗi Product, Cart rỗng.
8. Đơn COD thứ hai và snapshotA→B bằng Web.
9. Admin confirm→ship→complete,COMPLETED/PAID/completedAt; revenue+10.200.000,units+2,không gồm ship;stock19mỗi Product.
10. Dashboard đủ5report200, chart SVG render; Web restore giáA.
11. Browser cold-cache chặn toàn bộ HTTP(S) ngoài loopback: login/COD/Order/cancel PASS. **Không ngắt network adapter của máy hoặc chặn mạng backend**, không suy thành offline OS PASS.

Visual chart check độc lập sau animation:5pie sectors/2area paths/5bars ở dataset/window lần này,desktop1440không overflow. Số bar phụ thuộc status có dữ liệu; không buộc bằng6của lần chạy lịch sử.

Full backend suite chạy lại trong follow-up: **658passed/0failed/0errors/0skipped**,108.085sJUnit (console108.09s). [JUnit mới](../backend/evidence/phase07d-fix-pytest.xml), [receipt tổng hợp](../database/evidence/phase07d-fix-summary.json). Sau pytest,6testcollections vẫn rỗng và dev/benchmark fingerprint vẫn trùng baseline. Backend application/tests không sửa;658PASS của07A là evidence lịch sử riêng, không thay cho lần chạy mới.

## Database integrity và cleanup

Listener test5002/5174 đã dừng trước cleanup. Xóa đúng clone IDs/Order-Cart-Attempt thuộc Customer fixture theo journal trong transaction snapshot/majority;6collections ecommerce_test rỗng. Không reset/reseed/drop, không hủy hoặc đảo một Order COMPLETED live.

Full dev fingerprint trước/sau trùng, kể cả User cần giữ và fixture07C; full benchmark fingerprint cũng trùng. Dev42Users/5Categories/182Products/1Cart/101Orders/30Attempts;fixture07CpriceA/stock20/Cart rỗng.6validators/14declared+6_id_indexes và0orphan/reference mismatch. Protected source/canonical DB/API/evidence07B/07C hashes không đổi trong rehearsal; baseline được chụp sau sửa form đã được người dùng giao.

## Compass và gate còn lại

Đã thử lại Computer Use trên Compass1.52.0: mở được ứng dụng và đọc accessibility Welcome. Nút Add new connection không thao tác được: `coordinate input geometry is unavailable`; refresh selection/activate/reobserve và thử lại một lần vẫn cùng lỗi. Không sửa connection Atlas đã có, không gửi query tới Atlas, không đánh dấu GUI PASS. Lỗi thuộc khả năng điều khiển native trong phiên, không phải bằng chứng MongoDB/API lỗi.

Còn cần nhóm thực hiện:

- Compass local Documents3ngành → Order snapshot → Text aggregation Run → Explain, lưu ảnh theo mục13 của [review07D](phase-07d-final-rehearsal.md).
- Ba sinh viên rehearsal và ghi thời gian thực5/10phút.
- Thử ngắt internet thật trên máy bảo vệ, giữ services local rồi chạy COD; kết nối lại sau thử.
- Chốt báo cáo tổng hợp/slide nếu chưa có ngoài repository.

VNPAY LIVE SANDBOX vẫn BLOCKED thiếu merchant/publicIPN; không tuyên bố thanh toán provider thật PASS. Không đổi network settings, commit/push hoặc bắt đầu feature khác.

## Evidence

- [Browser11checks/HTTP147/snapshot](../database/evidence/phase07d-fix-browser.json), [chart visual](../database/evidence/phase07d-fix-chart-visual.json).
- [Environment/query preflight](../database/evidence/phase07d-fix-environment.json), [query/explain](../database/evidence/phase07d-fix-queries.json), [test outcomes](../database/evidence/phase07d-fix-test-outcomes.json), [exact cleanup/integrity](../database/evidence/phase07d-fix-integrity.json).
- [Snapshot sau Web edit](../database/evidence/phase07d-fix-browser/snapshot-A-after-B.png); ảnh form lưu thành công `admin-empty-image-price-saved-12000000.png` cùng thư mục.
- Helpers `scripts/demo/verify_final_rehearsal_fix.py`, `frontend/tests/phase07d-fix-rehearsal.mjs`, `phase07d-fix-chart-visual.mjs`. Chạy prepare→serve/preview→browser/charts→stop listeners→cleanup khi testDBrỗng và đúng ownership; không overwrite journal của phiên chưa cleanup.

**Đóng lỗi chặn Web price editor của07D. Các gate GUI/timing/offlineOS vẫn MANUAL PENDING; dừng review.**
