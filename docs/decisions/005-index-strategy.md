# ADR-005 — Index theo workload và benchmark trung thực

## Status

LOCKED CANDIDATES — PHASE02,07/10/2026. Đã khóa keys/options/query patterns cho baseline v1, **chưa apply hoặc benchmark**. Manifest [candidate-indexes.json](../../database/indexes/candidate-indexes.json) là nguồn chuẩn exact specification, không lặp bảng keys trong ADR này.

## Context and decision

Barem cần compound index và explain executionStats. Chọn18 indexes có use case:11 unique invariant (account/catalog identity, Cart owner, checkout/payment idempotency và một pending attempt/Order) +7 workload candidates (category/type price filter, history/admin/date/report/expiry). `_id` index built-in không tính trong18. Manifest ghi equality/sort/range/reason theo từng entry, kể cả no-sort/no-range.

Invariant unique bắt buộc để nghiệp vụ đúng ở phase implementation. Candidate workload baseline sẽ được apply/đo khi runtime được yêu cầu; nếu evidence không tốt phải cập nhật manifest/ADR và lý do, không claim đã tối ưu từ thiết kế giấy. Compound equality prefix trước date/price vừa range vừa sort; _id stable tie-break; report index hỗ trợ match và latest snapshot sort trước unwind, không hứa group/finalsort dùng index. [MongoDB ESR guideline](https://www.mongodb.com/docs/v8.0/tutorial/equality-sort-range-guideline/).

Search theo ADR008: normalized literal substring không anchored nên no name/text/wildcard index. Brand/attribute filters residual ở dataset180; không add index mọi tổ hợp. Partial providerTransactionNo index bỏ missing; số0 placeholder không persist. Partial pendingOrder unique bảo vệ concurrent retries; explicit expiry/history guard, không TTL-delete chứng từ.

## Benchmark procedure — phase sau

Clone fixtures sang DB benchmark có marker, giữ dev/demo indexes an toàn. Baseline forced natural scan hoặc clone chỉ _id (label rõ), cùng query/sort/projection/results; candidate named hint và thêm planner unhinted. find.explain(executionStats) hoặc database explain command cho aggregate theo driver/version thật; không giả định PyMongo aggregate(explain=True).

Collect winningPlan (nested cursor/SBE có thể khác), COLLSCAN/IXSCAN nếu có, nReturned,totalDocsExamined,totalKeysExamined,executionTimeMillis. Client monotonic p50/p95 đo riêng, warm-up/lặp>=30 đề xuất, lưu seed/count/selectivity/query/index/máy/topology/server/driver. Dataset100 Order có thể0ms hoặc planner chọn scan; không hứa speedup. Stress profile riêng không đổi dataset demo.

## Consequences / verification

Index tăng write/storage; unique constraints không được drop để tạo benchmark trên DB đang dùng. Phase02 checker chỉ kiểm tra field paths, manifest uniqueness và example constraints; benchmark NOT_MEASURED, apply NOT_APPLIED. Exact coverage/limitations ở database/indexes/README; không tạo reviews index khi feature deferred.
