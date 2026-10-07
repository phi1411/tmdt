# Review PHASE 05B — Categories + Products + Search/Filter

Ngày07/10/2026. **Backend Catalog hoàn thành trong scope được giao; dừng để review.** PHASE04 đã duyệt. Phiên này không triển khai Auth/User, Cart/Checkout/Order/Payment/Dashboard hoặc Frontend; source/evidence Auth/User PHASE05A từ worker khác được giữ nguyên. Không tự bắt đầu phase sau.

## Phạm vi và dependencies

API→service→repository→MongoDB modular monolith; chỉ categories/products read/write. Dependency trực tiếp: app blueprint registration, JWT/current DB Admin guard và auth User projection, foundation validation/pagination/response/ID helpers, canonical category/product validators, search ADR008 và index ADR005/manifest. Không thêm collection/dependency/schema/index, không seed/reset dev. Request adapter đọc canonical validator trong project để tránh schema attributes bị lệch giữa API và DB.

Acceptance:14 method/path Category/Product public/Admin chạy thật; visibility theo Product/Category hiện hành; polymorphism3 ngành; MongoDB search/filter/sort/pagination; strict allowlist/type validation; role guards/version patch/transaction rollback và races; contract frontend dùng được. UI/full business app không thuộc acceptance phiên này.

## 1. Category endpoints

Prefix `/api/v1`. Public `GET /categories`, `GET /categories/:slug` chỉ ACTIVE. Admin `GET /admin/categories`, `GET /admin/categories/:id`, `POST /admin/categories`, `PATCH /admin/categories/:id`, `DELETE /admin/categories/:id`. Create mặc định ACTIVE, không parentId; patch versioned/archive/reactivate; hard-delete chỉ không có bất kỳ Product reference (kể cả archived), type change referenced409. Stable list `_id ASC`, page1/pageSize20/max100. Version cap409, no-op patch không có editable fields422.

## 2. Product endpoints

Public `GET /products`, `GET /products/:slug`; Admin `GET /admin/products`, `GET /admin/products/:id`, `POST /admin/products`, `PATCH /admin/products/:id`, `DELETE /admin/products/:id`. Public Product và Category đều ACTIVE; missing/hidden detail404. Admin đọc cả INACTIVE/ARCHIVED; DELETE logical archive, repeat archive204 không tăng version/đổi stock. Không có hard-delete Product.

DTO list/detail có id/sku/name/slug/categoryId/current category/productType/brand/description/price/stock/images/attributes/version/UTC timestamps; status chỉ Admin. Category resolve backend bằng lookup, không thay stored Product schema; normalized fields/schemaVersion không trả frontend. Giá API numeric VND, DB explicit BSON long. Images URL-only, không fetch/upload/download.

## 3. Search/filter/sort/pagination

`q` theo nameNormalized: NFKD/casefold/đ→d/remove combining marks/collapse spaces, escaped literal substring AND tokens, trim<=100/max8tokens; empty bỏ filter. Brand exact normalized. categoryId/productType/brand/minPrice/maxPrice/size/color/ram/capacity intersection. Price inclusive unsigned query integer0..1e9, min<=max. Fashion size/color membership; ram/capacity exact. Public status query422; Admin optional status enum3.

Sort locked `latest` (createdAt/_id DESC), `price_asc`, `price_desc` (price/_id cùng chiều), không newest/name_asc/raw Mongo sort. Pagination defaults1/20/max100, emptytotal0pages, out-of-range page[] giữ total. `$match/$sort` trước Category lookup; visibility guard trước `$facet` items/count nên không hụt page hoặc count hidden category. Python chỉ nhận page/metadata, không tải catalogue về lọc.

## 4. Polymorphic handling

Một products collection, productType ELECTRONICS/FASHION/HOME_APPLIANCE. API request shape derive từ canonical products.json/oneOf và bounded dynamic attributes, không tạo Electronics-only response/schema. Known fields optional, supplied fields type-check theo branch. Unknown safe scalar/array/nested object keys được hỗ trợ tối đa3 objectlevels/30keys/string bounds; finite BSON-range numeric. Không buộc tai nghe có RAM hoặc Fashion có Electronics keys. Test3 shapes roundtrip, invalid known types/keys/depth/bounds, dynamic extension và stock0 pass.

## 5. Admin CRUD và concurrency

Guest401/Customer403 ở mọi Admin list/detail/create/patch/delete, role hiện hành từ DB. SKU immutable; patch chỉ supplied fields và expectedVersion predicate, price-only không đổi stock/attributes; attributes/images replacement toàn field, omitted giữ nguyên. Type move bắt buộc gửi attributes tương hợp. ARCHIVED chỉ PATCH status ACTIVE +expectedVersion; Category ACTIVE trước publish. Không rewrite Order snapshot.

Create/move/publish Product guarded `$inc Category.version` trong cùng transaction; Category archive/delete/type change ghi cùng Category, kiểm tra refs trong transaction. Snapshot read concern/majority write concern, tối đa3 transaction attempts; unknown commit chỉ retry commit3lần, không replay uncertain writes (503). Duplicates rollback cả guard increment. Real rs0 tests dùng barrier cho create/move vs Category archive/delete, publish vs archive, Product concurrent patch (một200/một409). Checkout/stock reservation integration chưa implement, chỉ giữ guard contract cho phase đó.

## 6. Query/index usage

Giữ nguyên14 declared indexes đã apply từ PHASE03; không thêm/drop/rebuild index. Unique category slug/product sku+slug và `_id` lookup giữ invariant. Runtime explain trên dev read-only:

