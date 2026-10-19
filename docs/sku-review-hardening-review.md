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

Rollout Render đang được thực hiện sau checkpoint local/Atlas. Chỉ claim public PASS khi có `backend/evidence/sku-review-public-smoke.json` và đối chiếu commit Live của cả hai dịch vụ. Tool `scripts/deploy/verify_sku_reviews_public.py` dùng fixtures ngẫu nhiên có journal/backup, test HTTPS COD/SKU/reviews/security và exact transaction cleanup; không chạy seed lên Atlas.

- **VNPAY disabled, Live Sandbox chưa kiểm thử** theo lựa chọn người dùng; không có thanh toán tiền thật.
- Build còn warning bundle JS928kB; audit0không đồng nghĩa bảo đảm security toàn sản phẩm.
- Tool viewport set390 nhưng DOM vẫn1280 kể cả tab mới/reload, vì vậy mobile/tablet sau dependency upgrade **MANUAL PENDING**, không gán PASS từ kích thước desktop. Reset override đã thực hiện.
- Compass GUI, rehearsal nhóm3người có bấm giờ và offline OS là manual gates của checkpoint07D; chưa có evidence mới để đóng.
- Backend Render vẫn dịch vụ$7/tháng hiện có; không tạo thêm dịch vụ trả phí/expiry worker. Phải suspend/delete khi hết tháng demo nếu không muốn tiếp tục tính phí.
