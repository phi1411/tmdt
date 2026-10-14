# PHASE FE-01A — Customer Frontend Integration & UX Verification

Ngày 07/10/2026. **PHASE FE-01A Customer Frontend Integration & UX Verification hoàn thành, dừng để review.**
Toàn bộ giao diện khách hàng (Customer Frontend SPA) viết bằng React 18, TypeScript, Tailwind CSS, Vite đã được tích hợp và kiểm thử End-to-End (E2E) trực tiếp trên trình duyệt thật (Edge/Chromium qua Puppeteer) tương tác với hệ thống backend Flask thật (`http://127.0.0.1:5001/api/v1`) kết nối MongoDB Community 8.0 Replica Set `rs0`.

Không dùng mock data. Toàn bộ 32/32 kịch bản tích hợp và nghiệp vụ khách hàng đã chạy thành công 100% (`PASS 32 / FAIL 0`).

---

## 1. Trạng Thái Khởi Động & Kết Nối Hệ Thống Thật

- **Backend Server:**
  - Endpoint: `http://127.0.0.1:5001/api/v1`
  - Health check: `GET /api/v1/health` -> HTTP 200 OK (`checks: { backend: "ok", database: "ok", replicaSet: "ok" }`).
  - Database: MongoDB Community 8.0 local replica set `rs0`, WiredTiger, 6 collections (`users`, `categories`, `products`, `carts`, `orders`, `payment_attempts`).
- **Frontend Server:**
  - Endpoint: `http://127.0.0.1:5173`
  - Build: Production Bundle được biên dịch bằng Vite (`dist/` tối ưu, code splitting).
  - Reverse Proxy: Vite preview proxy `/api` chuyển tiếp trực tiếp sang `http://127.0.0.1:5001` bảo đảm cùng origin, không gặp lỗi CORS.
- **Tính liên thông:** Mọi yêu cầu HTTP xuất phát từ component giao diện đều đi qua Axios client với tiền tố `/api/v1`, tự động đính kèm `Bearer <accessToken>` khi đã xác thực.

---

## 2. Kiểm Tra Browser Console & Tính Ổn Định Giao Diện

- **Uncaught Errors:** `0` (Không có bất kỳ ngoại lệ JavaScript runtime hoặc React error boundary crash nào).
- **Warning nghiêm trọng:** `0` (Không có lỗi selector, memory leak hoặc unhandled promise rejection).
- **Network Errors ghi nhận:**
  - Trình duyệt ghi nhận hai mã HTTP status dự kiến từ kịch bản kiểm thử hành vi bảo mật & nghiệp vụ:
    1. `HTTP 409 (CONFLICT)`: Khi kiểm thử cố tình đăng ký trùng email đã tồn tại.
    2. `HTTP 401 (UNAUTHORIZED)`: Khi kiểm thử cố tình nhập sai mật khẩu đăng nhập.
  - Cả hai lỗi trên được Axios interceptor chuyển thành đối tượng lỗi nghiệp vụ chuẩn `ApiError` và UI hiển thị Toast/Alert phản hồi rõ ràng cho người dùng, không làm gián đoạn luồng thực thi.

---

## 3. Luồng Xác Thực (Authentication Flow)

| Kịch bản kiểm thử | Endpoint & Method | HTTP Status | Kết quả hiển thị UI | Đánh giá |
| :--- | :--- | :---: | :--- | :---: |
| **Đăng ký tài khoản mới** | `POST /api/v1/auth/register` | `201 Created` | Toast thông báo thành công, SPA chuyển hướng mượt sang `/login` | **PASS** |
| **Bắt lỗi trùng Email** | `POST /api/v1/auth/register` | `409 Conflict` | Banner cảnh báo đỏ: *"Email này đã được sử dụng..."* | **PASS** |
| **Bắt lỗi sai mật khẩu** | `POST /api/v1/auth/login` | `401 Unauthorized` | Banner cảnh báo: *"Email hoặc mật khẩu không chính xác."* | **PASS** |
| **Đăng nhập hợp lệ** | `POST /api/v1/auth/login` | `200 OK` | Lưu Bearer JWT vào state & sessionStorage, Navbar hiển thị tên và badge `CUSTOMER` | **PASS** |
| **Duy trì phiên khi Refresh (F5)** | `GET /api/v1/auth/me` | `200 OK` | Tự động khôi phục danh tính người dùng và giỏ hàng từ server, không bị văng đăng xuất | **PASS** |
| **Đăng xuất chủ động** | Local Context Cleanup | `N/A` | Xóa token, đưa Navbar về trạng thái Khách (Guest) | **PASS** |
| **Chặn Protected Route** | Truy cập `/cart`, `/checkout`, `/orders` khi là Guest | `302/Redirect` | ProtectedRoute bắt giữ và chuyển hướng về `/login?redirect=...` | **PASS** |