| Query | Unhinted behavior | Cursor evidence |
| --- | --- | --- |
| ACTIVE +categoryId +price>=1, price ASC/id ASC | FETCH→IXSCAN ix_products_category_price, Category lookup `_id_`; named hint cũng chạy |60 returned/60 docs/60 keys |
| ACTIVE +productType=FASHION +price>=1, price ASC/id ASC | SORT→FETCH residual type→IXSCAN ix_products_category_price; Category lookup `_id_` |60 returned/180 docs/180 keys |

`ix_products_type_price` đã có canonical candidate nhưng **DECLARED_NOT_APPLIED** trong14-index selection của PHASE03; không tự apply trong phiên này. Substring q/brand/attributes residual, không claim index tăng tốc mọi filter. Full natural-vs-hint benchmark/p50/p95/stress deferred.

**INDEX CANDIDATE (chưa thay canonical strategy/apply):** `(status ASC,createdAt DESC,_id DESC)` cho default public ACTIVE/latest; `(createdAt DESC,_id DESC)` cho Admin all-status/latest cần đánh giá độc lập sau. Reference check categoryId mọi Product status cũng cần đo trước cân nhắc standalone categoryId candidate vì category-price có status prefix. Dataset180 nhỏ, không kết luận speedup trước benchmark. Những đề xuất này là notes cho review/performance phase, không index đã được phê duyệt.

## 7. Tests và runtime evidence

Chạy full workspace bằng `.venv/Scripts/python.exe -m pytest --junitxml=evidence/phase05b-pytest.xml -q` từ backend: **325 passed,0 failures/errors/skipped**,71.79s. Trong đó106 API/real Mongo Catalog integration cases +6 bounded retry unit cases=**112 Catalog**;55 foundation +25 auth foundation +133 Auth/User của worker khác. Không nhận Auth/User implementation là thành quả phiên Catalog.

`scripts/backend/verify_catalog_runtime.py`:9 real HTTP checks qua temporary localhost WSGI server từ source hiện tại: health/public category/product list/detail và Admin read200, Guest POST401, Customer DELETE403. List mặc định20 trên180 Product ACTIVE; categories3. Script không ghi dev, server tạm được đóng; mutations CRUD đã được Flask API integration kiểm tra trên test DB thật. Không thay process server nền của phiên khác; cần restart process nguồn cũ trước demo persistent server.

Persistent server hiện tại cũng kiểm tra `GET http://127.0.0.1:5001/api/v1/products?pageSize=1`→200/total180 và detail unknown query→422; Catalog đang truy cập được tại [local API](http://127.0.0.1:5001/api/v1/products). Không cần restart process trong phiên Catalog.

Fingerprint **toàn bộ** documents của6collections/options/validators/indexes trùng immutable baseline PHASE04: `3cb02b86dae359fe469356c818205b8ddc2e83768862d9f3c47776a79657c6a6`. Dev vẫn180products/3categories/40users/100orders/30payment_attempts/0carts. Owned ecommerce_test Category/Product/User fixtures xóa đúng IDs, không reset/reseed/drop. Evidence [JUnit](../backend/evidence/phase05b-pytest.xml), [runtime/explain](../backend/evidence/phase05b-runtime.json), [index/evidence overview](../backend/evidence/README.md).

## 8. API contract/docs

[api-contract](api-contract.md) đánh dấu14 Catalog method/path IMPLEMENTED, đủ auth/query/body/DTO/envelope/error/bounds/mutation behavior và example payload. Các feature Category/Product/Search/Admin Product đánh dấu backend API implemented, UI/Checkout checklist chưa done. PHASE05A contract/source/evidence giữ nguyên. Setup/architecture/AGENTS/module map/testing strategy cập nhật scope.

## 9. Files thêm/sửa trong phiên Catalog

Source mới:

- `backend/app/api/categories.py`, `products.py`, `admin_products.py`.
- `backend/app/services/category_service.py`, `product_service.py`, `catalog_transaction.py`.
- `backend/app/repositories/category_repository.py`, `product_repository.py`.
- `backend/app/schemas/catalog_schema.py`, `category_schema.py`, `product_schema.py`.
- `backend/tests/test_catalog.py`, `test_catalog_transaction.py`.
- `scripts/backend/verify_catalog_runtime.py`.

Source integration sửa trực tiếp: `backend/app/api/__init__.py` (thêm3blueprints, giữ registration worker khác), `backend/app/__init__.py` và `backend/app/schemas/query_contract.py` (docstrings đúng trạng thái). Không sửa Auth/User logic/config/locks hoặc MongoDB artifacts.

Docs: `AGENTS.md`, `docs/architecture.md`, `docs/api-contract.md`, `docs/backend-setup.md`, `docs/testing-strategy.md`, `docs/features/categories.md`, `products.md`, `search-filter.md`, `admin-products.md`, `docs/phase-05b-review.md`, `backend/README.md`, `backend/evidence/README.md`.

Evidence mới: `backend/evidence/phase05b-pytest.xml`, `backend/evidence/phase05b-runtime.json`; không ghi đè phase04/05a evidence. Workspace hiện không có `.git`, nên đây là manifest phiên Catalog, không giả định git diff/commit đã được tạo.

## 10. Bugs/DEFERRED và điểm dừng

Không phát hiện bug Catalog qua checks đã chạy; không còn failed/skipped Catalog test. Deferred: Frontend/UI/E2E, checkout stock transaction/guard integration, Cart unavailable UX, Order/payment/dashboard APIs, full performance benchmark và index candidate review. Local HTTP smoke/real test DB là bằng chứng backend, không khẳng định toàn Web app đã DONE. Images URL-only, no media service/Atlas Search. **Dừng để người dùng review, không tự làm phase tiếp theo.**
