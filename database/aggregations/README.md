# Aggregation pipelines v1 — đã verify trên MongoDB ở PHASE03

PHASE07B đã benchmark Revenue Day/Top5 canonical trên10.000Orders synthetic riêng, true-before/natural/named/unhinted equal outputs/oracle; qualified index đọc152docs trong7ngày thay10.000. [Raw aggregation explains](../../docs/evidence/performance/aggregation-explain.json), [review/methodology](../../docs/phase-07b-performance-review.md). Không đổi JSON stages hoặc revenue rule; index hỗ trợ initial match/latest sort, không toàn bộ unwind/group/rank. Broad6tháng đọc3.969docs cho thấy ảnh hưởng selectivity; latency local không production guarantee. Các ghi chú chưa benchmark bên dưới giữ lịch sử phase03/06B.

PHASE06B Dashboard API dùng đúng8artifacts qua DashboardRepository: tz-aware EJSON decode/deep-copy/bind validated range, không duplicate hoặc đổi JSON canonical.5Admin APIs chạy aggregate thật; Python chỉ metadata/default0/calendar buckets. [Review](../../docs/phase-06b-review.md), [contract](../../docs/api-contract.md), [explain](../../backend/evidence/phase06b-explain.json). Semantic BR-REPORT/ADR007 giữ nguyên; frontend/full benchmark chưa thuộc phase.

Đây là nguồn chuẩn pipeline JSON, không endpoint/dashboard implementation. Mỗi JSON là pipeline array dùng Extended JSON Date. PHASE03 dùng bson.json_util decode và bind range trước khi chạy thật; không truyền object `$date` chưa decode thẳng vào aggregate. [Kết quả thực và pipeline bound](../evidence/aggregation-results.json), [live verifier](../../scripts/validation/verify_database.py). JSON canonical vẫn giữ range tháng9 minh họa, verifier dùng range90ngày của seed.

Representative binding: từ `2026-08-31T17:00:00Z` inclusive đến `2026-09-30T17:00:00Z` exclusive, tương ứng tháng09/2026 tại Việt Nam. Backend sau này bind from/to đã validate vào initial match; interval chỉ day/month và timezone cố định. Không nhận pipeline từ client. Collection và input/output chính:

| Artifact | Collection | Match / stages | Output |
| --- | --- | --- | --- |
| [revenue-day.json](revenue-day.json) | orders | qualified completedAt range → group dateTrunc day → sort bucket | {_id:Date,revenue,orders} |
| [revenue-month.json](revenue-month.json) | orders | như trên, unit month | {_id:Date,revenue,orders} |
| [top-products.json](top-products.json) | orders | match → sort latest → unwind → group productId → sort quantity/revenue/ID →limit5→project | {productId,productName,quantity,revenue} |
| [category-revenue.json](category-revenue.json) | orders | match→sort latest→unwind→group categoryId→sort revenue/ID→project | {categoryId,categoryName,revenue} |
| [sales-summary.json](sales-summary.json) | orders | match qualified → group subtotal-discount, qty map/sum | {totalRevenue,qualifiedOrders,totalProductsSold} |
| [order-count.json](order-count.json) | orders | match createdAt range→count | {totalOrders} |
| [order-status.json](order-status.json) | orders | match createdAt→group orderStatus→sort/project | {status,count} |
| [customer-count.json](customer-count.json) | users | match role CUSTOMER→count (global) | {totalCustomers} |

Qualified=`COMPLETED AND PAID`, revenue=`subtotal-discount`, discount0, phí ship loại. COD/VNPAY cùng thời điểm completedAt; trả online trước khi giao chưa phải revenue. Cancelled/expired/review-required không qualify. Product/Category name lấy `$first` sau sort completedAt desc/_id desc trong tập qualified. Có thể cùng Product nhiều selections trong một Order nhưng cùng name snapshot; quantity group đúng shared productId.

Không `$lookup`, không tải raw Orders lên frontend, không sum Order.total sau unwind. Revenue pipeline order-level không unwind; Top5 đủ `$match/$unwind/$group/$sort/$limit`. Backend chỉ chuyển ID/date/money và điền bucket0, không tính lại metrics từ raw documents. Empty aggregation→0/[]; revenue buckets backend tạo khoảng ngày/month tối đa366 ngày theo local calendar.

Nguồn semantic: BR-REPORT/ADR007; feature admin-dashboard chỉ chứa REST/UI contract. MongoDB8.0 hỗ trợ [`$dateTrunc`](https://www.mongodb.com/docs/v8.0/reference/operator/aggregation/dateTrunc/). Các pipeline không có variable tên `from` chưa khai báo hoặc placeholder giá trị mơ hồ; EJSON bound examples có thể decode để chạy sau review.

Kiểm tra tĩnh phase02: field paths khớp validators,19examples kỳ vọng21.900.000VND/5units; không thay runtime. PHASE03 chạy cả8pipeline trên MongoDB8.0.32 local rs0 với180Product/100Order và so kết quả với phép tính độc lập:10.103.259.022VND/434units/60qualifiedOrders. Snapshot price mutation rollback giữ kết quả; [explain baseline](../evidence/explain-baseline.json) đã lưu. Benchmark đầy đủ và Dashboard API/UI vẫn thuộc phase sau.
