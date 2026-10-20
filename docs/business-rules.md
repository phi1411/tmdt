# Quy tắc nghiệp vụ

Trạng thái hiện hành20/10/2026: extension SKU/reviews đã triển khai theo ADR013 (7collections/16declaredindexes), frontend/backend/Atlas đã public; VNPAY Sandbox đã realWeb/testOTP/automaticIPN scoped PASS theo ADR014. Các đoạn v1/phase02 bên dưới giữ lịch sử; đọc cùng phần cập nhật cuối file và [review hiện hành](full-project-audit-20261020.md).

**LOCKED DESIGN v1 — PHASE02**, giữ nguyên qua backend05A Auth/User,05B Catalog và05C Commerce COD. Trạng thái implementation/evidence từng feature tại [API contract](api-contract.md), [review05C](phase-05c-review.md); VNPAY/Admin Orders/Dashboard/Frontend còn deferred theo phase. Đây là nguồn chuẩn behavior; exact shape ở database/validators, defaults/limits ở [foundation-decisions](foundation-decisions.md). Feature docs tham chiếu BR-* thay vì tự chọn rule.

## BR-AUTH — phân quyền và tài khoản

Guest không đăng nhập. Customer chỉ dùng dữ liệu của mình; Admin quản lý/thống kê. Register không nhận role, status hoặc tokenVersion. JWT xác minh signature/algorithm/exp/issuer/audience, subject ObjectId hợp lệ; role/status hiện hành lấy từ User. BLOCKED hoặc tokenVersion cũ →401. Quyền Admin thiếu →403, tài nguyên User khác →404 để không lộ tồn tại. Admin không tự checkout thay Customer trong baseline; API purchase chỉ Customer. Không cho khóa/demote Admin cuối cùng.

## BR-CATALOG — danh mục và sản phẩm

ProductType phải khớp Category. Product ACTIVE và Category ACTIVE mới được browse/checkout. SKU/slug unique cả archived; SKU immutable sau create. DELETE Product = archive; không xóa snapshot. DELETE Category chỉ khi không có bất kỳ Product reference; còn reference →409, muốn ẩn dùng archive. Rename không đổi snapshot cũ. Mọi Admin update Product phải có expectedVersion condition; chỉ patch các fields được phép, không ghi đè stock từ document stale sau checkout. Mọi mutation stock/metadata tăng Product.version.

Để giải quyết race Category archive/delete với Product creation/checkout: mọi transaction phụ thuộc Category làm guarded `$inc: {version: 1}` và cập nhật updatedAt Category đang ACTIVE, gồm create/move/publish Product và checkout. Archive/delete cũng ghi cùng Category nên xung đột được retry và revalidate. Dùng increment thực thay vì set timestamp có thể cùng mili-giây để chắc có write. Điều này hy sinh concurrency của danh mục để có invariant rõ trong phạm vi đồ án; Admin phải refresh expectedVersion sau checkout liên quan.

## BR-CART — Cart và giá

Backend là source of truth. Thêm/sửa cần Product tồn tại, ACTIVE, Category ACTIVE, số nguyên quantity >=1, selection hợp lệ, và tổng quantity của **mọi dòng cùng productId** không vượt stock. Cùng Product/canonical selection gộp dòng; legacy selections dùng pool Product, matrix SKU dùng kho SKU riêng đồng thời giữ root tổng. POST add canonicalize skuId optional và gộp alias trước giới hạn99. Cart không giữ hàng; tồn có thể thay đổi sau add.

Client chỉ gửi productId/quantity/selectedAttributes/cartVersion; gửi price/lineTotal bị 422. Response Cart dùng field version; request dùng cartVersion để phân biệt với Product.version. GET Cart lấy currentPrice từ Product, đánh dấu missing/inactive/out-of-stock nhưng không tự xóa item. Stale version →409. Fashion: nếu Product có sizes/colors không rỗng, yêu cầu size/color thuộc danh sách; không nhận tùy chọn lạ hay full attributes tự khai.

## BR-CHECKOUT — báo giá và giao dịch

