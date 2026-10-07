# Sàn thương mại điện tử đa ngành — đồ án NoSQL

**PHASE 04 hoàn thành Flask backend foundation; dừng để review.** App factory/config/PyMongo/health/errors/JWT-Argon2-guards/validation/logging đã hoạt động; 80 tests pass. Chỉ health IMPLEMENTED, các API nghiệp vụ/frontend vẫn PLANNED. Thiết kế MongoDB PHASE 02 và dữ liệu PHASE 03 giữ nguyên.

MongoDB Community 8.0.32/WiredTiger, local replica set **rs0 PRIMARY**, DB **ecommerce_dev**. Python 3.12.14/PyMongo 4.15.3/Flask 3.1.3. Server local hiện tại: [GET health](http://127.0.0.1:5001/api/v1/health), trả 200; port private 5001 vì 5000 có ứng dụng khác.

## Chạy backend

```powershell
./scripts/db/start-mongo.ps1
./scripts/backend/bootstrap.ps1
./scripts/backend/start.ps1
Push-Location backend
../.venv/Scripts/python.exe -m pytest --junitxml=evidence/pytest.xml
Pop-Location
```

Máy hiện tại đã có MongoDB và seed; không cần reset dữ liệu khi chạy backend. Hướng dẫn môi trường mới/config/test DB guards tại [backend setup](docs/backend-setup.md). Dependency runtime/dev locks trong backend; `.env` private, `.env.example` chỉ key/placeholder. Review [PHASE 04](docs/phase-04-review.md), [API contract](docs/api-contract.md), [module map](backend/README.md), [evidence](backend/evidence/README.md).

| Collection | Documents |
| --- | ---: |
| products |180 —60 mỗi ngành |
| categories |3 |
| users |40 —1 Admin/39 Customer |
| orders |100 —2–5 items/đơn |
| payment_attempts |30 fixture VNPAY |
| carts |0 —baseline lazy |

Sáu validators strict/error,14 declared indexes (+6 _id_).9 positive/33 invalid/11 duplicate constraint tests pass trên MongoDB.8 pipelines đã chạy: revenue **10.103.259.022VND**,60 COMPLETED+PAID,434 units, không shipping. Seed lần2 giữ nội dung/counts; export/import180 Product/100 Order giữ nguyên BSON. Explain planner IXSCAN đọc10 docs/10 keys, natural COLLSCAN180 docs/0 keys; cả hai0 ms ở độ phân giải timer, chưa benchmark đầy đủ.

## Dựng và kiểm tra MongoDB (PHASE 03)

Chi tiết cấu hình/guard/Compass: [MongoDB setup](docs/mongodb-setup.md).

    ./scripts/db/bootstrap.ps1
    ./.venv/Scripts/python.exe scripts/db/create_dev_env.py
    ./.venv/Scripts/python.exe scripts/db/init_db.py
    ./.venv/Scripts/python.exe scripts/seed/seed.py --reset
    ./.venv/Scripts/python.exe scripts/validation/verify_database.py

Bootstrap lần đầu tải runtime; có thể cung cấp -Python312 với đường dẫn Python 3.12 đã cài. Khởi động lại Mongo bằng scripts/db/start-mongo.ps1. Seed mặc định không --reset chỉ dry-run. Reset chỉ DB fixture local allowlist có ownership marker, từ chối ID lạ, không dropcollection/database. Password demo generate trong ignored .env/.local/demo-credentials.md và Argon2id trongDB; không commit credentials. Chưa có API login.

## Tài liệu và evidence

- [Review PHASE 03 đầy đủ](docs/phase-03-review.md): runtime/counts/distributions/results/indexes/explain/files/issues/deferred.
- [Evidence thực](database/evidence/README.md), [live verification](database/evidence/verification.json), [aggregation outputs](database/evidence/aggregation-results.json), [explain](database/evidence/explain-baseline.json).
- [Seed strategy](docs/seed-strategy.md), [nguồn catalog](database/sources/README.md), [demo plan](docs/demo-plan.md), [generated mongosh queries](database/evidence/demo-queries.mongodb.js).
- Thiết kế: [architecture](docs/architecture.md), [schema](docs/database-schema.md), [business rules](docs/business-rules.md), [foundation](docs/foundation-decisions.md).
- Canonical artifacts: [validators](database/validators/README.md), [indexes](database/indexes/README.md), [aggregations](database/aggregations/README.md), [design samples](database/samples/README.md).
- Agent protocol: [AGENTS](AGENTS.md). Lịch sử: [PHASE 01](docs/phase-01-review.md), [PHASE 02](docs/phase-02-review.md).

## Phạm vi source

DB tooling tại scripts/db,seed,validation,export,import; sources/evidence tại database. Backend foundation tại backend/app/tests và scripts/backend; sáu business collections users/categories/products/carts/orders/payment_attempts giữ nguyên. Foundation tests chỉ ghi fixture vào ecommerce_test riêng; full documents/validator/index fingerprint dev trước/sau trùng nhau. .tools/.local/.venv/.env/database/exports được ignore. Không tạo Git remote/PR/commit.

Spec/extra variants/giá biên soạn cho demo từ cache [DummyJSON Products](https://dummyjson.com/docs/products), ảnh URL CDN không localhost, không download hàng loạt. Chưa rehearsal Compass UI/Web; VNPAY là metadata fixture. Full Auth/Product/Cart/Checkout/Order/Payment/Dashboard, frontend, reviews/Atlas/cloudmedia, full benchmark và deployment chờ phase tiếp theo do người dùng giao.
