# Admin Product Management

## Goal

Giao diện/API CRUD Product và phối hợp Category, trọng tâm2.5đ CRUD. P0; API IMPLEMENTED PHASE05B, giao diện chưa làm. [Contract](../api-contract.md), [review](../phase-05b-review.md).

## Actors

ADMIN duy nhất có write permissions.

## Functional Requirements

List/detail all status, create, edit price/stock/metadata/attributes/category, activate/deactivate/archive Product. Category CRUD reused categories endpoints, không duplicate contract. Chưa upload media storage ngoài.

## Business Rules

BR-CATALOG: productType/category đúng, polymorphic attributes, SKU/slug unique, SKU immutable sau create, stock int>=0. Images absoluteURL-only theo foundation, no upload/cloud. ExpectedVersion + guarded patch không overwrite stock stale. Archive là DELETE hành vi logical; snapshot immutable. Chuyển category khác productType chỉ khi gửi attributes tương hợp cùng update được validate, không tự chuyển old attribute keys; guard Category write trong transaction.

## Permission

All `/admin/products*` ADMIN server guard; public/customer mutation bị403, Guest401.

## API

| Method / path | Request | Response data | Error |
| --- | --- | --- | --- |
| GET /admin/products | q?,categoryId?,status?,page/pageSize,sort? | 200 products/version + pagination | 401/403/422 |
| GET /admin/products/:id | id | 200 full editable Product | 404/401/403 |
| POST /admin/products | {sku,name,slug,categoryId,productType,brand,description,price,stock,images,attributes,status} | 201 Product | 409 duplicate/category;422 schema |
| PATCH /admin/products/:id | editable fields + expectedVersion | 200 Product | 404;409 stale/duplicate/category;422 |
| DELETE /admin/products/:id | {expectedVersion} | 204 archive | 404;409 stale |

Already archived DELETE no state change/stock side effect (204 nếu request hợp lệ/id hiện có), không hard-delete. PATCH archived chỉ reactivation bằng status ACTIVE với category ACTIVE/validator, không reuse SKU.

## Data

Read/write products; read/guard write categories; no Order write khi sửa giá. Paths `api/admin_products.py` → existing product service/repository/schema, category guard; frontend `features/admin-products/`, category form reused. Không tạo admin_product_repository trùng truy vấn Product nếu không có lý do.

## Validation

Required fields và price/stock/attributes schema, no body._id/timestamps; Category exists ACTIVE khi create/publish. Patch chỉ supplied fields; reject unknown, not replace whole DB document. URL HTTPS hoặc HTTP loopback dev, reject relative/javascript/data; no html description. nameNormalized/brandNormalized do backend derive theo ADR008, không nhận payload client. SKU PATCH reject422.

Request shapes lấy từ canonical categories/products validators qua catalog_schema request adapter, không sửa DB schema hoặc duy trì bản sao attributes khác. POST yêu cầu toàn bộ shared editable fields, status enum3 giá trị; Category create body riêng. PATCH attributes/images replacement toàn field, omitted fields giữ nguyên; đổi productType bắt buộc gửi attributes trong cùng request. ARCHIVED chỉ nhận PATCH status ACTIVE +expectedVersion. Version cap409 VERSION_LIMIT, category guard version cap409 CATEGORY_UNAVAILABLE. Mọi detail/mutation không nhận query; unknown422. JSON numbers nonfinite/outside BSON-range reject; images reject authority malformed/credentials. Description là plain text, UI phải escape khi render.

Category/Product guard transaction snapshot/majority, tối đa3 transaction attempts; unknown commit chỉ retry commit tối đa3, không replay writes khi outcome chưa rõ, trả503. Product price/stock patch với predicate version, không replace document. Checkout phải dùng cùng Category guarded write contract khi phase đó implement; phiên này không triển khai checkout/reservation.

## Edge Cases

Duplicate sku/slug, stale Product sau checkout decrement, category archived race, type/category chuyển, archive Product đang có Cart/Order. Cart báo unavailable; history giữ snapshot.

## Security

JWT Admin guards, allowlist mass assignment, arbitrary operators/URL scheme rejected. Không implement tải remote image server-side chưa có requirement.

## UI Behavior

