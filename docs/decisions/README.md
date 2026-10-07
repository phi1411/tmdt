# Architecture Decision Records — PHASE02

Cấu trúc phase01 đã được người dùng chấp nhận; PHASE02 khóa design v1 và dừng review, chưa triển khai nghiệp vụ. LOCKED DESIGN là nguồn nền tảng cho coding phase sau, không tuyên bố runtime DONE. Tài liệu [foundation-decisions](../foundation-decisions.md) resolve/defer các OQ cũ; phase01 review giữ lịch sử và được đánh dấu archived.

| ADR | Decision | Status |
| --- | --- | --- |
| [001](001-mongodb-modeling.md) | Product polymorphic chung products, URLs, validator | LOCKED |
| [002](002-embedded-vs-reference.md) | Bounded aggregate embed / independent reference | LOCKED |
| [003](003-order-snapshot.md) | Immutable Order snapshot, integermoney, transaction | LOCKED |
| [004](004-cart-storage.md) | carts riêng/User, currentpricing, versioned clear | LOCKED |
| [005](005-index-strategy.md) |18candidate indexes with query/ESR; no benchmarkyet | LOCKED candidates |
| [006](006-checkout-payment-consistency.md) | Reserve/quote/idempotency/IPN/expiry/late-review | LOCKED |
| [007](007-revenue-definition.md) | Completed+paid merchandise revenue by completedAt | LOCKED |
| [008](008-local-vietnamese-search.md) | Normalized Vietnamese substring/filter local | LOCKED |
| [009](009-foundation-locks.md) | Localreplicaset, Englishnames, flatCategory, URLmedia/defaults | LOCKED |

Không thêm role/CSDL ngoài requirement; reviews DEFERRED không MVP blocker. Future breaking change cần ADR superseding/migration/contract/tests. Exact validators/index/pipelines ở database/, meaning ở database-schema, behaviors ở business-rules, không copy exact spec nhiều nơi.
