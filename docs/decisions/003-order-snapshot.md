# ADR-003 — Snapshot Order và tiền

## Status

LOCKED DESIGN v1 — PHASE02,07/10/2026; giữ lựa chọn phase01, cập nhật theo yêu cầu khóa thiết kế.

## Context

Đơn mua10 triệu không được biến thành12 triệu khi Product đổi giá. Giá do frontend gửi dễ sai; float gây vấn đề arithmetic. Snapshot rời khỏi cập nhật kho tạo partial failure.

## Decision

Backend revalidate quote và Product khi checkout. Copy sku/name/image/attributes/selection/category, priceAtPurchase, quantity/lineTotal; copy customer/address; persist totals cùng Order. Snapshot fields immutable qua repository allowlist. Money BSON long/JSON integer VND, explicit conversion PyMongo. discount=0 đến khi có yêu cầu promotion.

Checkout nhiều Product + insert Order + clear đúng Cart version trong một transaction replica set; idempotency per User để retry không double-create. Snapshot không `$lookup` Product cho history/report. COD/VNPAY là payment state riêng.

## Alternatives and trade-offs

Chỉ productId: ít dung lượng nhưng history sai và trái yêu cầu; loại. Snapshot ở frontend: không đáng tin; loại. BSON Decimal128: hữu ích currency fractional nhưng VND integer và JSON conversion đơn giản hơn nên chọn long. Transaction tăng độ phức tạp/topology; cần vì đơn/kho/cart là nhiều document, không do embed tự tạo atomicity xuyên collection.

## Consequences and verification

Đổi giá10→12 triệu/tên/attributes/category/profile/address và archive Product không đổi đơn cũ. Test quantity×price/totals và rollback partial stock; không sửa schema snapshot khi sửa Product. Link ảnh chỉ giữ đường dẫn, fallback nếu file bị mất.
