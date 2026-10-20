# Kịch bản bảo vệ 10 phút —20/10/2026

Dùng cùng môi trường và account với [bản5phút](demo-script-5min.md). Bản local dùng `ecommerce_defense`, API5000, Web5173; bản public dùng Atlas. Dữ liệu chuẩn bị và trạng thái manual gates ở [handoff](defense-final-handoff-20261020.md).

| Thời gian | Người | Thao tác |
| --- | --- | --- |
| 0:00–0:40 | SV3 | Giới thiệu barem, seed180Products/100Orders/40Users và demo riêng. Live corpus hiện184Products/102Orders/44Users, không đánh đồng fixture với seed. |
| 0:40–1:40 | SV1/SV3 Compass | Ba ngành chung products, attributes đa hình; validator và BSONlong VND, ObjectId/Date. |
| 1:40–2:15 | SV1 Admin | Product CRUD/form attributes và ma trậnSKU. M100k/XL120k, tồn riêng; sửa description fixture riêng nếu còn thời gian. Không thay identity SKU đang giữ hàng. |
| 2:15–3:05 | SV1 Customer | SizeM100k+áo snapshot60k, quantity1 mỗiitem→Cart/address/COD/quote→Order190k cóship30k. |
| 3:05–4:15 | SV1/SV3 | Order snapshot60k→Admin Product70k→Order vẫn60k; mở embedded customer/address/category/items. |
| 4:15–5:00 | SV2/SV3 Dashboard | Ghi revenue baseline cùng from/to. Đơn mới chưa qualify; giải thích Orders theocreatedAt, doanh thu theocompletedAt. |
| 5:00–5:50 | SV1 Admin | Tìm đúng orderCode: confirm→ship→complete/thuCOD theo version/allowedActions. Không set PAID quaCompass. |
| 5:50–6:35 | SV2/SV3 | Refreshcùng range: revenue+160.000, units+2, ship30kexcluded. Giá hiện70k không đổi snapshot60k. Không hứa fixture vàoTop5. |
| 6:35–7:45 | SV2/SV3 Compass | Pipeline Top5/Revenue: match qualified/date→unwind/group/sort; dùng đúng from/to. Không JOIN giá Product sống. |
| 7:45–8:55 | SV2/SV3 | Benchmark07B/explain có cùng kết quả,30.000→20docs choselector; Revenue/Top5 window7ngày10.000→152Orders. Raw evidence nếu localbenchmark không có; không drop index. |
| 8:55–9:30 | SV3 | Mở canonical export và receipt import full7collections, giữ BSON/validator/index. Có thể trình diễn Compass import sangDBmới riêng theoguide; không import đèDBnghiệp vụ. |
| 9:30–10:00 | Cả nhóm | Review4sao từ đơnCOMPLETED+PAID/nhãntrìnhdiễn, VNPAYSandbox2bank+6SIT. NhậnQ&A sau timer. |

Sau demo restore riêng Product70k→60k. Đơn COMPLETED giữ nguyên và tồn giảm1mỗiProduct; không hoàn kho bằng reset. Với đúng một lần thêm từ baseline, matrixroot19→18 (M9→8, XL10 giữ nguyên), áo snapshot9→8. Tồn thực có thể khác nếu đã demo nhiều lần.

SV1: Schema/CRUD/checkout/snapshot. SV2: Aggregation/Index/metric. SV3: Data/Compass/UI/vận hành/thời gian. Agent chuẩn bị kịch bản và evidence; từng SV phải tự luyện và bấm giờ trước khi đánh dấu rehearsal người thật PASS.
