# Chạy Flask backend

PHASE04 foundation đã duyệt; PHASE05A có13 Auth/User/Admin User endpoints. Python3.12.14, Flask3.1.3, PyMongo4.15.3 chạy thật với MongoDB8.0.32/rs0; không thêm dependency. [API contract](api-contract.md) dành cho frontend; [review Auth/User](phase-05a-review.md) và [review foundation](phase-04-review.md) chứa kết quả kiểm tra.

## Cài và chạy trên Windows

Chạy từ thư mục project trong PowerShell. Môi trường MongoDB/seed PHASE 03 phải có trước, theo [MongoDB setup](mongodb-setup.md). Máy hiện tại đã có `.venv`, DB và dữ liệu; không cần seed/reset lại để chạy backend.

```powershell
./scripts/db/start-mongo.ps1
./scripts/backend/bootstrap.ps1
./scripts/backend/start.ps1
```

Bootstrap backend dùng Python 3.12 trong `.venv`, cài `backend/requirements-dev.lock.txt`, chuẩn bị JWT secret trong `.env` và kiểm tra dependency. Nếu chưa có `.venv`, dựng bằng `scripts/db/bootstrap.ps1` trước. Runtime-only dùng `backend/requirements.lock.txt`; thay dependency thì cập nhật requirements và chạy `scripts/backend/lock_dependencies.py` trong môi trường đã cài phiên bản cần khóa.

Start chạy server nền với cửa sổ ẩn, chờ health và từ chối thay thế process khác đang giữ cổng. Log/PID ở `.local/backend`. Có thể chạy foreground:

```powershell
./.venv/Scripts/python.exe -X utf8 backend/run.py
```