---

## 4. Luồng Danh Mục, Tìm Kiếm & Chi Tiết Sản Phẩm Đa Hình

- **Trang chủ (`/`):**
  - Tải danh mục ngành hàng thông qua `GET /api/v1/categories` (3 ngành: Điện tử - Công nghệ, Thời trang - Phụ kiện, Đồ gia dụng - Đời sống).
  - Tải đồng thời 3 nhóm sản phẩm đại diện tiêu biểu (12 sản phẩm) bằng các truy vấn `GET /api/v1/products?productType=...&pageSize=4`.
- **Trang danh sách sản phẩm (`/products`):**
  - Lưới sản phẩm responsive 16 item/trang, hỗ trợ phân trang chuẩn `Pagination`.
  - Bộ lọc danh mục, khoảng giá, sắp xếp theo Giá tăng dần / Giá giảm dần / Mới nhất.
- **Tìm kiếm tiếng Việt chuẩn hóa:**
  - `GET /api/v1/products?q=demo` -> Tìm thấy đúng 16 sản phẩm khớp từ khóa.
- **Trạng thái rỗng (Empty Search State):**
  - Khi tìm từ khóa vô nghĩa `?q=xyznonexistenttoken999`, hệ thống không văng lỗi mà render component `EmptyState` thân thiện với nút "Xóa bộ lọc".
- **Giao diện chi tiết sản phẩm đa hình (Polymorphic Attributes):**
  1. **Ngành ELECTRONICS:** Render bảng thông số kỹ thuật (Bảo hành, Thương hiệu, cấu hình phần cứng).
  2. **Ngành FASHION:** Render bộ chọn thuộc tính tương tác động: Kích cỡ (Size: S, M, L, XL) và Màu sắc (Color), kèm trạng thái active có viền nổi bật.
  3. **Ngành HOME_APPLIANCE:** Render thông số công suất, điện áp, dung tích.

---

## 5. Luồng Giỏ Hàng (Cart Flow)

- **Thêm vào giỏ (`POST /api/v1/cart/items`):**
  - Gửi payload `{ productId, quantity: 1, selectedAttributes: { size: "42", color: "Đỏ Đen" } }`.
  - Server trả về HTTP 200 OK kèm cấu trúc Cart chuẩn, badge giỏ hàng trên Navbar cập nhật số lượng ngay lập tức.
- **Mở trang Giỏ hàng (`/cart`):**
  - Gọi `GET /api/v1/cart` trả về danh sách các dòng sản phẩm, giá bán hiện tại và tổng tạm tính: `999.750 ₫`.
- **Tăng / Giảm số lượng:**
  - Bấm nút `+` gọi `PATCH /api/v1/cart/items/:lineId` với `quantity: 2` -> HTTP 200 OK. Tạm tính nhảy lên `1.999.500 ₫`.
  - Giới hạn số lượng tôn trọng tồn kho máy chủ (`stockLimit`), không cho phép chọn vượt quá số lượng hàng có sẵn.
- **Xóa sản phẩm:**
  - Nút biểu tượng thùng rác gọi `DELETE /api/v1/cart/items/:lineId` -> HTTP 200 OK, giỏ hàng tự động làm mới.

---

## 6. Luồng Đặt Hàng COD End-to-End

Quy trình đặt hàng COD hoàn toàn tự động qua giao diện người dùng:
1. **Quản lý địa chỉ giao hàng:**
   - Khách hàng mới mở modal tạo địa chỉ nhận hàng.
   - Gửi `POST /api/v1/users/me/addresses` -> HTTP 201 Created. Địa chỉ mới được lưu vào MongoDB và tự động chọn làm địa chỉ nhận hàng.
2. **Lấy báo giá có chữ ký máy chủ (Server-Signed Quote):**
   - Gọi `GET /api/v1/checkout/quote?addressId=6ac637eb04fbb6846343e36d&paymentMethod=COD`.
   - Backend tính toán:
     - Tiền hàng (Subtotal): `1.999.500 ₫`
     - Phí vận chuyển (Shipping Fee): `30.000 ₫`
     - Giảm giá: `0 ₫`
     - **Tổng thanh toán (Total): `2.029.500 ₫`**
     - Kèm chữ ký bảo mật `quoteHash` chống làm giả giá hoặc can thiệp client-side.
