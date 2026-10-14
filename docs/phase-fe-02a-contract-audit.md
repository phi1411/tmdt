# BÁO CÁO KIỂM TOÁN TÍNH NHẤT QUÁN API CONTRACT (FE-02A CONTRACT AUDIT)

Ngày thực hiện: 07/10/2026  
Người thực hiện: Frontend Agent (Antigravity)  
Trạng thái: **FE-02A API CONTRACT CONSISTENCY PASS — DỪNG ĐỂ REVIEW**

---

## 1. Mục Tiêu & Căn Cứ Kiểm Toán

Thực hiện rà soát, đối chiếu và chuẩn hóa toàn bộ mã nguồn Frontend ([`frontend/src`](file:///c:/Users/Admin/Documents/ChatGPT/tmdt/frontend/src)) với **nguồn sự thật (Source of Truth)** của hệ thống:
- [`docs/api-contract.md`](file:///c:/Users/Admin/Documents/ChatGPT/tmdt/docs/api-contract.md)
- [`docs/phase-06ab-integration-review.md`](file:///c:/Users/Admin/Documents/ChatGPT/tmdt/docs/phase-06ab-integration-review.md)
- Codebase Backend đã hoàn thành và khóa: [`backend/app/api/`](file:///c:/Users/Admin/Documents/ChatGPT/tmdt/backend/app/api), [`backend/app/schemas/`](file:///c:/Users/Admin/Documents/ChatGPT/tmdt/backend/app/schemas), [`backend/app/services/`](file:///c:/Users/Admin/Documents/ChatGPT/tmdt/backend/app/services).

Nguyên tắc tuân thủ tuyệt đối:
- **KHÔNG thêm feature mới**.
- **KHÔNG redesign**.
- **KHÔNG sửa Backend** (backend giữ nguyên 100%).
- Chỉ hiệu chỉnh tối thiểu và chính xác tại Frontend để đạt chuẩn API Contract đồng nhất.

---

## 2. Kết Quả Kiểm Toán 3 Trọng Tâm Chính

### 2.1. Canonical VNPAY Flow
- **Đối chiếu Backend Contract (`api-contract.md` dòng 132, 151, 159, 163)**:
  - Khi đặt hàng online: `POST /api/v1/orders` nhận `{ cartVersion, addressId, paymentMethod: "VNPAY", quoteToken }` kèm header `Idempotency-Key`. Backend tạo Order `PENDING` và atomic initial attempt trong transaction, trả về response `201 { order, payment: { method: "VNPAY", attemptId, attemptStatus, expiresAt, paymentUrl?, retryRequired? } }`.
  - Frontend sử dụng `paymentUrl` từ kết quả checkout để chuyển hướng (`window.location.href = paymentUrl`).
  - Nếu `paymentUrl` không có hoặc khi thử lại (retry attempt cho đơn chưa thanh toán): Endpoint chuẩn tắc là `POST /api/v1/orders/:id/payment-attempts` (nhận body `{ expectedVersion: number }` và header `Idempotency-Key`).
  - Trang kết quả VNPAY Return: `GET /api/v1/payments/vnpay/return?<queryString>` (chỉ đọc, xác thực chữ ký HMAC-SHA512 an toàn, không tự đánh dấu PAID).
  - Trạng thái thanh toán thực tế do IPN Webhook (`GET /api/v1/payments/vnpay/ipn`) xử lý authoritative trên backend. Frontend kiểm tra qua việc thăm dò `GET /api/v1/orders/:id` (owner).
- **Rà soát & Sửa đổi Frontend**:
  - `frontend/src/api/paymentApi.ts`: Endpoint `createPaymentAttempt` đã gọi đúng chuẩn `/orders/${orderId}/payment-attempts`.
  - `frontend/src/pages/CheckoutPage.tsx`: Đã cập nhật xử lý cả 2 trường hợp: nhận `paymentUrl` trực tiếp từ checkout response; nếu thiếu sẽ gọi fallback sang `paymentApi.createPaymentAttempt(res.order.id, res.order.version)`.
  - `frontend/src/pages/OrderDetailPage.tsx`: Bổ sung nút bấm "Thanh toán qua VNPAY" cho khách hàng khi đơn hàng ở trạng thái `PENDING` và chưa thanh toán, gọi trực tiếp `POST /api/v1/orders/:id/payment-attempts`.
  - Đảm bảo 100% amount (số tiền) do backend tính toán từ Order/Quote, frontend tuyệt đối không truyền số tiền lên server.

---

### 2.2. Canonical Dashboard Revenue Endpoint
- **Đối chiếu Backend Contract (`api-contract.md` dòng 193)**:
  - `GET /api/v1/admin/dashboard/revenue` (tham số bắt buộc `from`, `to` UTC ISO-8601; tham số tùy chọn `interval=day|month`).
  - Backend route đăng ký trong [`backend/app/api/admin_dashboard.py`](file:///c:/Users/Admin/Documents/ChatGPT/tmdt/backend/app/api/admin_dashboard.py) dòng 17: `@admin_dashboard_blueprint.get('/admin/dashboard/revenue')`.
  - Route `/admin/dashboard/revenue-series` **KHÔNG TỒN TẠI** trong backend.
- **Rà soát & Sửa đổi Frontend**:
  - Mã nguồn gọi API tại [`frontend/src/api/dashboardApi.ts`](file:///c:/Users/Admin/Documents/ChatGPT/tmdt/frontend/src/api/dashboardApi.ts) dòng 20: Đã gọi đúng `/admin/dashboard/revenue`.
  - Toàn bộ frontend không có call site nào gọi nhầm sang `revenue-series`.
  - Đã đính chính bảng kê trong tài liệu nghiệm thu [`docs/phase-fe-02-review.md`](file:///c:/Users/Admin/Documents/ChatGPT/tmdt/docs/phase-fe-02-review.md) từ chuỗi mô tả stale `/revenue-series` thành chuẩn xác `/revenue`.

---

### 2.3. Canonical Order Status Enum & Payment Status Enum
- **Đối chiếu Backend Contract (`backend/app/schemas/order_schema.py`, `dashboard_service.py`)**:
  - **`orderStatus` (6 trạng thái duy nhất)**:
    - `PENDING` (Chờ xử lý)
    - `CONFIRMED` (Đã xác nhận)
    - `SHIPPING` (Đang giao hàng)
    - `COMPLETED` (Hoàn thành)
    - `CANCELLED` (Đã hủy)
    - `EXPIRED` (Hết hạn giữ chỗ/thanh toán)
    > **Lưu ý then chốt**: `FAILED` **KHÔNG PHẢI** là một `orderStatus`! `FAILED` là trạng thái của thanh toán (`paymentStatus`).
  - **`paymentStatus` (5 trạng thái)**:
    - `UNPAID` (Chưa thanh toán - COD)
    - `PENDING` (Đang chờ thanh toán)
    - `PAID` (Đã thanh toán)
    - `FAILED` (Thanh toán thất bại)
    - `REVIEW_REQUIRED` (Cần đối soát)
- **Rà soát & Sửa đổi Frontend**:
  - [`frontend/src/types/order.ts`](file:///c:/Users/Admin/Documents/ChatGPT/tmdt/frontend/src/types/order.ts): `OrderStatus` đã chuẩn 6 enum, `PaymentStatus` đã chuẩn 5 enum.
  - [`frontend/src/types/dashboard.ts`](file:///c:/Users/Admin/Documents/ChatGPT/tmdt/frontend/src/types/dashboard.ts): `OrderStatusItem.status` được thu hẹp nghiêm ngặt thành chính xác 6 enum (`'PENDING' | 'CONFIRMED' | 'SHIPPING' | 'COMPLETED' | 'CANCELLED' | 'EXPIRED'`), loại bỏ fallback `string`.
  - [`frontend/src/pages/OrdersPage.tsx`](file:///c:/Users/Admin/Documents/ChatGPT/tmdt/frontend/src/pages/OrdersPage.tsx): Bổ sung tab lọc "Hết hạn" (`EXPIRED`) cho danh sách đơn hàng của Khách hàng; cập nhật badge thanh toán hỗ trợ đầy đủ `REVIEW_REQUIRED`.
  - [`frontend/src/pages/AdminOrdersPage.tsx`](file:///c:/Users/Admin/Documents/ChatGPT/tmdt/frontend/src/pages/AdminOrdersPage.tsx): Bộ lọc `status` và `paymentStatus` đã sử dụng độc lập và chính xác 100% 2 tập enum này.
  - [`frontend/src/pages/AdminDashboardPage.tsx`](file:///c:/Users/Admin/Documents/ChatGPT/tmdt/frontend/src/pages/AdminDashboardPage.tsx): Bảng màu và biểu đồ cột `orderStatus` hiển thị đúng 6 trạng thái (`COMPLETED`, `SHIPPING`, `CONFIRMED`, `PENDING`, `CANCELLED`, `EXPIRED`).

---

## 3. Kết Quả Tìm Kiếm Tĩnh (Static Search Audit)

| Chuỗi Tìm Kiếm | Vị Trí Xuất Hiện | Phân Loại | Kết Quả / Xử Lý |
|:---|:---|:---:|:---|
| `revenue-series` | `docs/phase-fe-02-review.md` | **Stale trong Docs** | Đã sửa trong review doc thành `/admin/dashboard/revenue`. Mã nguồn frontend đã dùng đúng `/revenue`. |
| `FAILED` | `src/types/order.ts`, `src/types/payment.ts`, `AdminOrdersPage.tsx`, `OrdersPage.tsx` | **Đúng** | Thuộc về `PaymentStatus` và `PaymentReturnResult.result`. Không tồn tại trong `OrderStatus`. |
| `PAYMENT_UNAVAILABLE` | `src/pages/CheckoutPage.tsx:86` | **Đúng** | Khớp chính xác mã lỗi HTTP 503 khi VNPAY chưa kích hoạt trên backend. |
| `paymentUrl` | `src/pages/CheckoutPage.tsx`, `PaymentReturnPage.tsx`, `types/checkout.ts`, `types/payment.ts` | **Đúng** | Khớp chính xác contract response từ Checkout và Payment Attempt. |
| `retry-attempt` | `docs/phase-fe-02-review.md` | **Stale trong Docs** | Đã sửa trong review doc thành `POST /api/v1/orders/:id/payment-attempts`. Không có trong code `src/`. |
| `payment-attempts` | `src/api/paymentApi.ts:12` | **Đúng** | Khớp chính xác endpoint canonical `POST /api/v1/orders/:id/payment-attempts`. |

---

## 4. Danh Sách Tệp Mã Nguồn Đã Hiệu Chỉnh Tối Thiểu

1. **[`frontend/src/types/dashboard.ts`](file:///c:/Users/Admin/Documents/ChatGPT/tmdt/frontend/src/types/dashboard.ts)**:
   - Thu hẹp kiểu `OrderStatusItem.status` thành chính xác 6 enum canonical của Backend.
2. **[`frontend/src/pages/OrdersPage.tsx`](file:///c:/Users/Admin/Documents/ChatGPT/tmdt/frontend/src/pages/OrdersPage.tsx)**:
   - Thêm tab trạng thái `EXPIRED` ("Hết hạn") vào danh sách tab lọc đơn hàng phía Khách hàng.
   - Bổ sung hiển thị `REVIEW_REQUIRED` trong `getPaymentStatusBadge`.
3. **[`frontend/src/pages/CheckoutPage.tsx`](file:///c:/Users/Admin/Documents/ChatGPT/tmdt/frontend/src/pages/CheckoutPage.tsx)**:
   - Tích hợp fallback gọi `paymentApi.createPaymentAttempt(res.order.id, res.order.version)` nếu checkout không trả sẵn `paymentUrl`.
4. **[`frontend/src/pages/OrderDetailPage.tsx`](file:///c:/Users/Admin/Documents/ChatGPT/tmdt/frontend/src/pages/OrderDetailPage.tsx)**:
   - Bổ sung nút thao tác "Thanh toán qua VNPAY" khi đơn hàng VNPAY ở trạng thái `PENDING` và chưa thanh toán, thực hiện đúng canonical flow `POST /orders/:id/payment-attempts`.
5. **[`docs/phase-fe-02-review.md`](file:///c:/Users/Admin/Documents/ChatGPT/tmdt/docs/phase-fe-02-review.md)**:
   - Sửa URL endpoint `/admin/dashboard/revenue-series` thành `/admin/dashboard/revenue`.
   - Sửa URL endpoint `/payments/vnpay/retry-attempt` thành `/orders/:id/payment-attempts`.
   - Đính chính danh sách enum trạng thái đơn hàng từ `FAILED` thành `EXPIRED`.

---

## 5. Kết Quả Kiểm Thử Sau Hiệu Chỉnh (Verification Results)

### 5.1. TypeScript Strict & Production Build
- Lệnh: `npm run build` (`tsc && vite build`)
- **Kết quả: 0 LỖI (0 errors, 0 warnings)**
- Bundle tạo mới trong `dist/`: `dist/assets/index-IQwOVkXp.js` (867.58 kB), `dist/assets/index-CtM2om75.css` (41.43 kB).

### 5.2. E2E Verification Suite (`frontend/tests/e2e-fe-02-verification.mjs`)
Chạy trực tiếp qua Edge headless kết nối Backend `127.0.0.1:5001` và Frontend `127.0.0.1:5173`:
- **Nhóm 1**: Customer Regression & Phân Quyền (Đăng nhập, chặn 403 khi vào Admin, duyệt catalog): **3/3 PASS**
- **Nhóm 2**: Admin Login & Dashboard Aggregations (4 thẻ KPI, Recharts, Top 5, UTC presets): **5/5 PASS**
- **Nhóm 3**: Quản lý Đơn hàng Admin (Danh sách đơn, Snapshot bất biến, `allowedActions`): **2/2 PASS**
- **Nhóm 4**: Quản lý Sản phẩm & Form Đa hình (`ELECTRONICS`, `FASHION`, `HOME_APPLIANCE`): **4/4 PASS**
- **Nhóm 5**: Quản lý Ngành hàng Admin (Danh sách, Modal tạo ngành hàng): **2/2 PASS**
- **Nhóm 6**: Quản lý Người dùng & Bảo vệ Admin: **2/2 PASS**
- **Nhóm 7**: Trang VNPAY Return (Xử lý 503 fallback khi VNPAY chưa bật trên dev): **1/1 PASS**
- **Nhóm 8**: Responsive Viewports (Desktop 1440px, Tablet 900px, Mobile 390px): **3/3 PASS**
- **TỔNG KẾT**: **22/22 FLOWS PASS (100% PASS, 0 FAIL)**.

---

## 6. Trạng Thái VNPAY Sandbox Thật (Live Sandbox Status)

> [!WARNING]
> **LIVE SANDBOX VẪN BLOCKED**:
> Môi trường hiện tại tiếp tục giữ nguyên cờ `VNPAY_ENABLED=false` do chưa có credentials Sandbox chính thức (`VNP_TMN_CODE`, `VNP_HASH_SECRET`) và URL IPN công khai.
> Frontend đã sẵn sàng 100% logic mã nguồn cho cả luồng Checkout Redirect, Retry Attempt, Verify Return và Polling Order. Không công bố pass sandbox trực tiếp khi chưa có cấu hình từ người dùng.

---

## TUYÊN BỐ NGHIỆM THU

**FE-02A API CONTRACT CONSISTENCY PASS.**

Toàn bộ các điểm sai lệch (mismatch) giữa tài liệu, contract và frontend đã được kiểm tra, giải quyết triệt để và đồng bộ hóa hoàn toàn.

Dừng lại tại đây để chờ người dùng review.
