# Sàn thương mại điện tử đa ngành — đồ án NoSQL

**Cập nhật19/10/2026:** Backend SKU/reviews hardening701tests PASS, frontend strict/build PASS, npm audit0findings. ADR013 khóa selection, tồn kho theoSKU, verified reviews và migration additive. Đã deploy cả backend/frontend Render,62publicHTTPS checks PASS, cleanup/fingerprint Atlas giữ nguyên và0orphans. Browser scoped390/768/1280 PASS; VNPAY disabled theo người dùng. [Review hiện tại](docs/sku-review-hardening-review.md), [ADR013](docs/decisions/013-sku-review-hardening.md).

**Checkpoint14/10/2026 (lịch sử):** NovaMart đã có React frontend, Flask backend, Auth/User, Catalog, Cart/Checkout/COD, Orders, Admin Dashboard và Payment implementation. Fullbackend674tests PASS; rehearsal với ảnh mới12nhóm PASS. [Website public](https://novamart-web.onrender.com) và [API health](https://novamart-api.onrender.com/api/v1/health) đã chạy trên Render/Atlas;50publicHTTP checks và exact cleanup PASS. Backend$7/tháng,Static Site/Atlas free. [Review deployment và giới hạn](docs/render-public-deployment-review.md) có dependency audit cần follow-up; VNPAY Live Sandbox chưa PASS và đang disabled.

Xem [hướng dẫn Render/Atlas](docs/render-deployment-guide.md), [kết quả kiểm thử mới](docs/render-deployment-review.md), [API contract](docs/api-contract.md) và [checklist bảo vệ](docs/pre-demo-checklist.md). `.env`/`.local`/credentials không thuộc repository. Các mục PHASE04 bên dưới giữ lịch sử foundation, không phải trạng thái feature hiện tại.

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

## Lịch sử Commit Dự án

Bảng nhật ký theo dõi chi tiết toàn bộ commit của dự án, cập nhật liên tục theo chuẩn:

| STT | Tác giả | Thay đổi | Tên commit |
| :---: | :--- | :--- | :--- |
| 1 | Nguyen Ngoc Phi | Tích hợp xác thực Auth, quản lý User và Catalog backend | `PHASE 05AB - Auth Users and Catalog integration pass` |
| 2 | Nguyen Ngoc Phi | Kiểm thử full system và hoàn thiện cấu hình Render deploy | `Novamart full system verified and Render deployment ready` |
| 3 | Nguyen Ngoc Phi | Cấu hình hạ tầng Render compute và verify public deploy | `Configure approved Render compute and public deployment verification` |
| 4 | Nguyen Ngoc Phi | Xác thực Render public và làm rõ database badge | `Verify public Render deployment and clarify database badge` |
| 5 | Nguyen Ngoc Phi | Ghi nhận tài liệu deployment và audit tên sản phẩm song song | `Record final deployment and concurrent product naming audit` |
| 6 | Sweet Bakery (hoang) | Thiết lập quy chuẩn Conventional Commits, quy tắc chia nhỏ commit chi tiết và bảng nhật ký dự án | `docs(convention): enforce atomic commit policy and project ledger` |
| 7 | Sweet Bakery (hoang) | Nâng cấp JSON Schema validator cho products (hỗ trợ tierVariations, skus, ratingSummary) và bổ sung validator reviews kèm indexes | `schema(db): upgrade product validator for tier variations and add reviews collection with indexes` |
| 8 | Sweet Bakery (hoang) | Cập nhật bộ kịch bản kiểm thử và xác thực ràng buộc DB cho collection reviews | `test(db): update verification probes and expected collections for reviews` |
| 9 | Sweet Bakery (hoang) | Xây dựng script nạp sản phẩm thực tế đa biến thể SKU và reviews xác thực | `feat(seed): add realistic multi-tier sku products and authentic reviews generator` |
| 10 | Sweet Bakery (hoang) | Nâng cấp giao diện chọn phân loại đa tầng dynamic tier variations, cập nhật giá và kho real-time theo SKU và khắc phục lỗi cứng size | `feat(ui): support dynamic tier variations and real-time sku price updates` |
| 11 | Sweet Bakery (hoang) | Cập nhật logic tính giá giỏ hàng và projection kho theo SKU ma trận đa ngành | `feat(backend): support multi-tier sku pricing and cart resolution` |
| 12 | Sweet Bakery (hoang) | Cập nhật file bằng chứng seed manifest ghi nhận collection reviews | `test(evidence): record seed manifest with reviews collection` |
| 13 | Sweet Bakery (hoang) | Cập nhật cấu hình fixture test backend cho collection reviews và ổn định kiểm tra mật khẩu môi trường test | `test(backend): add reviews collection to conftest fixture and stabilize seed password check` |
| 14 | Sweet Bakery (hoang) | Bổ sung tài liệu đặc tả clean-room kiến trúc sàn TMĐT tham chiếu Shopee và TikTok Shop | `docs(spec): add clean-room e-commerce specifications for shopee and tiktok shop` |
| 15 | Sweet Bakery (hoang) | Nâng cấp JSON Schema validator cho carts và orders hỗ trợ biến thể thuộc tính động | `fix(schema): allow dynamic selectedAttributes in cart and order validators` |
| 16 | Sweet Bakery (hoang) | Mở rộng schema xác thực SELECTION của giỏ hàng chấp nhận thuộc tính phân loại đa tầng và khắc phục lỗi 422 | `fix(cart): expand SELECTION schema to accept multi-tier variant attributes` |
| 17 | Sweet Bakery (hoang) | Xây dựng API và service truy vấn danh sách đánh giá sản phẩm cùng thống kê phân phối sao | `feat(api): add public product reviews and rating summary endpoint` |
| 18 | Sweet Bakery (hoang) | Tái thiết kế toàn diện trang chi tiết sản phẩm theo chuẩn Shopee Mall: badge Yêu Thích+, voucher shop, nút Mua Ngay và khu vực đánh giá UGC thực tế | `feat(ui): redesign product detail to authentic shopee standards with mall badges, vouchers, and ugc reviews` |
| 19 | Sweet Bakery (hoang) | Hoàn thiện ma trận toàn bộ hoán vị SKU thực tế, fix lỗi nhảy giá biến thể MacBook M3 và xử lý vô hiệu hóa phân loại hết hàng | `fix(catalog): complete sku permutation matrix and disable out-of-stock variations` |
| 20 | Sweet Bakery (hoang) | Sửa logic điều hướng đăng nhập Admin vào thẳng Dashboard, thêm nút truy cập nhanh Admin trên Navbar và bổ sung phạm vi toàn bộ dữ liệu seed cho biểu đồ phân tích | `fix(admin): route admin directly to dashboard on login and enhance navbar portal access` |
| 21 | Sweet Bakery (hoang) | Loại bỏ toàn bộ các text vô hồn về đồ án/sinh viên/demo trên Navbar, Footer và Checkout; chuyển đổi thành giao diện thương mại điện tử chuyên nghiệp chuẩn thương hiệu | `style(ui): sanitize student project and demo disclaimer copy into professional ecommerce brand experience` |
| 22 | Sweet Bakery (hoang) | Dọn dẹp bộ lọc sidebar trang danh mục sản phẩm, loại bỏ các nút cứng kích cỡ thời trang và RAM điện tử | `refactor(ui): clean up product catalog sidebar by removing rigid polymorphic attribute filters` |
| 23 | Sweet Bakery (hoang) | Xây dựng các trang chính sách pháp lý TMĐT (điều khoản, bảo mật, đổi trả, giao hàng) và chuẩn hóa liên kết chân trang | `feat(policy): add ecommerce policy pages and sanitize promotional banner icons` |
| 24 | Sweet Bakery (hoang) | Nâng cấp thanh tìm kiếm thông minh SmartSearchBar với lịch sử tìm kiếm localStorage, gợi ý từ khóa hot và auto-suggest debounced | `feat(search): implement smart search bar with local history and instant suggestions` |
| 25 | Sweet Bakery (hoang) | Hoàn thiện luồng đánh giá sản phẩm sau khi đơn hoàn tất (UGC Reviews), tính toán cập nhật điểm sao atomic và modal gửi nhận xét | `feat(reviews): implement verified purchase review submission and atomic rating aggregation` |
| 26 | Sweet Bakery (hoang) | Xây dựng bộ test case toàn diện kiểm thử 5 phase nâng cấp chuẩn Shopee và tinh chỉnh cấu hình proxy phát triển | `test(parity): add comprehensive test suite for shopee parity features and dev proxy` |

| 27 | Nguyen Ngoc Phi | Hoàn thiện transaction tồn kho SKU, xác thực phân loại và reviews atomic, cập nhật contract | `fix(commerce): enforce SKU stock and verified review invariants` |
| 28 | Nguyen Ngoc Phi | Bảng chọn khi mua, quản trị SKU, reviews phân trang và nâng dependency để đóng audit | `fix(frontend): complete purchase selection and SKU administration` |
| 29 | Nguyen Ngoc Phi | Migration Atlas additive giữ nguyên corpus, seed an toàn, design checker và evidence kiểm thử | `fix(tooling): migrate SKU review schema with exact integrity evidence` |
| 30 | Nguyen Ngoc Phi | Ghi nhận cả hai Render Live, 62 public checks, responsive và exact cleanup Atlas | `docs(deploy): record public SKU review verification and clean baseline` |
| 31 | Nguyen Ngoc Phi | Giám sát API/expiry và mốc vận hành Sandbox giữ nguyên seed | `fix(payment): supervise expiry and preserve historical demo fixtures` |
| 32 | Nguyen Ngoc Phi | Đồng bộ kết quả VNPAY với Order, phân biệt lỗi mạng và trạng thái ngân hàng | `fix(frontend): reconcile payment result with current order state` |
| 33 | Nguyen Ngoc Phi | Sửa reviews404 cho slug24hex và khóa ưu tiên existing ID khi trùng | `fix(reviews): resolve valid hexadecimal product slugs` |
| 34 | Nguyen Ngoc Phi | Bổ sung công cụ rehearsal Sandbox có journal/cleanup, evidence710tests và rà soát định mức | `test(payment): add owned sandbox rehearsal and hardening evidence` |
| 35 | Nguyen Ngoc Phi | Cho rehearsal dùng địa chỉ đã có khi chưa đặt mặc định và báo đúng phạm vi COD regression | `fix(tooling): resume owned sandbox fixtures without a default address` |
| 36 | Nguyen Ngoc Phi | Ghi nhận Render Sandbox config,710tests,62publicchecks,exact cleanup và gate điều khoản chưa xác nhận | `docs(payment): record sandbox readiness and pending provider consent` |
| 37 | Nguyen Ngoc Phi | Kiểm tra runtime/Atlas sau resume và ghi rõ browser chưa kết nối, không phát sinh đơn thử | `docs(payment): record readonly resume checks and browser handoff` |
| 38 | Nguyen Ngoc Phi | Xác minh hai giao dịch NCB Sandbox/automaticIPN, checkout Web, Admin/revenue và exact cleanup | `docs(payment): verify real sandbox checkout and callback integrity` |
| 39 | Nguyen Ngoc Phi | Sửa gộp SKU optional id trong Cart, khóa giới hạn99 và bổ sung4regression realrs0 | `fix(cart): merge equivalent SKU selections before quantity checks` |
