# BÁO CÁO NGHIỆM THU PHASE FE-02 — ADMIN FRONTEND & VNPAY PAYMENT INTEGRATION

Ngày hoàn thành: 07/10/2026  
Người thực hiện: Frontend Agent (Antigravity)  
Trạng thái: **PHASE FE-02 FRONTEND COMPLETE — DỪNG ĐỂ REVIEW**

---

## 1. Tổng Quan & Thiết Kế Layout Admin (Admin Portal)

Giao diện Quản trị viên (Admin Portal) được xây dựng theo ngôn ngữ thiết kế đồng bộ với Design System Novamart đã định hình ở Phase FE-01, nhưng được tối ưu hóa đặc thù cho các tác vụ quản trị, giám sát và vận hành hệ thống thương mại điện tử.

### Kiến Trúc Giao Diện & Bố Cục
- **AdminLayout (`frontend/src/layouts/AdminLayout.tsx`)**:
  - **Sidebar Cố Định (Desktop)**: Thanh điều hướng bên trái với nền slate sẫm chuyên nghiệp, phân cấp rõ ràng các phân hệ quản trị:
    - *Tổng quan* (`/admin/dashboard` - Icon Thống kê)
    - *Đơn hàng* (`/admin/orders` - Icon Hộp hàng)
    - *Sản phẩm* (`/admin/products` - Icon Thẻ sản phẩm)
    - *Ngành hàng* (`/admin/categories` - Icon Thư mục ngành hàng)
    - *Người dùng* (`/admin/users` - Icon Tài khoản người dùng)
    - Lối tắt nhanh quay lại *Cửa hàng Novamart* (`/`).
  - **Header Quản Trị**:
    - Hiển thị Breadcrumbs điều hướng linh hoạt theo route hiện hành.
    - Chỉ báo trạng thái kết nối cơ sở dữ liệu thời gian thực: `MongoDB rs0 (Replica Set)`.
    - Profile pill hiển thị avatar quản trị viên, họ tên, nhãn phân quyền `ADMIN`, và nút Đăng xuất an toàn.
  - **Mobile & Tablet Drawer**:
    - Nút Hamburger mở menu trượt mượt mà kèm backdrop làm mờ màn hình, tự động đóng khi chuyển route hoặc bấm ra ngoài.
- **Bảo Vệ Quyền Truy Cập Tuyệt Đối (`ProtectedRoute.tsx`)**:
  - Route quản trị (`/admin/*`) được bọc bảo vệ với cờ `requireAdmin={true}`.
  - Nếu người dùng chưa đăng nhập: Tự động chuyển hướng về `/login` kèm lưu lại route dự định.
  - Nếu người dùng đã đăng nhập với vai trò `CUSTOMER`: Bị chặn hoàn toàn, hiển thị trang 403 Access Denied chuyên nghiệp với giải thích rõ ràng và nút điều hướng về trang chủ.

---

## 2. Admin Dashboard & MongoDB Aggregation Analytics

Toàn bộ số liệu và biểu đồ phân tích trên Dashboard được tích hợp trực tiếp từ 5 MongoDB Canonical Aggregation Pipelines của Backend (`/api/v1/admin/dashboard/*`). Frontend tuyệt đối không tự tải toàn bộ dữ liệu đơn hàng về tính toán thủ công.

### 4 Thẻ Chỉ Số KPI (Summary Metrics)
Dữ liệu từ `GET /api/v1/admin/dashboard/summary`:
1. **Doanh Thu Hàng Hóa**: Thống kê tổng doanh thu thực tế từ các đơn hàng có trạng thái `COMPLETED` và thanh toán `PAID` (theo quy tắc nghiệp vụ bất biến: không tính doanh thu trên phí vận chuyển).
2. **Tổng Đơn Hàng**: Tổng số đơn hàng hợp lệ ghi nhận trong hệ thống.
3. **Sản Phẩm Đã Bán**: Tổng số lượng đơn vị sản phẩm đã bán thành công.
4. **Tổng Khách Hàng**: Tổng số tài khoản khách hàng (`CUSTOMER`) trong hệ thống.

