# Hoàn thiện SKU, Reviews và COD — 19/10/2026

Người dùng yêu cầu hoàn thiện các thiếu sót sau review GitHub, ưu tiên COD vì chưa có merchant VNPAY. Thực hiện trong clone `tmdt-review-20261017`, base193f1d8; giữ nguyên các thay đổi chưa commit và Mongo storage của checkout gốc.

## Kết quả implementation

- Bảng chọn chỉ xuất hiện khi bấm thêm giỏ/mua. Không tự chọn size/màu; hỗ trợ Product legacy và matrix; giữ modal khi API lỗi, chặn hết kho/thiếu lựa chọn.
- Exact options/SKU binding và quantity theo từng SKU; giá do server lấy. Checkout decrement, cancel/expiry restore root+SKU trong cùng transaction, once-only. Product stock=sumSKUstock, price=minSKUprice. Guard không đổi identity khi còn đơn giữ kho.
- Admin tạo/sửa nhóm lựa chọn, giá và kho từng SKU; tổng do server dẫn xuất. Không thêm collection biến thể riêng hoặc thay cách lưu Order snapshot.
- Review thuộc đúng Customer/Order/Product COMPLETED+PAID. Insert và ratingSummary cùng transaction/version guard; concurrency/rollback có regression thật trên rs0. Public feed che tên, bỏ user/order IDs, có pagination/rating/comment filter và visibility guard.
- Bỏ số review/rating/đã bán/discount/voucher/shop metrics giả, nút chat/helpful chưa có chức năng. Không tạo coupon/refund/seller/chat APIs.
- Seed bổ sung dry-run mặc định, chỉ insert Product thiếu khi `--apply`; không overwrite kho và không tạo review giả/gán Order ngẫu nhiên hoặc xóa reviews thật.
- Đồng bộ canonical validator/checker/design sample7collections,16declaredindexes; ADR013 và API contract giữ các contract cũ, thêm hai review routes (54method/path tổng).
- Tailwind4.3.3/PostCSS adapter và React Router DOM7.18.4 đóng9npm findings cũ. Không dùng audit fix force.

## Kiểm chứng đã chạy

| Phần | Kết quả |
| --- | --- |
| Full backend trên MongoDB8.0.32/rs0 thật | **701passed,0failed,0errors,0skipped;131.80s** |
| Regression mới | Selection tampering, independent SKU stock, last-unit concurrent checkout, cancellation/expiry replay, snapshot, Admin matrix validation/roundtrip, review rollback/concurrency/privacy |
| Frontend | `npm ci`, TypeScript strict và production build PASS15.69s; audit0knownfindings |
| Design checker | 7validators/22negativecases/8canonicalaggregations/20candidateindexes STATIC_PASS |
| Real Web trên owned ecommerce_test | Admin create/edit SKU; Customer buy/quote/COD; Admin confirm→ship→complete/PAID; Customer review; rating/filter; cancel/hoàn kho PASS scoped |
| Snapshot Web | SKU120.000đ→live140.000đ; Order giữ120.000đ |
| Stock real DB | Sau một completed SKU Trắng và một cancelled SKU Đen: root4=Đen2+Trắng2 |
| Browser console | Captured error/warn logs rỗng trong scoped journey |
| Cleanup test DB | Cả7collections0, không reset/reseed database hiện hữu |

Receipt: `backend/evidence/sku-review-hardening-checks.json`. UI walkthrough dùng bundle trước thay đổi nhỏ cuối về ẩn skuId và validate Review image URL; source cuối đã build lại. Không claim toàn bộ suite E2E cũ đã được rerun hay toàn bộ browser/network không lỗi trong mọi phiên.

## Atlas migration

`scripts/deploy/migrate_sku_reviews.py` mặc định chỉ plan; `--apply` có allowlisthost/database/replica, exact private BSON backup, fingerprint guard, transaction/version guard nếu cần sửa data, additive validators/indexes và retrospective validation. Không drop/reset/reseed. SKU mismatch đã có Order sẽ block để đối soát, không suy đoán kho. Review không chứng minh được purchase thì giữ document PENDING_AUDIT, không xóa.

