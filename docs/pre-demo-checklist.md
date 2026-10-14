# Checklist trước buổi bảo vệ

**Cập nhật14/10/2026:** đã sửa lỗi form ảnh rỗng; Admin Web đổi giá10→12triệu, snapshot giữ10 và restoreA PASS trên clone test. [Review bản sửa](phase-07d-price-editor-fix-review.md). Live fixture vẫnA/stock20/Cart rỗng,dev/benchmark fingerprint unchanged. Browser external-deny/COD PASS scoped; Compass/timing người thật/offlineOS vẫn cần nhóm tick sau khi thực hiện.

Ngày chuẩn bị 08/10/2026. Tick sau khi đã thao tác trên đúng máy bảo vệ; các ô GUI để trống vì phiên 07C chưa điều khiển được Compass. Dùng [readiness report](phase-07c-demo-readiness.md), [5 phút](demo-script-5min.md), [10 phút](demo-script-10min.md) và [Compass guide](compass-demo-steps.md).

## Trước khi vào phòng

- [ ] MongoDB local đang chạy; `rs0` PRIMARY; URI `mongodb://localhost:27017/?replicaSet=rs0`, database `ecommerce_dev`.
- [ ] Backend port 5001 trả health 200; frontend port 5173 mở được và proxy `/api/v1` tới 5001. Không chọn frontend 5174/server test của worker 07A.
- [ ] Đã lưu source/dependencies trên máy; không cần tải package lúc mất mạng. Không đổi port mà quên proxy, không tự khởi chạy expiry worker trên seed.
- [ ] Compass kết nối local, chọn đúng DB; ba Product/filter, Order, Aggregations và Explain đã chạy thử theo guide.
- [ ] Seed chính vẫn 180 Product/60 mỗi ngành, 100 Order/2–5 items và 40 User. Live DB có thêm một User được giữ ở 06AB và fixtures 07C; không ép live counts về seed bằng reset.
- [ ] Chạy helper `check`; Customer/Admin login thành công, có địa chỉ/phone, Cart trống, điện thoại giá A=10 triệu và mỗi fixture đủ ít nhất một đơn vị.
- [ ] Customer `defense07c@example.test` và Admin `admin@example.test` login ở hai browser/profile riêng ngay trước demo. Frontend hiện giữ token trong sessionStorage và phục hồi khi reload; token vẫn có thể hết hạn, khi 401 hãy login lại.
- [ ] Private credentials/fixture journal đã backup cục bộ; không chiếu `.env` hay `.local/phase07c/demo-credentials.md` lên màn hình bảo vệ.
- [ ] Mở sẵn hai Product fixture; áo chọn M/Black, quantity 1 mỗi Product. Cart không chứa seed Product để checkout chỉ thay đổi hai category/product riêng.
- [ ] Dashboard có dữ liệu: 4 KPI, revenue, Top5, category revenue, order status; chọn 30 ngày qua, Theo ngày và Làm mới. Chuẩn bị Network từ/to nếu muốn đối chiếu Compass cùng window.
- [ ] Hai fixture hiện có ảnh CDN; kiểm tra ảnh khi có mạng, cache nếu cần. Rehearsal14/10 xác minh ảnh render và giữ nguyên khi đổi giá. Khi chặn mạng, ảnh CDN có thể không tải; schema/snapshot/COD không phụ thuộc URL ảnh.
- [ ] Benchmark DB `ecommerce_benchmark` vẫn có 30.000 Product/10.000 Order; mở sẵn query và raw plans 07B. Không dùng benchmark cho checkout hoặc đăng nhập.
- [ ] Đã thử COD khi ngắt internet nhưng vẫn giữ MongoDB/backend/frontend local chạy. Rehearsal14/10 cold-cache chặn network ngoài loopback ở browser vẫn COD/cancel PASS; chưa thay thế một lần ngắt mạng toàn hệ thống.
- [ ] Ba SV rehearsal bằng đồng hồ: bản 5 phút ưu tiên, bản 10 phút có lifecycle completion; mỗi người nói đúng phần đã phân công.

