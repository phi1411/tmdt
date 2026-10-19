# Review bản GitHub mới — 17/10/2026

## Kết luận

Đã clone `https://github.com/phi1411/tmdt.git`, branch `master`, HEAD `193f1d8c66bb78dd5d1b3199e61caf67f05b548a` vào `C:/Users/Admin/Documents/ChatGPT/tmdt-review-20261017`.
So với checkpoint `f95d56b` ngày 14/10: **22 commit mới, 49 file thay đổi**, tác giả Git ghi `Sweet Bakery`; README ghi Sweet Bakery (hoang). Đây là thông tin lịch sử commit, không xác minh danh tính hay phân chia công việc ngoài Git.

Phần nền đã có Auth/User, Catalog CRUD, Cart/Checkout COD, snapshot Order, quản lý đơn và Dashboard MongoDB Aggregation. Đợt mới bổ sung nhiều UI và reviews/SKU; tuy nhiên có regression ngăn mua sản phẩm cũ và lỗi nhất quán SKU/reviews. **Chưa nên nghiệm thu toàn bộ bản mới hoặc deploy đè bản demo ổn định.** Không sửa application logic trong phiên review này.

## Những gì bạn cùng nhóm đã bổ sung

| Phần | Source hiện có | Giới hạn |
| --- | --- | --- |
| Chi tiết sản phẩm | Gallery, trang chi tiết mới, bảng thông số theo attributes, chọn biến thể nhiều tầng | Các nhãn Mall/voucher/số bán/chỉ số shop có nội dung dựng sẵn |
| SKU | Validator thêm tierVariations/skus; FE khớp tierIndex, giá/kho theo SKU; backend chọn giá SKU cho Cart/snapshot | Chưa hoàn thiện trừ/hoàn kho SKU và xác thực skuId khớp lựa chọn |
| Reviews | GET/POST product reviews, modal từ chi tiết đơn COMPLETED, kiểm tra owner/product/completed và chống trùng tuần tự | Chưa đảm bảo atomic summary; public projection và contract cần sửa |
| Tìm kiếm | Debounce 250ms, tối đa 5 gợi ý qua API; lịch sử localStorage tối đa 8 mục | Từ khóa “thịnh hành” là danh sách tĩnh, không thống kê hành vi thật |
| Chính sách | 4 trang giao hàng, đổi trả, điều khoản, bảo mật và liên kết footer | Nội dung hiển thị không đồng nghĩa hệ thống đã có refund/voucher/freeship |
| Admin/UI | Admin login chuyển dashboard, thêm đường vào admin; điều chỉnh dashboard/cart/checkout | Admin CRUD chưa quản lý fields SKU mới |
| Database/tooling | Reviews validator + 2 indexes; script 10 sản phẩm/24 review mẫu; 10 backend tests mới | Chưa cập nhật hết checker/tài liệu, chưa chứng minh migration Atlas |
| Đặc tả | Shopee/TikTok commerce specs | Nhiều mục là proposal; không tính là feature đã triển khai |

## Kiểm tra thực chạy

- Backend tại đúng HEAD: **684 tests, 684 pass, 0 fail, 0 error, 0 skip**, 116.88 giây. Có 674 test cũ và 10 test mới trong `test_shopee_parity.py`.
- Frontend `npm ci --ignore-scripts` thành công; `npm run build` chạy TypeScript strict + Vite thành công, 2244 modules, build Vite 16.85 giây. Còn cảnh báo chunk >500kB, JS khoảng 913.88kB.
- `npm audit`: **9 findings: 5 high, 4 moderate**, chưa sửa. Không kết luận mọi finding đều có thể khai thác trong runtime website.
- `scripts/validation/validate_design.py`: **FAIL `KeyError: 'reviews'`**, vì danh sách schema loader còn 6 collections nhưng index artifacts đã thêm reviews.
- Browser chạy production bundle của clone qua Vite preview và Flask thật: catalog hiển thị 180 products; mở `DEMO-ELE-001` tái hiện nút mua bị disabled dù DB stock=100.
- Chạy probes riêng trên MongoDB thật để kiểm tra tồn kho SKU, payload mismatch, reviews đồng thời, lỗi ghi summary và Admin SKU PATCH; kết quả phía dưới.
- Không chạy lại toàn bộ browser E2E lịch sử; 684 backend PASS/build PASS không thay thế được kiểm thử UI mới.

