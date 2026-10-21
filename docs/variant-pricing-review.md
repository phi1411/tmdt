# Giá theo phân loại — kiểm tra ngày21/10/2026

## Yêu cầu và hiện trạng

Người dùng muốn các lựa chọn như M/XL hoặc128GB/256GB có giá khác nhau và Admin nhập giá từng loại khi tạo sản phẩm. Cơ chế này đã được triển khai theo ADR013; không cần đổi thiết kế MongoDB hoặc tách mỗi loại thành Product riêng.

Trong cùng document Product, tierVariations mô tả nhóm/lựa chọn; skus[] giữ skuId, tierIndex, price (long), stock. Product.price là giá nhỏ nhất, Product.stock là tổng kho; backend tự dẫn xuất. attributes là thông số mô tả và không tự suy ra giá. Product legacy chỉ có sizes/colors nhưng chưa có bảng SKU vẫn dùng một giá chung.

## Hoàn thiện trong lượt này

- Làm rõ phần Admin thành “Phân loại, giá bán và tồn kho”, hướng dẫn nhập giá từng dòng và ví dụ M100k/XL120k.
- Khi có bảng SKU, ô giá chung hiện “Giá thấp nhất”, bị khóa và giải thích giá/kho tự tính. Không có bảng thì nhập giá chung như trước.
- Card, Detail và modal chưa chọn loại hiện “Từ” nếu các SKU khác giá; chọn đủ tổ hợp thì modal hiện đúng giá SKU, không có chữ “Từ”. Các SKU đồng giá hoặc sản phẩm legacy không thêm nhãn này.
- Không đổi backend, API, validator/index, giá/thuộc tính sản phẩm thật. Không tự tạo ma trận hoặc gán giá cho182/184sản phẩm đang có. Các thay đổi giao diện lượt này chưa commit/push/deploy.

## Kiểm chứng

| Kiểm tra | Kết quả |
| --- | --- |
| SKU/review hardening + coupon backend regression | 46/46 PASS; real rs0; backend/evidence/variant-pricing-regression.xml |
| FE selection + Payment status unit tests | 10/10 PASS; node --test tests/product-selection.test.mjs tests/payment-status.test.mjs |
| TypeScript + production build | PASS22,86s; vẫn có cảnh báo bundle >500kB |
| Browser với bundle production + Flask + MongoDB thật | 5/5 nhóm,26HTTP thành công,0page errors; backend/evidence/variant-pricing-browser.json |
| Tạo sản phẩm bằng form Admin | M100k/kho5,XL120k/kho7; root100k/kho12; giá SKU lưu Int64 |
| Mua hai loại | Modal hiện đúng100k/120k, Cart subtotal220k, quote/Order total250k gồm ship30k; không dùng coupon |
| Sửa giá bằng form Admin | M110k/XL150k; Order cũ vẫn100k/120k và đúng tên phân loại |
| Responsive | Modal XL375×812 không tràn ngang; ảnh thật trong .local/variant-pricing |
| Cleanup/integrity | Test7collections rỗng, full fingerprint test và development trước/sau khớp; backend/evidence/variant-pricing-browser-integrity.json |

Runner mở rộng scripts/qa/verify_cart_coupons.py --scenario variants dùng fixture Customer/Admin/Category/Product riêng, cleanup đúng IDs/owner. Không reset/reseed. Lần chạy đầu bị kẹt vì trang Admin ở nền; đã dừng đúng tiến trình QA sở hữu, cleanup PASS, chỉnh runner bringToFront/flags rồi chạy lại đủ5nhóm. Không coi lỗi điều khiển này là lỗi nghiệp vụ hoặc claim đã sửa vấn đề browser toàn hệ thống. Full737 backend là lượt20/10 của coupon; không claim đã chạy lại full suite hôm nay khi không đổi backend.

## Trên website public

GET Catalog read-only xác nhận sản phẩm Áo demo SKU — chọn M hoặc XL (slug ao-demo-sku-m-xl) có Size[M,XL], giá[100000,120000] trong cùng Product. Chỉ đọc API, không thay Atlas. Evidence backend/evidence/variant-pricing-public-readonly.json. Tính năng giá theo SKU đã có trên public; phần nhãn/gợi ý mới của lượt này chỉ ở source/local.

## Cách nhập của Admin

1. Admin → Sản phẩm → Thêm sản phẩm (hoặc sửa sản phẩm phù hợp).
2. Trong bảng phân loại, thêm nhóm Kích cỡ, nhập M,XL; hoặc Dung lượng, nhập128GB,256GB.
3. Bấm Cập nhật bảng phân loại; nhập giá và tồn kho cho từng dòng rồi lưu.
4. Khách chọn loại khi thêm giỏ/mua ngay; backend xác minh tổ hợp và lấy giá SKU, Order giữ snapshot lúc đặt.

Không đổi identity/xóa ma trận khi còn Order giữ kho (SKU_IN_USE), nhưng sửa giá/kho của SKU cùng identity được phép theo version. Không gán giá tự động từ RAM/size. Bộ lọc giá hiện dùng Product.price đại diện nhỏ nhất theo contract hiện hành, không tuyên bố lọc theo mọi giá SKU hoặc luôn đạt IXSCAN.
