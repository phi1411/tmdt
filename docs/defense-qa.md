# Phản biện bảo vệ NovaMart — 20 câu hỏi

Đáp án theo schema, business rules và source hiện tại; mỗi câu 2–5 câu trả lời. SV1 phụ trách câu 1–6, 13–16; SV2 phụ trách câu 7–12, 17–18; SV3 phụ trách câu 19–20 và mở evidence khi cần.

## 1. Tại sao dùng MongoDB thay vì SQL?

Đề tài yêu cầu NoSQL và các ngành hàng có bộ thuộc tính khác nhau, phù hợp với document linh hoạt. MongoDB cũng cho phép nhúng các dòng hàng và thông tin tại lúc mua vào một Order để đọc lịch sử thuận tiện. Nhóm vẫn dùng validator, index và transaction để giữ ràng buộc; SQL cũng có thể giải quyết bài toán này, không khẳng định MongoDB luôn tốt hơn.

## 2. Polymorphic Schema là gì?

Các document có một tập field chung nhưng cấu trúc một phần thay đổi theo loại. NovaMart dùng `productType` làm discriminator trong cùng collection `products`; `attributes` điện tử khác thời trang và gia dụng. Validator kiểm tra nhánh loại và kiểu dữ liệu, còn API kiểm tra allowlist nghiệp vụ.

## 3. Tại sao không tạo collection riêng cho từng ngành?

Các sản phẩm đều có tên, giá, tồn, ngành và trạng thái, đồng thời cần tìm kiếm và báo cáo chung. Một collection giúp dùng cùng CRUD/query và index cho các field bán hàng chung. Thuộc tính riêng nằm trong `attributes`, tránh phân tán logic theo ba collection.

## 4. Embed và Reference khác nhau thế nào?

Embed lưu dữ liệu con ngay trong document cha; reference lưu ID để đọc document khác khi cần. Order nhúng item và thông tin khách/địa chỉ tại lúc mua vì chúng thuộc một giao dịch lịch sử. Cart tham chiếu Product để lấy giá hiện tại, còn Product tham chiếu Category sống.

## 5. Tại sao Order phải snapshot Product?

Chỉ lưu `productId` rồi lấy tên và giá hiện tại sẽ làm hóa đơn cũ thay đổi sau khi Admin sửa Product. Checkout nhúng `productName`, SKU, `priceAtPurchase`, thuộc tính, category, khách và địa chỉ vào Order. ID vẫn dùng để truy vết và xử lý tồn, còn lịch sử hiển thị từ snapshot.

## 6. Nếu Product đổi giá thì sao?

Cart và quote mới dùng giá hiện tại từ backend, không tin giá client gửi. Order đã tạo giữ nguyên giá tại lúc mua và `lineTotal`; Product đổi 10 lên 12 triệu không sửa Order cũ. Quote có hạn dùng và kiểm tra trạng thái/version trước khi tạo đơn để phát hiện thay đổi liên quan.

## 7. `$unwind` dùng để làm gì?

Nó tách mảng `items` thành từng dòng để tính số lượng và doanh thu theo sản phẩm. Top5 sau đó group theo `items.productId` và sum quantity/lineTotal từ snapshot. Không sum `Order.total` sau unwind vì tổng đơn sẽ bị lặp theo số dòng hàng.

## 8. `$group` dùng để làm gì?

Nó gom các dòng có cùng key và áp dụng accumulator như `$sum`. Top5 gom theo Product ID; doanh thu gom theo bucket ngày hoặc tháng của `completedAt`. `$dateTrunc` dùng múi giờ `Asia/Ho_Chi_Minh` trong khi thời điểm lưu DB là UTC.

## 9. Compound Index là gì?

Đó là index gồm nhiều field theo thứ tự xác định. Ví dụ `ix_products_category_price` có `status, categoryId, price, _id`, phục vụ lọc trạng thái/ngành và sắp xếp giá có tie-break ID. Index giúp chọn đầu vào nhưng không tự tính toàn bộ group hay bảng Top5.

## 10. Tại sao thứ tự field trong index quan trọng?

Index sắp xếp keys theo thứ tự field nên equality, sort và range ảnh hưởng số key phải đọc. Query demo đặt status/category equality trước rồi price vừa làm range vừa sort, `_id` ổn định thứ tự khi đồng giá. Nhóm đo query thực và chọn trade-off, không áp một công thức cho mọi tổ hợp filter.

