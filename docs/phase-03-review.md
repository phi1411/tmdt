# Review PHASE 03 — MongoDB Implementation + Seed + Verification

**DONE trong phạm vi PHASE 03; dừng để review.** Database thật đã được kiểm thử. Thiết kế v1 giữ nguyên sáu collection, Product đa hình, Cart riêng, Order snapshot, revenue và payment architecture. Không cần correction/ADR mới. Yêu cầu gốc: [phase03 source](requirements-phase-03-source.txt).

## 1. Runtime

MongoDB **Community 8.0.32/WiredTiger**, ZIP chính thức khớp SHA-256; Python**3.12.14**, PyMongo**4.15.3**. Local single-node replica set **rs0**, member `localhost:27017`, health1, **PRIMARY**. DB chính **ecommerce_dev**. DB `ecommerce_test` cuối cùng trống sau rollback probes; `ecommerce_roundtrip` là slice Product/Order. Bindlocalhost, không Atlas, không credential hardcoded, không cài Windows service/thay PATH. [Setup](mongodb-setup.md), dependency lock và bootstrap tái lập môi trường.

## 2. Collections/counts thực

| Collection | Documents | Ghi chú |
| --- | ---: | --- |
| users |40 |1 ADMIN/39 CUSTOMER; Argon2id thật |
| categories |3 |Một cấp, slug unique, type-compatible |
| products |180 |60 ELECTRONICS/60 FASHION/60 HOME_APPLIANCE |
| carts |0 |Baseline lazy; validator test bằng rollback probe |
| orders |100 |25 đơn 2 items/21 đơn 3 items/20 đơn 4 items/34 đơn 5 items |
| payment_attempts |30 |Fixture VNPAY, không gọi provider |

Không thêm collection nghiệp vụ/reviews. IDs ObjectId, UTC BSONDate, money long, quantity/stock/version int. [Live verification](../database/evidence/verification.json) chứa topology/counts/invariants/indexes thật.

## 3. Validators

Apply nguyên sáu JSONSchema v1 từ database/validators, strict/error; so collection options thực với canonical. **9 positive accepted,33 invalid rejected mã121,11 unique duplicates rejected mã11000**. Positive gồm sáu collection và ba ProductType; Order embedded hợp lệ. Negative gồm required/enum/type mỗi collection, business enums, RAM/sizes/power type, snapshot thiếu priceAtPurchase, COMPLETED thiếu completedAt/unpaid, money int thaylong, Cartquantity0, unsafeattribute và sensitivepaymentfield. Mỗi probe abort transaction; DBtest cuối cùng0 docs, devdigest không đổi.

## 4. Product source/ảnh

