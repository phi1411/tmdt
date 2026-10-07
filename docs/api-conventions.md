# Quy ước REST API

**PHASE04 đã duyệt; PHASE05A health/common helpers và Auth/User/Admin User backend IMPLEMENTED.** Các phần ngoài Auth/User theo phase/worker riêng; trạng thái cụ thể tại [api-contract](api-contract.md). Prefix `/api/v1`; JSON UTF-8; path dưới đây tương đối prefix. IPN VNPAY là ngoại lệ envelope và response code theo provider khi feature được triển khai. Feature docs sở hữu endpoint; bảng này sở hữu conventions dùng chung.

## Success, error và kiểu dữ liệu

```json
{"data":{"id":"000000000000000000000101","price":10000000},"meta":{"requestId":"opaque-request-id"}}
```

```json
{"error":{"code":"VALIDATION_ERROR","message":"Dữ liệu không hợp lệ","details":[{"field":"quantity","reason":"Phải là số nguyên từ 1 đến 99"}]},"meta":{"requestId":"opaque-request-id"}}
```

List: `data:[]`, `meta:{requestId,page,pageSize,total,totalPages}`. Detail/mutation: `data:object`. DELETE thành công 204 không body. Không bọc danh sách thành `data.data`; không leak stack, Mongo query hoặc passwordHash. ObjectId string lowercase hex 24 ký tự; Date ISO 8601 UTC có `Z`; tiền JSON integer VND. Enum uppercase. Report trả `currency`, `timezone`, `from`, `to`, `revenueBasis` để tránh biểu đồ hiểu khác server.

| HTTP | Khi dùng | Error code điển hình |
| --- | --- | --- |
| 200 | GET/PATCH, action, idempotent replay | — |
| 201 | Tạo resource lần đầu; Location nếu có detail route | — |
| 204 | Delete/archive/xóa dòng thành công | — |
| 400 | JSON/query syntax không parse được, ID sai format | BAD_REQUEST |
| 401 | Không đăng nhập, token invalid/hết hạn/User blocked | UNAUTHENTICATED |
| 403 | Role không đủ | FORBIDDEN |
| 404 | Resource thiếu hoặc không thuộc owner | NOT_FOUND |
| 409 | Duplicate/stale/business transition/stock/quote | DUPLICATE_RESOURCE, CART_CHANGED, STOCK_CONFLICT, PRICE_CHANGED, INVALID_TRANSITION, IDEMPOTENCY_CONFLICT |
| 422 | Body shape/value/field không cho phép | VALIDATION_ERROR |
| 429 | Rate limit auth/payment | RATE_LIMITED |
| 503 | DB/provider unavailable | SERVICE_UNAVAILABLE |
| 500 | Lỗi server bất ngờ, log requestId | INTERNAL_ERROR |

Không trả 200 với `success:false`. DB duplicate-key map thành 409. Query/body unknown field reject 422; query operator/object client cung cấp không chuyển thẳng PyMongo.

## Auth/ownership

`Authorization: Bearer <access JWT>`. JWT trong memory frontend, không localStorage trong baseline. CORS allowlist origin từ config; không wildcard với credential. Không cookie auth baseline nên không ngầm thiết kế refresh/CSRF khác. Mọi protected API kiểm tra User ACTIVE/tokenVersion/role hiện hành. Resource owner lấy từ subject, không từ body.userId. Admin endpoints `/admin/*`; Customer mutation `/cart`, `/orders`, `/users/me`.

## Pagination, filter và concurrency

- `page` mặc định1 và >=1, `pageSize` mặc định20, max100. Integer strict. Pagination offset phù hợp dataset học thuật; mở rộng cursor chỉ khi có ADR.
- Sort allowlist theo feature: price_asc price/_id asc; price_desc price/_id desc; latest createdAt/_id desc. Product sort mặc định latest, Order lists luôn latest trong baseline. Không nhận sort object/raw query.
- Product filter: `q`, `categoryId`, `productType`, `brand`, `minPrice`, `maxPrice`, `sort`, `page`, `pageSize`, key attribute đã cho phép. q <=100 ký tự, escaped/normalized; không regex raw.
- Admin/Customer Order filter `status`, `from`, `to` theo createdAt; report theo metric contract completedAt.
- `[from,to)`, ISO UTC cho API; timezone báo cáo cố định `Asia/Ho_Chi_Minh`. UI ngày kết thúc inclusive phải đổi thành đầu ngày kế tiếp theo local timezone.
- Cart mutation có `cartVersion`; Admin Product/Category/User/Order mutation có `expectedVersion` (version tăng trong cùng write). Không dùng thời gian client làm concurrency token.
- Checkout `Idempotency-Key: opaque string 8..128`; payment attempt creation cũng có key, scope Order. Hash body canonical và không lưu secret trong hash input.

## Checkout quote contract

`GET /checkout/quote?addressId=<id>&paymentMethod=COD|VNPAY` trả `{cartVersion,items,subtotal,shippingFee,discount:0,total,currency:"VND",quoteToken,expiresAt,issues:[]}`. quoteToken do server ký, bound user/addressId/addressHash/payment/cartVersion và price/selection/fee; frontend gửi nguyên token khi POST /orders. Thiếu/bị sửa token →422; hết hạn →409 `QUOTE_EXPIRED`; giá/fees khác →409 `PRICE_CHANGED`, địa chỉ cùng ID đổi nội dung→409 `QUOTE_CHANGED`; lấy quote mới. Quote không giữ stock.

`POST /orders`: `{cartVersion,addressId,paymentMethod,quoteToken}` + Idempotency-Key. Response `{order, payment:{method,attemptId?,paymentUrl?,expiresAt?}}`; nếu link provider chưa dựng được, vẫn trả Order commit và `payment.retryRequired:true`, không ngụy trang checkout chưa tạo đơn.

## Report contract

`GET /admin/dashboard/summary?from=<UTC>&to=<UTC>` → `{totalRevenue,totalOrders,totalProductsSold,totalCustomers,currency,timezone,from,to,revenueBasis:"PAID_COMPLETED_MERCHANDISE"}`.

`GET /admin/dashboard/revenue?...&interval=day|month` → `{series:[{bucket:"2026-09-01",revenue:10400000,orders:1}],...reportMetadata}`; tháng bucket `2026-09`.

`GET /admin/dashboard/top-products?...` → `{items:[{productId,productName,quantity,revenue}],...reportMetadata}` (tối đa 5).

`GET /admin/dashboard/category-revenue?...` → `{items:[{categoryId,categoryName,revenue}],...reportMetadata}`.

`GET /admin/dashboard/order-status?...` → `{items:[{status,count}],dateBasis:"createdAt",...reportMetadata}`.

Window tối đa đã khóa366ngày; from<to, interval allowlist. API không trả raw Orders cho Dashboard tính toán. Empty group trả 0/[] và backend điền bucket rỗng. Luồng nhiều endpoint có thể thấy snapshot khác nhau nếu dữ liệu đổi giữa các call; chưa cam kết read snapshot xuyên HTTP request. Cần Dashboard refresh đồng bộ UI và ghi fetchedAt, không yêu cầu consistency tuyệt đối kiểu BI.

## Versioning và security

API contract đổi phải update feature doc và tests; breaking change cần ADR. Login sai dùng message chung, rate-limit theo IP/account, không tiết lộ User tồn tại. HTTPS khi kết nối ngoài localhost; secrets không đưa vào VITE_ env. IPN chỉ nhận allowlist, verify chữ ký trước DB write; response theo [VNPAY](https://sandbox.vnpayment.vn/apis/docs/thanh-toan-pay/pay.html), không dùng envelope thông thường.
