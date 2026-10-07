# PHASE 04 — Flask backend foundation review

**Hoàn thành foundation và dừng để review.** Server Flask thật kết nối MongoDB rs0, health 200, 80 tests pass. Thiết kế MongoDB v1 giữ nguyên; chưa triển khai đầy đủ API nghiệp vụ, frontend hoặc phase tiếp theo. [Yêu cầu gốc](requirements-phase-04-source.txt), [setup](backend-setup.md), [API contract](api-contract.md).

## 1. Backend structure

```text
backend/
  app/
    __init__.py, config.py
    api/health.py
    services/health_service.py
    repositories/user_repository.py
    schemas/validation.py, pagination.py, query_contract.py
    auth/__init__.py, tokens.py, passwords.py
    db/__init__.py
    errors/__init__.py, handlers.py
    utils/ids.py, serialization.py, responses.py, logging.py
  tests/conftest.py, test_foundation.py, test_auth_foundation.py
  evidence/pytest.xml, runtime-verification.json, README.md
  requirements.txt, requirements-dev.txt
  requirements.lock.txt, requirements-dev.lock.txt
  pytest.ini, run.py, README.md
```

Modular monolith API → service → repository → MongoDB. Health service sử dụng DB readiness primitive; UserRepository chỉ đọc projection phục vụ current identity. Không dựng CRUD hoặc stub trả thành công giả. Feature agents có routing module trong architecture và backend README.

## 2. Packages/dependencies

| Direct dependency | Version | Vai trò |
| --- | --- | --- |
| Flask | 3.1.3 | Factory/HTTP/errors/JSON provider |
| flask-cors | 6.0.5 | Origin allowlist |
| PyJWT | 2.15.1 | JWT HS256 |
| python-dotenv | 1.2.4 | Đọc private env file |
| PyMongo | 4.15.3 | Giữ version DB tooling, driver |
| argon2-cffi | 25.1.0 | Giữ Argon2id seed compatibility |
| jsonschema | 4.25.1 | API validation, đã dùng trong DB tooling |
| pytest (dev) | 9.1.1 | Test runner |

Runtime lock 22 packages; dev lock 28 packages gồm transitive dependencies và Windows marker. Đã chạy bootstrap với dev lock và `pip check`: pass. Lock DB tooling PHASE 03 giữ nguyên. Python đã kiểm thử 3.12.14; không thêm ORM/microservice/Redis hoặc frontend dependency.

## 3. Config strategy

`create_app(config=None, env_file=None)` hỗ trợ development/testing; config nhận dictionary overrides. Overrides ưu tiên process env, rồi private `.env`; testing không mặc định đọc env development. URI/JWT secret/issuer/audience từ env, thiếu/sai cấu hình dừng startup. `.env.example` chứa key/placeholder; secret thật chỉ trong ignored `.env`. Helper generate JWT secret giữ secret đã có và không in giá trị. Debugger/reloader tắt; payload mặc định 1 MiB, CORS exact origins, log level configurable. Chưa sử dụng VNPAY secrets.

## 4. MongoDB connection strategy

Một MongoClient/app/process, pooling qua requests; không tạo/đóng client mỗi request. `app.extensions['mongo']`/get_db()/get_mongo(); startup kiểm tra ping, đúng rs0, writable PRIMARY và sessions; atexit đóng client, tests explicit close. Primary reads/majority writes, timeout mặc định 3000 ms. Không tự apply schema/index/seed trong factory.

Dev `ecommerce_dev`: users 40, categories 3, products 180, carts 0, orders 100, payment_attempts 30. 6 validators và 14 declared indexes giữ nguyên. Tests ghi fixture vào `ecommerce_test` riêng có ownership marker, cleanup đúng IDs; không drop/reset DB dev hoặc test.

## 5. API prefix

`/api/v1` cố định; chỉ `/api/v1/health` đăng ký trong app thường. HEAD/OPTIONS do Flask/CORS tự động. Test probe routes chỉ tồn tại ở app pytest.

## 6. Response/error convention

Success `{data, meta:{requestId}}`; list helper thêm page/pageSize/total/totalPages; 201 có thể Location, 204 không body. Error `{error:{code,message,details:[]},meta:{requestId}}`. Server sinh requestId mới; response có X-Request-ID và nosniff.

Đã chuẩn hóa 200/201/204/400/401/403/404/405/409/413/415/422/429/500/503; 429 mới là convention, chưa có limiter. Hierarchy validation/authentication/authorization/not-found/conflict/business-rule/internal. Duplicate key → 409, driver availability error → 503, unexpected → 500; log an toàn, không trả stack/DB query. BSON ObjectId → id chuỗi hex24, datetime UTC → ISO milliseconds Z, BSON long → JSON integer VND; private password/hash/tokenVersion/checkout keys/secrets không serialize.

## 7. Auth foundation

JWT HS256 cố định, issuer/audience, required claims sub/tokenVersion/iat/nbf/exp/jti, TTL mặc định 1800 giây, private secret ≥32 byte. Bearer parser/get_current_user/require_auth/require_roles(CUSTOMER, ADMIN) dùng chung; đọc User ACTIVE/tokenVersion và role hiện tại từ DB mỗi protected request. Token không chứa password; authorization không tin role client/JWT.