### Hệ Thống Biểu Đồ Trực Quan Hóa (Recharts)
- **Biểu đồ Chuỗi Doanh Thu (Revenue Series - `AreaChart`)**:
  - Dữ liệu từ `GET /api/v1/admin/dashboard/revenue`.
  - Hỗ trợ xem theo chu kỳ ngày (`interval=day`) hoặc tháng (`interval=month`).
  - Thể hiện đồng thời 2 đường xu hướng: Doanh thu (VND, diện tích màu Emerald mượt mà) và Số lượng đơn hàng phát sinh.
- **Xếp Hạng Top 5 Sản Phẩm Bán Chạy (`top-products`)**:
  - Dữ liệu từ `GET /api/v1/admin/dashboard/top-products?limit=5`.
  - Hiển thị bảng xếp hạng trực quan: Ảnh đại diện, Tên sản phẩm, Ngành hàng, Số lượng bán thành công (`totalSold`), và Tổng doanh thu thu về.
- **Phân Bố Doanh Thu Theo Ngành Hàng (`category-revenue` - `PieChart`)**:
  - Dữ liệu từ `GET /api/v1/admin/dashboard/category-revenue`.
  - Biểu đồ Donut thể hiện tỷ trọng phần trăm và giá trị đóng góp doanh thu của từng ngành hàng (*Thiết bị điện tử*, *Thời trang*, *Đồ gia dụng*).
- **Phân Bố Trạng Thái Đơn Hàng (`order-status` - `BarChart`)**:
  - Dữ liệu từ `GET /api/v1/admin/dashboard/order-status`.
  - Cột biểu diễn trực quan số lượng đơn hàng ở từng trạng thái trong vòng đời: `PENDING`, `CONFIRMED`, `SHIPPING`, `COMPLETED`, `CANCELLED`, `EXPIRED`.

### Bộ Lọc Thời Gian Chuẩn Hóa
- Cung cấp các nút chọn nhanh: *Hôm nay*, *7 ngày qua*, *30 ngày qua*, *Tháng này*, *Toàn thời gian*.
- Bộ chọn khoảng thời gian tùy chỉnh (*Từ ngày* - *Đến ngày*).
- Frontend tự động chuyển đổi thời gian sang chuỗi ISO-8601 UTC (`from`, `to`) theo đúng API contract của MongoDB backend.

---

## 3. Quản Lý Sản Phẩm (Admin Product CRUD)

- **Danh Sách Sản Phẩm (`frontend/src/pages/AdminProductsPage.tsx`)**:
  - Tải dữ liệu qua `GET /api/v1/admin/products` với phân trang đầy đủ.
  - Bộ lọc tìm kiếm kết hợp: Tìm theo từ khóa (tên, SKU), lọc theo ngành hàng, lọc theo trạng thái (`ACTIVE`, `ARCHIVED`).
  - Hiển thị bảng dữ liệu chi tiết: Hình ảnh, Tên sản phẩm, Mã SKU, Ngành hàng, Giá bán niêm yết, Số lượng tồn kho, Trạng thái (Badge), Phiên bản tài liệu (`version`).
  - Nút thao tác nhanh: Xem chi tiết sản phẩm ngoài Cửa hàng, Chỉnh sửa, và Lưu trữ (Archive).
- **Modal Xác Nhận Lưu Trữ (Archive Modal)**:
  - Gọi `POST /api/v1/admin/products/:id/archive` với modal xác nhận thận trọng, ngăn ngừa thao tác nhầm lẫn.
