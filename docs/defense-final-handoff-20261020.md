# Bàn giao demo cuối — 20/10/2026

Phạm vi theo yêu cầu hoàn tất của người dùng: đóng bộ SIT VNPAY, chuẩn bị dữ liệu trình diễn SKU/review/snapshot bằng API hiện hữu, xuất/nhập bản sao local và cập nhật hướng dẫn bảo vệ. Không thêm feature, sửa application logic, reset/reseed hoặc đổi database architecture.

Điều kiện nghiệm thu: 6 ca SIT có kết quả từ provider; cleanup SIT khớp fingerprint trước thử; fixture demo mới có journal/private backup và nhãn dữ liệu trình diễn; toàn bộ document gốc giữ nguyên; Order COMPLETED+PAID trước khi review; snapshot không đổi khi đổi giá Product; export/import giữ kiểu BSON/validators/indexes. Compass GUI và phần nói có bấm giờ của ba sinh viên chỉ được đánh dấu sau khi người thật thực hiện.

Dependencies: contract Auth/User/Catalog/Commerce/Admin/Reviews hiện hữu; canonical validators/indexes; tooling fingerprint trong scripts/deploy/migrate_sku_reviews.py. Chỉ dùng API để tạo nghiệp vụ; PyMongo đọc kiểm chứng và sao chép sang database local riêng có ownership guard. Mật khẩu, Atlas URI và backup chứa dữ liệu riêng nằm trong .local bị gitignore.


## Kết quả đã thực hiện

| Hạng mục | Kết quả |
| --- | --- |
| VNPAY Sandbox SIT chính thức | **6/6 Đạt**, portal xác nhận Thành công; expected/actual codes00/00/01/02/04/97. Hai lượt NCB/testOTP/automaticIPN trước đó vẫn là evidence riêng. Không có tiền thật hoặc chứng nhận production. |
| Cleanup SIT | Đúng1User/1Cart/2Orders/2Attempts/1Product/1Category;0Reviews. Trở về full fingerprint479699... và counts43/5/182/2/101/30/0. Không reset/reseed. |
| Demo SKU | Product mới `DEFENSE-FINAL-SKU`: SizeM100.000đ/stock9, XL120.000đ/stock10; rootstock19. Bảng chọn xuất hiện khi mua; browser đã chọnXL và xác nhận giá120.000/stock10. |
| Demo COD/review | Order `ORD-6AD71662EC77AC8C719DAF03` được tạo bằngAPI, confirm→ship→complete, COMPLETED/PAID rồi mới review4sao. Nhận xét có nhãn rõ “Dữ liệu trình diễn ... không phải phản hồi khách hàng thật”. Không giả đánh giá của khách thật. |
| Demo snapshot | Product `DEFENSE-FINAL-SNAPSHOT`: lúc mua50.000đ, hiện60.000đ; Order giữ50.000. Hai item100.000+50.000, subtotal150.000, ship30.000, total180.000. Revenue tăng150.000, không cộng shipping. |
| Export/import | Canonical Extended JSON full7collections từ Atlas sang localDB mới `ecommerce_defense`; docs/types/options/validators/indexes equal, fingerprint10ebf1... khớp. Atlas read-only trong thao tác copy. |
| Local functional smoke | MongoDBrs0 PRIMARY/Flask5000/Vite5173 chạy thật; **20HTTP checks PASS**: COD/idempotency/cancel replay/stock restore một lần; VNPAYdisabled503. Exact cleanup về fingerprint10ebf1...; không động local `ecommerce_dev`. |
| Browser mới | Public Product/review/SizeXL; local login→MyOrders→detail đọc snapshot50.000/Order180.000. Scoped browser console error/warn0. Không claim rerun toàn bộ UI suite. |
| App validation gần nhất | **714/714 backend tests**, frontend TypeScript strict/build,6payment status tests và66publicHTTPchecks tại audit20/10. Lượt này chỉ thêm demo tooling/docs/data, không sửa application/tests nên không rerun fullsuite hoặc deploy lại app. |

## Mở để thử ngay

- Public: https://novamart-web.onrender.com/products/ao-demo-sku-m-xl — bấm Mua ngay, chọnM hoặcXL. Review nằm phía dưới.
- Local đã chạy: http://127.0.0.1:5173/ ; health http://127.0.0.1:5000/api/v1/health . Public dùngAtlas, local dùng bản sao riêng; ghi ở bên này không tự đồng bộ sang bên kia.
- Customer mới: `defense-final-20261020@example.test`. Mật khẩu ở file **private** `.local/defense-final/demo-credentials.md`. Admin hiện hữu vẫn `admin@example.test`, mật khẩu không thay đổi. Không chiếu account note hoặc backup lên màn hình bảo vệ.
- Local startup khi cần: chạy `scripts/demo/start_defense_local.py` bằng Python đã có, hoặc file private `.local/defense-final/start-local.cmd`. Nếu ports đang chạy, helper từ chối tạo bản trùng; mở phiên hiện có.
- Compass local URI: `mongodb://127.0.0.1:27017/?replicaSet=rs0` → `ecommerce_defense`. Chỉ dùng `novamart_demo` khi theo luồng public/Atlas.