Argon2id m19456 KiB/t2/p1, password 12–128 ký tự; hash/verify helpers và kiểm tra tương thích hash seed thật đã pass. `create_access_token` là internal helper, service login phase sau phải xác minh password trước khi gọi. Chưa có register/login/me/password HTTP endpoints, refresh token hay full auth feature.

## 8. Validation strategy

jsonschema Draft 2020-12, schema checked, type/required/enum/nested/additionalProperties. Integer strict loại bool và float; JSON NaN/Infinity bị từ chối. Error field/reason rõ, không echo raw received value. Malformed JSON/ID/query integer → 400, unsupported content type → 415, sai shape/value/unknown/repeated query → 422. ID lowercase hex24 nhất quán.

Pagination `page`/`pageSize`, mặc định 1/20, max100; không dùng alias limit. Product naming khóa theo docs: q/categoryId/productType/brand/minPrice/maxPrice/size/color/ram/capacity/sort/page/pageSize. Constants sort latest/price_asc/price_desc đã có; Product parser/search query chưa implement.

## 9. Test result

**80 passed, 0 failures, 0 errors, 0 skipped**; pytest 9.1.1, Python 3.12.14, thời gian suite khoảng 3.31 giây ở lần ghi evidence cuối. Bao gồm factory/config/test isolation/lifecycle, live Mongo health, topology/error branches, envelopes/status/BSON/redaction/size/CORS/log safety, validation/pagination, JWT tamper/expiry/algorithm/issuer/audience/claim types, real User role/status/version/deletion, Argon2 và seed compatibility. Client/API probes thực thi trên app test; fixture User dùng DB test thật. Không tuyên bố đã test checkout/payment transactions khi chúng chưa có.

[JUnit](../backend/evidence/pytest.xml), [HTTP + DB evidence](../backend/evidence/runtime-verification.json). Fingerprint toàn bộ dev documents/collection options/validators/indexes trước và sau cùng giá trị:

```text
3cb02b86dae359fe469356c818205b8ddc2e83768862d9f3c47776a79657c6a6
```

`devDataValidatorsIndexesUnchanged=true`, `testDatabaseEmptyAfterCleanup=true`. Runtime verification chỉ đọc DB. Baseline helper không ghi đè evidence cũ.

## 10. Health endpoint result

Server development đang chạy local ở `http://127.0.0.1:5001/api/v1/health`, response HTTP 200:

```json
{"data":{"status":"ok","checks":{"backend":"ok","database":"ok","replicaSet":"ok"}},"meta":{"requestId":"server-generated-id"}}
```

Đã gọi qua HTTP thật, không chỉ test client. Unknown path 404 NOT_FOUND, POST health 405 METHOD_NOT_ALLOWED; requestId header/body trùng. Nếu DB không ready thì 503, không lộ URI/host/version/credentials. Port5000 có ứng dụng khác nên cấu hình private API_PORT=5001; không dừng process đó.

## 11. API contract file

[docs/api-contract.md](api-contract.md): health IMPLEMENTED, helpers/envelopes/serialization/pagination nền tảng IMPLEMENTED, tất cả business endpoints PLANNED theo feature docs. Product detail dùng `/products/:slug` đúng contract đã khóa. Frontend agent đọc tài liệu này để biết API nào gọi được mà không đọc internals.

## 12. Files đã tạo/sửa

- Backend source/tests/dependency pins/locks/entrypoint/evidence/README như mục 1.
- scripts/backend: bootstrap.ps1, start.ps1, create_env.py, lock_dependencies.py, capture_database_baseline.py, verify_runtime.py.
- docs: requirements-phase-04-source.txt (bản nguyên yêu cầu), features/backend-foundation.md, backend-setup.md, api-contract.md, phase-04-review.md.
- Context cập nhật: AGENTS.md, README.md, docs/architecture.md, api-conventions.md, testing-strategy.md, features/auth.md.
- .env.example thêm keys nền tảng; private .env/.local chứa cấu hình và local runtime, được ignore.

Không sửa canonical validators/indexes/aggregations/database schema hoặc tạo frontend. Workspace chưa là Git repo nên không tạo commit/PR/remote; không có secret thật trong source/evidence bàn giao.

## 13. Issue/DEFERRED và điểm dừng

Không còn kiểm tra foundation thất bại đã biết. Local development port đổi5001 đã xử lý. Lần kiểm tra cuối phát hiện process MongoDB/backend đã dừng; đã khởi động lại bằng script project, chạy lại 80 tests và HTTP/fingerprint pass. Không xác định nguyên nhân process dừng từ log hiện có; service supervisor/deployment chưa thuộc phase. Full Auth/Register/Login, Product/Category CRUD, Cart, Checkout, Order, Payment/VNPAY, Dashboard, frontend, rate limiting, full transaction/concurrency tests, full benchmark và deployment chưa triển khai. Đây là phạm vi phase sau, không là API giả đã hoàn thành.

Xác nhận backend foundation hoạt động; chưa implement đầy đủ business feature; chưa sửa database design; chưa tạo frontend; chưa bắt đầu phase tiếp theo. **Dừng tại PHASE 04 để người dùng review.**
