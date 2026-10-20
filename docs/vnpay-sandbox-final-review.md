# VNPAY Sandbox và rà soát ràng buộc — chốt20/10/2026

## Kết quả hiện tại

**VNPAY SANDBOX END-TO-END PASS cho luồng thực đã kiểm thử.** Hai giao dịch130.000VND đã thanh toán bằng thẻ NCB và OTP test tại gateway chính thức; IPN tự động đã xác minh và commit Order CONFIRMED/PAID +attempt SUCCEEDED trước khi agent gửi bất kỳ replay/probe nào. Không phải callback tự ký hoặc cập nhật DB thành paid. **Bộ SIT chính thức đã đạt 6/6 ca trong follow-up cuối20/10 bên dưới.** Không thanh toán tiền thật hoặc tuyên bố được chứng nhận vận hành production.

Website: https://novamart-web.onrender.com ; health: https://novamart-api.onrender.com/api/v1/health . Application `ef9a481d6c01f84c380b66bcce9e13de7c9078d2` đang Live backend/static trên Render hiện hữu. VNPAY_ENABLED=true, merchant secret chỉ backend/private; Return `/payment/return`, IPN `/api/v1/payments/vnpay/ipn`. API+expiry cùng supervisor, fixedcutover2026-10-19T12:57:14Z bảo toàn5seedonline PENDING lịch sử. Không thêm dịch vụ trả phí hoặc đổi application source trong lượt20/10.

## Provider và Web thật20/10

| Kiểm tra | Kết quả / evidence |
| --- | --- |
| Gateway/NCB/OTP/automaticIPN/Return | PASS. Order ORD-6AD706D789D15B8F21C03A22, provider15709300; CONFIRMED/PAID, SUCCEEDED, callbackFingerprint có;130.000VND. `backend/evidence/vnpay-provider-live-20261020.json`. |
| Luồng hoàn toàn từ UI | Login→Product detail→Mua ngay→SizeM→Cart→checkout chọn địa chỉ có sẵn→VNPAY quote→xác nhận trên Web→gateway/NCB/testOTP→Return PAID. Order ORD-6AD7088889D15B8F21C03A2F/provider15709315; SKU100.000+ship30.000; Cart0, rootstock9=SKU6+3. `vnpay-web-live-20261020.json`. Không claim UI tạo mới địa chỉ/register ở lượt này; fixtures được chuẩn bị qua API. |
| Return readonly | Signed provider query đã thu từ redirect: verified/confirmed=true, authoritative=false, SUCCESS; full owned Order/attempt/Product digest không đổi. |
| Replay IPN thực đã ghi nhận | Gửi lại nguyên callback provider đã thu qua HTTPS→02, không đổi state/stock/timestamps. Đây là probe replay riêng sau automatic IPN, không thay bằng chứng IPN tự động. |
| Tamper | Sửa amount trong callback mà không ký lại→97, state giữ nguyên; signed amount mismatch/unknown reference/late/concurrency/rollback đã có deterministic real rs0 tests, không claim SIT live cho các case chưa chạy. |
| Admin sau payment | Không cho Admin manual confirm VNPAY409; ship→SHIPPING→complete→COMPLETED/PAID, paidAt/snapshot không đổi. Dashboard +100.000VND tiền hàng, loại30.000VND ship. `vnpay-post-payment-20261020.json`. |
| Hủy2unpaid Orders chuẩn bị SIT | CANCELLED/FAILED, replay cancel không đổi, giữ once-only stock restore; không trả kho thêm khi cleanup. |
| Browser | Hai màn hình Return PAID, Web Order COMPLETED; captured error/warn logs rỗng trong scoped final Web journey. Không claim mọi request/page/phiên đều không lỗi. Screenshots private `.local/vnpay-sandbox/bank-success-20261020.png`, `web-bank-success-20261020.png`, `order-completed-20261020.png`. |

Portal SIT đăng nhập thành công nhưng danh sách giao dịch rỗng sau chọn terminal; một lượt NCB bổ sung báo đơn không tồn tại/đã xử lý và một lượt báo lỗi xử lý. Mở lại tuần tự một giao dịch đã tới OTP, chưa kết luận nguyên nhân hoặc claim đã sửa provider. Không chạy bộ6case SIT trên dữ liệu seed hoặc các Order đã hủy. Hai giao dịch ngân hàng Sandbox thực ở trên thành công và IPN tự động đã được đối chiếu độc lập; **không suy rộng thành VNPAY chứng nhận SIT đầy đủ**. Không gửi email/support thay người dùng.