- **Form Tạo Mới & Chỉnh Sửa Đa Hình (`frontend/src/pages/AdminProductFormPage.tsx`)**:
  - Tuyến đường: `/admin/products/new` (Tạo mới) và `/admin/products/:id/edit` (Cập nhật).
  - **Phân khu 1 - Thuộc tính chung**: Tên sản phẩm, Slug (tự động tạo từ tên hoặc tùy biến), Mã SKU, Ngành hàng, Giá bán (VND), Tồn kho ban đầu, Danh sách link ảnh, Mô tả chi tiết.
  - **Phân khu 2 - Thuộc tính Đa hình (Polymorphic Attributes)**: Giao diện tự động thích ứng với cấu trúc thuộc tính riêng biệt theo `productType` của ngành hàng:
    - *ELECTRONICS*: Thời hạn bảo hành (tháng), Dung lượng RAM (GB), Bộ nhớ trong (GB), Chip xử lý, Kích thước màn hình (inch).
    - *FASHION*: Giới tính đối tượng (`MALE`, `FEMALE`, `UNISEX`), Chất liệu vải, Các kích cỡ sản phẩm (S, M, L, XL, XXL, Free Size), Bảng mã màu sắc.
    - *HOME_APPLIANCE*: Công suất tiêu thụ điện (W), Dung tích thiết bị (L), Điện áp hoạt động, Chất liệu vỏ máy.
  - Hỗ trợ gửi `version` trong request `PATCH /api/v1/admin/products/:id` nhằm đảm bảo kiểm soát xung đột đồng thời (Optimistic Concurrency Control).

---

## 4. Quản Lý Ngành Hàng (Admin Category Management)

- **Danh Sách Ngành Hàng (`frontend/src/pages/AdminCategoriesPage.tsx`)**:
  - Tải dữ liệu qua `GET /api/v1/admin/categories`.
  - Hiển thị thông tin Tên ngành hàng, Slug URL, Loại Schema Thuộc Tính (`productType`), Trạng thái hoạt động, Mô tả.
- **Tạo Mới & Chỉnh Sửa (Modal)**:
  - Cho phép nhập Tên ngành hàng, Slug, Mô tả và lựa chọn `productType` áp dụng (`ELECTRONICS`, `FASHION`, `HOME_APPLIANCE`).
  - Gửi API qua `POST /api/v1/admin/categories` hoặc `PATCH /api/v1/admin/categories/:id`.
- **Xóa Ngành Hàng & Xử Lý Ràng Buộc Toàn Vẹn (Referential Integrity)**:
  - Modal cảnh báo xác nhận khi thực hiện `DELETE /api/v1/admin/categories/:id`.
  - Khi Backend trả về lỗi `409 Conflict` (mã lỗi `CATEGORY_IN_USE` do ngành hàng còn chứa sản phẩm liên kết), Frontend bắt lỗi và hiển thị thông báo rõ ràng, không làm sập giao diện.

---

## 5. Quản Lý Đơn Hàng (Admin Order Lifecycle Management)

- **Danh Sách Đơn Hàng (`frontend/src/pages/AdminOrdersPage.tsx`)**:
  - Tải dữ liệu qua `GET /api/v1/admin/orders`.
  - Bộ lọc đa chiều: Lọc theo Trạng thái đơn hàng (`orderStatus`), Phương thức thanh toán (`paymentMethod`), và ô Tìm kiếm chính xác mã đơn hàng (`orderCode`).
  - Hiển thị rõ ràng Mã đơn hàng, Tên người nhận, Tổng tiền, Trạng thái đơn hàng, Trạng thái thanh toán, Ngày tạo.
- **Trang Chi Tiết Đơn Hàng (`frontend/src/pages/AdminOrderDetailPage.tsx`)**:
  - Tải chi tiết qua `GET /api/v1/admin/orders/:id`.
  - **Hiển thị Bất Biến Snapshot**:
    - Snapshot Người nhận & Địa chỉ giao hàng tại thời điểm đặt hàng.
    - Snapshot Danh mục sản phẩm: Ảnh sản phẩm, Tên sản phẩm, Tên ngành hàng, Đơn giá mua, Số lượng và Thành tiền tại thời điểm đặt hàng.
  - **Điều Khiển Vòng Đời Đơn Hàng Theo `allowedActions`**:
    - Frontend chỉ hiển thị các nút thao tác nghiệp vụ được phép dựa vào mảng `allowedActions` do Backend tính toán:
      - `confirm`: Nút "Xác Nhận Đơn Hàng" (gọi `POST /api/v1/admin/orders/:id/confirm`).
      - `ship`: Nút "Bàn Giao Vận Chuyển" (gọi `POST /api/v1/admin/orders/:id/ship`).
      - `complete`: Nút "Hoàn Tất Đơn Hàng" (gọi `POST /api/v1/admin/orders/:id/complete` - đối với đơn COD, tự động cập nhật thanh toán `PAID`).
      - `cancel`: Nút "Hủy Đơn Hàng" mở Modal yêu cầu nhập bắt buộc lý do hủy (gọi `POST /api/v1/admin/orders/:id/cancel`).
    - Các nút chuyển trạng thái tự động ẩn khi đơn hàng đã đạt trạng thái cuối (`COMPLETED`, `CANCELLED`).