Table search/filter/pagination, dynamic attributes form theo type, money integer, stock/version; preview ảnh/fallback, validation field errors, archive confirm. Conflict409 reload và yêu cầu xem lại thay đổi, không force overwrite.

PHASE07A hardening: form sửa Product giữ các attributes không có ô nhập, gồm known field chưa được form hỗ trợ và nested/unknown safe fields. Backend vẫn nhận attributes replacement theo contract; frontend merge thuộc tính gốc với các ô chỉnh sửa để việc đổi tên/giá không âm thầm xóa metadata đa hình.

Bộ lọc Category giới hạn chiều rộng theo container trên mobile, kể cả tên Category dài; bảng vẫn cuộn ngang bên trong vùng riêng, không làm toàn trang tràn ngang.

Follow-up07D ngày14/10/2026: ảnh là tùy chọn0–8 URL theo API contract. Form tạo/sửa cho phép textarea trống và gửi images=[]; không yêu cầu thêm ảnh để đổi giá. Chỉ loại dòng trắng, giữ URL đã nhập để backend báo lỗi validation thay vì âm thầm bỏ URL sai. Không thay validator hoặc dữ liệu fixture07C.

Pre-deploy14/10/2026: Brand cũng là tùy chọn theo contract (`brand` là string có thể empty). Bỏ required của ô Brand và không chặn submit khi brand trống; không bắt sửa metadata của60Product seed chỉ để lưu thay đổi khác. Backend validation/expectedVersion giữ nguyên.

## Acceptance Criteria

Create/read/update/archive Web/API cả3 ngành, Category integration đúng; snapshot price10→12 triệu vẫn giữ10; checkout/Admin concurrent không lost stock; permissions/validator đầy đủ.

## Testing Checklist

- [x] CRUD variants/unique/schema/category guard/role, actual validator/transaction rollback.
- [x] Patch price chỉ price, stale expectedVersion không overwrite stock; concurrent patch một success/một409.
- [x] Archive/repeat archive/reactivate/type move, dev/history fingerprint unchanged.
- [ ] Checkout stock race, Cart impact, dynamic forms/error states: thuộc phases sau.


## Cập nhật19/10/2026 — ADR013

SKU/reviews đã được người dùng yêu cầu hoàn thiện sau integration review. Product optional tierVariations/skus, root price=minSKUprice/stock=sumSKUstock; legacy không matrix giữ behavior cũ. Exact selection/SKU binding, stock reservation/restore theo SKU và Product trong cùng transaction; snapshot selectedAttributes.skuId/price immutable. Admin CRUD hỗ trợ ma trận, guard SKU_IN_USE khi đổi identity có đơn giữ kho. Reviews là collection thứ7, unique User/Order/Product, verified COMPLETED+PAID và atomic ratingSummary; public privacy/pagination/filter. Nguồn cập nhật: decisions/013-sku-review-hardening.md, features/reviews.md và mục SKU/Reviews của api-contract.md; các ghi chú DEFERRED hoặc pool Product-only trước đó là lịch sử v1, không phủ định extension này. Không đổi doanh thu/canonical pipelines hoặc Order snapshot cũ. VNPAY disabled theo lựa chọn hiện hành.


## Làm rõ giá theo phân loại21/10/2026

Theo yêu cầu người dùng: tận dụng ma trận SKU hiện có, không tách từng lựa chọn thành Product mới và không tự suy ra giá từ attributes. Admin thêm nhóm (Kích cỡ hoặc Dung lượng), nhập lựa chọn, cập nhật bảng rồi nhập giá/tồn từng tổ hợp. Label/helper cần phân biệt giá chung với giá thấp nhất và tổng kho tự tính; attributes vẫn là thông số mô tả. Khi SKU có nhiều giá, Catalog/Detail/modal chưa chọn hiển thị “Từ”; chọn đủ tổ hợp thì modal hiển thị giá chính xác. Không đổi request/schema/backend; sản phẩm legacy không có matrix dùng giá chung.

Acceptance: tạo sản phẩm M100k/XL120k bằng form, API/DB giữ hai giá long; chọn mỗi loại ở modal→giỏ→quote/Order giữ đúng giá; sửa giá SKU hiện tại không đổi snapshot cũ. Chạy SKU backend regression, strict/build và trình duyệt với fixture test riêng, cleanup exact IDs. Không tự gán giá/phân loại cho sản phẩm thật.
