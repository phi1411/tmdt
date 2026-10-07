# Profile và địa chỉ

## Goal

Customer quản lý dữ liệu sống dùng ở checkout; Order giữ bản sao độc lập. Backend PHASE05A IMPLEMENTED, frontend chưa triển khai.

## Actors

Customer; Admin quản lý account ở admin-users, không dùng profile API để sửa người khác.

## Functional Requirements

Xem/sửa profile name/phone; thêm/sửa/xóa/list address; chọn default address. Email login không sửa trong baseline. Không xóa account hoặc thay đổi role qua profile.

## Business Rules

BR-AUTH, BR-ORDER: addresses bounded embedded, defaultAddressId phải thuộc User; xóa default→null. Checkout chọn address explicit. Profile/address đổi không cập nhật Order snapshot. Mỗi mutation tăng User.version và check expectedVersion.

## Permission

Authenticated Customer owner. Admin dùng admin-users cho account management; không tự đọc địa chỉ mọi Customer qua `/users/me`.

## API

| Method / path | Request | Response data | Error |
| --- | --- | --- | --- |
| GET /users/me | Bearer | 200 publicProfile + addresses/version | 401/403 |
| PATCH /users/me | {name?,phone?,expectedVersion} | 200 updated publicProfile | 409 stale;422 fields |
| POST /users/me/addresses | {receiverName,phone,addressLine,province,ward?,district?,label?,expectedVersion} | 201 {address,version} | 409 limit/stale;422 |
| PATCH /users/me/addresses/:id | editable address fields + expectedVersion | 200 {address,version} | 404 not owned;409;422 |
| DELETE /users/me/addresses/:id | {expectedVersion} | 204 | 404/409 |
| PATCH /users/me/default-address | {addressId,expectedVersion} | 200 {defaultAddressId,version} | 404 not owned;409 |

## Data

Read/write users only, addresses embedded. Source thực tế dưới `backend/app`: `api/users.py`, `services/user_service.py`, `repositories/user_repository.py`, `schemas/user_schema.py`, `schemas/user_response.py`; tests `backend/tests/test_auth_users.py`. Direct dependency auth guard, strict validation/error/serialization; checkout chỉ là consumer contract cho phase sau. `frontend/src/features/users/` vẫn dự kiến. Các mutations chỉ đụng một document User: read snapshot + conditional update theo id/version/role/status/tokenVersion; không cần transaction nhiều document và không ghi Order.

publicProfile gồm publicUser ở auth + `{addresses:[publicAddress],defaultAddressId,updatedAt}`. publicAddress gồm `{id,receiverName,phone,addressLine,province,ward?,district?,label?}`. GET /users/me cung cấp danh sách địa chỉ; không thêm GET route riêng. Add không tự chọn default. Default address phải là ID thuộc owner, không nhận null để clear trong baseline; xóa default reset null nguyên tử. DELETE204 không trả version; client đọc lại profile. Các mutation profile/address/default tăng version một lần, không tăng tokenVersion.

## Validation

Name/receiver1..100; trim outer whitespace; phone8..15 digits với + tùy chọn, profile phone cho empty, address phone bắt buộc không empty. addressLine1..300, province1..100; ward/district optional1..100 nếu có; label1..50 nếu có; max10 addresses. Bounds cũng check trên input trước trim. expectedVersion integer strict1..2147483647 (không bool/float); mutation tại version tối đa bị409 thay vì overflow. PATCH cần ít nhất một editable field. Unknown body/query→422; malformed ID→400. Client không chọn `_id`/id address/role/status/email/hash/security fields.

## Edge Cases

No address, stale edits, deleting address lúc quote đã tạo: checkout revalidate source và quote/address intent, không dùng ID đã mất. Default delete/reset nguyên tử; hai add cùng lúc không vượt limit.

## Security

Subject tự xác định userId; trả404 ID không thuộc owner. Không log địa chỉ/phone đầy đủ. Không mass assignment từ body; plain text và escaped UI.

## UI Behavior

Form field errors, address cards/default badge, confirmation trước xóa; checkout hướng người dùng thêm address nếu chưa có. Baseline dùng trường text/address đơn giản; API địa giới bên ngoài DEFERRED, không blocker.

## Acceptance Criteria

Owner sửa đúng dữ liệu/version; default hợp lệ; limits enforce; người khác không truy cập; Order cũ vẫn nguyên snapshot.

## Testing Checklist

- [x] Profile validation, forbidden fields, stale version, concurrent edit/revoke-before-write.
- [x] Address CRUD/default, default delete, concurrent max-limit/default vs delete.
- [x] Cross-user address ID404; Order fixture snapshot giữ nguyên sau profile/address change và block.

UI/checkout/E2E vẫn deferred; test Order dùng fixture trong ecommerce_test, không implement Order API.
