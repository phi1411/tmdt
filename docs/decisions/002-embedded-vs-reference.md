# ADR-002 — Embed và reference theo aggregate

## Status

LOCKED DESIGN v1 — PHASE02,07/10/2026; giữ lựa chọn phase01, cập nhật theo yêu cầu khóa thiết kế.

## Context

MongoDB hỗ trợ object/mảng nhúng, nhưng mảng Orders trong User hoặc Reviews trong Product tăng vô hạn. Barem cần Order embed rõ và giải trình khi nào reference.

## Decision

Embed User.addresses (giới hạn), Cart.items, Order.items/customerSnapshot/shippingAddress/category snapshots. Reference Product.categoryId, Order.userId/productId (chỉ trace), Cart.productId, PaymentAttempt.orderId, Review references. Order detail/report đọc snapshot, không join Product để tính giá. History User truy vấn orders.userId với pagination.

## Alternatives and trade-offs

Embed toàn bộ Category vào Product sẽ phải đồng bộ tên/status khắp catalog; không chọn vì Category quản trị độc lập. Reference mọi field Order làm lịch sử phụ thuộc dữ liệu sống và trái barem; không chọn. Embed bounded aggregate giảm round-trip và có atomicity một document; duplicated snapshot là dữ liệu lịch sử có chủ đích, không lỗi cần “normalize” lại. [Nguồn MongoDB](https://www.mongodb.com/docs/manual/data-modeling/embedding/).

## Consequences and verification

Snapshot làm Order lớn hơn; bounded items, không lưu ảnh binary. MongoDB không enforce foreign key; service/transaction bảo vệ dữ liệu sống. Archive Product giữ reference để trả stock; Order vẫn đọc khi catalog đổi. Test history không dereference Product/User/Address và pagination không cần User.orders.
