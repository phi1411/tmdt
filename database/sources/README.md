# Nguồn catalog seed

Cache194 Product từ [DummyJSON Products](https://dummyjson.com/docs/products); repository [Ovi/DummyJSON](https://github.com/Ovi/DummyJSON). Checksum/date/mapping tại [provenance.json](provenance.json). Seed từ chối cache khác checksum; không cần API sống để chạy lại.

Normalize119 nguồn phù hợp:38 Electronics,46 Fashion,35 Home/Household. Tạo180 Product,60 mỗi ngành;61 biến thể bổ sung ghi rõ tên demo. Map field chung/ảnh/mô tả/brand vào schema nội bộ, dùng specification biên soạn theo từng nhóm, dimensions và nguồn ID trong attributes. Không import raw reviews/rating/PII. Giá dùng fixed25.000 cho dữ liệu giả lập VND, không phải tỷ giá hiện tại. Một Product một SKU/price/poolstock theo thiết kế đã khóa.

CDN image URLs được giữ nguyên; không tải media hàng loạt, không dùng localhost. Phần mềm repository MIT; project không chuyển quyền ảnh bên thứ ba. Mục đích là fixture đồ án; không coi spec demo là thông số thương mại đã xác minh.
