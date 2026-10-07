# ADR-001 — Product đa hình trong MongoDB

## Status

LOCKED DESIGN v1 — PHASE02,07/10/2026; giữ lựa chọn phase01, cập nhật theo yêu cầu khóa thiết kế. Tên vật lý `products` đã khóa theo chỉ dẫn phase02, OQ-01 resolved.

## Context

Điện tử/Thời trang/Gia dụng có thuộc tính khác nhau; đề bắt MongoDB và Polymorphic Schema. Tách collection mỗi ngành làm catalogue/search/CRUD chung khó hơn; bảng key-value kiểu SQL làm mất lợi thế document aggregate.

## Decision

Một `products` collection, fields chung + productType stable enum + attributes object. Category reference có cùng productType. `$jsonSchema` base + oneOf branch type-check known attributes; service validate key/selection/category. Không yêu cầu mọi Electronics có RAM; mọi nhóm có >=1 thuộc tính có ý nghĩa. Money long VND, stock int; images absolute URLs; exact validator tại database/validators/products.json.

## Alternatives and trade-offs

- Root fields theo từng ngành: nhanh thử nghiệm nhưng tên/type trôi, khó validator; không chọn.
- Collection mỗi ngành: validator tách dễ nhưng query/catalog phân mảnh và trái request; không chọn.
- Object attributes chung không discriminator: linh hoạt nhưng khó type validation và form; không chọn.
- Chosen: đọc/product detail tự nhiên, thêm key không migrate cột; cần validation/allowlist/index có chủ đích. Không claim MongoDB “không cần schema”.

## Consequences and verification

Admin form đổi theo nhóm; seed thể hiện ba shapes; filter chỉ keys supported, không wildcard index tự động. Schema type/category đổi cần migration và review, không sửa snapshot đơn cũ. Validator example tại database-schema; test hai ngành cùng collection và invalid shape.