## Lệnh chuẩn bị từ workspace root

Các helper dùng runtime đã có, không cài thêm dependency. Chạy tuần tự khi không có người thao tác cùng Customer fixture.

```powershell
./.venv/Scripts/python.exe -X utf8 scripts/demo/prepare_defense.py prepare
./.venv/Scripts/python.exe -X utf8 scripts/demo/prepare_defense.py check
./.venv/Scripts/python.exe -X utf8 scripts/demo/verify_queries.py
```

`prepare` reuse fixture được journal sở hữu, không tạo thêm mỗi lần. `check` đọc readiness và đối chiếu dữ liệu gốc; `verify_queries` chạy aggregation/explain và 5 Dashboard API, không ghi DB. Nếu fingerprint gốc đổi, dừng để đối chiếu write bên ngoài; không reset/reseed hoặc ghi đè baseline để làm check pass.

Nếu service chưa chạy, theo [backend setup](backend-setup.md) và [MongoDB setup](mongodb-setup.md). Backend: `./.venv/Scripts/python.exe -X utf8 backend/run.py`; frontend trong thư mục `frontend`: `npm run dev -- --host 127.0.0.1 --port 5173 --strictPort`. Không khởi chạy bản thứ hai nếu port đã có đúng ứng dụng.

## Tài khoản và recovery

Mật khẩu Customer riêng được sinh khi prepare, Admin lấy từ `SEED_DEMO_PASSWORD` đã xác minh khớp hash. Hai mật khẩu lưu trong ignored `.local/phase07c/demo-credentials.md`; `.local/phase07c/fixture.json` là journal private, không đưa vào evidence công khai. Đây là tài khoản demo local, không có production secret.

Nếu còn journal nhưng mất note, chạy lại `prepare` để tạo note. Nếu mất cả journal/password, không xóa Customer hay giả nhận ownership: dùng Web đăng ký email demo mới rồi thêm phone/địa chỉ, ghi lại ID và password private, chỉ dùng Product fixture đã đối chiếu. Admin mất mật khẩu phải khôi phục từ bản `.env` private đã backup; không reset/reseed toàn DB hay thay hash seed trong Compass.

## Trong và sau demo

Copy orderCode thực từ Web; không dùng mã API rehearsal thay cho đơn vừa đặt. Nếu quote hết hạn/giá đổi, lấy quote mới; nếu version conflict, refetch rồi thao tác tiếp. Không sửa snapshot/timestamps/status trong Compass để cứu demo.

Sau bản 5 phút, hủy Order riêng còn PENDING/CONFIRMED qua Web và đổi riêng giá điện thoại về A, hoặc chạy:

```powershell
./.venv/Scripts/python.exe -X utf8 scripts/demo/prepare_defense.py restore
./.venv/Scripts/python.exe -X utf8 scripts/demo/prepare_defense.py check
```

Helper cancel đúng Customer fixture, restore riêng price và clear Cart của Customer; không xóa document hoặc cộng stock thủ công. Sau bản 10 phút, Order COMPLETED giữ nguyên lịch sử/revenue và mỗi Product đã bán quantity 1 nên stock từ 20 còn 19 nếu chưa có lần bán khác. Restore giá không đảo giao dịch đã hoàn thành; lần bảo vệ tiếp theo kiểm tra tồn thực.

## Gate cần ký sau rehearsal thủ công

Người kiểm tra: ______; ngày/giờ: ______; bản 5 phút thực tế: ______; bản 10 phút: ______. Compass Documents/Order/Text pipeline/Explain: ______; Web COD → đổi giá → Order cũ: ______; offline COD: ______. Khi chưa điền các gate này, report chỉ xác nhận bộ chuẩn bị/API/query, chưa xác nhận live defense toàn bộ PASS.
