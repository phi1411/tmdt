# Rà soát toàn đồ án Novamart —20/10/2026

## Phạm vi và cách nghiệm thu

Đối chiếu barem/requirements→architecture/schema/business/API→source, kiểm tra Atlas read-only, smoke HTTPS trên fixture riêng có exact cleanup và tests real local rs0 riêng. Rà soát Auth/User/Catalog/SKU/Cart/Checkout/Orders/Payment/Admin/Analytics/Reviews và frontend liên quan. Sửa lỗi đã tái hiện, không thêm feature/refactor rộng/reset/reseed hoặc migration dữ liệu người dùng. Source trên clone tmdt-review-20261017, giữ nguyên các uncommitted files/storage checkout gốc. Acceptance: full backend pass sau fix, FE strict/build/tests, public smoke source đã deploy, DB fingerprint/schema/index/invariant giữ nguyên, ghi riêng manual gates và giới hạn.

## Phát hiện thực tế

**BUG-CART-01:** skuId là optional trong request compatibility nhưng Cart dùng nguyên JSON selection để tính lineId. Cùng SKU với/không skuId thành2dòng; tổng quantity SKU có thể vượt99mỗi dòng dù stock guard vẫn chống oversell.4tests mới thất bại trước fix:2thứ tự optionalid, bypass99, Cart legacy có sẵn2alias.

Sửa CartService POST add: resolve SKU server, canonicalize skuId, gộp alias hợp lệ đúng SKU trước kiểm tra99/50lines/stock. Giữ thứ tự đầu, cartVersion CAS và lỗi validation không ghi Cart. Dòng SKU khác hoặc không còn resolve được không bị gộp. GET không tự migration, không đổi schema/index/Order snapshot.23scoped tests pass, full714tests sau fix PASS và66publicHTTPSchecks PASS trên bản đã deploy. Contract/features/cart đồng bộ.

**DOC-01:** Một số đoạn thiết kế cũ còn ghi frontend/reviews deferred hoặc VNPAY disabled mà không nêu ngay trạng thái hiện hành. Sửa chú thích trạng thái, giữ lịch sử từng phase và liên kết ADR013/014/evidence. Không gán bằng chứng cũ thành kiểm thử mới.

## Đối chiếu barem

| Tiêu chí | Đáp ứng / còn cần chứng minh |
| --- | --- |
| Giải trình MongoDB với thuộc tính linh hoạt | database-schema, ADR001, polymorphic products; cần SV trình bày trade-off trong bảo vệ |
| JSON Schema polymorphic và Embedded Order |7canonical validators hiện hành, Product3discriminators, Order items/customer/address/category snapshots; xem Compass khi demo |
| CRUD danh mục/sản phẩm và tạo đơn | Public/Admin API +Web, transactions/version/validation; source tests và public checks |
| Snapshot không JOIN lịch sử/giá | checkout copy immutable snapshot, order DTO không lookup Product sống; test đổi giá giữ snapshot |
| Aggregation thời gian/Top5 |8canonical pipelines chạy MongoDB, match/unwind/group/sort; revenueCOMPLETED+PAID/completedAt, không shipping |
| Dummy data |182Products61Fashion/61Electronics/60HomeAppliance;100seedOrders2–5items,101live gồm fixture cố ý giữ; không reseed để ép live count |
| Hiệu năng/index | Báo cáo07B/explain và benchmark riêng30k/10k đã có; không claim chạy lại benchmark trong audit này |
| Demo sống | Web/API/payment thực đã có evidence; Compass GUI/import-export và nhóm3SV rehearsal có bấm giờ vẫn cần người thật |

## Kiểm tra database hiện tại

Atlas novamart_demo43Users/5Categories/182Products/2Carts/101Orders/30Attempts/0Reviews.43Users gồm1ADMIN/42CUSTOMER; Guest là trạng thái chưa đăng nhập, không là document User. Full fingerprint47969975612b28c5851bb056a462f8cf8a23ef3f66ebc54d58a62cd8b4ffddc2.

Deep audit:0invaliddocuments,0invariantfindings cho timestamp/defaultaddress/category/type/SKU sums/duplicateids/rating summary/cart references/Order refs+totals+terminalstockmarker/completedstate/PaymentAttempt owner+amount/verifiedreview purchase.182Products đều có ảnh; kiểm tra HTTP ảnh tách riêng.5VNPAY PENDING seed đã quá hạn là fixture lịch sử đã ghi trong ADR014, scanner cutover cố ý giữ; không tự expire/reset/đổi seed để làm report xanh. Đọc chi tiết Order vẫn áp dụng lazy expiry theo nghiệp vụ, nên rehearsal phải dùng fixture riêng thay vì chạm đơn lịch sử.

**Dữ liệu demo mở rộng:** Atlas hiện0Product có tierVariations/skus và0Review; chưa có ví dụ ma trậnSKU/reviews lưu lâu dài để click demo trực tiếp. Đây không là lỗi validator hay thiếu barem; tính năng đã test bằng fixture riêng và dọn exact. Không tự chèn review giả hoặc sửa seed chỉ để tạo cảm giác đã có người mua/đánh giá. Admin có thể tạo Product matrix; Customer phải hoàn tất Order thật trước review.

