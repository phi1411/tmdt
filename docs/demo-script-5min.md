# Kịch bản bảo vệ 5 phút — bản hiện hành20/10/2026

Chạy trên một môi trường xuyên suốt: Web local http://127.0.0.1:5173 + API5000 + Compass `ecommerce_defense`; hoặc publicWeb + Compass Atlas `novamart_demo`. Không đặt Order trên public rồi tìm trong bản sao local. [Bàn giao cuối](defense-final-handoff-20261020.md) ghi account private, startup và bằng chứng. Đây là kịch bản chuẩn bị; ba SV chưa thực hiện rehearsal có bấm giờ trong phiên agent.

Chuẩn bị trước timer: Customer/Admin hai phiên riêng; Cart chứa1 `DEFENSE-FINAL-SKU` SizeM giá100.000 và1 `DEFENSE-FINAL-SNAPSHOT` giá hiện tại60.000; địa chỉ demo có sẵn. Không gửi đơn trước bước checkout sống. Mở sẵn Compass và Dashboard.

| Thời gian | Người | Thao tác và lời nói |
| --- | --- | --- |
| 0:00–0:15 | SV3 | Giới thiệu MongoDB, seed180Products/3ngành/100Orders mỗi2–5items. Dữ liệu demo riêng làm livecounts lớn hơn seed. |
| 0:15–0:55 | SV1 nói/SV3 Compass | `products` filter3SKU DEMO-ELE-001/DEMO-FAS-001/DEMO-HOM-019. Mở attributes khác nhau trong cùng collection; ObjectId/Date/long và validator. |
| 0:55–1:35 | SV1 Web | Cart2items→COD→quote→Đặt hàng. Subtotal160.000, shipping30.000, total190.000 theo config hiện hành; luôn đọc quote thực. Copy orderCode mới. Size chọn trong bảng mua, không qua bộ lọc. |
| 1:35–2:35 | SV1/SV3 | Compass tìm đúng Order mới, mở items/customer/address/category snapshots. Admin đổi riêng `DEFENSE-FINAL-SNAPSHOT` 60.000→70.000; Order vừa đặt vẫn60.000. Không sửa stock, SKU hoặc Order. |
| 2:35–3:20 | SV2 nói/SV3 Dashboard | Revenue/Top5/category/status. COD PENDING/UNPAID chưa cộng doanh thu. Chỉ COMPLETED+PAID theo completedAt; tiền hàng không gồm ship. |
| 3:20–4:00 | SV2/SV3 Compass | Orders→Aggregations→Text→pipeline Top5. Chỉ $match/$unwind/$group/$sort/$limit và snapshot; không $lookup Product để lấy giá hiện tại. Bind from/to giống Dashboard khi đối chiếu. |
| 4:00–4:45 | SV2/SV3 | Evidence07B: benchmark riêng30.000Products/10.000Orders; selector COLLSCAN30.000docs→IXSCAN20docs/20keys cùng20kết quả. Không gọi đây là latency toàn API hoặc giả vừa drop index. Nếu DBbenchmark không có ở máy này, nói rõ đang xem raw evidence. |
| 4:45–5:00 | SV3 | Kết luận bốn mục barem; VNPAY Sandbox đã2bank/testOTP/automaticIPN và6/6 SIT, không tiền thật. |

Sau timer: hủy đúng Order demo còn PENDING/CONFIRMED qua Web để hoàn kho một lần; Admin restore riêng price70.000→60.000. Không reset/reseed hoặc cộng stock tay. Nếu đã COMPLETED thì giữ lịch sử/bán hàng, không ép hủy.

Đơn chuẩn bị `ORD-6AD71662EC77AC8C719DAF03` là **API preparation**, COMPLETED/PAID, hai snapshot100.000+50.000; Product thứ hai hiện60.000. Chỉ dùng làm standby và nói đúng nguồn, không gọi là Order Web vừa đặt. Review4sao có nhãn trình diễn từ chính đơn này. Các report07C/07D cũ dùng fixtures10triệu/200nghìn là evidence lịch sử riêng.
