# PHASE 05C — Cart / Checkout / Orders backend

Ngày 07/10/2026. **PHASE05C Cart/Checkout COD/Orders backend hoàn thành, dừng để review.** Phạm vi Customer Commerce trên source đã tích hợp05AB: Cart, server quote, COD checkout, immutable Order history/detail và cancel. Không đổi schema/collections/validators/indexes/locks/dependencies; không triển khai Frontend, VNPAY gateway, Admin Orders/Dashboard/Reviews hoặc phase sau.

## API và hành vi

10 method/path dưới `/api/v1`, Bearer **CUSTOMER ACTIVE**:

| Nhóm | Endpoints |
| --- | --- |
| Cart (5) | GET /cart; POST /cart/items; PATCH /cart/items/:lineId; DELETE /cart/items/:lineId; DELETE /cart |
| Checkout (2) | GET /checkout/quote; POST /orders + Idempotency-Key |
| Orders (3) | GET /orders; GET /orders/:id; POST /orders/:id/cancel |

[API contract](api-contract.md) ghi đầy đủ payload, DTO, error, query/version/idempotency semantics. Không bắt client gửi owner/price/totals/state. Cart version0 virtual, first insert1, lazy unique-owner race409; mutations/clear/checkout giữ document và tăng version. SHA256 lineId canonical đúng locked design; cùng selection merge, tổng quantity các selection cùng Product dùng một stock pool. GET resolve giá/tên/slug/image/stock hiện tại, giữ dòng invalid+issues, subtotal available và checkoutAllowed false khi có issue/rỗng. Không persist snapshot/giá vào Cart.

Quote dùng phone hồ sơ hợp lệ và owned saved address; price/selection/stock/Category ACTIVE revalidate. ShippingFee30000 configurable, discount0, integer VND/long, quote TTL300s. HS256 audience/key riêng về domain từ JWT_SECRET, bind owner/cartVersion/address/hash/payment/full snapshot pricingHash/expiry. Không dùng placeholder QUOTE_SIGNING_SECRET lịch sử và không cần cài dependency mới. Reprice tăng/giảm/fee/selection/snapshot→PRICE_CHANGED409; sửa address cùng ID→QUOTE_CHANGED409, cần quote và xác nhận mới. Token sai422, expired409.

POST hash canonical nguyên request intent; existing Order cùng User/key được đọc trước Cart/quoteexpiry. Same key/hash200 trả Order hiện hành, khác intent409. Mất response/ambiguous commit503 client retry nguyên body/key; không tự sinh key mới. COD tạo PENDING/UNPAID/version1, payment `{method:"COD"}`, không attempt/paidAt/paymentExpiresAt. COD collection money/COMPLETED do Admin Orders phase sau quản lý.

Order history/detail chỉ đọc Order snapshot, không Product/User/Category lookup; owned queries chống IDOR404. Summary không chứa address PII. Filter6status/[from,to) createdAt UTC, pagination1/20/max100, latest createdAt/_id desc và Mongo facet count/items. Detail có customer/address/items/category/attributes/image/price snapshots; không lộ checkout key/hash.

## Transaction và tồn kho

CheckoutService là transaction owner; dùng **cùng** utility bounded `catalog_transaction`, primary/snapshot read concern và majority commit. Tối đa3 transaction attempts/3 commit attempts; UnknownTransactionCommitResult retry commit, không blind rerun callback; exhausted503. Không external side effect trong callback.

Trong một session: revalidate live User tokenVersion/role/status + Cart version + address + confirmed quote; group quantity/Product; guarded ACTIVE Category $inc version; conditional Product stock>=total quantity/status/version + $inc stock negative/version; insert snapshot Order; clear items/Cart.version+1 rồi commit. Các Category/Product được ghi theo thứ tự ID ổn định. Không read–trừ Python–save mù. Category write guard serialize với Catalog archive/delete. Admin expectedVersion phải refresh sau stock/Category guard writes.