## Checks thực chạy

| Hạng mục | Kết quả mới trong audit20/10 |
| --- | --- |
| Full backend trước fix |710passed/0fail/error/skip117.750s; không phát hiện case optionalSKU trước khi bổ sung regression |
| Tái hiện lỗi |4/4tests mới FAIL trước sửa, cùng4case đạt sau sửa; không giấu lỗi này trong lịch sử |
| Full backend source cuối |**714passed/0failed/0errors/0skipped,116.247s**, real local rs0;7testcollections exact cleanup0 |
| Frontend | TypeScript strict+production build PASS13.11s,6/6payment status tests PASS; npm audit0knownfindings; Python pipcheckPASS |
| Public source mới |**66HTTPSchecks PASS**, canonicalSKU merge ở cả2SKU, updateCart, COD/idempotency/cancel-once/snapshot/Adminlifecycle/revenue+120kexclude shipping/reviews/security/CORS; exact cleanup2Users1Cart2Orders1Product1Category1Review0Attempts |
| Routes/shared foundation |54method/path,13blueprints,0collision, all/api/v1; một bộ JWT/current-role-status-tokenVersion/globalerrors/serialization/pagination/config/transaction helper; không tìm implementation cạnh tranh |
| Static design |STATIC_PASS7validators/22negativecases/8canonicalpipelines/20candidateindexes; checker không thay DB hoặc tự nghiệm thu feature |
| Aggregation thật Atlas |8pipelines chạy thật;60qualifiedCOMPLETED+PAID,10.103.259.022VND/434units; Top5 khớp phép tính độc lập từ snapshots, day/month/category sum khớp,0lookup |
| Browser readonly scoped | Mobile390catalog61Fashion+filter;Tablet768detail+purchase modal;Desktop1280Electronics/HomeAppliance attributes khác nhau;GuestAdmin→Login.7views/guards,0overflow,0brokenimages và captured warn/error0 trong scope |
| Image URL HTTP |320uniqueURLs,294HEAD200image/*;26không xác minh được/denied kể cả retry. SilverPot trong nhóm26vẫn load1000px trên browser, nên không kết luận26ảnh hỏng hoặc tự thay URL |

Backendfix **ef5e55335d3303ebffb171197dbc243231837d98** đã Live Render deployment `dep-dbbh0amq1p3s73cje72g`, API và payment-expiry cùng chạy/health200. Static frontend không đổi source trong audit này. Screenshot `.local/review/audit-20261020/render-live.png`. Không chạy lại bankOTP vì Cart canonical change đã đi qua COD/full payment tests; VNPAYrealWeb/automaticIPN evidence20/10trước audit vẫn giữ nguyên và đọc theo scope riêng.

Final Atlas counts/fingerprint trở về baseline trên; collection options/validators/indexes exact unchanged so với private BSON backup,0invaliddocuments/0invariantfindings. Local dev fingerprint47d0aef...unchanged, đúng ownedstorage; local test7collections0. Không chạm storage/originalcheckout và không reset/reseed.8canonical pipeline files không thay.

Evidence `backend/evidence/full-audit-20261020-{tests,public,browser,deep-integrity,final-integrity,images}.json`, static receipt riêng; raw JUnit/failed fixture logs và exact backup chứa private data chỉ trong ignored `.local/review`. Không commit token/merchantsecret/signedcallback/rawDBexport. Các bộ browser E2E22/32/phase07A trước đây không được rerun nguyên runner trong audit này; không dùng chúng thay66HTTP và scopedbrowser mới.

## Giới hạn và việc người dùng cần làm

- Compass GUI:2Product khác ngành cùngcollection, Order embedded snapshot, import/export; rehearsal nhóm3SV5–10phút và offlineOS chưa có evidence người thật để đóng.
- VNPAY20/10 đã2realSandbox testcard/OTP→automaticIPN→ReturnPAID, có fullWebcheckout; formalSIT riêng chưa hoàn tất vì portal không hiện giao dịch/extraUIerrors. Không claim certification/tiền thật, refund tự động không thuộc scope.
- JS bundle khoảng930kB còn warning; audit0knownfindings không là bảo đảm security toàn sản phẩm. Không thêm code-splitting redesign chỉ để tắt warning.
- Không benchmark production/write throughput/pentest toàn diện hoặc chứng nhận SLA trong audit này. Renderexisting$7/mo cần người dùng suspend/delete khi hết demo.


Follow-up sau audit: bộ VNPAY SIT chính thức đã6/6Đạt, exactcleanup về479699...; xem [payment review](vnpay-sandbox-final-review.md#follow-up-cuối2010--official-sandbox-sit-66-pass). Dữ liệu demo/SKU/review và bản sao local được bàn giao riêng tại [handoff](defense-final-handoff-20261020.md); baseline audit bên trên giữ đúng thời điểm đã đo.