---

## 6. Quản Lý Tài Khoản Người Dùng (Admin User Management)

- **Danh Sách Người Dùng (`frontend/src/pages/AdminUsersPage.tsx`)**:
  - Tải danh sách qua `GET /api/v1/admin/users`.
  - Lọc theo Vai trò (`CUSTOMER`, `ADMIN`), Trạng thái (`ACTIVE`, `BLOCKED`), và ô Tìm kiếm theo Tên hoặc Email.
  - Hiển thị Họ tên, Email, Số điện thoại, Vai trò, Trạng thái, Ngày tham gia.
- **Bảo Vệ Bất Biến Tài Khoản Quản Trị (Admin Protection)**:
  - Tài khoản có vai trò `ADMIN` được gắn nhãn bảo vệ ("Bảo vệ"), nút Khóa tài khoản bị vô hiệu hóa hoàn toàn từ giao diện, ngăn ngừa hành vi tự khóa tài khoản quản trị viên.
- **Khóa & Mở Khóa Khách Hàng (Customer Block/Reactivate)**:
  - Cung cấp Modal xác nhận với cảnh báo rõ ràng khi khóa tài khoản khách hàng.
  - Gửi API qua `PATCH /api/v1/admin/users/:id/status` với body `{ status: "BLOCKED" }` hoặc `{ status: "ACTIVE" }`.

---

## 7. Tích Hợp Cổng Thanh Toán VNPAY (Customer Flow)

- **Quy Trình Tại Trang Checkout (`frontend/src/pages/CheckoutPage.tsx`)**:
  - Khách hàng lựa chọn phương thức thanh toán `VNPAY`.
  - Khi bấm "Đặt Hàng", frontend gọi `POST /api/v1/orders`.
  - Backend thực hiện giữ chỗ trong transaction và trả về `paymentUrl` chứa chữ ký số VNPAY HMAC-SHA512.
  - Frontend tự động chuyển hướng khách hàng sang cổng VNPAY (`window.location.href = paymentUrl`).
  - **Graceful Fallback**: Nếu hệ thống backend chưa bật cổng thanh toán VNPAY (`VNPAY_ENABLED=false`, trả về `503 Service Unavailable`), giao diện bắt lỗi và hiển thị thông báo rõ ràng cho khách hàng chọn phương thức COD hoặc thử lại sau.

---

## 8. Tiếp Nhận Kết Quả Thanh Toán (Payment Return Behavior)

- **Trang Xử Lý Kết Quả Thanh Toán (`frontend/src/pages/PaymentReturnPage.tsx`)**:
  - Đăng ký phục vụ trên cả 2 tuyến đường: `/payment/return` và `/payment-result`.
  - Nhận toàn bộ tham số truy vấn từ cổng VNPAY (`vnp_Amount`, `vnp_BankCode`, `vnp_ResponseCode`, `vnp_TxnRef`, `vnp_SecureHash`,...).
  - Gọi API xác thực chữ ký: `GET /api/v1/payments/vnpay/return?<queryString>`.
  - **Xử Lý Trạng Thái Toàn Diện**:
    - **`SUCCESS`** (Mã `00`): Hiển thị thông báo giao dịch thành công rực rỡ, mã giao dịch, số tiền thanh toán, cùng nút xem đơn hàng và tiếp tục mua sắm.
    - **`PENDING`**: Hiển thị thông báo giao dịch đang được đối soát, kèm cơ chế tự động thăm dò (polling) trạng thái đơn hàng từ backend sau mỗi 3 giây.
    - **`FAILED`**: Hiển thị thông báo giao dịch không thành công kèm nguyên nhân và nút cho phép khách hàng thử thanh toán lại.
    - **`INVALID_SIGNATURE`**: Hiển thị cảnh báo chữ ký số không hợp lệ (nghi vấn can thiệp dữ liệu).
    - **`INVALID_RESPONSE`**: Hiển thị cảnh báo phản hồi cổng thanh toán không đúng cấu trúc.
    - **Cờ `paymentReviewRequired`**: Hiển thị cảnh báo đơn hàng đang được chuyển sang chế độ quản trị viên đối soát nếu có sai lệch giữa ngân hàng và hệ thống.

