# Authentication

## Goal

Đăng ký/đăng nhập JWT an toàn cho Customer/Admin. Backend PHASE05A IMPLEMENTED và đã kiểm tra HTTP thật; frontend FE-01A đã bàn giao, được kiểm tra lại ở PHASE07A. Giữ JWT/Argon2id/get_current_user/role guard của PHASE04. Đọc thêm [backend foundation](backend-foundation.md), [API contract](../api-contract.md), users contract và BR-AUTH.

## Actors

Guest đăng ký/đăng nhập; Customer/Admin sử dụng identity đã xác minh.

## Functional Requirements

Register Customer, login, current identity, đổi password, logout UI. Admin bootstrap qua seed, không public signup Admin. Không refresh-token/forgot-password/email-verification trong baseline.

## Business Rules

BR-AUTH: normalized email unique; ACTIVE mới login/request protected. Access token có TTL cấu hình; tokenVersion tăng khi đổi password/role/status. Logout xóa state/client token và sessionStorage theo tab; không claim logout này thu hồi mọi JWT đã phát nếu chưa tăng version.

## Permission

Register/login public. Current identity/password chỉ authenticated owner. Không cho client tự set role/status.

## API

Prefix/envelope theo api-conventions:

| Method / path | Request | Response data | Error |
| --- | --- | --- | --- |
| POST /auth/register | {name,email,password,phone?} | 201 {user:publicUser} | 409 email duplicate;422 validation |
| POST /auth/login | {email,password} | 200 {accessToken,expiresIn,user} | 401 invalid credentials/blocked;429 rate limit |
| GET /auth/me | Bearer token | 200 publicUser | 401 invalid/expired |
| PATCH /auth/password | {currentPassword,newPassword} + Bearer | 200 {reauthenticationRequired:true} | 401 wrong current/invalid token;422 password |

Logout không endpoint; FE-01A giữ access token theo tab trong sessionStorage và state; refresh/forgot routes không được tự thêm.

## Data

Read/write users; không embed token lists. Source thực tế dưới `backend/app`: `auth/`, `api/auth.py`, `services/auth_service.py`, `services/user_service.py`, `repositories/user_repository.py`, `schemas/auth_schema.py`, `schemas/user_response.py`; tests `backend/tests/test_auth_users.py`. Direct dependencies User projection, JWT/Argon2id, strict validation/error/envelope và factory đăng ký blueprint. Frontend hiện hữu: `frontend/src/contexts/AuthContext.tsx`, `api/authApi.ts`, `api/client.ts`, `pages/LoginPage.tsx`, `pages/RegisterPage.tsx`, `routes/ProtectedRoute.tsx`.

## Validation

Email syntax/trim/lowercase, <=254 ký tự, không strip dot/plus; name1..100 sau trim; password baseline12..128 ký tự, cho Unicode/space, giữ nguyên và không silent truncate; hash Argon2id m19456/t2/p1. Phone optional/empty khi register; nếu có dữ liệu phải8..15 chữ số với dấu + tùy chọn sau trim. Policy và hash cost tại foundation-decisions. Body/query allowlist strict; field role/status/tokenVersion/id/hash bị reject422, không silently ignore. Bounds chuỗi cũng được kiểm tra trên input trước trim. Login/password request áp dụng cùng password bounds.

## Edge Cases

Duplicate concurrent signup dựa unique index; invalid hash/token/subject; blocked sau login; password đổi vô hiệu tokenVersion cũ. Frontend F5 khôi phục sessionStorage theo tab rồi gọi /auth/me; identity vẫn do backend xác minh. Logout/401 xóa token; không có refresh token hay localStorage persistence.

## Security

Argon2id theo [OWASP password storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html), chốt cost sau benchmark. Không log password/JWT/hash; allowlist JWT algorithm/issuer/audience; generic login error; rate limits và CORS; secrets server-only.

Rate limiter local per app/process, cửa sổ60s: login30/IP và10/normalized email; register10/IP; password30/IP và10/subject. Tính cả attempts thành công/thất bại, IP tính cả body malformed; login account tính sau validation. Dùng socket remote_addr, không tin X-Forwarded-For. Keys HMAC với random secret process, thread-safe, tối đa10.000 buckets đang sống; hết capacity→429, không evict bucket để lách limit.429 có Retry-After. Unknown account verify dummy Argon2id hash; wrong/unknown/blocked/corrupt hash cùng401 message. Limiter không dùng chung giữa process và reset khi restart; distributed limiter/production proxy chưa triển khai.

publicUser chỉ `{id,name,email,phone,role,status,version,createdAt}`; không addresses/passwordHash/tokenVersion/schemaVersion. Đổi password tăng version/tokenVersion trong cùng write, check hash/version token/status/role hiện hành để chặn race block/revoke; trả reauthenticationRequired và không tự phát token mới. Version BSON int không được overflow.

## UI Behavior

Form loading/field errors, disabled submit đang xử lý; redirect về trang được phép sau login. 401 protected đưa về login, không retry vô hạn. Admin/Customer route guard theo role backend trả.

## Acceptance Criteria

Customer đăng ký/đăng nhập; Admin chỉ seed; blocked/token invalid bị chặn; passwordHash không response; đổi password khiến JWT cũ vô hiệu; permission backend hoạt động.

## Testing Checklist

- [x] Valid/invalid/duplicate/concurrent register trên unique index thật.
- [x] Login wrong/unknown/blocked/corrupt hash/limit, JWT expiry/tamper/algorithm/subject.
- [x] Payload role ADMIN bị reject; password update/tokenVersion, concurrent password change và block giữa verify/write.
- [x] FE-01A/PHASE07A UI register/login/logout, F5 khôi phục sessionStorage theo tab qua /auth/me, 401 thu hồi local token và route guard; không có refresh token/localStorage.