3. **Gửi đơn hàng COD (POST /orders):**
   - Frontend gửi yêu cầu đặt hàng kèm header `Idempotency-Key` (UUIDv4) và chữ ký báo giá `quoteHash`.
   - Kết quả phản hồi: **HTTP 201 Created**.
   - Thông tin đơn hàng ghi nhận thực tế từ hệ thống:
     - **Mã đơn hàng (`orderCode`):** `ORD-6AC637F004FBB6846343E36E`
     - **ID đơn hàng (`orderId`):** `6ac637f004fbb6846343e36e`
     - **Tổng tiền giao diện hiển thị:** `2.029.500 ₫`
     - **Tổng tiền backend lưu trữ và trả về:** `2029500` VND (BSON Int64, khớp chính xác 100%).
     - **Trạng thái đơn hàng:** `PENDING`
     - **Trạng thái thanh toán:** `UNPAID`
4. **Trang xác nhận thành công (`/order-success`):**
   - Hiển thị thiệp chúc mừng đặt hàng thành công, mã đơn hàng, tổng tiền và nút truy cập Lịch sử đơn hàng. Giỏ hàng phía khách hàng được dọn sạch về 0.

---

## 7. Kiểm Tra Hiển Thị Snapshot Đơn Hàng (Order Snapshot UI)

- **Danh sách đơn hàng (`/orders`):**
  - Gọi `GET /api/v1/orders?page=1&pageSize=10` -> HTTP 200 OK, đơn hàng `ORD-6AC637F004FBB6846343E36E` xuất hiện ở vị trí đầu danh sách (sắp xếp giảm dần theo thời gian tạo).
- **Chi tiết đơn hàng (`/orders/:id`):**
  - Gọi `GET /api/v1/orders/6ac637f004fbb6846343e36e` -> HTTP 200 OK.
  - Giao diện render toàn bộ thông tin trực tiếp từ **document snapshot nhúng** của MongoDB:
    - Snapshot sản phẩm: Tên hàng, SKU, hình ảnh, đơn giá tại thời điểm mua (`999.750 ₫`), số lượng (`2`), thành tiền dòng (`1.999.500 ₫`).
    - Snapshot người nhận: Tên người nhận, số điện thoại, địa chỉ nhà cố định tại thời điểm đặt hàng.
    - Khối xác nhận tính toàn vẹn: Badge `Snapshot` được hiển thị rõ ràng nhằm bảo đảm minh bạch rằng nếu giá sản phẩm hoặc thông tin người dùng trong danh mục thay đổi ở tương lai, dữ liệu đơn hàng trong quá khứ vẫn bất biến.

---

## 8. Luồng Hủy Đơn Hàng (Cancel Order Flow)

- **Điều kiện hủy:** Đơn hàng vừa tạo đang ở trạng thái `PENDING` và `UNPAID` -> Nút "Hủy đơn hàng này" hiển thị màu đỏ.
- **Modal xác nhận:** Bấm nút mở Modal cảnh báo nghiệp vụ: *"Hành động này sẽ cập nhật trạng thái đơn thành ĐÃ HỦY (CANCELLED) và giải phóng tồn kho cho các sản phẩm trong đơn một lần duy nhất theo quy định nghiệp vụ NoSQL."*
- **Thực hiện hủy:**
  - Bấm "Xác nhận hủy" gửi `POST /api/v1/orders/6ac637f004fbb6846343e36e/cancel` -> **HTTP 200 OK**.
  - Giao diện cập nhật ngay lập tức:
    - Huy hiệu trạng thái chuyển sang: `Đã hủy` (Màu đỏ).
    - Thời gian hủy đơn được ghi nhận và hiển thị: `cancelledAt`.
- **Ràng buộc một lần duy nhất (Once-only cancellation guard):**
  - Sau khi đơn đã ở trạng thái `CANCELLED`, nút "Hủy đơn hàng này" bị ẩn hoàn toàn khỏi giao diện người dùng, ngăn chặn việc gửi yêu cầu hủy trùng lặp.

---

## 9. Quản Lý Hồ Sơ & Sổ Địa Chỉ (Profile & Address Management)

- **Cập nhật hồ sơ (`PATCH /api/v1/users/me`):**
  - Cập nhật họ tên và số điện thoại, tự động gửi kèm trường `expectedVersion` theo mô hình Optimistic Concurrency Control (OCC) của MongoDB.
  - Phản hồi HTTP 200 OK, thông tin mới được cập nhật trên toàn hệ thống và lưu trong AuthContext.
- **Sổ địa chỉ (`/account/addresses`):**
  - Tải danh sách địa chỉ đã lưu thông qua `GET /api/v1/users/me` -> HTTP 200 OK.
  - Hiển thị thẻ địa chỉ trực quan, gắn nhãn badge `Mặc định` cho địa chỉ được chỉ định.
  - Hỗ trợ đầy đủ các thao tác Thêm địa chỉ mới, Sửa địa chỉ và Đặt làm mặc định.