1. Customer active, Cart đúng owner và cartVersion, không rỗng; addressId thuộc User.
2. `GET /checkout/quote?addressId=...&paymentMethod=COD|VNPAY` trả cartVersion, server-price items, fees/totals, quoteToken/expiry và issues; không tạo Order/giữ stock. Quote hết hiệu lực khi dữ liệu sống đổi.
3. `POST /orders` gửi cartVersion/addressId/paymentMethod/quoteToken và Idempotency-Key; không gửi tổng/giá. Trong transaction: revalidate User/Cart/Category/Product, cộng quantity theo productId, conditional decrement (`stock >= tổng quantity`, ACTIVE) **từng Product** và tăng Product.version, copy snapshot, insert Order (+ attempt nếu VNPAY), clear items, giữ Cart document và tăng đúng version rồi commit.
4. Client phải được báo 409 `PRICE_CHANGED` nếu Product price/selection khác báo giá **đã xác nhận**. Implementation cần server-issued `quoteToken`/quote fingerprint đã ký trong response quote và POST; token gắn user/cartVersion/addressId/addressHash/paymentMethod, giá/fee, TTL cấu hình, không cho client tự tạo hoặc sửa. addressHash là hash canonical fields địa chỉ đã thấy; address sửa cùng ID sau quote →409 `QUOTE_CHANGED`, yêu cầu quote mới. Reprice và so với token ở checkout; 409 cần quote mới và người dùng xác nhận lại. TTL quote đã khóa5phút theo foundation-decisions. Hợp đồng quoteToken là bắt buộc để không âm thầm đổi số tiền khách vừa thấy.
5. Retry transaction theo driver hữu hạn. Mọi operation cùng session; failure bất kỳ rollback toàn bộ. Không gọi VNPAY bên trong callback transaction.
6. Sau commit trả Order và thanh toán COD hoặc link adapter VNPAY. Mất response dùng lại cùng Idempotency-Key để trả Order cũ, không trừ stock thêm. Link VNPAY lỗi không rollback Order đã commit; retry tạo URL cho cùng attempt.

Hash idempotency gồm request intent `cartVersion,addressId,paymentMethod,quoteToken`; check Order existing trước đọc Cart hiện tại. Replay cùng key/hash trả cùng kết quả ngay cả khi Cart đã clear hoặc quote đã hết hạn; khác hash →409. Body mới phải có key mới; UI không sinh key mới mỗi retry network.

Tổng: `lineTotal = priceAtPurchase × quantity`; `subtotal = ΣlineTotal`; `discount` tính theo BR-COUPON/ADR015 (v1 trước đây bằng0); `total=subtotal-discount+shippingFee`. Không có VAT riêng; ship flat default30000 VND cấu hình server, quote phải nêu rõ. VNPAY cap9.999.999.999 VND (amount×100 có tối đa12chữ số) reject trước khi trừ kho; COD dùng cap Order5e12. Không client override phí. Mọi tiền integer VND, không negative, không overflow.

## BR-ORDER — trạng thái, trả hàng và snapshot

| Từ → đến | Ai/khi nào | Hiệu ứng |
| --- | --- | --- |
| create → PENDING | Customer checkout | Trừ stock/giữ hàng; COD UNPAID, VNPAY PENDING |
| PENDING → CONFIRMED | Admin với COD; IPN hợp lệ với VNPAY | VNPAY phải PAID; COD vẫn UNPAID |
| CONFIRMED → SHIPPING | Admin | VNPAY bắt buộc PAID |
| SHIPPING → COMPLETED | Admin xác nhận giao/thu tiền | COD UNPAID→PAID; paidAt, completedAt được set; VNPAY đã PAID |
| PENDING/CONFIRMED → CANCELLED | Customer owner hoặc Admin, chỉ chưa PAID/REVIEW_REQUIRED | Trả stock đúng một lần; COD giữ UNPAID, VNPAY→FAILED; invalidate pending attempt→EXPIRED |
| PENDING → EXPIRED | Server expiry VNPAY chưa trả tiền | Trả stock đúng một lần, paymentStatus→FAILED, pending attempt→EXPIRED |

COMPLETED/CANCELLED/EXPIRED là terminal trong baseline. Không nhảy trạng thái, không hoàn tiền tự động, không hủy SHIPPING/COMPLETED hoặc PAID. Admin không tùy ý set paymentStatus=PAID cho VNPAY. Một orderStatus transition dùng expectedVersion và predicate status hiện hành; cập nhật + trả stock trong cùng transaction. `stockReleasedAt` là marker để không trả kho hai lần. Không dùng TTL index xóa Order/attempt để làm expiry; explicit expiry task có thể chạy lặp an toàn, expiry worker contract mỗi30giây và hold15phút tại foundation-decisions; implementation worker thuộc phasePayment. Không thêm PROCESSING trong MVP vì CONFIRMED→SHIPPING đủ workflow; EXPIRED chỉ online hold timeout, không stage giao vận.