---

## 9. Danh Sách API Endpoints Đã Tích Hợp

| STT | Phương Thức | Tuyến Đường (Path) | Mục Đích Nghiệp Vụ | Trạng Thái |
|:---:|:---:|:---|:---|:---:|
| 1 | `POST` | `/api/v1/auth/login` | Đăng nhập tài khoản Admin & Customer | Hoàn thành |
| 2 | `GET` | `/api/v1/admin/dashboard/summary` | 4 chỉ số KPI tổng hợp từ MongoDB Aggregation | Hoàn thành |
| 3 | `GET` | `/api/v1/admin/dashboard/revenue` | Biểu đồ chuỗi doanh thu theo thời gian | Hoàn thành |
| 4 | `GET` | `/api/v1/admin/dashboard/top-products` | Bảng xếp hạng Top 5 sản phẩm bán chạy nhất | Hoàn thành |
| 5 | `GET` | `/api/v1/admin/dashboard/category-revenue` | Biểu đồ phân bổ doanh thu theo ngành hàng | Hoàn thành |
| 6 | `GET` | `/api/v1/admin/dashboard/order-status` | Biểu đồ phân bổ trạng thái đơn hàng | Hoàn thành |
| 7 | `GET` | `/api/v1/admin/orders` | Danh sách đơn hàng phía quản trị với bộ lọc | Hoàn thành |
| 8 | `GET` | `/api/v1/admin/orders/:id` | Chi tiết đơn hàng, snapshot và allowedActions | Hoàn thành |
| 9 | `POST` | `/api/v1/admin/orders/:id/confirm` | Chuyển trạng thái đơn sang CONFIRMED | Hoàn thành |
| 10 | `POST` | `/api/v1/admin/orders/:id/ship` | Chuyển trạng thái đơn sang SHIPPING | Hoàn thành |
| 11 | `POST` | `/api/v1/admin/orders/:id/complete` | Hoàn tất đơn hàng sang COMPLETED | Hoàn thành |
| 12 | `POST` | `/api/v1/admin/orders/:id/cancel` | Hủy đơn hàng kèm lý do | Hoàn thành |
| 13 | `GET` | `/api/v1/admin/products` | Danh sách sản phẩm quản trị | Hoàn thành |
| 14 | `GET` | `/api/v1/admin/products/:id` | Chi tiết sản phẩm phục vụ form sửa | Hoàn thành |
| 15 | `POST` | `/api/v1/admin/products` | Thêm mới sản phẩm với thuộc tính đa hình | Hoàn thành |
| 16 | `PATCH`| `/api/v1/admin/products/:id` | Cập nhật thông tin sản phẩm và version | Hoàn thành |
| 17 | `POST` | `/api/v1/admin/products/:id/archive`| Lưu trữ (Archive) sản phẩm | Hoàn thành |
| 18 | `GET` | `/api/v1/admin/categories` | Danh sách ngành hàng | Hoàn thành |
| 19 | `POST` | `/api/v1/admin/categories` | Tạo ngành hàng mới kèm productType | Hoàn thành |
| 20 | `PATCH`| `/api/v1/admin/categories/:id` | Chỉnh sửa tên, slug ngành hàng | Hoàn thành |
| 21 | `DELETE`| `/api/v1/admin/categories/:id`| Xóa ngành hàng có kiểm tra toàn vẹn | Hoàn thành |
| 22 | `GET` | `/api/v1/admin/users` | Danh sách người dùng hệ thống | Hoàn thành |
| 23 | `PATCH`| `/api/v1/admin/users/:id/status` | Khóa hoặc mở khóa tài khoản khách hàng | Hoàn thành |
| 24 | `POST` | `/api/v1/orders` | Đặt hàng VNPAY (nhận paymentUrl) & COD | Hoàn thành |
| 25 | `GET` | `/api/v1/payments/vnpay/return` | Xác thực chữ ký và kết quả VNPAY Return | Hoàn thành |
| 26 | `POST` | `/api/v1/orders/:id/payment-attempts` | Tạo phiên thanh toán mới / thử lại cho đơn VNPAY | Hoàn thành |