## Database sau chuẩn bị

Có chủ đích giữ thêm1User/1Category/2Products/1Cart/1Order/1Review;0Attempts. **44Users/6Categories/184Products/3Carts/102Orders/30Attempts/1Review**.7validators/16declared+7_id_indexes,0invalid documents; reference checks được ghi trong final integrity receipt. Toàn bộ corpus trước chuẩn bị giữ nguyên khi loại đúng các document mới theo ownership journal; canonical fingerprint gốc **47969975612b28c5851bb056a462f8cf8a23ef3f66ebc54d58a62cd8b4ffddc2**. Full corpus mới **10ebf1a6b6fe36dc472c487f299a55436a8fb236c5e9e908f28177d48cd6dbb7**.

Seed180Products/100Orders mỗi2–5items/40Users và những account/fixture người dùng yêu cầu giữ không bị sửa.5historical online PENDING seedDEMO0001 giữ nguyên theo cutoff, không phải giao dịch Sandbox mới cần hết hạn. Localdev fingerprint47d0... và test7collections rỗng giữ nguyên. Không nhập private export vào Git.

Đơn chuẩn bị hoàn tất được giữ làm bằng chứng, không ép CANCELLED hoặc hoàn kho sau đó. Nếu nhóm tạo đơn mới khi tập/demo, số đếm/stock/revenue tăng giảm theo nghiệp vụ thật; không dùng helper tạo mới để reset baseline. Helper gặp journal dở hoặc corpus khác sẽ dừng và yêu cầu đối chiếu, không tự xóa hay ghi đè.

## Ba việc người thật còn cần thực hiện

1. **SV3 mở Compass**: xem3ngành, Order snapshot, Aggregation/Explain, rồi Export/Import sangDB mới theo [hướng dẫn](compass-demo-steps.md). Agent hiện chỉ điều khiển được browser, không có nativeCompass input; receiptPyMongo không thay evidenceGUI.
2. **Ba SV tập5–10phút có bấm giờ**, theo [script5phút](demo-script-5min.md)/[10phút](demo-script-10min.md), phân công đúng Schema/CRUD, Aggregation/Index, Data/UI/Compass. Agent không thể thay phần nói/phối hợp của nhóm.
3. Nếu bài cần **offline toàn máy**, nhóm tự ngắtInternet rồi thửCOD/cancel local và nối lại; agent chưa tắt mạngOS. VNPAY/ảnhCDN cầnInternet; localCOD functional PASS không đồng nghĩa đã kiểm tra ngắtOS.

Không còn blocker thiếu merchant/IPN hoặc bộSIT của phần Sandbox. Không claim mọi gate người thật đã PASS. Không mở thêm dịch vụ trả phí; Render backend hiện hữu tiếp tục tính phí cho tới khi người dùng suspend/delete, không có lịch tự ngừng.

## Files và evidence

- `backend/evidence/vnpay-sit-final-20261020.json`, `vnpay-sit-final-cleanup-20261020.json`: provider6cases/states/exactcleanup.
- `backend/evidence/defense-demo-final-20261020.json`: demo giữ lại, original corpus unchanged, schema/index checks.
- `backend/evidence/defense-export-import-20261020.json`: full canonical import equality.
- `backend/evidence/defense-local-smoke-20261020.json`:20HTTPchecks/exactcleanup.
- `backend/evidence/defense-final-integrity-20261020.json`: final counts/references/fingerprints/runtime/browser scope.
- `scripts/demo/prepare_sku_review_demo.py`: guarded one-shotAPI preparation; rerun completed journal chỉ verify.
- `scripts/demo/export_defense_copy.py`: source read-only, target ownership/empty/equalityguard; không overwrite bản sao đã khác.
- `scripts/demo/start_defense_local.py`, `verify_defense_local.py`: startup riêng và disposable smoke.
- Private `.local/defense-final/`: journal, fullbackup, accountnote, runtime, export và screenshots. Khôngcommit/publish.

Latest appbackend deployed ef5e553, static ef9a481; lượt bàn giao không thay appbundle. Commit documentation/tooling mới không cần redeploy runtime. Originalcheckout `tmdt` có helper/demo concurrent chưacommit vẫn giữ nguyên; workingclone là `tmdt-review-20261017`.