## Lỗi thực tế đã sửa19/10

| Vấn đề | Thay đổi và kiểm chứng |
| --- | --- |
| Render chỉ API, thiếu worker chủ động hoàn kho | Supervisor hai process API/expiry trong dịch vụ hiện hữu; child dừng bất thường thì stop peer/exit nonzero, bounded shutdown. Giữ worker khi tắt creation. Real child-process tests PASS. |
| Bật worker sẽ expire5online seed cũ | Fixed createdAt cutover, không nâng mốc sau restart; real rs0 cutoff/stock-once PASS. Lazy expiry/IPN không bỏ invariant cũ. |
| Return giữ PENDING/review cũ hoặc báo bank failure khi lỗi mạng | Lấy Order hiện hành đúng id, giữ signature guard; phân biệt chưa xác minh, retry; discard async cũ.6FE tests PASS. |
| Reviews404 với slug24hex | Existing ID có ưu tiên; ID không tồn tại fallback slug; UI dùng product.id.2real DB tests PASS. |

ADR013 là quyết định SKU/reviews được giao trước đó, ADR014 khóa vận hành payment. Không thêm Seller/Shipper/Staff/refund/coupon, đổi schema/index/API nghiệp vụ hoặc pipeline trong đợt này. Helper d09f6e6 hỗ trợ rehearsal dùng địa chỉ chưa default và tiếp tục đúng Cart riêng.

## Source tests và barem

- **710passed/0failed/0errors/0skipped,226.015s**, full real rs0 run19/10. Frontend strict+build PASS34.69s;6/6status tests; npm audit0knownfindings. Không rerun suite20/10 vì không đổi app/tests. Safe receipt `backend/evidence/vnpay-audit-checks.json`; JUnit/log gốc ignored `.local/vnpay-sandbox`. Build còn warning bundle khoảng930kB; không claim security tuyệt đối.
- Route54method/path/13blueprints/0collision/all/api/v1. Auth/User/Catalog/Commerce/Payment/Admin/Reviews cùng tồn tại.
- Design checker7validators/22negativecases/8canonicalpipelines/20candidateindexes STATIC_PASS; live16declared+7_id_indexes, không apply candidates khác.
-182Products:61Electronics/61Fashion/60HomeAppliance;100seedOrders mỗi2–5items, live101bao gồm fixture bảo vệ giữ có chủ ý. Polymorphic cùng products; Order snapshots/embedded và BSONlong VND giữ nguyên; revenueCOMPLETED+PAID/completedAt/items snapshot/no shipping/no live Product lookup.
-62publicHTTPS regression19/10 PASS: COD/SKU/cancel-once/snapshot/Admin/revenue/reviews/ACL/ownership/blocked/invalidJWT/payload/CORS. Receipt `vnpay-cod-review-regression.json` fingerprint trung gian bao gồm fixture online PENDING, trước/sau bằng nhau. Không nhầm với baseline cuối.

## Database integrity và cleanup

Hai lượt20/10 cleanup exact có journal/private backup: tổng2Users/2Carts/5Orders/5Attempts/2Products/2Categories,0Reviews. Mỗi lượt về đúng baseline **43Users/5Categories/182Products/2Carts/101Orders/30Attempts/0Reviews**, full canonical BSON fingerprint **47969975612b28c5851bb056a462f8cf8a23ef3f66ebc54d58a62cd8b4ffddc2**.7validators/16declaredindexes match canonical,0invaliddocuments/0orphans,5historicalpending giữ nguyên. Không reset/reseed/rollback seed hoặc xóa account người dùng/fixture bảo vệ. Local Mongo/storage/checkout gốc không khởi động hoặc ghi trong20/10.

Receipts backend/evidence: `vnpay-sandbox-cleanup-20261020.json`, `vnpay-web-cleanup-20261020.json`, `vnpay-final-integrity-20261020.json`. Evidence19/10 được giữ nguyên, generic cleanup19không bị ghi đè. Full source working clone `tmdt-review-20261017`; các uncommitted helper/demo files checkout gốc giữ nguyên.

## Lịch sử gate và việc còn lại

