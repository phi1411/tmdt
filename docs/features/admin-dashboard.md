# Admin Dashboard và MongoDB Aggregation

## Goal

Dashboard chứng minh MongoDB xử lý doanh thu/time/Top5 và các metric sản phẩm. Backend PHASE06B IMPLEMENTED:5API/8canonical pipelines trên MongoDB thật; frontend chưa làm. Đọc BR-REPORT/ADR-005 và [review06B](../phase-06b-review.md).

## Actors

ADMIN only; SV2 thiết kế query, SV3 tích hợp Web/benchmark/demo.

## Functional Requirements

Total Revenue/Orders/Products Sold/Customers; day/month revenue; Top5; category revenue; order status distribution. Pipeline→Flask→REST→React/Recharts, không tải toàn Orders lên browser để cộng. Filter từ/to timezone Việt Nam, metadata định nghĩa metric, empty buckets0.

## Business Rules

BR-REPORT: revenue merchandise completed+paid theo completedAt, ship excluded; discount0. Total Orders/status theo createdAt; Customers global count current role CUSTOMER gồm blocked. Top rank quantity→revenue→productId; snapshot names gần nhất; category group snapshot ID. Không cộng Order.total sau unwind, không `$lookup` Product lấy current price.

## Permission

All `/admin/dashboard/*` ADMIN server auth. Guest/Customer không nhận raw report/order data.

## API

| Method / path | Request | Response data | Error |
| --- | --- | --- | --- |
| GET /admin/dashboard/summary | from,to UTC | 200 summary + reportMetadata | 401/403/422/503 |
| GET /admin/dashboard/revenue | from,to,interval=day/month | 200 {series:[{bucket,revenue,orders}],...metadata} | 401/403/422/503 |
| GET /admin/dashboard/top-products | from,to | 200 {items:[{productId,productName,quantity,revenue}],...metadata} max5 | 401/403/422/503 |
| GET /admin/dashboard/category-revenue | from,to | 200 {items:[{categoryId,categoryName,revenue}],...metadata} | 401/403/422/503 |
| GET /admin/dashboard/order-status | from,to | 200 {items:[{status,count}],dateBasis:createdAt,...metadata} | 401/403/422/503 |

Envelopes/bucket/time metadata api-conventions canonical. from/to bắt buộc; revenue interval mặc định day. Metadata `{currency,timezone,from,to,revenueBasis,fetchedAt}` với VND/Asia/Ho_Chi_Minh/PAID_COMPLETED_MERCHANDISE, times UTC milliseconds Z. Revenue thêm interval, status thêm dateBasis. Không endpoint nhận pipeline JSON hoặc tự thêm payment method/status charts ngoài design.

## Data

Source dưới `backend/app`: `api/admin_dashboard.py`, `services/dashboard_service.py`, `repositories/dashboard_repository.py`, `schemas/dashboard_schema.py`; canonical `database/aggregations/`; test `backend/tests/test_admin_analytics.py`. Read-only Order snapshots/users customer count, no Product/Category lookup. Direct dependencies BR-REPORT/Order schema/user.role count/index ADR/auth/validation/envelopes; không Cart/Payment adapter/Review. Frontend vẫn dự kiến.

### Canonical aggregation design

Pipeline definitions chỉ ở [database/aggregations](../../database/aggregations/README.md): Revenue Day/Month, Top5, CategoryRevenue, SalesSummary, OrderCount/Status và CustomerCount. Exact EJSON/stage/field mappings ở đó; feature doc không giữ bản pipeline thứ hai.

Repository decode EJSON canonical với tz-aware Date, cache8templates/deep-copy/bind range vào initial match. Không duplicate pipeline trong backend. Top5 match/sort latest/unwind/group/sort rank/limit/project, no lookup. Summary dùng sales-summary/order-count/customer-count; các reports còn lại dùng đúng artifact. maxTimeMS10000/allowDiskUse=false; backend không tải Orders về Python để cộng/group, chỉ metadata/default/bucket filling.

## Validation

Full ISO UTC seconds/Z/+00:00/fractional1..6, năm tối đa9998 tránh calendar overflow; from/to bắt buộc, from<to, window<=366×24h. Interval day/month, ZoneInfo Asia/Ho_Chi_Minh, unknown/repeated query422. Daily/monthly labels YYYY-MM-DD/YYYY-MM. Bucket điền0 nếu giao window, tối đa367day buckets khi partial-day boundaries. Money/units integer0..2^53-1; vượt giới hạn→503, không float rounding.

## Edge Cases

No qualified orders→summary0 (Customers vẫn global), Top/category[], series bucket0. Status đủ6states PENDING/CONFIRMED/SHIPPING/COMPLETED/CANCELLED/EXPIRED, missing count0. VN month/day/leap boundaries, shipping>0, top ties/<5, renamed/missing current Product/Category không đổi report. PENDING không tăng revenue; COD completion delta subtotal. Các query/HTTP reports độc lập, không cam kết snapshot xuyên calls.

## Security

Admin guard, query allowlist/range cap, no arbitrary aggregation injection, no PII in response. Không expose explain public; DB credentials chỉ backend.

## UI Behavior

KPI cards nhãn rõ doanh thu hàng hóa, Customers toàn hệ thống; day/month switch; Top5/category/status charts. Loading/error/empty riêng từng panel, không fake0 khi API fail; metadata và fetchedAt; refresh sau hoàn tất đơn, ngày inclusive UI chuyển to-exclusive UTC.

## Acceptance Criteria

MongoDB thật trả fixture450 revenue/8units/Top5, đủ4required stages, no live history lookup/current prices, COD completion delta đúng, timezone/explain evidence. Definition giữ ADR007; full benchmark/UI kiểm tra phase sau.

## Testing Checklist

- [x] Fixture450/8units, dates/status/global Customers/empty/default buckets.
- [x] Shipping excluded, unwind không nhân Order total; live Product đổi giá/name/delete không đổi report.
- [x] Timezone/range/leap/boundaries/ties/Top5 limit/authorization/query allowlists.
- [x] Mongo executionStats, named-index/natural equal results, real HTTP và COD completion delta.
- [ ] Frontend/Web rehearsal/full benchmark chưa triển khai.
