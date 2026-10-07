# ADR-009 — Local foundation, Category và defaults

## Status

LOCKED DESIGN v1 — PHASE02,07/10/2026. Resolve OQ-01/02/03/06/09 design scope; Review OQ-07→DEFERRED. Operational secrets/deployment còn deferred.

## Context and decision

User chốt English names, local MongoDB, React+Vite+TypeScript+Tailwind, URL media và không backend features ở phase02. Chọn local MongoDB Community8.0 single-node replica set rs0/WiredTiger để transaction hoạt động và demo offline; Atlas về sau optional, không dùng Atlas-only features. Target Python3.12, dependency exact patches/lockfile thực hiện bootstrap sau review.

Category một cấp, không parentId:3 nhóm đề tài đủ browse/filter, taxonomy tree tăng CRUD/invariant không giúp điểm NoSQL. `slug` unique, status ACTIVE/ARCHIVED, productType compatibility reference; một type có nhiều Category, type không đổi khi có Product. Category guarded version write chống archive/delete races như BR-CATALOG, chấp nhận contention nhỏ cho đồ án.

Cart ADR004 giữ nguyên vì không lỗi modeling đáng kể. Product.images URL-only, không upload/cloud dependency; validators shape và dịch vụ allowlist scheme/host cho HTTP dev. Order giữ URL string/fallback. reviews không tạo ở MVP.

Defaults/limits canonical ở foundation-decisions: shipflat30k, quote5min, onlinehold15min, expiry poll30s; transaction/quote/bounds có contract để không còn thiếu policy backend. TTL-delete không dùng cho đơn/lịch sử. Backend fail config invalid thay silent defaults khác tài liệu. Các giá trị là lựa chọn baseline configurable, không giả định giảng viên yêu cầu30k.

## Trade-offs and consequences

Local một node không HA production nhưng độc lập internet cho COD/Compass, supports modeling/transactions. Single-level/flatship/shared variant stock giữ project phù hợp3SV. URL media có thể unavailable, UI fallback; cloudupload/tree/variant stock nếu bổ sung cần ADR/migration. No phase02 installs/server startup/seed/business endpoints; docs và declarative artifacts thôi.
