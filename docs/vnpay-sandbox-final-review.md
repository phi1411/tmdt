# VNPAY Sandbox và rà soát ràng buộc — 19/10/2026

## Phạm vi và trạng thái

Người dùng cung cấp merchant Sandbox và giao hoàn tất tích hợp, rà soát/sửa logic còn thiếu. Source làm trên clone `tmdt-review-20261017`, giữ nguyên các thay đổi chưa commit và storage của checkout gốc. Chỉ môi trường test, không thanh toán tiền thật, không dịch vụ trả phí mới. Website: https://novamart-web.onrender.com ; health: https://novamart-api.onrender.com/api/v1/health .

Application commit `ef9a481d6c01f84c380b66bcce9e13de7c9078d2` đã Live trên backend và static Render hiện hữu. Backend có cấu hình merchant riêng, VNPAY_ENABLED=true, API và expiry worker cùng supervisor; khóa bí mật không nằm trong source/frontend/evidence. IPN đã lưu thành công tại SIT của VNPAY; việc lưu cấu hình này tự nó không chứng minh gateway đã gửi IPN tự động.

**CODE/BUILD/PUBLIC REGRESSION PASS; PROVIDER BANK/IPN PENDING_USER_TERMS_CONFIRMATION.** Real gateway nhận signed URL và mở biểu mẫu thẻ NCB/Test130.000VND. Sau nhập thẻ test, gateway yêu cầu chấp nhận điều khoản; agent đã xin xác nhận tại bước này và chưa nhận câu trả lời khi chốt. Không bấm chấp nhận, không nhập OTP, không đánh dấu Order PAID hoặc claim automatic IPN/Live Sandbox PASS. SIT nhận hai mã giao dịch thử nhưng chưa chạy bộ case IPN do cần hoàn thành bước provider prerequisite. Không dùng callback tự ký để thay bằng chứng ngân hàng Sandbox.

## Lỗi thực tế đã sửa

| Vấn đề | Sửa và kiểm chứng |
| --- | --- |
| Render chỉ chạy API, thiếu worker chủ động giải phóng kho khi người mua bỏ thanh toán | Supervisor hai process API/expiry trong cùng dịch vụ. Child chết dừng peer và exit nonzero; shutdown có giới hạn. Bật worker khi bật VNPAY; giữ worker khi tắt tạo link. Real child-process tests PASS. |
| Seed có5online PENDING lịch sử quá hạn, bật worker thẳng sẽ đụng corpus demo | Mốc createdAt vận hành cố định `2026-10-19T12:57:14Z`; chỉ scanner lọc mốc, không reset/đổi fixture. Real rs0 test hoàn kho once và giữ Order trước mốc PASS. Không được nâng mốc sau restart. |
| Return giữ thông báo PENDING cũ sau khi Order FAILED/EXPIRED; review flag và lỗi mạng gây hiểu sai | View lấy Order mới đúng id, signature guard giữ nguyên; hiển thị review sau poll, lỗi mạng là chưa xác minh và có retry; bỏ kết quả async cũ.6FE tests PASS. |
| Reviews404 khi slug hợp lệ nhưng giống24ký tự ObjectId | Existing ID có ưu tiên, ID không tồn tại thì fallback slug; UI dùng product.id.2real DB tests bao gồm collision PASS. |

Không thay API nghiệp vụ/schema/index/pipeline trong đợt này. Không thêm Seller/Shipper/Staff/refund/coupon. COD và doanh thu vẫn giữ invariant cũ. ADR014 ghi quyết định vận hành; ADR013 là quyết định đã được giao về SKU/reviews, thay giới hạn lịch sử ở phase02.

## Kiểm chứng source cuối

