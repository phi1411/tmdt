# PHASE07B — MongoDB performance benchmark & index evidence

**PHASE 07B PERFORMANCE EVIDENCE PASS — dừng để review.** Ngày08/10/2026. Đo MongoDB thật; không thêm feature, sửa frontend/business rule/API/schema hoặc apply/remove index dev. Database benchmark giữ lại để dùng Compass07C; chưa thực hiện07C.

## 1. Queries đã benchmark

1. Product selector: ACTIVE + ELECTRONICS + exact Category + price2–5triệu, price/_id ASC, limit20; cùng filter/projection/sort với Web contract.
2. Full public Product repository cho query1, gồm Category lookup/active guard/facet count/page1size20.
3. Product selector: ACTIVE + ELECTRONICS cross-category + normalized exact brand `Benchmark Brand 1` + price2–5triệu, price/_id DESC, limit20.
4. Full public Product repository cho query3.
5. Revenue Day canonical: COMPLETED+PAID/completedAt range, `$dateTrunc` Asia/Ho_Chi_Minh, group merchandise revenue và sort ngày.
6. Top5 canonical: qualified match→latest snapshot sort→unwind→group Product→rank quantity/revenue/ID→limit5→project.

Không benchmark query giả tách khỏi ứng dụng: dùng `parse_product_query/PRODUCT_SORTS/PRODUCT_PROJECTION`; full pipeline capture trực tiếp `ProductRepository.list`; Dashboard load qua `DashboardRepository.pipeline`. Selector tách chi phí truy xuất đầu vào, không giả làm toàn endpoint. Full repository measurement không gồm HTTP/JWT/serialization/frontend.

## 2. Dataset và môi trường

**BENCHMARK DATASET — KHÔNG phải dummy data chính thức của đề.** Database literal `ecommerce_benchmark` riêng, local27017/rs0; seed20261008/anchor2026-10-01.30.000Products đa hình/30Categories/40Users synthetic/10.000Orders COD, carts/payment_attempts0; sáu canonical validators strict/error và11unique invariant indexes. Product3types/5brands/30categories/price1–20triệu, ACTIVE khoảng70%; không hứa giống phân phối khách hàng thật.

Orders60%COMPLETED+PAID,10%mỗi PENDING/CONFIRMED/SHIPPING/CANCELLED;2–5items/qty1–3, integer VND long, historical price97%current, embedded category/name/price snapshots. Dates tạo ngẫu nhiên reproducible trong270ngày. Stock1000 trừ net reservations; Mongo verify refs/subtotal/total/stock và full validate6collections. Không copy dev credentials/PII; sample User hash không phục vụ benchmark login; không gateway/checkout write load.

Khoảng hẹp đo Dashboard `[2026-07-31T17:00:00Z,2026-08-07T17:00:00Z)` tương ứng7ngày Việt Nam. Oracle độc lập: **152 qualified Orders/10.552.893.400VND/1.030units**;7Revenue rows/5Top rows. Canonical Mongo outputs bằng oracle, phí ship bị loại. [Manifest/oracle](evidence/performance/dataset-manifest.json).

MongoDB8.0.32/WiredTiger/PyMongo4.15.3/Python3.12.14; Windows10 build19044,12logicalCPU, một node rs0 localhost. Không Atlas/cold-cache/distributed/deployment benchmark. [Runtime](evidence/performance/benchmark-results.json).

## 3. Index strategy và field order

| Query | Compound index | Lý do |
| --- | --- | --- |
| Category-price | status ASC, categoryId ASC, price ASC, _id ASC | Hai equality trước; price vừa range vừa sort, `_id` stable tie. `productType` còn residual, Category tương thích type. |
| Type-price/brand | status ASC, productType ASC, price ASC, _id ASC | Equality cho type cross-category; reverse scan hỗ trợ price/_id DESC. Brand chưa có trong index, phải FETCH/filter; không claim brand/search covered. |
| Qualified revenue/latest snapshot | orderStatus ASC, paymentStatus ASC, completedAt DESC, _id DESC | Hai equality rồi date range; hỗ trợ latest sort trước unwind. Group/dateTrunc/rank cuối vẫn phải tính. |

