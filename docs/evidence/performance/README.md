# Performance evidence — PHASE07B

Evidence từ MongoDB8.0.32/rs0 thật, **BENCHMARK DATASET** riêng. [Bảng tóm tắt](benchmark-summary.md), [review/talk track](../../phase-07b-performance-review.md), [lệnh chạy](../../../scripts/performance/README.md).

| File | Nội dung |
| --- | --- |
| dataset-manifest.json | Counts/seed/anchor/window/BSON hashes/status distribution và independent revenue/Top5 oracle |
| before-index.json | True pre-build, unique indexes giữ nguyên, command/raw explain/stats/result digest |
| after-index.json | Named index/natural/planner unhinted, cùng query/kết quả; raw explain |
| aggregation-explain.json | Revenue/Top5 và broad-range sensitivity, initial index scope/optimizer stages |
| benchmark-results.json | Runtime/hardware/cursor methodology,6query comparisons và30latency samples mỗi mode |
| benchmark-summary.md | BEFORE/AFTER và client p50/p95, dễ chèn báo cáo |
| index-audit.json |20actual dev indexes gồm14declared+6_id_,18manifest classifications, KEEP/CANDIDATE/no REMOVE |
| storage.json | Actual collStats/indexSizes trước/sau3read indexes; build duration; write throughput NOT_MEASURED |
| dev-seed-smoke.json | Seed180Products/100Orders read-only explain, không speedup milliseconds |
| safety-verification.json | Real validator121/ref/arithmetic/full validate, marker/lock/foreign data refusal, exact fixture cleanup |
| reproducibility-verification.json | Verified cleanup→rebuild và hashes identical trên toàn6collections |
| dev-integrity-reproduce.json | Final successful command: full dev docs/options/indexes và protected backend/canonical source hashes before/after |
| final-verification.json | Evidence/links/samples/source/schema/index checks; phân biệt dev unchanged trong measurements với external shared dev writes sau đó |

`nReturned` lấy từ `$cursor` khi có, nếu optimized root thì lấy root executionStats. Optimizer có thể đẩy GROUP vào cursor, nên số này không luôn là documents đầu vào hoặc số dòng REST cuối. Có `statisticsScope`, `finalResultRows`, và riêng full-api `pagedItemsReturned/matchingTotal`. Raw plan/stages giữ đầy đủ; Top5 final5 khác cursor152 trong lượt đo.

ExecutionTimeMillis của explain khác client latency; explain bỏ qua plan cache. Không dùng nReturned của facet1 làm sốProducts. Không claim toàn pipeline hoặc brand/substring được index. Timings chỉ observations máy hiện tại; keys examined có thể tăng từ0 vì COLLSCAN không đọc key, cần xem cùng docs examined. Storage index phát sinh thêm và writes phải duy trì index; không đo write throughput.

Các dev-integrity receipts khác giữ lịch sử command. Lần `all` ban đầu đo thành công nhưng lock teardown trên Windows fail; metadata sửa rõ trạng thái và được supersede bằng final `reproduce` exit0. Không xóa dấu vết failure hoặc claim pass từ lượt command lỗi.
