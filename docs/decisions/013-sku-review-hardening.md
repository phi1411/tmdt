# ADR013 — Hoàn thiện SKU và Reviews sau integration review

Ngày19/10/2026; người dùng yêu cầu hoàn tất các thiếu sót bản mới, xác nhận ưu tiên COD và chưa có merchant Sandbox. Không triển khai coupon/refund/chat/seller hay thanh toán tiền thật.

## Vấn đề

Đợt commit15–16/10 đã thêm SKU/reviews nhưng kho SKU không được ghi khi checkout, skuId không khớp options, ratingSummary không atomic, admin chưa sửa SKU và tài liệu/checker còn design6collections cũ. Bảng chọn khi mua đã hoàn thành riêng.

## Quyết định

- Giữ products/orders/cart hiện tại; hỗ trợ tối đa4tầng/100SKU theo validator đã có. SKU ID duy nhất trong Product, tierIndex khớp đúng option, không trùng tổ hợp. Tier names/options không trống/trùng; skuId không được dùng làm tier name. SKU price integer VND, stock integer. Legacy Product không có SKU vẫn dùng pool cũ.
- Product có ma trận dùng root stock=sum(SKU.stock), price=min(SKU.price); server dẫn xuất, không tin root do client gửi. Admin gửi hai arrays cùng nhau khi thay ma trận. Không đổi/xóa/rebind SKU đang được tham chiếu bởi Order chưa giải phóng kho; không chuyển legacy↔SKU khi còn Order giữ kho của Product. Cart stale có thể báo SELECTION_CHANGED, Order snapshot giữ nguyên.
- Resolve selection duy nhất ở service: exact keys và values, skuId nếu gửi phải khớp tierIndex, unknown/mismatch bị reject. Quantity tổng theo Product và SKU. Checkout transaction decrement root+mọi SKU đã mua bằng version/stock predicates; cancel/expiry restore cùng SKU theo snapshot, chỉ một lần. Snapshot giữ selectedAttributes.skuId canonical và giá SKU.
- Reviews một Customer/Product/Order COMPLETED+PAID; ownership và item eligibility ở backend. Insert và recompute ratingSummary từ VISIBLE reviews trong cùng snapshot/majority transaction; Product version write serialize cạnh tranh, retry transient theo utility hiện hữu. Unique compound index vẫn giữ. Public DTO không order/user IDs/orderCode; read có pagination/rating/comment filter và public Product visibility.
- Admin SKU UI dùng các fields đã chốt; đồng bộ contract/spec/schema/checker. Seed supplementary chỉ dry-run mặc định, idempotent và không xóa review thật; fixture verified phải có đúng completed order owner/items. Không reset/reseed live DB.
- Migration additive có exact backup/journal/dry-run, kiểm tra corpus hiện hữu, apply validators/indexes + normalize SKU aggregates/rating summaries; không sửa lịch sử Order, giá/tồn legacy hay user data. Deployment chỉ sau tests và rehearsal pass; VNPAY disabled.

## Trade-off / kiểm chứng

Stock gốc là aggregate nên cần giữ đồng bộ tất cả writers; guards Admin chống làm mất SKU còn giữ kho. Review recompute có chi phí tăng theo reviews/Product nhưng bounded timeout và index feed; ưu tiên tính đúng cho đồ án. Test transaction/concurrency/rollback/once-only restore, tampering, public projection, admin roundtrip và UI COD, full suite/build/checker. Không claim hiệu năng production hay live Sandbox.

## Dependency hardening

Audit9findings có5high từ Tailwind3toolchain và React Router6. Nâng có chủ đích lên Tailwind4.3.3 + PostCSS adapter4.3.3 và React Router DOM7.18.4 (peer React>=18, Node>=20; giữ React18/Node24 đã chọn). Giữ theme/config/tokens và component API, không redesign. CSS dùng `@import`/`@config` theo [hướng dẫn chính thức](https://tailwindcss.com/docs/upgrade-guide) và [PostCSS adapter](https://tailwindcss.com/docs/installation/using-postcss). API DOM được re-export để tương thích nâng v6→v7 theo [React Router changelog](https://reactrouter.com/start/start/changelog). Khóa dependency và chạy lại build/route/responsive/browser trước deploy; không dùng npm audit fix --force.
