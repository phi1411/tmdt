# Shopping Cart

## Goal

Giỏ hàng persist server, source of truth để checkout. P0; chưa implement. Đọc ADR-004, BR-CART và Product read contract.

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

lineId opaque URL-encoded server ID. GET line fields: productId/name/image/currentPrice/quantity/selectedAttributes/lineTotal/available/issues; subtotal chỉ available lines và `checkoutAllowed=false` nếu có issue, không coi subtotal là báo giá cuối.

## Data

Read/write carts, read products/categories; no Orders/payments writes. Paths `api/cart.py`, `services/cart_service.py`, `repositories/cart_repository.py`, Product/Category read methods, `schemas/cart_schema.py`, `features/cart/`. Chỉ đọc checkout doc nếu task đổi contract Cart→Checkout.

## Validation

Quantity int1..99, max50 lines đã khóa; selected keys size/color allowed/membership; no boolean/float/price; version nonnegative int. Sum requested quantity same Product across lines before stock check.

## Edge Cases

Product missing/inactive, stock reduced, Product price/attributes changed, version stale, simultaneous add/remove, no Cart/empty; changing selection cần remove/add, chưa PATCH arbitrary attributes. Cart update không tự cập nhật Order.

## Security

Owner enforced in query; input operators reject, no trust frontend totals; bounded array/selection sizes. Current price read không lộ hidden product detail ngoài thông tin dòng Cart cần xử lý.

## UI Behavior

Quantity controls/loading per line, conflicts refresh Cart, unavailable issue và delete; show giá hiện tại và ghi giá kiểm tra lại ở Checkout. Checkout button disabled empty/issues, server vẫn validate độc lập.

## Acceptance Criteria

Add/update/delete/clear persist cùng owner; current pricing; stock/selection/version enforced; multi-selection không vượt pool stock; lazy-create race không duplicate Cart.

## Testing Checklist

- [ ] Merge/selection/total qty/invalid price và ownership.
- [ ] Stock0/inactive/category archived/missing/price changed.
- [ ] Stale/concurrent mutations, lazy upsert and empty Cart.