## 11. Index prefix là gì? Index này có phục vụ mọi query không?

Prefix là phần đầu liên tiếp của compound index, ví dụ status rồi categoryId. Query chỉ có price mà không ràng buộc các field đầu có thể không dùng index hiệu quả như query đầy đủ. Brand/search/thuộc tính riêng chưa được index này bao phủ; muốn thêm index phải có workload và evidence.

## 12. COLLSCAN và IXSCAN khác nhau?

COLLSCAN đọc các document collection để kiểm tra điều kiện; IXSCAN đọc keys của index để chọn ứng viên. IXSCAN thường còn FETCH document nếu query không covered. Nhóm so cùng query, cùng kết quả qua `nReturned`, `totalDocsExamined`, `totalKeysExamined`, không suy ra tốc độ chỉ từ 0 ms.

## 13. MongoDB transaction dùng ở đâu?

Checkout cần kiểm tra/giữ tồn, insert Order và xóa Cart cùng một transaction vì invariant trải nhiều document. Hủy đơn và hoàn kho một lần cũng cần atomicity; callback thanh toán và lifecycle phải giữ trạng thái nhất quán. Update một document đã atomic, nhưng không đủ cho toàn bộ checkout.

## 14. Tại sao dùng replica set local?

MongoDB transaction nhiều document cần replica set hoặc sharded cluster, không dùng standalone trong project này. Nhóm dùng một node local `rs0` PRIMARY để phát triển và demo offline. Một node phục vụ chức năng transaction nhưng không chứng minh khả năng chịu lỗi như cụm nhiều node production.

## 15. Nếu hai người mua sản phẩm cuối cùng cùng lúc?

Backend giảm tồn với điều kiện stock đủ trong transaction, không đọc tồn rồi ghi một cách rời rạc. Chỉ transaction giữ được invariant mới commit; bên còn lại gặp xung đột hoặc hết hàng và nhận lỗi/lấy quote mới. Retry có giới hạn và idempotency key ngăn cùng ý định tạo hai Order; không cho stock âm.

## 16. MongoDB không có foreign key thì giữ reference thế nào?

Service kiểm tra User/Product/Category tồn tại và hợp lệ, còn checkout dùng guarded writes để chống thay đổi đồng thời. Validator đảm bảo hình dạng và kiểu dữ liệu, không tự bảo đảm reference trỏ tới document có thật. Nhóm kiểm tra orphan/invariant qua evidence; không coi ObjectId đúng kiểu là đủ.

## 17. Vì sao frontend không tự tính doanh thu?

Doanh thu cần lọc đúng trạng thái, thời gian và dùng snapshot lịch sử nên được tính bằng MongoDB aggregation. Flask trả metric và metadata qua API; React/Recharts hiển thị kết quả. Cách này tránh tải mọi Order về browser, đồng thời giữ một định nghĩa dùng chung và kiểm soát quyền Admin.

## 18. Doanh thu có gồm phí ship? Vì sao đặt COD chưa tăng doanh thu?

Business rule chỉ tính Order `COMPLETED` và `PAID`, theo `completedAt`, với doanh thu `subtotal - discount`. COD mới đặt còn PENDING/UNPAID nên chưa qualify; hoàn thành và thu COD mới làm revenue tăng. `total` có shipping nhưng không dùng làm doanh thu hàng hóa; Total Orders/status lại theo `createdAt`, Customers là count toàn cục.

## 19. Tại sao tiền dùng BSON long và thời gian UTC?

Tiền là số nguyên VND để tránh sai số float, validator yêu cầu BSON long. Thời điểm lưu BSON Date UTC để so sánh nhất quán; báo cáo cắt ngày/tháng theo múi giờ Việt Nam. Export/import Extended JSON giữ ObjectId/Date/long và nested document, còn JSON thường có thể làm mất kiểu.

## 20. VNPAY chưa demo live thì chứng minh gì? Mất mạng có bảo vệ được không?

Backend đã implement integration và có deterministic tests; thiếu merchant credentials/public registered IPN nên LIVE SANDBOX vẫn BLOCKED. Return chỉ đọc trạng thái, IPN được xác minh mới cập nhật authoritative; không giả giao dịch ngân hàng đã chạy. Luồng bảo vệ chính là COD local, Compass và aggregation không cần internet; fixture không dùng ảnh ngoài mạng và evidence lưu sẵn trên máy.
