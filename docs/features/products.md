# Product và Product Detail

**Trạng thái hiện hành20/10/2026:** API và giao diện của feature đã triển khai; các mốc phase/deferred bên dưới là lịch sử. Evidence tại [full audit](../full-project-audit-20261020.md) và [handoff](../defense-final-handoff-20261020.md). Không chạy lại toàn bộ UI suite trong lần đồng bộ tài liệu này.

## Goal

Catalogue đa ngành và contract Product dùng chung; CRUD/UI contract tại admin-products. P0; read API IMPLEMENTED PHASE05B, UI đã triển khai. [Contract](../api-contract.md), [review](../phase-05b-review.md).

## Actors

Guest/Customer xem; Admin quản trị bằng API riêng.

## Functional Requirements

List ACTIVE với Category ACTIVE, detail bằng slug, fields/ảnh/thuộc tính/tồn; backend Product CRUD service dùng Admin API. Search/filter doc sở hữu query behavior, admin-products sở hữu write endpoints tránh hai CRUD contract khác nhau.

## Business Rules

BR-CATALOG: một products collection, productType+attributes; categoryId reference đúng type. SKU/slug unique; Product legacy dùng stock/price chung selections. MatrixSKU theo ADR013 dùng giá và tồn riêng, rootprice=minSKUprice/rootstock=sumSKUstock; xem mục SKU/Reviews của API contract. Versioned patch, archive không hard-delete; price/tên đổi không sửa Order. Không check Category ACTIVE bằng field category snapshot stale.

## Permission

Public read ACTIVE và Category ACTIVE; inactive/archived detail404. Admin read mọi status/write qua `/admin/products`.

## API

| Method / path | Request | Response data | Error |
| --- | --- | --- | --- |
| GET /products | query theo search-filter | 200 Product cards + pagination | 400/422 |
| GET /products/:slug | slug | 200 detail{id,sku,name,price,stock,images,attributes,productType,categoryId,version,...} | 404 inactive/missing/category archived |

CRUD endpoints duy nhất ở admin-products; Product data không trả password/admin-only metadata hoặc giả định có Review.

List/detail dùng cùng DTO `{id,sku,name,slug,categoryId,category,productType,brand,description,price,stock,images,attributes,version,createdAt,updatedAt}`; category là `{id,name,slug,productType}` current, public không trả status/normalized fields/schemaVersion. Attributes trả nguyên object động hợp lệ; tiền numeric VND, timestamps UTC. Detail theo slug, không thêm alias theo id. Unknown query trên detail422. List count/pagination sau Category ACTIVE lookup, không paginate trước bước visibility guard.

## Data

Read products và categories current; write thông qua Admin service. Paths `api/products.py`, `services/product_service.py`, `repositories/product_repository.py`, `schemas/product_schema.py`; `features/products/`. Dependencies category read contract, search-filter; Cart chỉ cần Product-read dependency, không inspect payment/dashboard.

## Validation

Mongo polymorphic schema theo database-schema; price long integer positive/stock int>=0; attributes bounded/type-checked, no operator keys. Không buộc mọi Electronics có RAM. Fashion selection keys map sizes→size/colors→color.

## Edge Cases

No image fallback; stock0 vẫn xem được nhưng disable add; slug đổi link cũ404 (không tự thêm redirects); inactive category; Product archived sau khi Cart đã add. Price current có thể khác history.

## Security

Allowlist public projection; plain-text description; không HTML raw. Image là absoluteURL: HTTPS, HTTP chỉ localhost/127.0.0.1 dev, reject javascript/data/relative path; không backend fetch arbitrary URL. Search query xây server-side.

## UI Behavior

Cards VND/ảnh/tồn; detail render attributes theo nhóm và unknown approved key label; Fashion yêu cầu selections; login trước add nếu Guest. Loading/empty/404/error rõ, không pretend available khi API lỗi.

**Cập nhật UI 19/10/2026:** Size/màu/cấu hình là lựa chọn khi mua. Nút mua ở card và trang chi tiết mở `ProductPurchaseModal`; không hiển thị dãy nút phân loại thường trực trên trang hoặc bộ lọc danh mục. Modal dùng `tierVariations`/`skus` đã có; Fashion legacy dùng `attributes.sizes/colors` và sản phẩm thường vẫn mua được. Không tự chọn phân loại. Khách chọn đủ options và quantity rồi xác nhận; thiếu lựa chọn/SKU hết hàng thì disable xác nhận. SKU ID gửi cùng đúng tổ hợp được khớp; giá chỉ hiển thị theo dữ liệu API. Add thành công mới đóng, Mua ngay thành công chuyển tới Cart; lỗi giữ modal. Modal đóng được bằng nút/overlay/Escape, giữ focus, bố cục vừa màn hình mobile. Không đổi API/DB hoặc nghiệm thu các lỗi SKU backend đã ghi trong review17/10.

Dependency UI: `components/common/ProductPurchaseModal.tsx`, `utils/productSelection.ts`, `ProductCard.tsx`, `pages/ProductDetailPage.tsx`, CartContext hiện có.

## Acceptance Criteria

Ba nhóm cùng collection browse/detail đúng fields; status/category filter đúng; price/stock current từ backend; CRUD dùng contract Admin; Order cũ độc lập.

## Testing Checklist

- [x] Ba schema shapes/type mismatch, bounded unknown attributes, public projection.
- [x] ACTIVE/inactive category/stock0/unknown404, integer price BSON long/API numeric.
- [ ] Attributes render/selections và không HTML injection.


## Cập nhật19/10/2026 — ADR013

SKU/reviews đã được người dùng yêu cầu hoàn thiện sau integration review. Product optional tierVariations/skus, root price=minSKUprice/stock=sumSKUstock; legacy không matrix giữ behavior cũ. Exact selection/SKU binding, stock reservation/restore theo SKU và Product trong cùng transaction; snapshot selectedAttributes.skuId/price immutable. Admin CRUD hỗ trợ ma trận, guard SKU_IN_USE khi đổi identity có đơn giữ kho. Reviews là collection thứ7, unique User/Order/Product, verified COMPLETED+PAID và atomic ratingSummary; public privacy/pagination/filter. Nguồn cập nhật: decisions/013-sku-review-hardening.md, features/reviews.md và mục SKU/Reviews của api-contract.md; các ghi chú DEFERRED hoặc pool Product-only trước đó là lịch sử v1, không phủ định extension này. Không đổi doanh thu/canonical pipelines hoặc Order snapshot cũ. VNPAY disabled theo lựa chọn hiện hành.


Cập nhật21/10/2026: SKU có nhiều mức giá thì Card/Detail/modal chưa chọn hiển thị Từ + giá nhỏ nhất; chọn đủ tổ hợp thì modal hiển thị giá SKU chính xác. Admin nhập giá từng dòng qua bảng Phân loại, giá bán và tồn kho; attributes không tự tính giá. Không đổi API/schema, không tự chuyển sản phẩm legacy thành matrix. Kiểm chứng tại docs/variant-pricing-review.md.