---

## 10. Trạng Thái Responsive & Trải Nghiệm Thiết Bị

Hệ thống được kiểm thử tự động trên 3 kích thước màn hình tiêu chuẩn:
- **Desktop (1440x900)**: Layout mở rộng tối ưu, Sidebar cố định bên trái, lưới Dashboard 4 KPI trải ngang, 2 biểu đồ lớn song song, bảng quản trị rộng rãi đầy đủ cột.
- **Tablet (900x768)**: Sidebar thu gọn vào Drawer, Header hiển thị nút Hamburger toggle, các thẻ KPI tự động ngắt dòng 2 cột, bảng dữ liệu hỗ trợ thanh cuộn ngang mượt mà.
- **Mobile (390x844)**: Tối ưu hoàn toàn cho cảm ứng, Drawer mở trượt có hiệu ứng mượt mà, KPI xếp chồng 1 cột, các nút thao tác đơn hàng chuyển thành khối bấm rõ ràng.

---

## 11. Kết Quả TypeScript & Production Build

- Trình biên dịch: `tsc -b && vite build`.
- Kết quả biên dịch: **0 lỗi TypeScript, 0 lỗi cảnh báo cú pháp**.
- Artifact đầu ra (`dist/`):
  - `dist/index.html`: `0.83 kB`
  - `dist/assets/index-CtM2om75.css`: `41.43 kB` (gzip: `7.46 kB`)
  - `dist/assets/index-CDJJ-r_9.js`: `866.58 kB` (gzip: `236.59 kB` - bao gồm toàn bộ Recharts, Lucide Icons, Router, và các trang quản trị).

---

## 12. Kiểm Tra Không Suy Thoái Khách Hàng (Customer Regression Check)

Toàn bộ luồng khách hàng từ Phase FE-01 đã được kiểm tra lại trên hệ thống thật và hoạt động 100% ổn định:
- Đăng nhập / Đăng xuất Khách hàng (`customer01@example.test`): Status 200, JWT lưu trữ hợp lệ.
- Duyệt Catalog, Danh mục, Xem chi tiết sản phẩm: Đầy đủ và mượt mà.
- Thêm vào giỏ hàng, cập nhật số lượng: Chuẩn xác.
- Đặt hàng COD (End-to-End): Snapshot bất biến ghi nhận chính xác, đơn hàng hiển thị trong mục "Đơn hàng của tôi".
- **Bảo Vệ Phân Quyền**: Khách hàng cố tình truy cập `/admin/*` bị chặn ngay lập tức bởi `ProtectedRoute` với giao diện thông báo 403.

---

## 13. Frontend API Requirement (Khảo Sát Yêu Cầu Backend)

1. **Ràng Buộc Ngành Hàng (Category Reference Integrity)**:
   - Endpoint `DELETE /api/v1/admin/categories/:id` trả về `409 Conflict` (kèm mã `CATEGORY_IN_USE`) nếu ngành hàng đang có sản phẩm. Frontend đã xử lý bắt lỗi này hiển thị trực quan cho Quản trị viên. Đề xuất: Trong tương lai có thể bổ sung trường `productCount` trong response `GET /api/v1/admin/categories` để Quản trị viên nhận biết trước trên bảng danh sách.