Raw receipts trong thư mục ignored `.local/review/`: `pytest.xml`, `pytest.log`, `probes.py`, `probes.json`, `validate-design.log`, `npm-audit.json`, `legacy-product-ui.txt`, `legacy-product.png`, `public-readonly.json`.

## Lỗi và việc cần hoàn thiện

### 1. Cao — sản phẩm không có SKU bị báo hết hàng

`frontend/src/pages/ProductDetailPage.tsx:172`: `isOutOfStock = !matchedSku || currentStock <= 0`.
Với sản phẩm legacy không có tierVariations/skus, matchedSku luôn null. Browser đã xác nhận `DEMO-ELE-001`, stock=100 nhưng hiển thị “Hết hàng”; “Thêm Vào Giỏ Hàng”/“Mua Ngay” disabled.
Đây cũng ảnh hưởng sản phẩm mới tạo từ Admin vì Admin chưa có fields SKU. Cần giữ đường mua legacy khi SKU không được sử dụng và thêm regression UI.

### 2. Cao — không trừ/hoàn tồn kho riêng SKU

`backend/app/repositories/product_repository.py:47` và `:53` chỉ `$inc stock` ở root; checkout vẫn tổng hợp quantity theo productId. Resolver dùng SKU stock nhưng commit không cập nhật stock đó.
Probe đặt SKU stock=1/root stock=10: **hai checkout COD đều 201**, sau đó SKU stock vẫn1/root stock=8. Bán vượt kho SKU tái hiện được ngay cả khi đặt tuần tự. Cần thống nhất nguồn tồn kho và guard/decrement/restore theo SKU trong toàn lifecycle trước nghiệm thu biến thể.

### 3. Cao — skuId không buộc khớp các lựa chọn

`backend/app/services/commerce_pricing.py:66–75` lấy SKU theo skuId trước; valid_selection chỉ kiểm tra các giá trị lựa chọn thuộc options, không ràng buộc SKU đã chọn có đúng tierIndex đó.
Probe gửi tên cấu hình giá **42.000.000đ** kèm skuId cấu hình giá **35.000.000đ**: Add Cart **200**, currentPrice=35.000.000đ. Snapshot cũng dùng cùng chiến lược lookup, có thể ghi tên lựa chọn và giá không tương ứng. Cần reject mismatch và SKU không tồn tại.

### 4. Cao — reviews/ratingSummary chưa atomic

`backend/app/services/review_service.py:74–91`: insert review rồi đọc/cộng/set summary bằng các thao tác độc lập; không có transaction hay atomic increment cho tổng hợp.
Probe ép hai request đọc cùng summary trước khi ghi: **2 review documents nhưng totalReviews=1**. Probe lỗi ghi summary sau insert: review vẫn tồn tại. Unique compound index chống duplicate nhưng không giải quyết hai review khác nhau hoặc partial failure. Test hiện tại tên “atomic” chỉ kiểm tra một request tuần tự nên chưa phát hiện lỗi này.

### 5. Trung bình — Admin chưa quản lý SKU mới

`backend/app/schemas/product_schema.py:11` vẫn giữ allowlist cũ, không có tierVariations/skus; form quản trị cũng chưa có bộ chỉnh sửa tương ứng.
Probe Admin PATCH gửi skus trả **422 VALIDATION_ERROR**. Hiện muốn bổ sung/sửa ma trận SKU phải dùng script/DB trực tiếp. Cần chốt có hỗ trợ quản trị biến thể trong phase này hay giữ phạm vi cũ.

### 6. Trung bình — dữ liệu/claim trên giao diện chưa phản ánh nghiệp vụ

Trang chi tiết dùng fallback 5.0 sao/24 reviews, phần dưới 12 “đánh giá xác thực”, số đã bán `120 + stock`, giá gạch tính `currentPrice * 1.15`, banner -15%, voucher 30k/50k, freeship, chỉ số shop dựng sẵn. Browser xác nhận một sản phẩm chưa có review vẫn hiển thị các con số này.
Checkout vẫn discount=0 và phí vận chuyển cấu hình, không có voucher/refund/chat backend mới. Nút Chat/Xem shop chưa có hành động thực; helpful review chỉ hiện toast. Cần bỏ/ghi rõ nội dung minh họa hoặc dùng dữ liệu thật; không ghi vào báo cáo là feature hoàn thành.

### 7. Trung bình — review public và seed review cần chỉnh

