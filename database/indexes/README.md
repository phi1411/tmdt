# Candidate indexes v1 — đã khóa thiết kế, chưa đo

Nguồn chuẩn: [candidate-indexes.json](candidate-indexes.json). Manifest18 indexes:11 invariant unique constraints và7 workload candidates. `_id` index tự có không liệt kê lại. Mỗi entry có collection/name/ordered keys/options/queryPattern/equalityFields/sortFields/rangeFields/fieldOrderReason. `sortFields:{}`/`rangeFields:[]` nghĩa query không có sort/range, không thiếu phân tích.

Foundation PHASE03 tạo11 invariant unique indexes và3 workload indexes: `ix_products_category_price` (browse theo ngành/giá), `ix_orders_user_history` (owner/history), `ix_orders_qualified_completed` (cohort doanh thu). Tổng14 declared +6 `_id_`. Bốn index type-price/admin-status/created-at/payment-expiry giữ candidate; chưa có workflow và workload đủ để tạo thêm. Manifest18entries vẫn giữ specification phase02, không đồng nghĩa tất cả đã apply. Index thực và baseline tại [evidence](../evidence/README.md); benchmark chi tiết chưa chạy.

Compound quan trọng:

- products: ACTIVE+category equality → price range/sort →_id tie; type equality cross-category có candidate riêng.
- orders: User history, Admin status/latest, createdAt global, qualified revenue completedAt và payment-expiry predicate.
- attempts: unique txnRef/orderKey/providerTransactionNo; partial unique orderId với status=PENDING chống hai attempt active đồng thời.

Price ascending sort `_id` ascending; descending sort `_id` descending để reverse scan cùng index được dùng. Latest sort createdAt desc/_id desc. Predicate brand/attribute và normalized substring là residual filter trên MVP nhỏ; không claim covered query/index acceleration cho tất cả tổ hợp.

Không index nameNormalized cho substring không anchored, không text index/Atlas Search/wildcard attribute trong MVP. Customer count/Category active list trên40 User/3 Category không cần thêm index không có evidence.

Ở phase performance: collection clone riêng, compare `hint({$natural:1})`/clone chỉ `_id` với named index + planner unhinted, cùng query/results. Capture explain executionStats, winningPlan, COLLSCAN/IXSCAN, totalDocsExamined/totalKeysExamined/executionTimeMillis và latency p50/p95 riêng. Index đầu pipeline chỉ giúp match/latest sort, không bảo đảm group/final sort sau unwind dùng index. [MongoDB ESR guideline](https://www.mongodb.com/docs/v8.0/tutorial/equality-sort-range-guideline/).