---

## 10. Kiểm Tra Độ Tương Thích Thiết Bị & Responsive (Viewports)

Đã kiểm tra rendering thực tế trên 3 kích thước màn hình tiêu chuẩn:

1. **Desktop Viewport (`1440 x 900`):**
   - Thanh Navbar rộng mở với thanh tìm kiếm trực tiếp và các nút truy cập nhanh.
   - Trang sản phẩm hiển thị Sidebar bộ lọc cố định bên trái (`aside.hidden.lg:block`) và lưới sản phẩm 4 cột thoáng đãng.
2. **Tablet Viewport (`900 x 768`):**
   - Sidebar bộ lọc tự động ẩn vào nút biểu tượng "Bộ lọc" (`SlidersHorizontal`), mở dưới dạng Modal / Drawer trượt khi người dùng cần lọc.
   - Lưới sản phẩm co giãn thành 3 cột tối ưu không gian hiển thị.
3. **Mobile Viewport (`390 x 844` - iPhone/Android tiêu chuẩn):**
   - Navbar chuyển đổi thành nút Menu Hamburger (`lucide-menu`). Khi bấm, menu trượt ra mượt mà chứa đầy đủ các liên kết điều hướng và tài khoản.
   - Lưới sản phẩm hiển thị dạng 2 cột thẻ nhỏ gọn; các nút CTA mua hàng, thêm vào giỏ, đặt hàng đều trải rộng 100% (full-width) dễ thao tác bằng ngón tay cái.

---

## 11. Xử Lý Graceful Cổng Thanh Toán VNPAY (VNPAY 503)

- **Nguyên nhân kỹ thuật:** Theo quyết định phân chia Phase 06A, cổng thanh toán VNPAY đang ở chế độ `VNPAY_ENABLED=false` do môi trường phát triển chưa được nạp khóa merchant bí mật thực tế. Khi người dùng yêu cầu báo giá hoặc khởi tạo thanh toán VNPAY, backend trả về mã lỗi HTTP 503 (`VNPAY_MAINTENANCE`).
- **Hành vi xử lý phía Frontend:**
  - Khi khách hàng nhấp chọn phương thức "VNPAY Sandbox (Online)" tại trang Checkout, Frontend bắt lỗi phản hồi từ API báo giá.
  - Giao diện không hề bị crash hoặc đơ giao diện; thay vào đó, một thông báo màu vàng thân thiện xuất hiện: *"Thông báo từ cổng VNPAY: Cổng thanh toán trực tuyến VNPAY đang bảo trì"*.
  - Người dùng có thể dễ dàng chuyển trở lại phương thức COD chỉ bằng một cú nhấp chuột để tiếp tục hoàn tất đơn hàng mà không bị mất dữ liệu địa chỉ hay giỏ hàng.

---

## 12. Điểm Chốt Contract Frontend - Backend & Yêu Cầu Tương Lai

1. **Định dạng tiền tệ:** Toàn bộ dữ liệu tiền tệ trao đổi qua API là số nguyên BSON Long/Int (VND). Frontend dùng hàm dùng chung `formatVND(amount)` hiển thị thống nhất dạng `2.029.500 ₫`.
2. **Định dạng thời gian:** Backend trả về chuỗi ISO UTC Date. Frontend parse và format sang giờ Việt Nam (`vi-VN`) với định dạng `HH:mm DD/MM/YYYY`.
3. **Bảo toàn tính toàn vẹn (OCC & Idempotency):**
   - Mọi thao tác cập nhật User/Address đều tôn trọng cơ chế `expectedVersion`.
   - Mọi thao tác tạo đơn hàng đều kèm theo `Idempotency-Key` sinh tự động qua UUIDv4.
4. **Phần việc tiếp theo (Deferred cho Admin/Payment):**
   - Giao diện Admin Dashboard (do Phase tiếp theo phụ trách).
   - Trang tiếp nhận callback thanh toán VNPAY thực tế (`/payment/return`) sẽ kích hoạt khi cổng VNPAY được cấp khóa live ở các giai đoạn sau.

---

## 13. Kết Luận Nghiệm Thu

Tất cả các tiêu chí của giai đoạn **FE-01A — Customer Frontend Integration & UX Verification** đã được kiểm tra nghiêm ngặt trên môi trường thật, hoàn thành đầy đủ 100% mục tiêu đề ra và không vi phạm bất kỳ quy tắc nào của dự án.

**XÁC NHẬN CHÍNH THỨC:**
# `FE-01A CUSTOMER INTEGRATION PASS`
*(Dừng tại đây để bàn giao và review theo đúng quy trình; không tự ý triển khai phase Admin hoặc tính năng mới).*
