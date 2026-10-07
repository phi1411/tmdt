# ADR-004 — Cart riêng theo User

## Status

LOCKED DESIGN v1 — PHASE02,07/10/2026; giữ lựa chọn phase01, cập nhật theo yêu cầu khóa thiết kế.

## Context

Cart thay đổi thường xuyên, User có password/role/profile và addresses. Cần server source of truth và khả năng checkout clear Cart đúng version. Không có guest checkout trong scope.

## Decision

Collection `carts`, một document/User với unique userId; items bounded embedded và reference Product; version cho optimistic concurrency. Không authoritative price; GET Cart enrich giá/availability, checkout reprice. Create lazily khi add đầu tiên, GET chưa có Cart trả items=[] và version0; first mutation cartVersion0, upsert guarded unique index; race loser nhận CART_CHANGED rồi fetch lại.

## Alternatives and trade-offs

Embed User.cart: update một document dễ nhưng tranh chấp ghi với auth/profile, đọc account có nguy cơ mang Cart payload, không giảm transaction vì vẫn cần Product/Order; không chọn. LocalStorage only: UX nhẹ nhưng backend không source of truth/cross-device yếu; không chọn. Separate Cart: thêm collection/query, bù lại lifecycle/concurrency và ownership rõ; không cần expire/xóa tự động nếu chưa có yêu cầu.

## Consequences and verification

Admin không quản lý Cart người khác. Tổng qty across selections cùng Product phải check chung. Test duplicate merge, nonexistent lazy Cart, concurrent upsert và checkout version stale. Cart không giữ stock; chỉ transaction checkout giữ stock.
