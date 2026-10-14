# Evidence backend

Follow-up07D14/10/2026: `phase07d-fix-pytest.xml` là full suite mới658passed/0failure/error/skip,108.085s,backend app/tests không đổi. Frontend formimages=[]đã sửa và kiểm chứng qua AdminWeb/snapshot thật;[review](../../docs/phase-07d-price-editor-fix-review.md),[summary/integrity](../../database/evidence/phase07d-fix-summary.json). Dev/benchmark unchanged,testempty saupytest;manualCompass/timing/offlineOS vẫnpending,khônggọi07DFINALPASS.

PHASE07A — full system hardening:

- `phase07a-pytest.xml`: full suite658passed/0failure/error/skip,195.587s; backend source/test hashes khớp06AB.
- `phase07a-system.json`: strict production build và chunk warning,22+32regression/25full-system groups/258HTTP/6frontend Payment contract cases/3chart views,13blueprints52paths, source manifest và runtime health thật. Browser unexpected errors/assets/network=0; expected negative console/navigation aborts ghi riêng. Private env values scan99public files,0matches.
- `phase07a-db-integrity.json`: owned test fixtures cleanup/exactIDs,6test collections rỗng; dev/test6validators14declared+6_id_,0global orphans. Original corpus f8c36f... giữ nguyên; full dev0a3ebe... có fixture07C được giữ theo task của worker đó,07AdevWrites0. Không reset/reseed/sweep fixtures khác.
- [Full system review](../../docs/phase-07a-full-system-review.md); browser evidence riêng tại frontend/tests/phase07a-*.json. VNPAY LIVE SANDBOX BLOCKED;6fault-injection FE cases không phải provider rehearsal. Không commit/push, dừng review.

PHASE06AB — backend integration checkpoint:

- **Database cleanup follow-up:** `phase06ab-db-cleanup.json` xác minh exact email/Order/cancellation từ E2E FE-01A, xóa đúng1User/1Cart/1Order/0Attempt, restore2metadata Product/Category với stock97 giữ nguyên; transaction snapshot/majority/private backup. Fingerprint cuối f8c36f... khớp original06AB41Users baseline có account được giữ; seed-only virtual digest3cb02b... khớp historical.6validators/14declared indexes +6_id_/global orphan audit PASS; backend source unchanged. [Cleanup review](../../docs/phase-06ab-db-cleanup-review.md). Pending data review trong evidence integration gốc bên dưới đã được giải quyết, không viết lại lịch sử external writes; live Sandbox vẫn BLOCKED.

- `phase06ab-pytest.xml`: full suite được chạy lại trên source hiện tại,658 passed/0failed/errors/skipped,188.676s JUnit; không dùng lại kết quả worker.
- `phase06ab-integration.json`:96 real HTTP checks pass,13blueprints/52method-path/0duplicate/collision/shadow;5 contract sections khớp routes/features,16 shared primitives duy nhất. Payment/Commerce/Admin cùng app; fixture revenue360000VND/3units, loại60000shipping, PAID chưa COMPLETED và cancelled/expired/review không vào revenue; đổi live Product không đổi historical snapshot/revenue.
- Dev6validators/14declared indexes +6_id_ khớp canonical artifacts. Full fingerprint trước/sau smoke trùng; ecommerce_test6collections cleanup rỗng. Có external dev changes trước smoke: User đầu đã được người dùng xác nhận giữ, User/Cart/Order tiếp theo còn chờ xác nhận; không claim full-session dev unchanged. Original baselines giữ nguyên; JSON ghi rõ external delta/pending data review. LIVE SANDBOX BLOCKED, không claim real provider rehearsal.
- Không application fix/refactor/Frontend/feature mới/commit/push. [Review và FRONTEND HANDOFF](../../docs/phase-06ab-integration-review.md).

PHASE06A — VNPAY Sandbox Payment backend:

