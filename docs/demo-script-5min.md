# Kịch bản bảo vệ 5 phút — ưu tiên barem

**Cập nhật14/10/2026:** lỗi form ảnh rỗng đã được sửa. Hai fixture hiện có ảnh CDN; rehearsal mới xác minh Web đổi giá giữ ảnh/attributes, Order giữ snapshot và COD/cancel trên clone test. Xem [review mới](render-deployment-review.md). Compass GUI, thời gian người thật và ngắt mạng OS vẫn MANUAL PENDING; [report12/10](phase-07d-final-rehearsal.md) giữ lịch sử trước sửa.

Chuẩn bị: Customer/Admin login ở hai browser/profile riêng; điện thoại fixture giá A = 10 triệu, áo 200 nghìn, Cart trống; Compass local mở sẵn collection và pipeline. Mật khẩu ở ignored `.local/phase07c/demo-credentials.md`, không chiếu file này. Theo [checklist](pre-demo-checklist.md) và [Compass từng click](compass-demo-steps.md); các gate GUI cần rehearsal trước khi gọi live defense PASS.

| Thời gian | Ai nói / ai thao tác | Màn hình và lời nói |
| --- | --- | --- |
| 0:00–0:15 | SV3 nói và điều khiển | “NovaMart dùng MongoDB local rs0. Nhóm chứng minh bốn mục: schema đa hình, snapshot, aggregation và index.” Nêu seed 180 Product/3 ngành/100 Order, fixture 07C riêng. |
| 0:15–0:55 | SV1 nói, SV3 Compass | Filter ba seed SKU: DEMO-ELE-001, DEMO-FAS-001, DEMO-HOM-019. Chỉ field chung và mở attributes ram/storage/chip, sizes/colors/material, power/capacity/voltage. “Một collection products, thuộc tính thay đổi theo productType và được validator kiểm tra.” |
| 0:55–1:35 | SV1 Customer Web, SV3 ghi mã | Mở điện thoại `/products/defense-07c-dien-thoai`, thêm 1; áo `/products/defense-07c-ao-thun`, chọn M/Black, thêm 1. Cart → Checkout → địa chỉ Demo → COD → đọc quote → Đặt hàng. Copy orderCode thật; nếu rehearsal thấy thiếu thời gian, chuẩn bị Cart hai item trước timer, vẫn checkout sống. |
| 1:35–2:35 | SV1 nói, SV3 Compass/Admin | Filter đúng Order mới; chỉ priceAtPurchase A, item/category/customer/address embedded. Admin đổi **chỉ price** điện thoại 10 → 12 triệu; reload Product và Order, Order vẫn 10 triệu. Đọc đoạn 30 giây dưới đây; giữ Order PENDING trong bản 5 phút. |
| 2:35–3:20 | SV3 Dashboard, SV2 nói | `/admin/dashboard`: 30 ngày qua → Theo ngày → Làm mới. Chỉ 4 KPI và revenue/Top5/category/status. “MongoDB group/sum Orders COMPLETED+PAID theo completedAt; doanh thu không gồm shipping. Đơn COD mới chưa qualify. React hiển thị response API.” |
| 3:20–4:00 | SV2 nói, SV3 Compass | orders → Aggregations → Text → paste Top5 → Run. Chỉ match/unwind/group/sort/limit và pre-sort/project phụ trợ; mỗi item được gom theo productId, không lấy giá hiện tại. Nếu dùng file seed standby, nói range khác Dashboard 30 ngày; muốn đối chiếu phải bind cùng from/to. |
| 4:00–4:45 | SV2 nói, SV3 Explain | Chuyển **ecommerce_benchmark**, products, dùng query/shell 07B trong guide. Natural COLLSCAN đọc 30.000 docs/0 keys; named IXSCAN đọc 20 docs/20 keys; cùng 20 kết quả. “Equality trước, rồi price/_id; đây là selector, không phải latency toàn API.” Dự phòng dev query: 182 → 10 docs, cùng 10 kết quả, 0–1 ms không chứng minh tốc độ. |
| 4:45–5:00 | SV3 kết thúc | “Bốn bằng chứng là schema, snapshot lịch sử, aggregation trong MongoDB và index thực. COD local; VNPAY đã có integration/tests, live merchant/IPN chưa cấu hình.” Sau timer mới restore giá và hủy đơn thử theo checklist. |

## Đoạn snapshot 30 giây — SV1

“Nếu chỉ lưu productId rồi lấy giá hiện tại, hóa đơn cũ sẽ thay đổi khi Admin sửa giá hoặc thông tin sản phẩm. Vì vậy lúc checkout, nhóm nhúng vào Order bản chụp giá, tên, SKU, thuộc tính, ngành hàng, khách và địa chỉ. Product ID vẫn giữ để truy vết và xử lý tồn kho, còn hiển thị hóa đơn dùng snapshot. Giá Product từ 10 lên 12 triệu nhưng Order vẫn 10 triệu, nên lịch sử mua hàng không bị sửa ngược.”

## Chuyển lời giữa ba người

SV3 giới thiệu → “SV1 trình bày mô hình và checkout”; SV1 xong snapshot → “SV3 mở Dashboard, SV2 giải thích cách tính”; SV2 xong index → “SV3 tổng kết dữ liệu và vận hành”. SV3 điều khiển Compass xuyên suốt để tránh đổi người cầm chuột. Không nhập password, tạo Category, cài phần mềm hoặc tìm file giữa 5 phút.

## Khi còn ít thời gian hoặc lỗi live

Giữ ba Product và checkout từ Cart đã chuẩn bị; snapshot A → B là trọng tâm. Mở sẵn Dashboard/pipeline và ba metric explain. Order API rehearsal/seed chỉ dùng với nhãn nguồn trung thực nếu Web lỗi; không gọi evidence cũ là checkout vừa thành công. Khi 401, login lại; frontend hiện phục hồi token từ sessionStorage khi reload, vẫn nên giữ hai phiên Customer/Admin riêng.