- Full backend MongoDB rs0 thật: **710 passed/0failed/0errors/0skipped,226.015s**. JUnit gốc lưu riêng tại `.local/vnpay-sandbox/pytest-audit-final.xml`; safe receipt `backend/evidence/vnpay-audit-checks.json`.
- Frontend TypeScript strict + production build PASS34.69s;6/6payment status tests PASS; npm audit0knownfindings. Bundle JS còn cảnh báo kích thước khoảng930kB; không claim zero warning hoặc security tuyệt đối.
- Route audit54method/path,13blueprints,0collision, prefix/api/v1 nhất quán. Auth/User/Catalog/Commerce/Payment/Admin/Reviews cùng tồn tại.
- Design checker STATIC_PASS:7validators,22negativecases,8canonicalpipelines,20candidateindexes. Database demo dùng16declared+7_id_indexes, không apply index candidate khác.
- Rà soát seed:182Products gồm61Electronics/61Fashion/60HomeAppliance;100seedOrders có2–5items. Live101Orders bao gồm fixture bảo vệ cố ý giữ, không là seed sai định mức.
- Snapshot item/product/category/address và tiền BSON long VND giữ nguyên; Revenue=COMPLETED+PAID/completedAt/items snapshot, không shipping hoặc lookup giá Product sống. Canonical aggregation8pipelines không đổi; bằng chứng snapshot/concurrency/rollback/ownership/amount tampering nằm trong full suite và public regression.

## Bằng chứng public, cleanup và giới hạn

Public regression sau khi bật VNPAY: **62HTTPS checks PASS**, COD/SKU reserve/cancel-once/snapshot/Adminlifecycle/revenue+120.000VND không shipping/reviews/ownership/blocked/invalidJWT/payload/CORS. Exact cleanup2Users1Cart2Orders1Product1Category1Review0Attempts, canonical7validators/16indexes match và0invaliddocuments. Receipt `backend/evidence/vnpay-cod-review-regression.json`; fingerprint lượt này bao gồm fixture VNPAY đang PENDING, trước/sau c20920d... khớp. Không nhầm fingerprint trung gian này với baseline cuối479699.... Kết thúc lượt kiểm tra chờ người dùng: cleanup đúng1User1Cart2Orders2Attempts1Product1Category;0Reviews. Atlas về43Users/5Categories/182Products/2Carts/101Orders/30Attempts/0Reviews, fingerprint **47969975612b28c5851bb056a462f8cf8a23ef3f66ebc54d58a62cd8b4ffddc2** khớp baseline trước cả đợt;7validators/16declaredindexes match canonical/0invaliddocuments/0orphans,5historicalpending giữ nguyên. Isolated test7collections0, dev47d0aef... không đổi. Receipts `vnpay-sandbox-cleanup.json`, `vnpay-final-integrity.json`, `vnpay-provider-rehearsal.json` trong backend/evidence. Không xóa dữ liệu người dùng/seed hoặc reset/reseed. Chỉ dọn đúng fixture có journal và backup riêng.

Windows production supervisor fault probe riêng có kết quả INCONCLUSIVE_WRAPPER_PID_ENUMERATION; không suy rộng thành lỗi trên Render Linux. API/worker local đã health/scan và real child-process unit checks PASS; Render đã thực chạy cả hai process. Các gate Compass GUI/nhóm3người rehearsal có bấm giờ/offline OS vẫn cần người dùng làm theo demo pack, không được tự đóng bằng browser scoped tests.


## Việc cần người dùng

1. Xác nhận đồng ý điều khoản sử dụng **VNPAY Sandbox** để agent tạo giao dịch mới và tiếp tục qua OTP test; hoặc tự thao tác bước đó trên trình duyệt. Các Order của lượt đang chờ đã được dọn nên không tái dùng đường dẫn cũ.
2. Sau bank OTP thành công phải đối chiếu IPN server thật và Return readonly. Nếu gateway không tự gửi IPN, merchant cần đăng ký URL public với VNPAY; việc lưu trong SIT không thay thế xác nhận nhà cung cấp. Agent chưa gửi email/support message.
3. Rehearsal nhóm3SV: Compass xem2ngành/embedded snapshot/import-export và bấm giờ5–10phút; offline OS là gate thủ công lịch sử. Nội dung báo cáo/demo pack có sẵn, chưa chứng minh các thao tác người thật này trong phiên.

Backend/static vẫn dùng dịch vụ Render hiện hữu$7/tháng+static free; worker nằm cùng dịch vụ. Không hẹn lịch tự ngừng; người dùng suspend/delete khi kết thúc demo. Secret chỉ private/backend config, không nằm trong diff được commit.
