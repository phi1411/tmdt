# Category

**Trạng thái hiện hành20/10/2026:** API và giao diện của feature đã triển khai; các mốc phase/deferred bên dưới là lịch sử. Evidence tại [full audit](../full-project-audit-20261020.md) và [handoff](../defense-final-handoff-20261020.md). Không chạy lại toàn bộ UI suite trong lần đồng bộ tài liệu này.

## Goal

Danh mục một cấp, CRUD quản trị và browse public, chứng minh>=3 ngành. P0; API IMPLEMENTED PHASE05B, UI đã triển khai. [Contract](../api-contract.md), [review](../phase-05b-review.md).

## Actors

Guest/Customer xem; Admin CRUD.

## Functional Requirements

Public list/detail ACTIVE; Admin list/detail tất cả/create/update/archive/delete category chưa referenced. Không category tree/subcategory trong baseline.

## Business Rules

BR-CATALOG: slug unique; productType stable khi đã có Product. Archive ẩn catalog/chặn checkout phụ thuộc Category. Delete chỉ không có Product reference kể cả archived. Guarded Category version increment/write chung trong create/move/publish Product và checkout để serialize với archive/delete; check references trong transaction, không check rồi delete ngoài transaction.

## Permission

GET public chỉ ACTIVE; `/admin/categories*` chỉ Admin. User không tự tạo ngành.

## API

| Method / path | Request | Response data | Error |
| --- | --- | --- | --- |
| GET /categories | page/pageSize | 200 active categories paginated | 400/422 |
| GET /categories/:slug | slug | 200 category | 404 inactive/missing |
| GET /admin/categories | status?,page/pageSize | 200 categories/version | 401/403/422 |
| GET /admin/categories/:id | id | 200 category | 401/403/404 |
| POST /admin/categories | {name,slug,productType,description?} | 201 category | 409 duplicate;422 |
| PATCH /admin/categories/:id | {name?,slug?,description?,status?,productType?,expectedVersion} | 200 category | 409 referenced type/stale;422 |
| DELETE /admin/categories/:id | {expectedVersion} | 204 hard-delete only unused | 409 CATEGORY_IN_USE/stale;404 |

## Data

Read/write categories; Product reference existence reads; category write guard coordinated Product/checkout transactions. Paths `api/categories.py`, `services/category_service.py`, `repositories/category_repository.py`, `schemas/category_schema.py`; `features/categories/` reused in Admin. Dependency product_repository only for existence/reference guard, not dashboard/payment.

## Validation

Name1..100, slug lowercase hyphenated<=120; productType enum, status ACTIVE/ARCHIVED; description<=2000; expectedVersion strict int. Product/category types không mismatch.

Create không nhận status (mặc định ACTIVE) theo body contract; name không whitespace-only. PATCH chỉ supplied fields, ít nhất một field ngoài expectedVersion; unknown field/query422. ExpectedVersion1..2147483647; version cap409 VERSION_LIMIT. List ổn định `_id ASC`, pagination1/20/max100; public không nhận status filter. Response fields và errors chi tiết tại api-contract. Category version tăng thật khi Product create/move/publish nên form phải reload version.

## Edge Cases

Duplicate rename; category trống; Product create race delete; archive race checkout; archived product vẫn block hard-delete. Rename chỉ đổi catalog hiện tại, report nhãn snapshot không đổi.

## Security

Admin guard server, allowlist patch fields; no raw operator/object injection, text escaped. Public không lộ archived category.

## UI Behavior

Admin table/filter/form, archive khác delete chưa dùng; 409 hiển thị lý do còn Product, không force delete. Public category navigation bỏ archived.

## Acceptance Criteria

CRUD hoạt động Web/API; ba ngành hợp lệ; unique/refs/types enforce cả race; public và checkout tôn trọng archive; snapshot category lịch sử không bị rewrite.

## Testing Checklist

- [x] Public/admin permissions, invalid enum/slug/duplicates trên MongoDB thật.
- [x] Unused delete; referenced delete409; type change referenced409; rollback guard.
- [x] Create/move/publish vs archive/delete race trên rs0; fingerprint dev/history unchanged.
- [ ] Checkout race và UI: phase sau, chưa implement ở PHASE05B.