19/10 đã tới gateway nhưng dừng xin xác nhận điều khoản, exact cleanup; evidence cũ không được sửa thành paid.20/10 người dùng xác nhận tiếp tục; lần đầu browser inventory rỗng, readonly health/Atlas giữ nguyên (`vnpay-resume-20261020.json`). Follow-up cùng ngày đã mở đúng chat trên host qua Codex navigation, browser kết nối lại và hoàn tất hai lượt ngân hàng/UI ở trên. Không còn blocker thiếu merchant, điều khoản hoặc kết nối browser trong scoped rehearsal này.

Compass GUI/import-export live, nhóm3SV rehearsal5–10phút có bấm giờ và offlineOS vẫn là manual gates lịch sử, chưa có evidence mới để đóng. Bộ SIT chính thức chưa hoàn tất như giới hạn đã nêu. Các phần API/UI/DB bám barem và demo pack đã có; không tuyên bố tất cả gate người thật đã xong. Backend Render$7/tháng hiện có+staticfree, không lịch tự ngừng; suspend/delete khi kết thúc demo nếu không muốn tiếp tục tính phí. VNPAY vẫn chỉ Sandbox, không tiền thật.


## Follow-up cuối20/10 — OFFICIAL SANDBOX SIT 6/6 PASS

Sau khi tạo tuần tự hai giao dịch mới và đưa từng giao dịch tới màn hình OTP, portal VNPAYGW SIT Testing đã liệt kê cả hai. Chọn giao dịch thứ hai cho ca thất bại và chạy bộ kiểm tra chính thức. Không gửi OTP hoặc tự ký IPN trong lượt SIT này; hai lượt bank/testOTP ở phần trước là bằng chứng độc lập. Danh sách `DS GD đã test` xác nhận giao dịch VN6AD714CFEC77AC8C719DAEFA **Thành công** lúc14:18:30 ngày20/10/2026. Không suy đoán nguyên nhân của lỗi danh sách rỗng trước đó.

| Ca provider | Expected/actual RspCode | Portal |
| --- | --- | --- |
| Thanh toán thành công | 00 / 00 | Đạt |
| Thanh toán thất bại | 00 / 00 | Đạt |
| Không tìm thấy giao dịch | 01 / 01 | Đạt |
| Callback đã xử lý | 02 / 02 | Đạt |
| Sai số tiền có checksum hợp lệ | 04 / 04 | Đạt |
| Sai checksum | 97 / 97 | Đạt |

Order thành công ORD-6AD714CFEC77AC8C719DAEF9 →CONFIRMED/PAID, attemptSUCCEEDED/provider15709390; Order thất bại ORD-6AD714F6EC77AC8C719DAEFB →PENDING/FAILED, attemptFAILED/provider15709393. Không review flag; rootstock8=SKU5+3 sau hai lần reserve từ10. Callback lỗi/trùng không reserve thêm hoặc sửa state thành công. Ca thất bại vẫn giữ Order để retry trước deadline theo contract; cleanup exact chỉ xóa toàn bộ fixture riêng, không cộng kho seed.

Evidence an toàn: `backend/evidence/vnpay-sit-final-20261020.json` và `vnpay-sit-final-cleanup-20261020.json`. Screenshot private `.local/defense-final/sit-success.png`. Cleanup đúng1User/1Cart/2Orders/2Attempts/1Product/1Category,0Reviews; canonical full fingerprint trước/sau **47969975612b28c5851bb056a462f8cf8a23ef3f66ebc54d58a62cd8b4ffddc2** và counts43/5/182/2/101/30/0 khớp. Generic cleanup19 và các evidence lịch sử được giữ nguyên.

Đóng gate bộ6case SIT; không cần người dùng chạy lại để hoàn tất tích hợp Sandbox. Đây là kết quả test của portal Sandbox, không phải chấp thuận merchant production/tiền thật. Bản application backend hiện hành ef5e553 chứa bản sửa Cart; frontend ef9a481 không đổi trong follow-up này. Latest app validation là714backend tests và66public checks tại [audit20/10](full-project-audit-20261020.md), không chạy lại vì lượt SIT không sửa application/tests. Dữ liệu demo mới được giữ có chủ đích sau cleanup này được ghi riêng tại [bàn giao cuối](defense-final-handoff-20261020.md).
