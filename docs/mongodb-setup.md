# MongoDB local — PHASE 03

Môi trường dùng MongoDB Community **8.0.32**, WiredTiger, single-node replica set **rs0**, chỉ bind `localhost:27017`. DB chính `ecommerce_dev`; `ecommerce_test` dành cho probe rollback; `ecommerce_roundtrip` dành riêng kiểm tra export/import Product/Order. Không dùng Atlas. Các script không xây API nghiệp vụ.

## Dựng trên Windows

Chạy PowerShell ở root project:

```powershell
./scripts/db/bootstrap.ps1
```

Bootstrap tải ZIP MongoDB từ [nguồn chính thức](https://www.mongodb.com/try/download/community), kiểm SHA-256 của hãng, giải nén trong `.tools`; cài Python 3.12 riêng bằng uv nếu chưa cung cấp `-Python312 <path>`, tạo `.venv` và cài dependencies pinned trong `scripts/db/requirements.lock.txt`. Không cài Windows service hoặc thay PATH toàn máy. Máy cần kết nối internet khi bootstrap đầu tiên. Runtime đã tải và nguồn Product cache cho phép seed/verify lại offline.

Nếu đã có binary MongoDB8.0, dùng `./scripts/db/start-mongo.ps1 -MongodPath <absolute-path>`. Script tạo config/data/log tại `.local/mongodb`, mở tiến trình nền, initiate rs0 một lần, chờ PRIMARY; từ chối thay tiến trình khác đang chiếm27017 hoặc reconfigure replica set khác. Những lần khởi động sau chạy `./scripts/db/start-mongo.ps1`. Tiến trình tồn tại sau khi terminal đóng; dữ liệu lưu trên đĩa. Không mở ra mạng, không chứa credential DB. Đây là môi trường development local theo [hướng dẫn replica set của MongoDB](https://www.mongodb.com/docs/v8.0/tutorial/deploy-replica-set-for-testing/).

## Cấu hình và tài khoản demo

Copy `.env.example` thành `.env`; đặt `SEED_DEMO_PASSWORD` bằng password development riêng dài12–128 ký tự. Không dùng placeholder làm password. `.env` và `.local` được ignore. Seed đọc biến môi trường trước `.env`; không in password ra console hoặc ghi plaintext vào DB. Argon2id m19456/t2/p1 với salt ngẫu nhiên mỗi User. Accounts: `admin@example.test`, `customer01@example.test`; cùng password fixture trong `.env`. Tài liệu credential riêng trên máy hiện tại là `.local/demo-credentials.md`. Không có API login ở phase này. JWT/VNPAY secrets chưa dùng và không cần điền.

## Apply và seed

```powershell
./.venv/Scripts/python.exe scripts/db/init_db.py
./.venv/Scripts/python.exe scripts/seed/seed.py
./.venv/Scripts/python.exe scripts/seed/seed.py --reset
./.venv/Scripts/python.exe scripts/validation/verify_database.py
./.venv/Scripts/python.exe scripts/validation/verify_reproducibility.py --reset
```

Seed mặc định dry-run, không kết nối/ghi DB. `--reset` là reset explicit chỉ dữ liệu fixture, giữ validator/index. Các công cụ mutation chỉ nhận ba DB allowlist trên local27017/rs0, tạo filesystem ownership marker khi DB còn trống, từ chối DB có dữ liệu trước marker hoặc khác project. Seed từ chối bất kỳ document ngoài tập deterministic IDs, gồm Cart tạo thủ công. Không drop database/collection; reset+insert+stock/price update cùng transaction. Không chạy reset trên DB đang dùng ở phase API về sau.

Apply tạo sáu collection với validator `strict/error` từ JSON canonical, không copy schema. Tạo11 unique constraints +3 workload indexes. `.local` ownership marker không phải collection nghiệp vụ. `init_db.py` có thể chạy lại. Đọc `database/evidence/verification.json` để xem kết quả thật, không nhầm với kiểm tra tĩnh phase02.

## Export/import và Compass

```powershell
./.venv/Scripts/python.exe scripts/export/export_data.py
./.venv/Scripts/python.exe scripts/import/import_data.py
./.venv/Scripts/python.exe scripts/import/import_data.py --reset
```

Export tạo `database/exports/products.json`, `orders.json` và checksum/count manifest; canonical Extended JSON arrays giữ ObjectId, UTC Date, int/long. Không export User/passwordHash. Import mặc định dry-run; reset chỉ `ecommerce_roundtrip`, apply đủ validator/index trước import, kiểm checksum và so sánh toàn bộ BSON sau transaction. Roundtrip là backup slice hai collection; không clone User/Category/Attempt nên không đại diện DB nghiệp vụ hoàn chỉnh. Referenced IDs được giữ nguyên để trace về DB gốc.

Compass kết nối `mongodb://localhost:27017/?replicaSet=rs0`. Xem `ecommerce_dev` cho dữ liệu đầy đủ, `ecommerce_roundtrip` cho bản import. Có thể nhập file JSON vào collection tương ứng trong roundtrip sau khi tạo DB/validators bằng công cụ; document trùng `_id` sẽ bị từ chối nếu chưa làm sạch slice riêng. Xuất với Extended JSON, không chọn CSV cho snapshot nested. Script roundtrip là bằng chứng kiểm thử; thao tác UI Compass sẽ rehearsal khi chuẩn bị bảo vệ.

## Evidence và giới hạn

Evidence lưu tại `database/evidence`: manifest nguồn/version/tồn kho, kết quả8 pipelines, explain executionStats thô, live checks, reseed và roundtrip. Probe validator/unique chạy trong `ecommerce_test` và abort từng transaction, DB test cuối cùng trống. Explain gồm planner không hint, natural scan và named index trên cùng dataset/query; không suy ra p50/p95 hoặc tốc độ production từ một lần chạy180 Product.

MongoDB/Python binary, data WiredTiger, password, cache download và log không commit. Muốn chuyển project sang đường dẫn/máy khác, bootstrap/seed lại; ownership marker chứa đường dẫn project và không được copy sang vị trí mới để vượt guard. Không cần xóa DB của người khác để dựng lại.