Cancel transaction guard owner/expectedVersion/PENDING hoặc CONFIRMED/chưa PAID hoặc REVIEW_REQUIRED/no review flag/absence stockReleasedAt. Order→CANCELLED + cancelledAt/stockReleasedAt/version+1; $inc restore grouped Product quantities/version; invalidate pending attempts→EXPIRED cùng session. COD giữ UNPAID, online cancellation foundation giữ FAILED. CANCELLED replay200 không viết/restore lần nữa, EXPIRED/SHIPPING/COMPLETED reject409. Archived Product vẫn restore; missing Product/stock overflow/version-limit→STOCK_RESTORE_FAILED409, safe alert event và rollback toàn bộ.

## Snapshot và security verification

Test mua giá10000000, cập nhật12000000/tên/specification/image/archive, Category rename/archive, User name/phone/address xóa; Order đọc lại giữ nguyên **toàn bộ DTO**. Thử xóa Product/Category và chặn live-read repository cũng không ảnh hưởng history/detail. Tiền snapshot là BSON long; address không copy id/label. Cart current price và quote mới nhận giá tăng/giảm hiện tại; Order chỉ dùng giá server khi khách xác nhận lại.

Security tests chạy Guest401/Admin403/blocked401 trên cả10commerce endpoints; A không đọc/hủy Order B404, B không chỉnh/xóa line Cart A, address của B404. Reject mass assignment userId/price/total/state/paymentStatus, bool/float quantities/version, query operators/unknown/repeated filters, bad IDs, quote tamper/owner/address/version/expiry. Không fake callback, ReturnUrl hay thanh toán thành công.

## Evidence và kiểm tra thực chạy

Evidence cuối được ghi tại:

- [Commerce JUnit](../backend/evidence/phase05c-commerce-pytest.xml):126 tests, pass126, fail0/error0/skip0.
- [Full-suite JUnit](../backend/evidence/phase05c-pytest.xml):451 tests, pass451, fail0/error0/skip0; foundation80 + Auth/User133 + Catalog112 + Commerce126. Không chọn subset hoặc loại test cũ. Commerce và full suite chạy lại trên source cuối, SHA256 manifest trước/sau giữ nguyên.
- [HTTP/runtime/integrity](../backend/evidence/phase05c-runtime.json):38/38 checks qua listener HTTP thật current source, không Flask test client; login Customer/Admin thật→Product→Cart add/merge/update→quote→COD checkout→Cart clear/stock decreased→history/detail→live price/name/attributes change→snapshot unchanged→cancel/replay→stock restored. Test routes10blueprints/38method-path/0collision;10Commerce endpoints khớp API contract và3feature docs. Source manifest, runtime Python3.12.14/Flask3.1.3/PyMongo4.15.3/pytest9.1.1/MongoDB8.0.32/rs0 và full development fingerprint được lưu. Servers tạm shutdown/close sau smoke; thêm5checks trên server project5001: health200, Cart/Orders/quote guest401 (routes đã đăng ký), Catalog200.

Development fingerprint documents/options/validators/indexes trước/sau đều `3cb02b86dae359fe469356c818205b8ddc2e83768862d9f3c47776a79657c6a6`, khớp05AB/phase04; counts users40/categories3/products180/carts0/orders100/payment_attempts30. Sáu collections ecommerce_test rỗng sau full suite và HTTP cleanup. Không chỉ đối chiếu counts; không thay index/validator/seed/dev data. [Evidence index](../backend/evidence/README.md).

Commerce integration dùng MongoDB8.0.32 local rs0 thật, canonical validators/indexes đã có. Synchronization wrappers chỉ tạo race/fault, DB commit/rollback thực. Ca race: lazy Cart creation/CAS, stock1 hai Customer, checkout same key, Category archive thắng transaction, cancel twice/concurrent; fault item thứ2/Order insert/Cart clear/cancel restore thứ2/attempt invalidate. Ca response mất sau **real commit**→503 rồi retry200 chứng minh one Order/one stock decrement.

