# ADR-007 — Doanh thu merchandise khi hoàn tất

## Status

LOCKED DESIGN v1 — PHASE02,07/10/2026. Resolve OQ-08; supersede baseline cần review phase01.

## Context

Cộng mọi Order sẽ tính cả hủy/chưa thu COD. Tính VNPAY ngay lúc trả nhưng COD lúc giao làm report phụ thuộc payment method, khó bảo vệ. Tổng collected chứa shipping không phân bổ được Top Product/Category.

## Decision

Qualified sale chỉ COMPLETED+PAID. Revenue hàng hóa=`subtotal-discount` (discount0), excludes shipping. Cả COD/VNPAY ghi nhận theo completedAt; COD lúc completed mới paid, VNPAY có thể paid trước nhưng chỉ completed mới revenue. Cancelled/expired/late-review excluded. Metadata phải nói rõ merchandise/dateBasis. Revenue day/month/top/category cùng cohort completedAt `[from,to)` UTC và buckets giờVN. TotalOrders/status theo createdAt; Customers global hiện tại.

## Alternatives / trade-off

PaidAt cash-in report hữu ích đối soát nhưng khác sales-revenue metric, deferred. Gross Order.total làm product/category sums khác headline nếu có ship; không chọn. Completed+paid nhất quán/dễ chứng minh, không phải tuyên bố chuẩn kế toán cho doanh nghiệp thực tế. Refund/promotion nếu thêm cần ADR về allocation/recognition trước code.

## Consequences / validation

Dashboard chưa tăng revenue ngay khi checkout/online paid; demo hoàn tất COD rồi refresh. Snapshot categoryId/name giúp report không JOIN. Metadata/fixtures/time boundary kiểm tra ở canonical aggregation designs, runtime sau review. Second successful txn cần đối soát nhưng không xóa/cộng lại legitimate sale trước đó.