Snapshot customer/address/items/totals không sửa sau checkout. Không có endpoint đổi địa chỉ/sản phẩm của Order; chỉ hủy và đặt lại nếu rule cho phép. Product archived vẫn tồn tại để trả kho; Category rename/archive không ảnh hưởng lịch sử.

## BR-PAYMENT — COD và VNPAY

COD: đặt đơn UNPAID, chỉ chuyển PAID cùng COMPLETED. VNPAY: ký server secret, amount từ Order.total nhân 100 theo contract provider; tx reference unique cho từng attempt. Xác minh chữ ký, merchant code, amount, txnRef và cả response/transaction status. ReturnUrl chỉ hiển thị/poll API; không tin query string từ browser để đổi Order. IPN server đã xác minh mới cập nhật attempt/Order, idempotent khi callback lặp. [VNPAY contract chính thức](https://sandbox.vnpayment.vn/apis/docs/thanh-toan-pay/pay.html).

VNPAY failure hợp lệ: attempt→FAILED, Order giữ PENDING và paymentStatus→FAILED, stock giữ đến deadline; retry tạo attempt mới→PENDING và tăng Order.version, không kéo dài deadline. Một Order chỉ có một attempt PENDING qua partial unique index. Capture verifiedAt UTC một lần trước transaction retry; providerPaidAt nếu có phải parse GMT+7 hợp lệ, nếu không có thì dùng verifiedAt làm paidAt/deadline guard. IPN success cần cả hai code00; txnRef/amount/merchant đúng, duplicate query keys bị reject trước ký/xử lý.

IPN response đã khóa: HTTP200 provider envelope {RspCode,Message};00 sau commit ghi nhận lần đầu (kể cả record review),02 nếu callback đã ghi nhận,01 unknown reference,04 amount mismatch,97 signature/merchant invalid,99 DB/internal failure để provider retry. Không trả00/02 trước commit. OrderInfo server tạo chữ/số/khoảng trắng, không dấu; ReturnUrl<=255 ký tự; HMAC-SHA512 canonical sorted URL-encoded params. Đây là adapter contract, chưa có handler chạy.

Callback success cạnh tranh với cancel/expiry phải serial bằng transaction và state predicate. Nếu cancel/expiry thắng, callback success vẫn ghi nhận tiền thực nhận ở attempt nhưng **Order.paymentStatus=REVIEW_REQUIRED**, `paymentReviewRequired=true`, không hồi sinh Order/trừ kho/ghi doanh thu. Manual reconciliation được Admin phụ trách ngoài ứng dụng; refund API/automation DEFERRED. Callback success chỉ tự confirm trước deadline và providerPaidAt không muộn deadline; nếu callback tới sau deadline thì expire/restore kho nếu cần trong cùng transaction rồi review, không phụ thuộc worker đã chạy hay chưa. Không coi FAILED/CANCELLED là chưa nhận tiền khi đã có callback success hợp lệ. Callback failure sau success không downgrade. Retry payment: chỉ Order PENDING còn trong paymentExpiresAt, chưa PAID, không có attempt PENDING còn hiệu lực; success của bất cứ attempt phải qua guard paymentStatus. Nếu Order đã PAID mà một txn khác cũng success: attempt mới REVIEW_REQUIRED và Order.paymentReviewRequired=true nhưng **giữ Order.paymentStatus=PAID và orderStatus**, để doanh thu hợp lệ trước đó không bị mất/cộng lần hai. Duplicate callback cùng txn không phải thu tiền lần hai và không bật review flag.

## BR-REPORT — định nghĩa metric

Định nghĩa đã khóa theo [ADR007](decisions/007-revenue-definition.md). Không cộng mọi Order. COD hoàn tất giao/thu tiền mới qualify; VNPAY IPN PAID trước giao chưa qualify, chỉ COMPLETED mới vào doanh thu.

- **Qualified sale:** `orderStatus=COMPLETED AND paymentStatus=PAID`.
- **Revenue:** `subtotal-discount` của qualified sales, **không gồm shipping**, VND. Baseline discount=0 nên bằng ΣlineTotal. Total collected (gồm ship) nếu hiển thị phải là metric khác.
- Revenue by Day/Month và Top 5/Category: cùng filter `[from,to)` trên **completedAt**, group timezone `Asia/Ho_Chi_Minh`. Input ngày UI là giờ Việt Nam; server chuyển boundaries sang UTC.
- Total Orders + Order Status Distribution: tất cả Orders tạo trong `[from,to)` theo **createdAt**, có cả cancelled/expired; mô tả nhãn rõ để không hiểu là cùng cohort Revenue.
- Total Products Sold: Σitems.quantity của qualified sales trong khoảng completedAt; không count số dòng.
- Total Customers: số User role CUSTOMER hiện tại (gồm BLOCKED), global, không phụ thuộc khoảng ngày. Không hiểu là khách đã mua/khách mới.
- Top 5: group theo productId, rank quantity desc → item revenue desc → productId asc; nhãn từ snapshot gần nhất trong tập qualified, không lookup Product.
- Category revenue: categoryId snapshot; nhãn từ snapshot gần nhất. Rename Category không chia hai nhóm cùng ID.
- Không có dữ liệu → metric 0, Top 5=[], series ngày/tháng hiển thị bucket 0. Backend được điền bucket trống sau aggregation, không tải Orders để tính.

Aggregation có unwind phải cộng tiền từng item. Không sum order.total sau unwind (sẽ nhân số dòng) hoặc đếm số Order bằng số item. Refund/discount allocation nếu bổ sung phải đổi metric contract + ADR trước implementation.


## Cập nhật19/10/2026 — ADR013

SKU/reviews đã được người dùng yêu cầu hoàn thiện sau integration review. Product optional tierVariations/skus, root price=minSKUprice/stock=sumSKUstock; legacy không matrix giữ behavior cũ. Exact selection/SKU binding, stock reservation/restore theo SKU và Product trong cùng transaction; snapshot selectedAttributes.skuId/price immutable. Admin CRUD hỗ trợ ma trận, guard SKU_IN_USE khi đổi identity có đơn giữ kho. Reviews là collection thứ7, unique User/Order/Product, verified COMPLETED+PAID và atomic ratingSummary; public privacy/pagination/filter. Nguồn cập nhật: decisions/013-sku-review-hardening.md, features/reviews.md và mục SKU/Reviews của api-contract.md; các ghi chú DEFERRED hoặc pool Product-only trước đó là lịch sử v1, không phủ định extension này. Không đổi doanh thu/canonical pipelines hoặc Order snapshot cũ. Ghi chú lựa chọn COD trước/VNPAY disabled ở19/10 đã được thay bằng config enabled và rehearsal Sandbox20/10; xem payment-setup và vnpay-sandbox-final-review.


## BR-COUPON — mã giảm giá giỏ hàng (ADR015)

Theo yêu cầu20/10/2026, bổ sung NOVA25: từ500.000đ tiền hàng hợp lệ giảm25%, tối đa50.000đ/đơn, không giảm phí giao hàng. Không cộng dồn mã, chưa giới hạn lượt hoặc quản trị chiến dịch. Chưa biết giá vốn nên chỉ giới hạn mức giảm, không bảo đảm lợi nhuận. Ô mã trên cổng VNPAY do provider quản lý; mã Novamart nhập tại Cart, dùng được cả COD/VNPAY.

Cart lưu couponCode tùy chọn, mutation CAS tăngversion; quote/checkout tính lại và ký pricing snapshot. Giỏ không còn đủ điều kiện phải bỏ mã hoặc điều chỉnh, không âm thầm đặt giá khác. Order lưu coupon snapshot và item.discountAllocated; chia theo lineTotal bằng phần nguyên/largest remainder, tổng chính xác bằng discount, không float. Top Product/Category tính lineTotal-discountAllocated, fallback0 cho lịch sử; Summary/ngày/tháng vẫn subtotal-discount. Phí giao hàng không là doanh thu hàng hóa. Clear/checkout bỏ mã cùng transaction/CAS, replay không áp giảm thêm lần nữa. Các phát biểu discount0 ở evidence trước đây chỉ mô tả baseline lúc đó.
