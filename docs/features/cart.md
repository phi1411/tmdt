# Shopping Cart

## Goal

Giỏ hàng persist server, source of truth để checkout. **PHASE05C backend IMPLEMENTED**, frontend deferred. Đọc ADR-004, BR-CART, [API contract](../api-contract.md) và [review](../phase-05c-review.md).

## Actors

Customer. Guest xem shop và đăng nhập trước add; Admin không dùng Cart baseline.

## Functional Requirements

Get Cart, add/merge line, update quantity, delete line/clear, current price/totals/availability; versioned mutations. Không giữ hàng khi add, không guest merge Cart.

## Business Rules

BR-CART: same Product/canonical selection merge; khác selection cùng shared stock. Tổng quantity mọi line Product<=stock; Product+Category ACTIVE. Không nhận price client. GET invalid line giữ lại và đánh issues. Cart chưa có trả version0/items=[]; first add create lazily; concurrent first add unique userId guard.

## Permission

Customer owner từ JWT; không route `/cart/:userId`. Admin/Guest mutation403/401.

## API

| Method / path | Request | Response data | Error |
| --- | --- | --- | --- |
| GET /cart | Bearer | 200 {version,items,current totals,issues} | 401/403 |
| POST /cart/items | {productId,quantity,selectedAttributes,cartVersion} | 200 updated Cart | 404 Product;409 stock/stale/inactive;422 |
| PATCH /cart/items/:lineId | {quantity,cartVersion} | 200 updated Cart | 404 line;409;422 |
| DELETE /cart/items/:lineId | {cartVersion} | 204 | 404 line;409 stale |
| DELETE /cart | {cartVersion} | 204 | 409 stale |

lineId là SHA256 hex64 canonical do server tạo, truyền nguyên trong URL. GET line fields: lineId/productId/name/slug/image/currentPrice/quantity/selectedAttributes/stock/lineTotal/available/issues; subtotal chỉ available lines và `checkoutAllowed=false` nếu rỗng/có issue, không coi subtotal là báo giá cuối. Missing Product giữ dòng: name/slug/currentPrice=null, image rỗng, stock/lineTotal0. Issue codes PRODUCT_MISSING/PRODUCT_UNAVAILABLE/CATEGORY_UNAVAILABLE/SELECTION_CHANGED/STOCK_CONFLICT. Không nhận query. DELETE dùng JSON body; frontend GET sau204 lấy version mới. Clear Cart chưa có với version0 no-op; Cart tồn tại clear tăng version và giữ document.

## Data

Read/write carts, read products/categories; no Orders/payments writes. Backend paths `app/api/cart.py`, `app/services/cart_service.py`, `app/services/commerce_pricing.py`, `app/repositories/cart_repository.py`, ProductRepository.find_many/CategoryRepository.find, `app/schemas/cart_schema.py`; tests `backend/tests/test_commerce.py`. Dependency Auth/current User và shared validation/errors/serialization. Frontend `features/cart/` chưa tạo. Owner/version CAS và unique userId index xử lý lazy insert race→CART_CHANGED409, không cơ chế version khác.

## Validation

Quantity int1..99, max50 lines đã khóa; selected keys size/color allowed/membership; no boolean/float/price; version nonnegative int. Sum requested quantity same Product across lines before stock check.

## Edge Cases

Product missing/inactive, stock reduced, Product price/attributes changed, version stale, simultaneous add/remove, no Cart/empty; changing selection cần remove/add, chưa PATCH arbitrary attributes. Cart update không tự cập nhật Order.

## Security

Owner enforced in query; input operators reject, no trust frontend totals; bounded array/selection sizes. Current price read không lộ hidden product detail ngoài thông tin dòng Cart cần xử lý.

## UI Behavior

Quantity controls/loading per line, conflicts refresh Cart, unavailable issue và delete; show giá hiện tại và ghi giá kiểm tra lại ở Checkout. Checkout button disabled empty/issues, server vẫn validate độc lập.

UI19/10/2026: Product card/detail mở bảng chọn phân loại trước add. Confirm gửi productId/quantity/selectedAttributes qua CartContext hiện hữu; không gọi mutation trước khi khách xác nhận đầy đủ. Không đóng/chuyển Cart nếu API add thất bại; backend tiếp tục quyết định giá/tồn/validation. Mua ngay chuyển Cart sau add thành công, không tự đặt đơn hoặc thanh toán.

## Acceptance Criteria

Add/update/delete/clear persist cùng owner; current pricing; stock/selection/version enforced; multi-selection không vượt pool stock; lazy-create race không duplicate Cart.

## Testing Checklist

- [x] Backend merge/canonical selection/shared total qty/invalid price và ownership.
- [x] Stock0/inactive/category archived/missing/price changed; invalid line vẫn remove được.
- [x] Stale/concurrent CAS, lazy insert unique guard và empty/clear retained version.
- [ ] Frontend Cart UI/E2E deferred.


## Audit20/10/2026 — canonical SKU identity

Cùng SKU phải gộp thành một dòng dù request có/không gửi skuId optional. POST add chuẩn hóa selection theo SKU server đã resolve và gộp các alias hợp lệ có sẵn của đúng SKU đó trong Cart, giữ thứ tự dòng đầu; áp dụng giới hạn99 sau khi cộng tất cả alias. SKU khác và dòng không còn resolve hợp lệ không bị gộp. Không đổi GET hoặc tự migration toàn DB; mutation vẫn cartVersion CAS, reject/stock conflict không ghi Cart. Regression4cases: hai thứ tự optional skuId, không bypass99 và merge Cart legacy trước checkout snapshot.
