# Rà soát mã giảm giá tại giỏ hàng — 20/10/2026

## Phạm vi và kết quả

Đã bổ sung mã của Novamart tại Cart theo yêu cầu mới của người dùng. Ô ưu đãi trên trang VNPAY thuộc nhà cung cấp và không được sửa. Chưa commit/push/deploy phiên bản mới lên Render, chưa áp dụng validator mới trên Atlas.

NOVA25: tiền hàng hợp lệ từ 500.000đ giảm 25%, tối đa 50.000đ/đơn. Không giảm phí giao hàng, không cộng dồn mã. Áp dụng các ngành hàng hiện có khi mọi dòng Product/Category/selection/stock hợp lệ. Chưa có cấu hình chọn riêng sản phẩm hoặc quản trị nhiều chiến dịch. Người dùng chọn chỉ giới hạn mức giảm, không thêm giá vốn; không cam kết lãi thực tế. Một đơn 500.000đ tiền hàng + 30.000đ phí giao hàng trả 480.000đ sau giảm.

## Thay đổi

- Cart có ô nhập, áp dụng/bỏ mã; server lưu couponCode với version CAS. Reload/đổi COD–VNPAY giữ mã. Giỏ giảm dưới ngưỡng → discount0, couponIssue và chặn checkout đến khi điều chỉnh/bỏ mã. Clear/checkout bỏ mã cùng items.
- Quote/checkout tự tính và ký cả coupon snapshot, không nhận client discount/total. Revalidate trong transaction; replay không tạo thêm Order hoặc giảm lần nữa.
- Order lưu coupon và discountAllocated từng item, giữ nguyên priceAtPurchase/lineTotal gốc. Phân bổ integer theo tỷ lệ, largest remainder, tổng đúng bằng discount.
- Checkout/Customer detail/Admin detail hiển thị mức giảm thực tế. VNPAY URL/attempt/IPN dùng Order.total sau giảm; không đổi adapter/cổng thanh toán.
- Top Product/Category trừ discountAllocated, legacy thiếu tương đương0. Revenue ngày/tháng/summary vẫn subtotal-discount, chỉ COMPLETED+PAID/completedAt, loại ship.
- Mở rộng validator carts/orders, không thêm collection/index/dependency. Migration cộng thêm, lưu backup riêng, không backfill/reseed/reset. ADR015/requirements/schema/business/API và feature docs đã cập nhật. PPTX/SRS Word/PDF đã bàn giao giữ nguyên; chúng mô tả baseline trước tính năng mới này.

## Kiểm tra thực chạy

| Hạng mục | Kết quả | Evidence |
| --- | --- | --- |
| Full backend | 737 passed, 0 failed/errors/skipped; 227,05s | backend/evidence/cart-coupon-pytest.xml |
| Kiểm thử coupon mới | 23/23; biên 499.999/500.000, cap, sai mã, ACL, CAS, tampering, stale quote, snapshot, replay/cancel, allocation, doanh thu và VNPAY/IPN | backend/tests/test_coupons.py |
| SKU/review/coupon sau đồng bộ test indexes | 56/56, 14,32s | backend/evidence/cart-coupon-focused.xml |
| TypeScript strict | PASS, gồm lần noEmit sau khi bổ sung types | frontend/tsconfig.json |
| Production build | PASS; cảnh báo chunk >500kB hiện hữu | frontend/dist (ignored) |
| Browser production bundle + Flask thật + rs0 thật | 8/8 nhóm, 20HTTP (19 thành công +1 mã sai422 chủ ý), 0 page errors, không lỗi API ngoài dự kiến | backend/evidence/cart-coupon-browser.json |
| Responsive | Desktop1440×1000/Mobile375×812 không tràn ngang, xem ảnh thật | .local/coupon-browser (private/ignored) |
| Cleanup browser | Test7collections trở về rỗng, full test fingerprint khớp trước/sau | backend/evidence/cart-coupon-browser-integrity.json |

Lần full suite đầu: 704 pass/33 setup errors do database test trên máy còn validator Product trước SKU. Đã đồng bộ **chỉ ecommerce_test** với canonical Product/Review validators; chạy lại full737 PASS. Sau đó bổ sung đúng2Review indexes canonical còn thiếu trên test, chạy scoped56 PASS. Đây là sửa môi trường test theo source đã có, không sửa Product/Review application logic hoặc dữ liệu development/Atlas. Các lỗi điều khiển input/đợi nút/toast của runner browser đã được chỉnh trong runner; kết quả bảng trên là lượt cuối hoàn chỉnh.

## Dữ liệu local và migration

Browser rehearsal chỉ ghi fixture sở hữu trong ecommerce_test, xóa đúng IDs/owner sau chạy; không sửa seed. Full development fingerprint trước/sau browser khớp 71274256… (gồm documents/options/indexes, trước migration local).

Sau khi kiểm thử đã áp dụng migration **local ecommerce_dev**: chỉ options/validators carts/orders đổi; toàn bộ documents/indexes6collections trước/sau có cùng hash b89ad5e9…. Counts giữ nguyên42Users/3Categories/182Products/1Cart/101Orders/30Attempts, invalid0. Backup validator cũ trong .local/coupon-migration, evidence backend/evidence/cart-coupon-local-migration.json. Không giả định local corpus6collections bằng Atlas7collections ở các báo cáo trước.

## Cách kiểm tra lại

1. Trên rs0 local thuộc project, chuẩn bị ecommerce_test đúng7canonical validators/16declared+7_id_ indexes, giữ ownership marker. Không seed/reset ecommerce_dev để chạy test.
2. Chạy full pytest tại backend; frontend npm run build.
3. Chạy `.venv/Scripts/python.exe scripts/qa/verify_cart_coupons.py` tại root; cần cổng5000/5175 trống. Runner dùng Edge headless, bundle production và fixture riêng; không cần mật khẩu người dùng, không thanh toán thật. Dọn dữ liệu và dừng listeners trong finally.
4. Tool migration `scripts/db/migrate_cart_coupons.py --database ecommerce_dev` mặc định chỉ kiểm tra; thêm `--apply` để cập nhật local. Dừng runtime writers khi migration. Không dùng init/reseed để triển khai coupon.

## Trước khi đưa lên Render

Chốt deploy riêng: kiểm tra source diff có thay đổi đồng thời của người khác; backup + kiểm tra compatibility toàn bộ Atlas documents, áp dụng đúng carts/orders validators trước backend, deploy backend và frontend cùng contract. Không thay index/collection/seed. Smoke giỏ→quote→COD/VNPAY amount→history/dashboard và cleanup fixture đúng owner; real Sandbox checkout với mã mới chưa được claim PASS. Mã NOVA25 chưa hoạt động trên public Render trong task này. Không có bước cần người dùng cung cấp thêm giá vốn vì đã chọn không quản lý giá vốn.