2. **Cấu Hình Cổng VNPAY**:
   - Khi môi trường triển khai thực tế có khóa VNPAY Sandbox, chỉ cần kích hoạt `VNPAY_ENABLED=true` ở Backend; Frontend đã hoàn thiện 100% mã nguồn để xử lý chuyển hướng `paymentUrl` và đón nhận kết quả tại `/payment/return`.

---

## 14. Trạng Thái VNPAY Sandbox Thật (Live Sandbox Status)

> [!WARNING]
> **LIVE SANDBOX BLOCKED**:
> Môi trường máy chủ hiện tại chưa được cấu hình tài khoản thương nhân thật (`VNP_TMN_CODE`, `VNP_HASH_SECRET`) và chưa có URL IPN công khai (Public Webhook) được đăng ký trên cổng VNPay Sandbox.
> Do đó, cờ `VNPAY_ENABLED` trên máy đang đặt là `false`. Frontend đã được thiết kế sẵn sàng toàn bộ cơ chế chuyển hướng, tiếp nhận kết quả và cơ chế fallback an toàn (bắt mã `503 Service Unavailable` mà không gây gián đoạn phiên làm việc). Không công bố nghiệm thu kết nối tiền thật / sandbox trực tiếp khi chưa có credentials chính thức từ người dùng.

---

## 15. Tồn Đọng & Kế Hoạch Tiếp Theo (Deferred)

- **Không có bug runtime hoặc compile error nào tồn đọng.**
- **Deferred (Nằm ngoài phạm vi đồ án)**:
  - Tích hợp tiền thật / cổng thanh toán ngân hàng trực tiếp.
  - Phân quyền nhiều cấp (Shipper, Seller, Kế toán) do đồ án thống nhất chỉ có 2 vai trò: `CUSTOMER` và `ADMIN`.

---

## 16. Kết Quả Kiểm Thử E2E Tự Động (E2E Verification Summary)

Bộ kiểm thử tự động `frontend/tests/e2e-fe-02-verification.mjs` chạy qua trình duyệt Microsoft Edge không đầu (headless) kết nối trực tiếp Backend WSGI `127.0.0.1:5001` và Frontend Preview `127.0.0.1:5173`:

| Nhóm Kiểm Thử | Số Flow | Kết Quả |
|:---|:---:|:---:|
| 1. Customer Regression & Bảo Vệ Quyền Truy Cập (Login, Chặn 403, Duyệt Catalog) | 3 | **3/3 PASS** |
| 2. Admin Login & Dashboard Aggregation (4 KPI, Recharts, Top 5, Bộ lọc UTC) | 5 | **5/5 PASS** |
| 3. Quản Lý Đơn Hàng Admin (Danh sách đơn, Chi tiết Snapshot, allowedActions) | 2 | **2/2 PASS** |
| 4. Quản Lý Sản Phẩm & Form Đa Hình (List, Form New, FASHION attributes, HOME_APPLIANCE attributes) | 4 | **4/4 PASS** |
| 5. Quản Lý Ngành Hàng Admin (List categories, Modal New category) | 2 | **2/2 PASS** |
| 6. Quản Lý Người Dùng & Bất Biến Admin (List users, Khóa bảo vệ Admin) | 2 | **2/2 PASS** |
| 7. Tiếp Nhận VNPAY Return (/payment/return an toàn, xử lý 503 fallback) | 1 | **1/1 PASS** |
| 8. Responsive Viewports (Desktop 1440px, Tablet 900px, Mobile 390px Drawer) | 3 | **3/3 PASS** |
| **TỔNG CỘNG** | **22** | **22/22 PASS (100%)** |

---

## 17. Tuyên Bố Hoàn Thành

**PHASE FE-02 FRONTEND COMPLETE.**  
Hệ thống Admin Portal Novamart và luồng tích hợp VNPAY Frontend đã được hoàn thiện toàn diện, kiểm thử thực tế và sẵn sàng nghiệm thu.  
Theo đúng quy trình phát triển, Frontend Agent xin dừng tại đây để chờ người dùng review và chỉ đạo bước tiếp theo.
