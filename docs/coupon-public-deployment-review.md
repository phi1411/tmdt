# Triển khai mã giảm giá và dữ liệu demo — 21/10/2026

## Kết quả

Backend và frontend Render đều Live trên commit `b5f3daef9d6d591042fc7f2e8569540182e6cf0f`. Website: https://novamart-web.onrender.com. Commit `bc9b49a` trước đó làm rõ giá theo phân loại cũng đã có trong bản này.

| Dịch vụ | Deploy | Kết quả |
| --- | --- | --- |
| novamart-api | dep-dbc4h7vavr4c73er5m60 | Live, 46,2 giây |
| novamart-web | dep-dbc4i3jncjis738bf5a0 | Live, 32,3 giây |

## Chính sách đang áp dụng

| Mã | Tiền hàng tối thiểu | Tỷ lệ | Giảm tối đa |
| --- | ---: | ---: | ---: |
| DEMO10 | 100.000đ | 10% | 20.000đ |
| DEMO15 | 300.000đ | 15% | 40.000đ |
| NOVA25 | 500.000đ | 25% | 50.000đ |

Một mã mỗi đơn; không giảm phí giao hàng. Backend quyết định tiền giảm. Chưa có giá vốn nên giới hạn này không phải kiểm soát lãi thực tế. Không tạo collection quản lý chiến dịch: chính sách ở `backend/app/services/coupon_service.py`, mã được chọn lưu ở `carts.couponCode`, chính sách tại thời điểm mua nhúng ở `orders.coupon`.

## Kiểm tra đã thực hiện

- Full backend: **746 passed, 0 failures, 0 errors, 0 skipped**, JUnit 214,801 giây. Lần khởi chạy đầu chưa chạy được do MongoDB local đang dừng; đã khởi động lại đúng storage rs0 và chạy lại toàn bộ thành công.
- Frontend strict TypeScript và production build PASS; 10 kiểm thử frontend PASS. Còn cảnh báo kích thước chunk trên 500 kB.
- 24 kiểm tra public HTTP và MongoDB PASS: health 200, CORS đúng origin, coupon route trả 401 cho Guest, Catalog 200; 7 validators khớp canonical và không có document vi phạm; reference Cart→User, Order→User, Attempt→Order không mồ côi.
- Cart thật trên website: đăng nhập khách demo, hiển thị đủ ba chính sách; NOVA25 áp dụng cho tiền hàng 560.000đ, giảm 50.000đ, còn 510.000đ trước phí ship. Console không có error/warn trong phạm vi tab kiểm tra. Ảnh tại `backend/evidence/coupon-public-cart.png`.
- Quote COD và VNPAY cùng tổng sau giảm cho cả ba mã. Chưa thực hiện giao dịch ngân hàng/OTP mới có coupon; không gán kết quả Sandbox cũ cho phạm vi này.

## Dữ liệu giữ lại theo yêu cầu

Tạo qua API: một Customer demo, một Cart và ba COD Orders. Mỗi Order đã hủy hợp lệ, trạng thái CANCELLED/UNPAID; kho Product/SKU hoàn lại đúng số ban đầu. Không có Payment Attempt gắn với các đơn này và không tăng doanh thu.

| Mã | Order | Tiền hàng | Giảm | Ship | Tổng |
| --- | --- | ---: | ---: | ---: | ---: |
| DEMO10 | ORD-6AD84918CC278E2C97CE5DF4 | 160.000 | 16.000 | 30.000 | 174.000 |
| DEMO15 | ORD-6AD8491BCC278E2C97CE5DF6 | 420.000 | 40.000 | 30.000 | 410.000 |
| NOVA25 | ORD-6AD8491ECC278E2C97CE5DF8 | 560.000 | 50.000 | 30.000 | 540.000 |

Cart của Customer `6ad84914cc278e2c97ce5df1` giữ `couponCode: NOVA25`. Thông tin đăng nhập và backup chỉ ở `.local/coupon-demo`, không commit.

Trong Compass, chọn `novamart_demo.orders`, nhập:

```json
{"coupon.code":{"$in":["DEMO10","DEMO15","NOVA25"]}}
```

Để chỉ đúng ba đơn mới, có thể lọc thêm `userId: ObjectId("6ad84914cc278e2c97ce5df1")`. Mở `coupon`, `discount`, `items.discountAllocated`, `subtotal`, `shippingFee`, `total` để giải thích snapshot và cách tính.

## Phạm vi toàn vẹn dữ liệu

Migration chỉ mở rộng hai validators Cart/Order; fingerprint documents/indexes trước và sau migration bằng nhau. Sau tạo demo, hash toàn bộ Orders cũ vẫn khớp; tổng discountAllocated bằng discount, tiền BSON long và công thức tổng tiền hợp lệ. Giữ fixture mới có chủ đích, không reset hoặc reseed. Version/thời gian của Product/Category chịu ảnh hưởng bình thường của luồng đặt/hủy; không tuyên bố toàn corpus bất biến sau khi chủ động tạo dữ liệu.

Counts sau demo: 46 Users, 3 Categories, 184 Products, 5 Carts, 109 Orders, 34 Payment Attempts, 215 Reviews. Đây là snapshot lúc kiểm tra, có dữ liệu của các phiên trước.

Không sửa PPTX/SRS, không đổi plan Render, không đưa ba script review chưa được review vào commit. Không chỉnh ô khuyến mại thuộc giao diện nhà cung cấp VNPAY.

## Evidence

- `backend/evidence/coupon-deploy-pytest.xml`
- `backend/evidence/coupon-deploy-atlas-schema.json`
- `backend/evidence/coupon-public-demo.json`
- `backend/evidence/coupon-public-deployment.json`
- `backend/evidence/coupon-public-cart.png`