Cache194 records từ [DummyJSON Products](https://dummyjson.com/docs/products), checksum `d8528cbb47dedc9ddfd769d46dd1ee680b215f850fbf631fedb979be0f02fcab`. Normalize119 nguồn phù hợp (38 Electronics/46 Fashion/35 Home);61 biến thể bổ sung ghi rõ demo để có180/60 mỗi ngành. [Provenance](../database/sources/provenance.json), [manifest từng Product/version/inventory](../database/evidence/seed-manifest-ecommerce_dev.json). Không import raw dataset/reviews/PII. Spec theo ngành biên soạn cho fixture; giá synthetic USD×25.000 và điều chỉnh biến thể, không phải thông số hãng/tỷ giá hiện tại.

Electronics có RAM/storage/chip hoặc connectivity/compatibility; Fashion sizes/colors/material/gender/fit/sole; Home material/capacity/assembly/room/dimensions/power khi phù hợp. **180/180 có HTTPSimageURL**, không localhost. HEAD đại diện3ngành đều200/imagewebp, [evidence](../database/evidence/image-url-checks.json); chỉ3URLs được probe availability, không tải tất cả media. Frontend về sau cần fallback nếu CDN đổi.

## 5. Users/password

40 password verify thật, đúng Argon2id m19456/t2/p1 với salt riêng. DB không plaintext. Dev accounts `admin@example.test`, `customer01@example.test`; privatepassword trong ignored `.env`/`.local/demo-credentials.md`, không commit. Không có API login trong phase03.

## 6. Status/payment distribution

| Order status | Count | COD / VNPAY |
| --- | ---: | --- |
| COMPLETED |60 |40/20 |
| PENDING |10 |5/5 |
| CONFIRMED |10 |10/0 |
| SHIPPING |10 |10/0 |
| CANCELLED |5 |5/0 |
| EXPIRED |5 |0/5 |

Payment methods70 COD/30 VNPAY. Order paymentStatus60 PAID/30 UNPAID/5 PENDING/5 FAILED. Attempts20 SUCCEEDED/5 PENDING/5 EXPIRED. Verify terminal/paid/deadline timestamps, provider cap/amount×100, owner/order refs; COD không có Attempt. VNPAY metadata mô phỏng, không card/secret/rawcallback/providertransaction thật. Dates90ngày trước anchor2026-10-01T00:00:00Z; Pending chưa hết hạn tại anchor nhưng sẽ đến hạn ở thời điểm demo sau đó. Không chạy expiryworker hoặc đổi clock ở phase03.

## 7. Snapshot/references/stock

Seed transaction snapshot-read/majority-write: insert Product cơ sở → đọc lại Product/Category/User từ MongoDB → sinh Order/Attempts → cập nhật tồn/currentprice → commit. MỗiOrder2–5Product khác nhau/quantity1–3, full item/customer/address/category snapshots. Verify normalization/selection/reference/chronology/arithmetic/type/cap và snapshot origin từ baseversion.

Order `DEMO-2026-0001` có Product `DEMO-ELE-001` giá mua10 triệu, currentProduct12 triệu. Verifier đổi tạm price99 triệu/name trong transaction rồi chạy lại năm báo cáo doanh thu, output không đổi; abort và so devdigest giữ nguyên. Chứng minh snapshot fixture, chưa có checkoutAPI.

Inventorymanifest initial100/Product, sold/reserved/released/final; final=initial−sold−reserved, terminal cancelled/expired ghi stockReleasedAt, netreleased0. Đối chiếu từngProduct/finalstock>=0. Đây là fixture phù hợp rule, chưa chứng minh worker/service hoàn kho hoặc concurrency ứng dụng.

## 8. Aggregation thực

Chạy8 pipeline trên DB, range `[2026-07-03T00:00:00Z,2026-10-01T00:00:00Z)`, timezoneAsia/Ho_Chi_Minh. Revenue chỉ COMPLETED+PAID/completedAt, subtotal−discount, không ship/$lookup; Top5 đủ match/unwind/group/sort/limit. So với phép tính Python độc lập. [Pipeline bound và toàn bộ output](../database/evidence/aggregation-results.json).

Tổng **10.103.259.022VND**, **60 qualifiedOrders**, **434 units**; loại1.800.000ship.46 day buckets/3 month buckets:

| Tháng Việt Nam | Revenue VND | Orders |
| --- | ---: | ---: |
| 07/2026 |3.423.072.936 |17 |
| 08/2026 |3.883.307.042 |25 |
| 09/2026 |2.796.879.044 |18 |

Category: Thời trang7.879.869.734; Điện tử1.363.853.484; Gia dụng859.535.804VND. Sum bằng tổng revenue. OrderCount100/Status theo createdAt; CustomerCount39global.

| Top5 Product | Units | Revenue VND |
| --- | ---: | ---: |
| Longines Master Collection — bản demo02 |12 |472.496.856 |
| Carbon Steel Wok |9 |6.747.750 |
| Selfie Lamp with iPhone — bản demo02 |9 |3.541.392 |
| Samsung Galaxy S8 |8 |99.998.000 |
| Apple Airpods |8 |25.998.000 |

## 9. Indexes thực

14 declared+6 automatic_id_ kiểm list_indexes/keys/unique/partialoptions:

| Collection | Ngoài `_id_` |
| --- | --- |
| users |uq_users_email |
| categories |uq_categories_slug |
| products |uq_products_sku,uq_products_slug,ix_products_category_price |
| carts |uq_carts_user |
| orders |uq_orders_code,uq_orders_checkout,ix_orders_user_history,ix_orders_qualified_completed |
| payment_attempts |uq_attempts_txn_ref,uq_attempts_order_key,uq_attempts_provider_txn(partial),uq_attempts_pending_order(partial) |

Ba workload index cho browse/category/price, ownerhistory, qualifiedrevenue. Bốn typeprice/adminstatus/createdat/paymentexpiry vẫn candidate, chưa apply. Manifest18specs phase02 giữ nguyên;11 duplicates đều bị chặn đúng namedindex.

## 10. Explain baseline

Cùng Product ACTIVE/Electronics/price1–20triệu, sortprice/_idasc,limit10; cùng data/results. [Raw executionStats/winningPlan](../database/evidence/explain-baseline.json):

| Run | Winning stages | Returned | Docs | Keys | ms |
| --- | --- | ---: | ---: | ---: | ---: |
| Planner không hint |LIMIT→FETCH→IXSCAN |10 |10 |10 |0 |
| Natural |SORT→COLLSCAN |10 |180 |0 |0 |
| Namedindex |LIMIT→FETCH→IXSCAN |10 |10 |10 |0 |

0 ms là độ phân giải timer trên180 docs, không bảo đảm latency hoặc benchmark tốc độ. Chưa p50/p95/stress/concurrency/fulloptimization; không sửa dataset để làm đẹp số liệu.

## 11. Seed reproducibility

RNG20261007/fixedanchor/deterministicIDs. Defaultdryrun; explicitreset chỉ DBlocal allowlist/project ownership marker và tập fixtureIDs, giữ validators/indexes, transaction atomic. Không dropDB/collection. Reset từ chối ID lạ, kể cả Cart thủ công.

Seed thực lần2 giữ counts/digest (trừ saltedpasswordHash): `15abd857414775548c9a2575884ec95089af6ca9ef4762c825395f36d96996a4`. [Reseed evidence](../database/evidence/reproducibility.json). Password rehash có salt ngẫu nhiên, verify lại40/40.

## 12. Export/import/demo readiness

Export Product/Order canonicalEJSON arrays +checksum/countmanifest vào database/exports; không exportUser/hash. Importactual ecommerce_roundtrip sau applyvalidators/indexes: **180 Product/100 Order toàn bộ BSON bằng export**, [roundtrip result](../database/evidence/roundtrip-results.json). Slice giữ refs về gốc, không cloneUser/Category, không backupDB nghiệp vụ đầy đủ.

[Demo plan](demo-plan.md) có SKU/orderCode/range/index scenario. [Mongosh queries](../database/evidence/demo-queries.mongodb.js) được generate từ pipelines canonical với ISODate. Pipelines đã execute qua PyMongo; chưa rehearsal Compass UI hoặc executeJS bằng mongosh, chưa Webcheckout.

## 13. Files tạo/sửa

Tạo docs/mongodb-setup.md,phase-03-review.md,requirements-phase-03-source.txt; scripts/db(common/initDB/initReplica/bootstrap/start/createEnv/dependencylock); scripts/seed(seed/cachemetadata); scripts/validation(verify_database/verify_reproducibility/check_image_urls); scripts/export(export_data/export_demo_queries),scripts/import/import_data; database/sources(cache/provenance/README),database/evidence(manifests/reports/demoqueries/README).

Sửa README,AGENTS,.gitignore,.env.example,architecture/database-schema/seed-strategy/demo-plan và README validators/indexes/aggregations. JSONcanonical6validators/18candidates/8 pipelines không sửa. Backend app/frontend src vẫn scaffold. Localignored .tools/.venv/.local/.env/database/exports. Phase02staticreport giữ nguyên lịch sử; không Git remote/PR/commit.

## 14. Checks thực đã chạy

Bootstrap/checksum/Python/dependencies → startmongod/initiateRS/PRIMARY → initDB → seeddryrun/reset → liveverify → reseed+verify → export/importdryrun/reset/fullBSONcompare →3 image HEAD → generatequeries. Staticchecker cũng pass nhưng không thay LIVE_MONGODB_PASS. Sourcephase03 copy nguyên bản. Evidence EJSON đọc được bằng bson.json_util.

## 15. Issues/DEFERRED

Không còn failing DB/seed/validator/index/aggregation/roundtrip check trong phạm vi này. Giới hạn: spec/giá là demo fixture, CDNexternal, pendinganchorhistorical, roundtripchỉ2collection, explainsinglerun, chưa Compass UI rehearsal.

DEFERRED: Flask business/auth/cart/checkout/orderAPI/JWTguards, service race/idempotency/concurrency, VNPAYintegration/IPN/expiryworker, frontend/dashboardUI, fullperformancebenchmark, Compassrehearsal; Reviews/Atlas/cloudmedia/taxonomy/variantstock theo design cũ. Không đưa vào phase03.

## 16. Xác nhận

**Database thật đã được kiểm thử. Chưa implement Flask business feature. Chưa implement frontend. Chưa bắt đầu phase tiếp theo. Dừng để người dùng review.**
