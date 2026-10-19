# Bảng chọn phân loại khi mua — 19/10/2026

## Kết quả

Đã thực hiện trên bản clone `tmdt-review-20261017`, base `193f1d8`, theo yêu cầu chuyển lựa chọn size/màu/cấu hình vào lúc mua. Chưa commit/push/deploy; workspace `tmdt` cũ giữ nguyên.

- Bấm Thêm/Chọn mua trên card, hoặc Thêm vào giỏ/Mua ngay trên detail mới mở bảng chọn.
- Bảng hiển thị size/màu từ Fashion legacy hoặc các tầng SKU sẵn có, giá, kho và số lượng. Không tự chọn phân loại.
- Chỉ xác nhận được khi đã chọn đủ; tổ hợp hết hàng bị khóa. `skuId` lấy từ đúng tổ hợp FE đã khớp, cùng selectedAttributes và quantity gửi API Cart hiện hữu.
- Sản phẩm không có phân loại vẫn mua được; không phụ thuộc matchedSku như lỗi trước.
- Add thất bại giữ bảng mở. Thành công mới đóng; Mua ngay thành công chuyển Cart, không tự tạo Order/thanh toán.
- Escape/nút đóng/overlay dismiss, giữ focus trong bảng và trả focus khi đóng; khóa cuộn nền, hỗ trợ mobile dạng bảng đáy màn hình.
- Sidebar/chips không còn size/color/ram/capacity. Link lọc lựa chọn cũ được chuẩn hóa bỏ các keys đó, giữ tiêu chí tìm kiếm chung. Backend filter API không đổi.

## Files

`frontend/src/components/common/ProductPurchaseModal.tsx`, `frontend/src/utils/productSelection.ts`, `ProductCard.tsx`, `pages/ProductDetailPage.tsx`, `pages/ProductsPage.tsx` và UI behavior trong feature docs products/cart/search-filter.

## Kiểm tra

TypeScript strict và production build cuối PASS (Vite34.90s/2246modules); Vite còn cảnh báo chunk >500kB như trước. `git diff --check` PASS.

Browser dùng production bundle + Flask thật trên MongoDB review riêng. **17 nhóm kiểm tra PASS**:

1. Không hiện các nút phân loại trước khi bấm mua.
2. Xác nhận disabled khi chưa chọn.
3. Chọn thiếu một nhóm vẫn disabled.
4. Guest thêm giỏ thất bại giữ bảng mở, không chuyển trang.
5. Escape đóng bảng và khôi phục focus.
6. Card mở bảng ngay tại trang hiện hành.
7. Add thành công đóng bảng.
8. Giỏ giữ áo XL/Đen, quantity2 và đúng giá API.
9. Tổ hợp SKU hết hàng disabled.
10. Cấu hình SKU đổi giá35→42triệu, số lượng giới hạn theo stock5.
11. Mua ngay thành công mới chuyển Cart, giữ cấu hình và giá42triệu.
12. Sản phẩm không có SKU vẫn xác nhận và thêm giỏ thành công.
13. Bỏ variant query, giữ minPrice.
14. Mobile390×844: bảng và nút xác nhận trong viewport, không overflow ngang.
15. Tablet768×1024: bảng nằm trong viewport, không overflow ngang.
16. Tab/Shift+Tab không đưa focus ra khỏi bảng.
17. Bản build cuối giữ quantity là số nguyên khi nhập2.7→2.

Raw receipts ignored: `.local/review/purchase-ui-checks.json`, `purchase-cart-result.json`, `purchase-build.log`, `purchase-dialog-desktop.png`, `purchase-dialog-mobile.png`, `purchase-cleanup.json`. Ảnh Product của fixture SKU dùng domain test có thể không tải; có fallback, không dùng các lỗi ảnh fixture này để kết luận chất lượng ảnh live.

## Phạm vi và giới hạn

Không đổi backend/schema/index/DB architecture. **Các lỗi backend tồn kho SKU, tampering skuId và reviews đã ghi trong review17/10 chưa được sửa/nghiệm thu bởi thay đổi UI này.** FE ghép lựa chọn đúng không thay thế validation backend. Không tuyên bố full system E2E hoặc VNPAY Live PASS mới.

684 backend PASS là kết quả review17/10 trước thay đổi UI; không chạy lại full backend ở task chỉ sửa FE này. Không reset/reseed DB hiện hữu hoặc ghi Atlas. Mongo review dùng dbPath riêng `.local/review/mongo-data`; các fixture của UI nằm trong `ecommerce_test` của instance đó, cleanup theo IDs/userId trước khi đóng môi trường. Không tạo Order mới trong phiên UI.

Khi dừng console Windows, cả API và Mongo review cùng dừng trước finally cleanup. Đã mở lại đúng storage review, đối chiếu ownership/counts/exact fixture relationships, backup riêng và xóa đúng IDs trong transaction. Kết quả cuối cả7 test collections=0; đã đóng lại các listeners review. Original storage và Atlas không được mở/ghi bởi harness.
