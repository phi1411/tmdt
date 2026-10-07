# Admin Dashboard và MongoDB Aggregation

## Goal

Dashboard chứng minh MongoDB xử lý doanh thu/time/Top5 và các metric sản phẩm. P0 doanh thu/Top5; P1 metrics bổ sung. Chưa implement/chạy pipeline. Đọc BR-REPORT và ADR-005.

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
| GET /admin/dashboard/revenue | from,to,interval=day/month | 200 {series:[{bucket,revenue,orders}],...metadata} | 401/403/422 |
| GET /admin/dashboard/top-products | from,to | 200 {items:[{productId,productName,quantity,revenue}],...metadata} max5 | 401/403/422 |
| GET /admin/dashboard/category-revenue | from,to | 200 {items:[{categoryId,categoryName,revenue}],...metadata} | 401/403/422 |
| GET /admin/dashboard/order-status | from,to | 200 {items:[{status,count}],dateBasis:createdAt,...metadata} | 401/403/422 |

Envelopes/bucket/time metadata api-conventions canonical. Không endpoint nhận pipeline JSON từ client.

## Data

Read orders snapshots, users for customer count, no writes; no Product lookup. Paths `api/admin_dashboard.py`, `services/dashboard_service.py`, `repositories/dashboard_repository.py`, `schemas/dashboard_schema.py`; canonical artifacts `database/aggregations/`; frontend `features/admin-dashboard/`. Direct dependencies Order schema/BR-REPORT, user.role count, index ADR; không đọc Cart/Payment adapter/Review implementation.

### Canonical aggregation design

Pipeline definitions chỉ ở [database/aggregations](../../database/aggregations/README.md): Revenue Day/Month, Top5, CategoryRevenue, SalesSummary, OrderCount/Status và CustomerCount. Exact EJSON/stage/field mappings ở đó; feature doc không giữ bản pipeline thứ hai.

Revenue pipeline match/group/sort, Top5 match/unwind/group/sort/limit; mọi historical metrics đọc snapshot và không lookupProduct. BR-REPORT/ADR007 là semantic source; runtime repository sau này decode/bind JSON designs, không cho client gửi arbitrarypipeline.

## Validation

from<to, Dates parse UTC, interval enum, range cap đã khóa366ngày; timezone cố định, no client pipeline/field name. completedAt required khi COMPLETED trong service. Revenue/units long/integer tránh float; API kiểm tra safe range.

## Edge Cases

No qualified orders, only cancelled/unpaid, month/day boundary VN, shipping>0, top tie/<5 products, renamed Product/Category, out-of-range/stale data. Live checkout PENDING không làm revenue tăng đến completed+paid.

## Security

Admin guard, query allowlist/range cap, no arbitrary aggregation injection, no PII in response. Không expose explain public; DB credentials chỉ backend.

## UI Behavior

KPI cards nhãn rõ doanh thu hàng hóa, Customers toàn hệ thống; day/month switch; Top5/category/status charts. Loading/error/empty riêng từng panel, không fake0 khi API fail; metadata và fetchedAt; refresh sau hoàn tất đơn, ngày inclusive UI chuyển to-exclusive UTC.

## Acceptance Criteria

MongoDB thật trả metrics đúng fixture450 revenue/8 units/Top5, đủ4 stages trong Top5, no history lookup/current prices, no frontend raw Order calculation. Dashboard động sau COD completion, index/explain evidence và timezone đúng. Definition đã khóa tại ADR007; runtime correctness và benchmark vẫn kiểm tra phase sau.

## Testing Checklist

- [ ] Fixture totals/day/month/top/category/status/customer date bases.
- [ ] Shipping excluded, unwind no duplicate order total, Product price10→12 does not alter report.
- [ ] Timezone/from-to/empty/ties/renames, Admin authorization.
- [ ] Explain with/without index equal results; Web API network and live demo delta.
