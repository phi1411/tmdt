# Admin User Management

**Trạng thái hiện hành20/10/2026:** API và giao diện của feature đã triển khai; các mốc phase/deferred bên dưới là lịch sử. Evidence tại [full audit](../full-project-audit-20261020.md) và [handoff](../defense-final-handoff-20261020.md). Không chạy lại toàn bộ UI suite trong lần đồng bộ tài liệu này.

## Goal

Quản lý tài khoản trong hai persisted roles hiện có. Backend PHASE05A IMPLEMENTED; frontend đã tích hợp. Không mở rộng sang Seller/Staff.

## Actors

ADMIN list/detail, block/reactivate Customer.

## Functional Requirements

Search/list Customers/Admins, detail public-safe account fields, chuyển Customer ACTIVE/BLOCKED. Role changes, create Admin, reset password hộ khách/xóa User chưa requirement nên không cung cấp API baseline.

## Business Rules

BR-AUTH: BLOCKED không login/checkout/protected request; status đổi tăng tokenVersion và User.version cùng update. Không sửa/hủy Orders khi block User. **Mọi Admin account status/role không chỉnh bằng UI/API này**, nên không thể khóa/demote Admin cuối hoặc race làm mất Admin; role admin bootstrap chỉ seed/config có kiểm soát. Đây là scope quản trị tối thiểu, không suy ra quyền thêm role.

## Permission

ADMIN endpoints; Customer không dùng admin management kể cả tự thân. Profile riêng ở users doc.

## API

| Method / path | Request | Response data | Error |
| --- | --- | --- | --- |
| GET /admin/users | q?,role?,status?,page/pageSize | 200 public-safe accounts/version | 401/403/422 |
| GET /admin/users/:id | id | 200 account{id,name,email,phone,role,status,version,createdAt} | 404/401/403 |
| PATCH /admin/users/:id/status | {status:ACTIVE/BLOCKED,expectedVersion} | 200 account | 409 protected Admin/stale;422 |

No passwords/hash/address detail in list; address full read không cần quản lý account. Query q normalized bounded, không raw regex.

## Data

Read/write users only; no Orders cascade. Source dưới `backend/app`: `api/admin_users.py`, `services/user_service.py`, `repositories/user_repository.py`, `schemas/admin_user_schema.py`, `schemas/user_response.py`; tests `backend/tests/test_auth_users.py`. `frontend/src/features/admin-users/` vẫn dự kiến. Auth middleware đọc status/tokenVersion để revoke request sau; dependencies auth, strict validation/error/envelope/pagination, không dashboard. CAS status theo id/version/role/status/tokenVersion, một atomic User write.

Account DTO đúng `{id,name,email,phone,role,status,version,createdAt}`, không địa chỉ/hash/security fields. q<=100 ký tự, trim/lowercase, literal substring trên name/email (escaped regex, case-insensitive), empty q bỏ filter; role/status exact enum. Page1/pageSize20 mặc định, max100, sort cố định createdAt DESC/_id DESC; không nhận sort. Empty total→totalPages0; page vượt cuối trả data[] với total hiện tại. Không thêm index/schema; count và page là hai reads, không claim snapshot nhất quán khi có thay đổi đồng thời.

## Validation

Status enum/expectedVersion integer strict1..2147483647, valid ID, Customer target; no body.role/passwordHash/tokenVersion fields. Same status200 no-op chỉ khi expectedVersion còn đúng; không tăng version/tokenVersion/updatedAt. Admin target luôn409 BUSINESS_RULE_VIOLATION kể cả same status. Stale version409 CONFLICT; unknown target404; malformed ID400; unknown/repeated query422. Mutation tại version/tokenVersion maximum409, không overflow BSON int.

## Edge Cases

Admin target/self block rejected; customer logged in trước bị block token invalid; simultaneous status changes stale409; filter empty; unblocking không khôi phục token cũ (version không giảm).

## Security

Role current from DB, strict projection no credential leakage, server Admin authorization. Không trust JWT stale role claims. Sanitized actor/target/status log, no mass assignment.

## UI Behavior

Table pagination/search/filter, status badge, confirm block/reactivate Customer; Admin row không có status action, API vẫn reject nếu gọi tay. Conflict refetch, no role dropdown chưa requirement.

## Acceptance Criteria

Admin list/detail và Customer status management đúng; block revokes access, history intact, protected Admin invariant đúng cả concurrency; no sensitive fields exposed.

## Testing Checklist

- [x] Admin-only read/write, projection/query validation/literal search/pagination.
- [x] Customer block/reactivate/tokenVersion/expectedVersion; unblock không hồi sinh JWT cũ, same-status no-op.
- [x] Admin/self protection, simultaneous status mutation một winner, no Order cascade qua fixture snapshot.