Máy hiện tại dùng [health ở cổng 5001](http://127.0.0.1:5001/api/v1/health) vì cổng 5000 đang có ứng dụng khác. `.env.example` mặc định 5000; đổi `API_PORT` trong `.env` nếu cần. Debugger/reloader tắt. Server development này phục vụ kiểm thử local; deployment chưa thuộc phase.

## Configuration

`create_app(config=None, env_file=None)` hỗ trợ development/testing; config là dictionary overrides. Thứ tự ưu tiên: config overrides → environment process → `.env`. Testing không tự đọc `.env` development. Configuration được đọc khi tạo app; đổi `.env` cần khởi động lại process backend của project.

| Key | Quy tắc |
| --- | --- |
| APP_ENV | development hoặc testing |
| MONGODB_URI | URI từ env, có replicaSet=rs0, không directConnection |
| MONGODB_DB | ecommerce_dev trong development đã thống nhất |
| MONGODB_TEST_DB | ecommerce_test; testing bắt buộc tên riêng kết thúc _test |
| MONGODB_REPLICA_SET | rs0 |
| MONGODB_TIMEOUT_MS | Mặc định 3000, khoảng 100–30000 |
| JWT_SECRET | Secret riêng tối thiểu 32 byte; không dùng placeholder |
| JWT_ISSUER / JWT_AUDIENCE | ecommerce-api / ecommerce-web theo example |
| JWT_ACCESS_TTL_SECONDS | Mặc định 1800; HS256 cố định |
| API_HOST / API_PORT | Mặc định 127.0.0.1 / 5000 |
| FRONTEND_ORIGIN / CORS_ORIGINS | Origin chính hoặc allowlist phân cách dấu phẩy; exact HTTP(S) origins |
| MAX_CONTENT_LENGTH | Mặc định 1048576 byte |
| LOG_LEVEL | Mặc định INFO |
| SHIPPING_FEE_VND | PHASE05C default30000, integer0..1000000, blank/invalid fail startup |
| QUOTE_TTL_SECONDS | PHASE05C default300, integer1..3600, blank/invalid fail startup |
| VNPAY_ENABLED | PHASE05C bắt buộc false; bật bị từ chối đến khi adapter/expiry worker có |

`.env` và `.local` được ignore. `create_env.py` chỉ tạo JWT secret nếu chưa có/đang placeholder, giữ secret đã có và không in giá trị. Không tải VNPAY secrets khi feature chưa triển khai. Ví dụ env chỉ chứa tên key và placeholder, không chứa credential thật.

PHASE05C quote key domain-separated SHA256 từ JWT_SECRET, audience checkout-quote-v1. QUOTE_SIGNING_SECRET placeholder lịch sử trong private .env không dùng, không cần tạo secret khác. Phải có phone profile hợp lệ trước checkout (không lấy phone address thay profile). VNPAY request mới503 PAYMENT_UNAVAILABLE, không tạo online hold/attempt; COD tạo PENDING/UNPAID, thu tiền/completed thuộc Admin Order worker sau.

## MongoClient và tầng ứng dụng

Một MongoClient cho mỗi app/process, pool dùng qua nhiều request; không đóng ở teardown mỗi request. Client được giữ tại `app.extensions['mongo']`, truy cập qua `get_db()`/`get_mongo()`. Startup kiểm tra ping, rs0, writable PRIMARY và sessions; thất bại dừng app bằng thông báo an toàn. Health kiểm tra lại và trả 503 khi DB mất readiness. Atexit đóng client; fixture đóng explicit sau mỗi app test.

Factory không seed, không tạo collection/validator/index. API xử lý HTTP và gọi service; repository giữ truy vấn. PHASE05A AuthService/UserService giữ nghiệp vụ; UserRepository thêm credential/public projections và single-document conditional writes cho version/status/tokenVersion/default address. Không trả nguyên DB document làm public DTO.

Login/register/me/password qua HTTP đã có; mỗi protected request đọc User ACTIVE/tokenVersion/role hiện tại từ DB, giữ JWT/Argon2id helpers cũ. Memory JWT1800s mặc định; logout UI xóa token, refresh không có. Factory khởi tạo dummy Argon2id hash và local per-process auth limiter; limits60s ở [auth](features/auth.md). Validation dùng jsonschema Draft2020-12 với integer strict; pagination1/20, max100. Đọc [Auth](features/auth.md), [User](features/users.md), [Admin User](features/admin-users.md) để tìm module trực tiếp. Các feature khác có worker riêng.

## Kiểm thử an toàn

Fixture kết nối `ecommerce_test` trên rs0, kiểm tra ownership marker `.local/ecommerce_test.ownership.json` và 6 collections đã được dựng ở PHASE 03. Không tự tạo marker để bỏ qua guard; môi trường mới dựng DB test bằng `./.venv/Scripts/python.exe scripts/db/init_db.py --database ecommerce_test` theo quy trình MongoDB setup. Tool chỉ claim DB mới/trống và từ chối DB không thuộc project. Tests chỉ thêm User fixture với ID riêng rồi xóa đúng các ID đó, không drop/reset DB, chỉ đọc `ecommerce_dev` để kiểm tra seed/hash compatibility.

```powershell
Push-Location backend
../.venv/Scripts/python.exe -m pytest --junitxml=evidence/pytest.xml
Pop-Location
./.venv/Scripts/python.exe scripts/backend/verify_runtime.py
```

Verify runtime gọi HTTP thật, kiểm tra JUnit, test cleanup và đối chiếu fingerprint toàn bộ documents/collection options/indexes với baseline riêng `.local/phase04-db-before.json` đã chụp trước khi triển khai PHASE 04. Trên workspace mới chưa có baseline, chạy `scripts/backend/capture_database_baseline.py` trước tests; script chỉ đọc DB và từ chối ghi đè baseline. Evidence baseline của phase hiện tại phải giữ nguyên; thay dữ liệu ở phase sau cần kế hoạch kiểm tra riêng.

PHASE04 lịch sử:80 passed, không fail/error/skip; health200, route thiếu404, sai method405; fingerprint trước/sau trùng. Evidence này giữ nguyên.

PHASE05A scoped tests (không nhận test module của worker khác vào evidence Auth/User):

```powershell
Push-Location backend
../.venv/Scripts/python.exe -X utf8 -m pytest -q tests/test_foundation.py tests/test_auth_foundation.py tests/test_auth_users.py --junitxml=evidence/phase05a-pytest.xml
Pop-Location
./.venv/Scripts/python.exe -X utf8 scripts/backend/verify_auth_users.py
```

Kết quả213 passed,0 fail/error/skip và20 real HTTP checks. Verify Auth/User dựng HTTP server tạm dùng ecommerce_test trên cổng trống, kiểm tra marker/topology, đóng server và xóa đúng fixture emails. Fingerprint dev so với baseline PHASE05A; chỉ đọc dev. Trước lần triển khai đầu mới dùng `verify_auth_users.py --capture`; file mở exclusive nên không ghi đè baseline đã có. Không reset DB. Dùng JUnit/evidence riêng PHASE05A, không ghi đè evidence PHASE04. [Evidence](../backend/evidence/README.md).

## PHASE05B Catalog

14 Category/Product public/Admin method/path đã có, [contract](api-contract.md) và [review](phase-05b-review.md). Không thêm dependency hoặc reseed. Fixture Catalog kiểm tra ownership/topology từ foundation; tạo/xóa đúng Category/Product IDs riêng trong ecommerce_test, giữ dev toàn bộ documents/validators/indexes. Canonical validator files trong project là dependency request adapter.

```powershell
Push-Location backend
../.venv/Scripts/python.exe -X utf8 -m pytest -q --junitxml=evidence/phase05b-pytest.xml
Pop-Location
./.venv/Scripts/python.exe -X utf8 scripts/backend/verify_catalog_runtime.py
```

Evidence PHASE05B ghi full workspace325 passed (112 Catalog +80 foundation +133 Auth/User); không ghi đè PHASE04/05A. Nếu chỉ chạy Catalog/foundation: chỉ định tests/test_catalog.py tests/test_catalog_transaction.py tests/test_foundation.py tests/test_auth_foundation.py (192 cases); counts evidence khi đó phản ánh scope đã chạy. Verify Catalog mở HTTP server localhost tạm từ source hiện tại, **read-only dev** public/Admin GET và unauthorized writes bị guard chặn; server đóng sau checks. Explain smoke category/type-price chỉ dùng index có sẵn, candidate chưa applied ghi đúng trạng thái. Fingerprint dev so với immutable phase04 baseline; no reset/reseed/index creation. Runtime server nền của project cần restart theo quy trình xác minh process đang giữ cổng nếu còn chạy source cũ; smoke không thay thế process của phiên khác.

## PHASE05C Commerce

10 Customer Cart/Checkout COD/Order method/path đã implement; [review](phase-05c-review.md), [contract](api-contract.md). Thực chạy Commerce và full backend suite, sau đó HTTP verifier:

```powershell
Push-Location backend
../.venv/Scripts/python.exe -m pytest tests/test_commerce.py -q --junitxml=evidence/phase05c-commerce-pytest.xml
../.venv/Scripts/python.exe -m pytest -q --junitxml=evidence/phase05c-pytest.xml
Pop-Location
./.venv/Scripts/python.exe -X utf8 scripts/backend/verify_commerce_runtime.py
```

Verifier dùng source hiện tại/temporary HTTP listeners; owned ecommerce_test phải trống trước/sau smoke. Dev fingerprint đối chiếu baseline `.local/phase05c-before.json` chụp trước implementation và05AB, không reset/reseed. Không ghi đè evidence cũ. Để dùng endpoints mới trên persistent server5001, restart backend project đúng quy trình xác minh process; verifier không tự thay process đó; phiên05C đã xác minh/restart đúng project process5001 để nạp source mới. VNPAY/Admin lifecycle/Dashboard/Frontend deferred, không bắt đầu phase tiếp theo.

## PHASE06B Admin Orders/Analytics

Chụp manifest trước final tests, giữ evidence phase cũ:

```powershell
./.venv/Scripts/python.exe -X utf8 -c "import json,sys;from pathlib import Path;sys.path.insert(0,'scripts/backend');from verify_integration_05ab import source_manifest;Path('.local/phase06b-source-before-tests.json').write_text(json.dumps(source_manifest(),indent=2),encoding='utf-8')"
Push-Location backend
../.venv/Scripts/python.exe -X utf8 -m pytest tests/test_admin_analytics.py -q --junitxml=evidence/phase06b-worker-pytest.xml
../.venv/Scripts/python.exe -X utf8 -m pytest -q --junitxml=evidence/phase06b-pytest.xml
Pop-Location
./.venv/Scripts/python.exe -X utf8 scripts/backend/verify_admin_runtime.py
```

Baseline immutable `.local/phase06b-before.json` chụp `verify_admin_runtime.py --capture` trước implementation, không ghi đè; khớp05C. Verifier chỉ mutate owned ecommerce_test nếu6collections rỗng, exact ID cleanup; dev chỉ đọc HTTP reports/explain/fingerprint. Trước verifier, persistent backend5001 phải chạy source mới theo quy trình xác minh project process; smoke health200/Admin anonymous401. Backend source/test hashes phải giữ nguyên từ trước tests; contract docs có thể được worker song song cập nhật, current11routes được audit riêng và cả hai manifest lưu trong evidence. ZoneInfo trên Windows reuse tzdata2025.2 từ DB tooling lock trong cùng `.venv`, không dependency mới. [Review](phase-06b-review.md).

## Log và giới hạn lịch sử PHASE05B

## Render production runtime (14/10/2026)

Install `backend/requirements-render.txt` from repository root and start `python backend/serve.py` with `APP_ENV=production`. This uses Waitress, not the local development runner. Set Atlas SRV URI, expected `MONGODB_REPLICA_SET`, `MONGODB_DB=novamart_demo`, private JWT secret/issuer/audience, exact HTTPS `FRONTEND_ORIGIN`, and `VNPAY_ENABLED=false`. Render supplies `PORT`; production defaults to `0.0.0.0`. Local `.env` is not automatically loaded. Keep repository root available because Dashboard loads canonical files from `database/aggregations`.

Read-only startup verification: `./.venv/Scripts/python.exe scripts/deploy/verify_render_runtime.py` (uses ignored `.local/atlas-upload/connection.json`, temporary owned listener5003). See [Render guide](render-deployment-guide.md). Production URL/TLS/proxy checks remain separate from this local WSGI check.

Catalog done chỉ trong backend scope. Checkout/category/stock concurrency tích hợp, Cart/Order/Payment/Dashboard/Frontend và full benchmark chưa thuộc phiên Catalog; Commerce đã có evidence05C riêng phía trên. latest INDEX CANDIDATE ở review Catalog, chưa tạo index. Không tự tiến phase.

Structured logs có requestId, method, endpoint, status, latency và error type/frame locations. Không ghi raw body/query/header/token/password/exception text hoặc locals. Client nhận lỗi an toàn và requestId; CORS không thay authorization. Auth limiter hiện local per-process/reset khi restart; chưa distributed limiter/deployment proxy. Full transaction tests, benchmark, VNPAY/frontend/deployment chỉ làm khi phase tương ứng được giao; không nghiệm thu trong PHASE05A.