Chạy từ project PowerShell (không ghi đè evidence phase cũ):

```powershell
Push-Location backend
../.venv/Scripts/python.exe -m pytest tests/test_commerce.py -q --junitxml=evidence/phase05c-commerce-pytest.xml
../.venv/Scripts/python.exe -m pytest -q --junitxml=evidence/phase05c-pytest.xml
Pop-Location
./.venv/Scripts/python.exe -X utf8 scripts/backend/verify_commerce_runtime.py
```

Test marker xác minh project/ecommerce_test/localhost:27017/rs0, test fixtures exact own IDs/userIds/emails cleanup; không drop/reset/reseed. HTTP script từ chối test DB có data trước ghi. Dev baseline `.local/phase05c-before.json` chụp **trước implementation**, khớp immutable05AB và full documents/options/validators/indexes; giữ seed180Product/40User/100Order/3Category/0Cart/30attempts và6validators/14declared indexes.

## Files và dependency ảnh hưởng

- New APIs: `backend/app/api/cart.py`, `checkout.py`, `orders.py`; registry `api/__init__.py` thêm3blueprints, không sửa registration cũ.
- New services: `cart_service.py`, `checkout_service.py`, `order_service.py`, `commerce_pricing.py`; reuse `catalog_transaction.py`, không sửa utility/shared JWT/validation/errors/serialization.
- New repositories: `cart_repository.py`, `order_repository.py`, `payment_attempt_repository.py`; ProductRepository thêm find_many/conditional decrement/restore; UserRepository thêm session-aware active identity/profile checkout read. Không đổi CRUD/DTO contract Auth/Catalog.
- New schemas: `cart_schema.py`, `checkout_schema.py`, `order_schema.py`; config thêm fee/TTL validation và fixed online gate, `.env.example` bỏ unused quote secret placeholder.
- Tests: `backend/tests/test_commerce.py`; evidence verifier `scripts/backend/verify_commerce_runtime.py`, three phase05c evidence files; local baseline ignored.
- Docs: API contract, feature cart/checkout/orders, architecture, requirements status, backend setup/README, database-schema/business-rules status, testing strategy/evidence index, AGENTS và review này.

Workspace chưa có Git HEAD theo05AB, không tạo Git repo; runtime evidence lưu SHA256 source manifest.

## Giới hạn và điểm dừng

VNPAY **gateway/online Order+initial attempt/expiry worker deferred** theo Payment phase. Schema/enums/payload và cancellation attempt dependency giữ nguyên, nhưng VNPAY_ENABLED=false fixed; config bật bị từ chối startup, quote/new checkout online503 trước ghi. Đây là quyết định gate implementation để không tạo hold thiếu expiry/adapter, không sửa canonical data model. Không fake payment URL hoặc PAID. Existing owned online Order có thể đọc/cancel theo locked state policy; callback/expiry race chưa nghiệm thu.

Admin lifecycle CONFIRMED→SHIPPING→COMPLETED/thuCOD, Admin Orders/Dashboard/Frontend/Reviews, production deployment, load benchmark đều deferred. Không phát hiện runtime bug trong phạm vi đã kiểm tra; backend acceptance không suy ra full app/barem hoàn thành. Đã phát hiện server project5001 chạy source cũ (Cart/Orders404), xác minh command line đúng absolute backend/run.py trước khi restart đúng process project; giữ logs cũ trong ignored .local/backend. Server mới health200, Cart/Orders/quote guest401 và Catalog200, tiếp tục chạy cho review. HTTP mutation flow dùng ecommerce_test/temporary listeners và đóng sau kiểm tra; server dev không có mutation.

**Cart/Checkout COD/Orders backend hoàn thành. Không implement VNPAY gateway thật hoặc Frontend. Dừng PHASE05C để review; không bắt đầu phase tiếp theo.**