Đã rehearsal trên storage local riêng, sau đó apply Atlas `novamart_demo`: **43Users/5Categories/182Products/2Carts/101Orders/30Attempts/0Reviews**,0Productupdates/0reviewquarantines. Fingerprint documents trước/sau **47969975612b28c5851bb056a462f8cf8a23ef3f66ebc54d58a62cd8b4ffddc2**;7validators/16declaredindexes,0invaliddocuments. Giữ cả các User/Cart mới phát sinh từ người dùng; không coi counts42/1 cũ là lý do xóa dữ liệu. Receipt migration tại `backend/evidence/sku-review-hardening-migration.json`; backup có password hashes nên chỉ lưu ignored `.local`.

Tái lập: tạo private JSON chứa `uri` và `database` trong `.local`, chạy migration với `--connection-file` trước để xem plan; chỉ thêm `--apply` sau khi kiểm tra đúng đích. Không đưa URI/password vào terminal arguments, Git hoặc chat.

## Deployment và giới hạn

**PUBLIC SKU/REVIEW/COD VERIFICATION PASS.** Cả hai dịch vụ Render đã Deploy succeeded|Live với application commit`928b6c8201ae5480396bc44c98b1170998bff11f`. Backenddeploy`dep-dbas334s728c739fccs0`; frontenddeploy URL ghi tại browser receipt. **62HTTPS checks PASS**, COD/SKU reserve+cancel-once/snapshot120k→live140k/Adminlifecycle/revenue+120k no shipping/reviews eligibility+duplicate+privacy/guest+CustomerACL+ownership+invalidJWT+blocked/tampering/CORS. Exact cleanup2Users1Cart2Orders1Product1Category1Review0Attempts, full fingerprint479699... khớp, toàn bộ7validators/16indexes match canonical và0orphans. Receipts: `backend/evidence/sku-review-public-smoke.json`, `sku-review-public-browser.json`, `sku-review-final-integrity.json`. Website: https://novamart-web.onrender.com ; API health: https://novamart-api.onrender.com/api/v1/health .

Public browser kiểm tra7nhóm scoped: mobile390home/catalog/filter/modallegacy chọn size/color; tablet768detail/AdminSKUeditor4rows; desktop1280Dashboard3sectors/1area/6bars và modal; không tràn ngang, captured console error/warn logs rỗng. Admin form chỉ draft, không submit public browser; real SKU mutation đã chứng minh qua Web owned local +62publicHTTP. Không claim đã rerun toàn bộ public UI suite.

Tool `scripts/deploy/verify_sku_reviews_public.py` dùng fixtures ngẫu nhiên có journal/backup, test HTTPS COD/SKU/reviews/security và exact transaction cleanup; không chạy seed lên Atlas.

- **VNPAY disabled, Live Sandbox chưa kiểm thử** theo lựa chọn người dùng; không có thanh toán tiền thật.
- Build còn warning bundle JS928kB; audit0không đồng nghĩa bảo đảm security toàn sản phẩm.
- Viewport thử local ban đầu áp dụng vào tab đang selected khác nên DOM mục tiêu vẫn1280; lần follow-up public áp dụng đúng active tab đã đo thật390/768/1280 và kiểm tra layout/modal. Đóng pending responsive trong phạm vi các trang đã liệt kê, không suy rộng thành mọi trang. Đã reset override và logout Admin.
- Compass GUI, rehearsal nhóm3người có bấm giờ và offline OS là manual gates của checkpoint07D; chưa có evidence mới để đóng.
- Backend Render vẫn dịch vụ$7/tháng hiện có; không tạo thêm dịch vụ trả phí/expiry worker. Phải suspend/delete khi hết tháng demo nếu không muốn tiếp tục tính phí.

## Trạng thái bàn giao

Đã push3commit implementation (ee66a77/08a3a25/928b6c8) và manual deploy cả backend/static trên dịch vụ hiện hữu. Commit tiếp theo chỉ đóng evidence/docs, không thay runtime. Local Mongo/API/preview kiểm thử riêng đã dừng sau kiểm tra7testcollections0; isolated dev fingerprint47d0aef... không đổi, original checkout/storage không đụng. Original uncommitted helper/demo files không đưa vào các commit này. Còn người dùng chuẩn bị merchant khi muốn VNPAY, và tự rehearsal Compass/nhóm3người có bấm giờ/offlineOS.