- `phase06a-payment-pytest.xml`:102 scoped Payment tests pass/0fail/error/skip,27.60s; real rs0 atomic checkout/attempt/retry/IPN/expiry/cancel races/rollback/ambiguous commit, signature vector/security/Return readonly/CLI expiry.
- `phase06a-pytest.xml`:658 full tests pass/0fail/error/skip,187.99s =451 existing+102Payment+105Admin/Analytics do worker06B riêng. Source backend/tests/API contract final manifest giữ nguyên trước tests→sau HTTP.
- `phase06a-runtime.json`:50 current-source real HTTP checks pass,13blueprints/52method-path/no collision,3Payment routes khớp contract/feature docs, full dev fingerprint trước/sau trùng immutable05C/phase04;6test collections rỗng sau exact cleanup. Fixture credentials giả; live Sandbox BLOCKED vì thiếu merchant/IPN config, không real redirect/bank/IPN claim. [Review06A](../../docs/phase-06a-review.md), [setup](../../docs/payment-setup.md).
- `phase06a-commerce-regression.xml`:126 Commerce pass sau core implementation; final full suite phía trên kiểm tra source cuối. Baseline ignored `.local/phase06a-source-before-tests.json`; không reset/reseed/drop/mutate dev hoặc ghi đè evidence phase khác.

PHASE06B — Admin Orders + Analytics:

- `phase06b-worker-pytest.xml`:105 scoped tests trên real rs0/canonical validators, role/lifecycle/version/replay/concurrency/rollback/snapshot/date/day-month/Top5/empty report và pipeline oracle450VND/8units.
- `phase06b-pytest.xml`:658 full backend tests pass/0 fail/error/skip, gồm451 existing +105Admin/Analytics +102Payment của worker06A. Backend source/test hashes từ trước scoped/full runs giữ nguyên đến cuối runtime; contract docs được worker06A cập nhật trong lúc tests và audit riêng, hai manifests lưu đầy đủ. Không gán implementation Payment cho06B.
- `phase06b-runtime.json`:46 HTTP checks guest401/customer403 trên11endpoints, Admin lifecycle/dashboard/COD/cancel replay, seed read-only oracle, source manifest/routes13blueprints/52method-path/no collision và full dev fingerprint before/after. Persistent backend5001 thêm3checks health200/Admin401. Test cleanup exact fixture IDs/6collections rỗng; không reset/reseed dev.
- `phase06b-explain.json`:8 canonical pipelines và named-index/natural Top5 results equal; revenue reuse ix_orders_qualified_completed60docs/60keys, natural100docs/0keys. Không index mới/full benchmark/speedup claim. [Review06B](../../docs/phase-06b-review.md).
- Baseline ignored `.local/phase06b-before.json` exclusive capture trước implementation; final manifest `.local/phase06b-source-before-tests.json`. Không Frontend/VNPAY gateway/schema/revenue rule change trong worker06B.

PHASE05C — Commerce backend:

- `phase05c-commerce-pytest.xml`:126 pass/0 fail/error/skip trên source cuối; real rs0 Cart/version/lazy create/shared selection stock, signed quote/reprice/address/idempotency, snapshot độc lập, checkout/cancel rollback và concurrency. Fault synchronization không thay DB transaction bằng mock.
- `phase05c-pytest.xml`:451 full tests pass/0 fail/error/skip (80foundation +133Auth/User +112Catalog +126Commerce), source hashes trước/sau final tests giữ nguyên. Không ghi đè evidence lịch sử.
- `phase05c-runtime.json`:38 current-source HTTP checks pass, Customer login→Product→Cart→COD checkout→history/snapshot→cancel/replay, stock decrease/restore/Cart version verified.10blueprints/38method-path/no collision,10commerce endpoints khớp contract/feature docs; runtime/source manifest/full dev fingerprint trước/sau trùng05AB/phase04;6test collections rỗng sau cleanup. VNPAY503 trước write, no fake payment. [Review Commerce](../../docs/phase-05c-review.md).
- Baseline riêng ignored `.local/phase05c-before.json` chụp dev trước implementation; `.local/phase05c-source-before-tests.json` khóa manifest source cuối trước final scoped/full runs. Không reset/reseed/index creation hoặc mutate dev. VNPAY gateway/Admin Orders/Dashboard/Frontend/benchmark chưa nghiệm thu.

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
