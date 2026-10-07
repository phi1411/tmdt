# Backend foundation — PHASE 04

## Goal

Nền tảng Flask hoạt động với MongoDB đã khóa để feature agents triển khai độc lập. PHASE04 chỉ health là endpoint thực; phase này đã duyệt. PHASE05A đã thêm Auth/User APIs, xem [review](../phase-05a-review.md); tài liệu này giữ phạm vi nghiệm thu foundation, không đại diện trạng thái toàn app sau các worker.

## Actors

Developer chạy app/tests; frontend dùng contract public; feature agents dùng factory, errors, validation, auth guards và DB connection.

## Functional Requirements

App factory development/testing, environment config, MongoClient dùng chung, startup/readiness, API prefix/envelopes/requestId, error mapping, BSON serialization, CORS/logging, JWT/Argon2/role primitives, request validation và pagination.

## Business Rules

Giữ nguyên database-schema/BR-AUTH và api-conventions: User ACTIVE/tokenVersion/current DB role; không JWT-role-only authorization. Không implement register/login/CRUD/Cart/Checkout/Order/Payment/Dashboard. API gọi service, repository truy cập DB, service phase sau sở hữu transaction boundary.

## Permission

Health public và không tiết lộ credential/topology address/version. Protected feature phase sau sử dụng require_auth/require_roles(CUSTOMER hoặc ADMIN). Guest không persisted role; thiếu token401, thiếu quyền403.

## API

GET `/api/v1/health` IMPLEMENTED:200 data.status=ok/checks backend/database/replicaSet=ok; DB không ready503 SERVICE_UNAVAILABLE. GET/POST/PATCH/DELETE nghiệp vụ trong feature docs PLANNED. [API contract](../api-contract.md) là tài liệu frontend đọc.

## Data

Read-only MongoDB khi app startup/health; UserRepository chỉ lookup identity bằng _id/projection. Không apply validator/index/seed trong factory. Source: backend/app/__init__.py,config.py,db/__init__.py,api/health.py,services/health_service.py,repositories/user_repository.py,auth/,errors/,schemas/,utils/. Tests tại backend/tests, runtime evidence backend/evidence. Dependency trực tiếp: api-conventions, auth và MongoDB config; không cần đọc Product/Payment internals.

## Validation

JSON Schema Draft2020-12 qua jsonschema, integer strict không bool/float, required/enum/nested/unknown properties theo schema feature. JSON syntax400, shape/value422, unsupported contenttype415. ObjectId lowercasehex24→400; pagination page/pageSize/default1/20/max100. Query keys không allowlist hoặc lặp→422; không alias limit/search/category.

## Edge Cases

DB unavailable/wrong replica set fails startup; mất DB sau startuphealth503. Client sống qua nhiều request, không đóng tại appcontext teardown. Test mode bắt buộc DB riêng suffix_test, không lấy .env dev mặc định. Nested secrets/BSON serialize thống nhất, naiveDatetime/nonfinite output là programmingerror500; NaN JSON input400. Unknownroute404/method405/body quá1MiB413.

## Security

JWT HS256 cố định/issuer/audience/requiredclaims/TTL, secret env tối thiểu32bytes và không placeholder; Argon2id m19456/t2/p1. CORS exact origins, no credential cookies, debugger/reloader off. Server-generated requestId. Structured logs chỉ event/requestId/method/endpoint/status/duration/errorType/frame locations; không exceptiontext/body/query/header/password/JWT/secret. Password/private fields bị loại ở response serialization; feature sau vẫn phải chọn public DTO/projection.

## UI Behavior

Không frontend. Client dùng error.code/details/meta.requestId; không suy luận health200 nghĩa login hoặc feature nghiệp vụ đã có. Tokens giữ memory theo auth design; CORS chỉ là browser policy, không thay authorization.

## Acceptance Criteria

Server thật trả health200 và MongoDB rs0 usable; pytest foundation pass; dev documents/validators/indexes trước/sau giữ nguyên. Test probes không registered trong app thường. API contract phân biệt IMPLEMENTED/PLANNED; không secret thật trong source/evidence.

## Testing Checklist

- [x] Factory/config precedence/required settings/test DB guard/client lifecycle.
- [x] Health live MongoDB, readiness failures, wrong topology.
- [x] HTTP/error envelopes, BSON types/private redaction, size/CORS/requestId/log safety.
- [x] JWT tamper/expiry/algorithm/issuer/audience/subject, blocked/version/currentrole checks.
- [x] Argon2 policy và seed hash compatibility; validation/nested/pagination/query allowlist.
- [x] Runtime HTTP smoke; dev data/validator/index fingerprint unchanged, exact test fixture cleanup.
- [ ] Business features và frontend ở phase sau, khi người dùng giao.
