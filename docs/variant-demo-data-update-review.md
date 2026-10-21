# Cập nhật dữ liệu giá theo phân loại — 21/10/2026

Người dùng yêu cầu chuẩn bị dữ liệu demo trên DB. Đích: Atlas `novamart_demo` đang phục vụ website Render; không sửa application logic hoặc DB local.

- Đã cập nhật35Product thời trang có size/màu legacy sang tierVariations/skus, qua Admin PATCH có expectedVersion/transaction và kiểm tra SKU_IN_USE.
- Giữ1Product demo matrix sẵn có M100k/XL120k; tổng36Product hiện có giá theo SKU.
- Bỏ qua26Product đang có PENDING/CONFIRMED/SHIPPING Orders giữ kho. Không hủy đơn hoặc đổi identity SKU của chúng.
- Giá gốc giữ nguyên; mức chênh lấy5% theo bậc size và2% theo bậc màu, phần chênh làm tròn lên1.000đ. Đây là giá demo theo người dùng giao, không phải dữ liệu giá vốn/lợi nhuận.
- Tổng stock từngProduct giữ nguyên, chia đều vào các tổ hợp và phân bổ phần dư theo thứ tự. Rootprice vẫn minSKUprice; giá SKU là BSONlong.
- Orders fullhash trước/sau khớp, tổngdocuments từngcollection không đổi, validators/indexes giữ nguyên và invalidProducts0. Protected Product fields đối chiếu từngdocument đều giữ nguyên; chỉ thêmmatrix/version/updatedAt.
- Đã đọc lại Public API3Product và đối chiếu giá với DB. Lần GETdetail đầu dùngid bị404; kiểm tra lại đúng slug PASS, không phát sinh thêmwrites.
- Không reset/reseed, không sửa Orders/reviews, không deploy/commit/push, không chạy lại fulltest cho thao tác data qua API hiện có.

Backup canonical BSON và payload kế hoạch/progress ở `.local/variant-pricing/20261020T180523Z/` (private/ignored). Receipt không có credential: `backend/evidence/variant-demo-data-update.json`.

Ví dụ demo: https://novamart-web.onrender.com/products/gigabyte-aorus-men-tshirt-108
Compass cần kết nối Atlas/novamart_demo; dữ liệu local ecommerce_dev không được đồng bộ trong lượt này.