Keys/options đều từ manifest hiện có, không thiết kế index mới. Không áp ESR máy móc: khi cùng field price/date vừa range vừa sort thì dùng chung một vị trí; chọn sort khác với range cần trade-off ESR/ERS và đo riêng. Không tạo index cho mọi brand/attribute/substring. [MongoDB ESR/ERS](https://www.mongodb.com/docs/v8.0/tutorial/equality-sort-range-guideline/).

Chỉ build3read indexes trên benchmark. `ix_products_category_price` và `ix_orders_qualified_completed` đã tồn tại dev; `ix_products_type_price` chỉ được thử trong benchmark, vẫn CANDIDATE ở dev.

## 4–7. BEFORE/AFTER, plans và docs/keys examined

True BEFORE giữ `_id_` và unique constraints, chưa có suitable read indexes; không gọi “không có bất kỳ index nào”. AFTER gồm natural hint, named hint và planner unhinted; không drop integrity indexes. Results/digest đều bằng nhau qua4modes và mọi lượt đo.

| Query | BEFORE plan/docs/keys | AFTER named plan/docs/keys | Final output | Giảm docs |
| --- | --- | --- | --- | ---: |
| Category selector | COLLSCAN /30.000/0 | IXSCAN /20/20 |20Products |99,933% |
| Category full repository | COLLSCAN /30.000/0 | IXSCAN /96/96 |1facet,20items,total96 |99,680% |
| Type+brand selector | COLLSCAN /30.000/0 | IXSCAN /160/160 |20Products |99,467% |
| Type+brand full repository | COLLSCAN /30.000/0 | IXSCAN /1.108/1.108 |1facet,20items,total214 |96,307% |
| Revenue Day | COLLSCAN /10.000/0 | IXSCAN /152/152 |7days |98,480% |
| Top5 | COLLSCAN /10.000/0 | IXSCAN /152/152 |5Products |98,480% |

AFTER unhinted planner chọn IXSCAN trên named index phù hợp cho cả6variants. Natural AFTER vẫn COLLSCAN, cùng BSON dataset/query/results. WinningPlan đầy đủ, SORT/FETCH/LIMIT/GROUP/IXSCAN/COLLSCAN và executionTimeMillis/nReturned/docs/keys nằm trong [before-index.json](evidence/performance/before-index.json), [after-index.json](evidence/performance/after-index.json). Không chỉ lưu label tự đặt.

COLLSCAN có0keys vì không đọc B-tree keys; indexed keys tăng từ0 không là regression tự động. Category selector dừng sau20; full repository phải count96match. Type+brand selector phải FETCH160 để lấy20; full pipeline scan1.108price/type candidates rồi brand residual còn214. Projection không covered, lookup/facet không được index hóa toàn bộ.

`nReturned` là output execution subtree của `$cursor` hoặc optimized root, không luôn số documents đầu vào hoặc số rows REST cuối. SBE có thể push GROUP vào cursor: Revenue cursor nReturned7 nhưng đọc152docs; Top5 cursor152, final5. Evidence có `statisticsScope/finalResultRows/pagedItemsReturned/matchingTotal` và raw optimizer stages.

## 8. Aggregation explain

Revenue và Top5 dùng `ix_orders_qualified_completed` cho qualified/date access; Top5 dùng date/_id order lấy snapshot label mới nhất. Index không phục vụ `$unwind`, group quantities/revenue và final rank sort. Không `$lookup` Product/Category để dựng lịch sử, không sum Order.total sau unwind. [Aggregation explains](evidence/performance/aggregation-explain.json) giữ canonical stages và optimized stages, không sửa pipeline JSON.

Sensitivity6tháng `[2026-01-01,2026-07-01)` đọc **3.969/10.000docs** với index, giảm60,31%, kém chọn lọc hơn window7ngày152docs. Đây là counterexample cho kết luận “index luôn giảm98%”; không lặp benchmark latency wide range, chỉ explain/results equality.

Dev seed read-only selector: natural180docs/0keys, named20docs/20keys, cùng20Products. Explain observations0–2ms không là speedup; seed180Products/100Orders chỉ dùng cardinality demo. [Small dev smoke](evidence/performance/dev-seed-smoke.json).

## 9–11. Index audit: KEEP/CANDIDATE/REMOVE

[Audit đầy đủ18entries và20actual dev indexes](evidence/performance/index-audit.json): **14declared +6automatic `_id_`**, keys/options match manifest, không index lạ.

- **KEEP11unique/integrity:** User.email, Category.slug, Product.sku/slug, Cart.userId, Order.orderCode +userId/checkoutKey, Attempt.txnRef +orderId/attemptKey +partial providerTransactionNo +partial pendingOrder. Đây là constraint chống duplicate/replay/concurrent attempts, không drop vì chi phí write.
- **KEEP3workload đang dùng:** `ix_products_category_price`, `ix_orders_user_history` (Customer owner/history), `ix_orders_qualified_completed`.07B đo category/qualified; history giữ vì contract/query thật, chưa riêng timing07B.
- **CANDIDATE chưa apply dev:** `ix_products_type_price` (đã đo positive trên benchmark, cân nhắc khi cross-category load tăng); `ix_orders_admin_status`, `ix_orders_created_at`, `ix_orders_payment_expiry` (use cases thật, chưa có benchmark workload riêng để apply). Expiry candidate còn residual paymentStatus và sort tie `_id` của runtime cần xét khi đo.
- **REMOVE/REDUNDANT:** không có index nào đã chứng minh dư thừa; không tự xóa index dev. Prefix trùng không đủ kết luận redundancy khi uniqueness/partial semantics khác nhau.

Manifest JSON giữ exact locked specification/historical `benchmarkStatus:NOT_MEASURED` từPHASE02; trạng thái đo runtime mới nằm trong07B evidence và README, không giả rằng18candidates đều được apply hoặc đo.

Index storage benchmark quan sát: Products **4.603.904→6.283.264bytes**, tăng1.679.360bytes cho2read indexes; Orders **1.196.032→1.449.984bytes**, tăng253.952bytes cho qualified index. [CollStats/indexSizes/build times](evidence/performance/storage.json). Storage có thể đổi theo checkpoint/compression; không suy rộng dung lượng production. Insert/update phải duy trì keys, đặc biệt price/status/date mutations; write throughput/concurrency chưa đo. Không trình bày “càng nhiều index càng tốt”.

## 12. Latency, checks thực chạy và hạn chế

Mỗi6query ×4modes:5warm-ups +30measured samples, tổng720samples và120warm-ups. Client monotonic perf_counter_ns bao gồm materialize cursor/network/BSON decode, không gồm hash assertion; named/natural/unhinted shuffle order sau build. p50=median/p95=nearest rank. No-suitable-index pre-build là phase trước build, nên không interleave được với indexed; natural AFTER cung cấp control cùng phase.

| Query selector/pipeline | Natural p50/p95 ms | Named p50/p95 ms |
| --- | ---: | ---: |
| Category selector |29,103 /42,596 |1,200 /3,077 |
| Type+brand selector |31,359 /47,739 |1,824 /4,441 |
| Revenue Day |16,149 /21,643 |2,974 /5,254 |
| Top5 |22,540 /28,986 |3,726 /8,039 |

Bảng6variants/4modes và samples đầy đủ tại [benchmark-summary.md](evidence/performance/benchmark-summary.md), [results JSON](evidence/performance/benchmark-results.json). Không claim “nhanh hơn X lần”, cold cache, production SLA, throughput, HTTP/frontend hoặc toàn bộ tổ hợp filter. Local single client/warm cache/synthetic/selective window và background load của máy ảnh hưởng timing. Explain bỏ qua plan cache; executionTimeMillis không thay latency measured của query thật. [MongoDB explain](https://www.mongodb.com/docs/v8.0/reference/explain-results/), [aggregation optimization](https://www.mongodb.com/docs/v8.0/core/aggregation-pipeline-optimization/).

Đã chạy thật: setup +all measurements;8safety probes (dev DB refused, exclusive lock, wrong/missing marker, validator121, changed dataset cleanup refused, full BSON/index validation và refs/money/stock); verified cleanup→setup→same6BSON hashes→full measurement lại. Final `reproduce` exit0 và lock được dọn đúng. Lầnall đầu measurement pass nhưng lock teardown fail WinError32; đã sửa đóng file trước unlink, giữ receipt lỗi/superseded, không claim command đó pass. Backend suite không chạy lại vì app/tests/API/canonical artifacts không đổi; không dùng lịch sử658tests làm bằng chứng benchmark mới.

## Dev integrity

Full documents/options/validators/indexes fingerprint trước/sau các commands setup/measurements/reproduce/safety giữ nguyên tại thời điểm chạy:

`f8c36f1872e7de3b42ae7e949e16e6f2a81fbdca20a24eeb3789033c358b50ce`

Counts trong các measurements **41Users/3Categories/180Products/0Cart/100Orders/30attempts**, giữ User được người dùng chấp thuận ở06AB. Không ép về baseline40Users, không reset/reseed/stock restore hoặc chạy expiry dev. [Final reproduce integrity](evidence/performance/dev-integrity-reproduce.json), [safety](evidence/performance/safety-verification.json). Protected hashes của backend/app, backend/tests, API contract,6validators/8pipelines/samples/index manifest trước/sau match. Test/roundtrip DB không được ghi trong07B.

**Shared dev changes sau measurements:** kiểm tra chốt tài liệu phát hiện42Users/5Categories/182Products/1Cart/101Orders/30attempts, fingerprint khác baseline đo. Snapshot chat cùng workspace cho thấy phiên **Implement Catalog APIs** đang chuẩn bị Customer/haiProduct/đơn COD demo snapshot; phiên **Xây dựng sàn thương mại điện tử** đang chạy lại frontend E2E.07B không gửi yêu cầu/đổi/xóa fixtures của hai phiên đó. Mọi write target của performance tooling là ecommerce_benchmark; các receipts chứng minh dev unchanged trong từng command đo/guard. Không claim dev bất biến toàn phiên hoặc tự revert về41Users; ghi live snapshot riêng tại [final verification](evidence/performance/final-verification.json). Performance PASS là kết quả benchmark đã đo, không nghiệm thu cleanup/demo/Frontend của worker khác.

## 13. Files/scripts/evidence

- Tạo `scripts/performance/benchmark.py`, `perf_common.py`, `dataset.py`, `verify_safety.py`, `README.md`; không dependency mới.
- Tạo `docs/features/performance-benchmark.md` đủ13sections, `docs/phase-07b-performance-review.md`, `docs/evidence/performance/` chứa JSON/rawplans/samples/summaries/guard/reproducibility receipts.
- Cập nhật context/performance docs: `AGENTS.md`, `docs/architecture.md`, `docs/testing-strategy.md`, `docs/requirements.md`, `docs/demo-plan.md`, ADR005, database index/aggregation READMEs; không sửa canonical JSON/validators/backend/frontend/API behavior.
- Private marker/lock/dataset state tại ignored `.local/`; không export dev documents/credentials. [Lệnh setup/run/cleanup](../scripts/performance/README.md). Benchmark database giữ cho07C; cleanup chỉ khi không cần dùng nữa. Không Git commit/push hoặc tự chuyển phase.

## DEFENSE TALK TRACK

“Nhóm em đo cùng query và cùng dữ liệu trên MongoDB thật. Em dùng database benchmark riêng30.000sản phẩm và10.000đơn, giữ nguyên dữ liệu demo. Trước index, query lọc ngành và giá phải COLLSCAN30.000documents; compound index giảm xuống20documents cho trang20sản phẩm và planner chuyển IXSCAN. Index đặt equality trước, rồi giá để vừa lọc vừa sắp xếp. Dashboard dùng COMPLETED+PAID theo completedAt, không cộng phí ship; index giảm scan10.000xuống152đơn trong khoảng này. Index chỉ giúp stages đầu, group và Top5 vẫn phải tính. Nhóm có explain và30lượt latency mỗi mode, nhưng không hứa tốc độ production; thêm index cũng tốn storage và chi phí ghi.”

**PHASE 07B PERFORMANCE EVIDENCE PASS. Dừng để review.**
