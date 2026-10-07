# Evidence backend

PHASE05B — Catalog:

- `phase05b-pytest.xml`:325 workspace tests passed,0 fail/error/skip;112 Catalog +80 foundation +133 Auth/User của phiên khác. Catalog integration dùng canonical validators/unique indexes và real local rs0; races/rollback/version patch/polymorphism/search/filter/pagination đều thực chạy. Auth/User code/evidence không thuộc implementation phiên Catalog.
- `phase05b-runtime.json`:9 HTTP checks qua temporary localhost server/current source, public/admin reads200, Guest write401/Customer write403. Dev180 Product/3 Category/40 User/100 Order và toàn bộ documents/validators/indexes fingerprint trùng immutable phase04 baseline. Category/Product test fixtures đã cleanup.
- Explain smoke: category-price unhinted/hinted IXSCAN trên index đã có; category lookup `_id_`. Type-price declared candidate chưa applied, planner behavior lưu nguyên. Không full benchmark/p50/p95 hoặc claim speedup; không thêm/drop index. [Review Catalog](../../docs/phase-05b-review.md).
- Persistent localhost server5001:Product list200/total180 và unknown detail query422; không cần thay process. Runtime ghi kết quả2checks này riêng `persistentServerSmoke`.

PHASE05AB — integration checkpoint:

- `phase05ab-pytest.xml`: full suite source hiện tại325 pass/0 fail/error/skip, không chạy subset; module breakdown80 foundation +133 Auth/User +112 Catalog.
- `phase05ab-integration.json`:35 HTTP checks pass trên same-app Auth/User/Catalog và dev/persistent server; JWT từ login dùng được cho Catalog, block token được cả hai module enforce.7 blueprints/28 method-path, không collision; contract13 Auth/User +14 Catalog khớp routes/feature docs; shared primitive definitions duy nhất.
- Source manifest và full dev documents/options/validators/indexes fingerprint trước/sau giữ nguyên, khớp historical baseline; test fixtures cleanup,6 collections test rỗng. Chưa có Git HEAD, không giả định commit SHA. [Review checkpoint](../../docs/phase-05ab-integration-review.md). Không bắt đầu Commerce/Frontend.

PHASE05A — Auth/User:

- `phase05a-pytest.xml`:213 passed,0 failures/errors/skips;80 foundation +133 Auth/User. Python3.12.14/pytest9.1.1/MongoDB8.0.32 local rs0, users validator và unique email index thật; concurrent register/profile/address/default/status/password đã kiểm tra.
- `phase05a-runtime-verification.json`:20 HTTP checks thật qua temporary threaded local server trên owned ecommerce_test, bao phủ13 endpoints/Auth/User/Admin và token revocation. Server được đóng sau smoke; fixture xóa đúng email/ID.
- Baseline riêng `.local/phase05a-db-before.json` giữ immutable. Fingerprint toàn bộ dev documents/options/validators/indexes trước/sau trùng;40 User/180 Product/100 Order giữ nguyên, ecommerce_test rỗng sau cleanup. Không ghi credentials vào evidence.

PHASE04 — evidence lịch sử giữ nguyên:

- `pytest.xml`: 80 tests passed, 0 failures/errors/skipped, Python 3.12.14 / pytest 9.1.1; suite kiểm tra Flask foundation và auth helpers với MongoDB test thật.
- `runtime-verification.json`: HTTP server thật health 200, unknown route 404, wrong method 405; requestId đúng envelope/header; rs0 PRIMARY và fingerprint dev DB trước/sau trùng.

Fingerprint bao gồm toàn bộ documents của 6 collections, collection options/validators và indexes. Baseline riêng tại ignored `.local/phase04-db-before.json`; không đưa documents/password hashes vào evidence public. Fixture đã cleanup, 6 collections ecommerce_test đều rỗng.

Đây là bằng chứng foundation, không chứng minh business API, transaction checkout/payment, full benchmark hay frontend đã hoàn thành. Chạy lại theo [backend setup](../../docs/backend-setup.md). Kết quả MongoDB PHASE 03 vẫn ở `database/evidence`.