Public GET trả raw review documents, gồm orderCode/orderId/userId/schemaVersion. Điều này trái với guideline public projection trong `docs/features/reviews.md`; không có bằng chứng từ đây rằng khách đọc được toàn Order vì Order API vẫn có ownership guard.
GET hiện cố định tối đa20, chưa có pagination/filter API; FE lọc trên tập20 tải về.
`scripts/seed/seed_real_ecommerce.py:503–507` gán user/order theo vị trí mảng, không kiểm tra order owner, trạng thái hoàn tất hay product trong items. Các review mẫu vì vậy chưa được chứng minh là “verified purchase”. Script còn xóa toàn bộ review của 10 sản phẩm mỗi lần chạy, reset một số metadata khi upsert. **Không chạy script này trên dev/Atlas trong phiên review.** Cần fixture có quan hệ đúng và chiến lược giữ dữ liệu người dùng trước khi sử dụng.

### 8. Tài liệu/schema migration và công cụ kiểm tra chưa đồng bộ

`docs/api-contract.md` chưa có 2 routes reviews; `docs/features/reviews.md` vẫn DEFERRED với rule một review/User/Product, khác code unique User/Order/Product. `docs/database-schema.md` vẫn 6 collections và chưa có SKU. Specs mới lại mô tả SKU là proposal cần phase/ADR/migration riêng. Chưa thấy ADR/migration cập nhật nguồn thiết kế tương ứng trong diff22commit.
`validate_design.py` fail là lỗi thực của checker sau khi thêm reviews. Cần đồng bộ contract, business rules/schema/index counts, data migration và checker, rồi kiểm tra lại backend + UI integration.

## Bản GitHub và bản đang chạy Render

Kiểm tra HTTPS chỉ đọc ngày17/10: health200, product list200/total182; GET reviews của **ID sản phẩm lấy trực tiếp từ list** trả404. Sản phẩm mẫu đầu list chưa có skus. Đây không chứng minh mọi sản phẩm live đều thiếu SKU, nhưng cho thấy API live chưa phục vụ route reviews mới. Chưa đăng nhập Render để đối chiếu deployment commit, chưa redeploy trong phiên này.

VNPAY Live Sandbox vẫn chưa có evidence mới; giữ trạng thái chưa nghiệm thu theo báo cáo deployment trước. Thanh toán tiền thật ngoài phạm vi đồ án. Các gate Compass GUI, rehearsal 3 người có bấm giờ/offline OS còn là phần kiểm chứng thủ công theo checkpoint cũ, không có evidence mới đóng chúng trong diff này.

## An toàn dữ liệu/phạm vi

- Original checkout `tmdt` có thay đổi chưa commit từ trước; giữ nguyên, không pull/reset/stash hay ghi đè.
- Mongo local cũ đang không chạy tại thời điểm bắt đầu. Khởi động **instance mới với dbPath trong `.local/review/mongo-data` của clone**, MongoDB8.0.32/rs0; tạo fixtures mới trong storage riêng để chạy suite hardcode localhost27017. Không mở storage Mongo cũ, không đổi validators/indexes/data Atlas.
- Review fixture: 40 users/3categories/180products/100orders/30attempts và 7 collection validators trên storage mới; mọi seed Order có2–5items. Đây là dữ liệu kiểm thử mới, không claim là live counts của DB người dùng.
- Sau suite/probes, **cả7 test collections đều0**. Đã cleanup đúng fixture IDs và đóng các dịch vụ kiểm thử riêng sau review; không reset/reseed DB hiện hữu.
- Không sửa application logic, không commit/push/deploy. File review này là tài liệu mới trong clone; harness/credentials/artifacts nằm dưới ignored `.local`/`.env`.

## Thứ tự xử lý đề nghị

1. Sửa regression mua legacy, guard SKU/giá và tồn kho xuyên checkout/cancel/expiry.
2. Làm reviews + summary nhất quán, sửa public projection/fixture verified và bổ sung concurrency/failure tests.
3. Đồng bộ tài liệu, migration/checker; làm rõ giới hạn Admin SKU và bỏ các claim số liệu/ưu đãi chưa thật.
4. Chạy lại full backend + frontend E2E trên schema mới; sau đó mới review việc deploy và rehearsal theo barem.

Phần chức năng cốt lõi phục vụ đồ án đã tồn tại; phần nâng cấp mới chưa thể kết luận hoàn tất chỉ dựa trên 684 test PASS.
