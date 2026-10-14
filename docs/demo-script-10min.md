# Kịch bản bảo vệ 10 phút

**Cập nhật14/10/2026:** Web đổi giá với ảnh mới, immutable snapshot, COD lifecycle và revenue delta đã PASS trên clone test, không dùng API fallback để đổi giá. Xem [review mới](render-deployment-review.md). Compass GUI/thời gian người thật vẫn MANUAL PENDING. Không hoàn thành live Order rồi ép stock20 bằng reset; [report12/10](phase-07d-final-rehearsal.md) giữ lịch sử trước sửa.

Theo [checklist](pre-demo-checklist.md), [Compass guide](compass-demo-steps.md) và credentials private. Giữ bốn trọng tâm của [bản 5 phút](demo-script-5min.md), thêm CRUD, lifecycle COD và biến động Dashboard. VNPAY không phải bước bắt buộc.

| Thời gian | Người | Thao tác / lời nói |
| --- | --- | --- |
| 0:00–0:40 | SV3 | Nêu barem, dữ liệu mô phỏng: seed 180 Product/60 mỗi ngành/100 Order với 2–5 item. User được giữ từ 06AB và fixture 07C là dữ liệu thêm có chủ đích. MongoDB local rs0, frontend 5173/backend 5001. |
| 0:40–1:40 | SV1 nói, SV3 Compass | products xem ba ngành, field chung và attributes khác nhau; validator oneOf/productType, ObjectId/Date/long. Giải thích collection chung phục vụ browse/CRUD/report đa ngành. |
| 1:40–2:15 | SV1 Admin Web | Mở form sửa Product fixture hiện có, chỉ field chung và form theo ngành. Có thể update description của **fixture riêng**, lưu và đọc lại; thay đổi price ở dưới cũng là CRUD Update nên bỏ bước description nếu rehearsal thiếu thời gian. Không archive Product đang cần checkout. |
| 2:15–3:05 | SV1 Customer Web, SV3 hỗ trợ | Điện thoại quantity 1 + áo M/Black quantity 1 → Cart → địa chỉ/COD/quote → Đặt hàng; copy orderCode. Nêu backend lấy giá và commit tồn/Order/Cart trong transaction. |
| 3:05–4:15 | SV1 nói, SV3 Compass/Admin | Mở đúng Order, chỉ item/customer/address/category snapshot. Giá A 10 triệu; Admin đổi riêng Product price sang B 12 triệu; Order cũ vẫn A. Dùng đoạn snapshot 30 giây ở bản 5 phút; giải thích reference sống khác dữ liệu lịch sử nhúng. |
| 4:15–5:00 | SV3 Dashboard, SV2 nói | Chọn 30 ngày/Theo ngày/Làm mới, ghi baseline Revenue/Products Sold/Orders/Customers. COD mới PENDING/UNPAID chưa vào revenue; Order count theo createdAt và Customers toàn cục, các KPI không cùng cohort. |
| 5:00–5:50 | SV1 Admin Order Web | Tìm đúng orderCode → Chi tiết → Xác nhận → Giao hàng → Hoàn thành/thu COD, theo allowedActions và version mới. Nếu conflict, refetch; không ép PAID hay sửa timestamps trong Compass. |
| 5:50–6:35 | SV2 nói, SV3 Dashboard | Làm mới cùng range: merchandise revenue tăng **10.200.000 VND**, units +2; ship 30.000 không cộng revenue, total đơn 10.230.000 có ship. Giá Product B không đổi số tăng từ snapshot A; Product bán một đơn vị mỗi SKU có thể chưa vào Top5, không hứa đứng đầu. |
| 6:35–7:45 | SV2 nói, SV3 Compass | orders Aggregations/Text: match qualified/completedAt → pre-sort nhãn → unwind → group → rank → limit → project. Revenue match/group/dateTrunc/sort; lấy from/to Network để bind cùng Dashboard, hoặc nói rõ file seed standby dùng range khác. Backend bổ sung metadata/bucket 0, React render chart. |
| 7:45–8:55 | SV2 nói, SV3 Compass | Chuyển **ecommerce_benchmark**, query category/status/type/price, sort price/id, limit 20. Natural 30.000/0 docs/keys, named 20/20, cùng 20 results; mở raw evidence 07B nếu cần true pre-build. Nêu full repository cần count/lookup/facet nên đọc 96 docs, không lấy selector làm toàn API; revenue/Top5 đọc 10.000 → 152 ở window 7 ngày. Không drop index. |
| 8:55–9:30 | SV3 | Mở [evidence index](defense-evidence-index.md): validators/type probes, seed manifest, 8 pipeline outputs, explain/roundtrip và test/E2E lịch sử. Import/export dùng Extended JSON giữ BSON/nested; roundtrip Product/Order là slice, không import lại dev đang demo. |
| 9:30–10:00 | Cả nhóm, SV3 điều phối | Kết thúc demo, nhận phản biện theo [20 Q&A](defense-qa.md). Nêu COD local/ảnh fixture rỗng và VNPAY live BLOCKED. Phần hỏi đáp diễn ra sau timer. |

## Sau buổi demo

Restore riêng giá điện thoại về A qua Admin hoặc helper. COMPLETED là terminal, helper giữ Order và doanh thu thực của fixture, không rollback bằng manual DB update. Với đúng một Order hai Product, quantity 1 mỗi Product, mỗi stock từ 20 còn **19**; nếu đã có lần bán khác dùng tồn thực. Bản 5 phút giữ PENDING, có thể hủy sau proof để hoàn kho; không reseed toàn DB cho buổi bảo vệ sau.

## Phân công theo đề

SV1 phụ trách Schema/CRUD/Order snapshot và transaction checkout. SV2 phụ trách Aggregation/Index/Performance và định nghĩa metric. SV3 phụ trách Dummy Data/Compass/Frontend-Dashboard, giữ thời gian, chuyển màn hình và mở evidence. Dù một người phát triển chính, từng SV phải rehearsal và giải thích được phần đã phân công; SV3 không đọc thay cả nhóm.
