# Compass demo — hướng dẫn20/10/2026

Agent hiện chỉ điều khiển được browser, chưa thực hiện GUI Compass. PyMongo đã export/import và kiểm chứng thật; kết quả đó không thay bằng chứng thao tác GUI của SV3. Xem [bàn giao cuối](defense-final-handoff-20261020.md) và [checklist](pre-demo-checklist.md).

## 1. Chọn đúng môi trường

- **Local:** Add new connection → URI `mongodb://127.0.0.1:27017/?replicaSet=rs0` → Connect → **ecommerce_defense**. Dùng cùng Web http://127.0.0.1:5173 và API5000.
- **Public:** dùng Atlas URI private trong `.local/review/atlas-runtime-connection.json` → **novamart_demo**. Dùng cùng Web https://novamart-web.onrender.com. Không chiếu URI chứa mật khẩu.

Bản sao local độc lập từ20/10: đặt Order trên public sẽ không xuất hiện trong local. Không chọn sampleDB/benchmark/test hoặc import đè database nghiệp vụ.

Checkpoint hiện có7collections,7validators,16declared+7_id_indexes;44Users/6Categories/184Products/3Carts/102Orders/30Attempts/1Review. Counts có thể tăng sau demo hợp lệ. Guest là người chưa đăng nhập; User chỉ CUSTOMER/ADMIN.

## 2. Polymorphic và SKU

Products → Documents → Filter → Find:

```javascript
{sku:{$in:["DEMO-ELE-001","DEMO-FAS-001","DEMO-HOM-019"]}}
```

Mở attributes: điện tử có RAM/storage/chip; thời trang có sizes/colors/material; gia dụng có power/capacity/voltage. Cùng collection, discriminator productType và validator. Không chọn HOM-001 (giường) để khẳng định có power.

SKU demo:

```javascript
{sku:"DEFENSE-FINAL-SKU"}
```

Mở tierVariations/skus: M100.000/stock9, XL120.000/stock10; root price100.000/stock19 tại checkpoint. Đây là tồn riêng từng SKU. Fixture legacy07C không có matrix vẫn dùng pool Product; không áp quy tắc đó cho SKU demo mới.

## 3. Snapshot

Order chuẩn bị **qua API**, COMPLETED/PAID; không gọi là đơn Web vừa tạo:

```javascript
{orderCode:"ORD-6AD71662EC77AC8C719DAF03"}
```

Mở items/customerSnapshot/shippingAddress:2items100.000+50.000, subtotal150.000, ship30.000, total180.000. Products filter `{sku:"DEFENSE-FINAL-SNAPSHOT"}` có giá hiện60.000; Order vẫn giữ50.000.

Luồng live theo script5/10phút: giá hiện60.000 → checkout Order mới → Admin sửa70.000 → Order vẫn60.000. Filter bằng orderCode thật vừa copy từ Web. Sau proof restore riêng Product60.000; hủy đơn chưa hoàn thành qua Web, không cộng kho tay hoặc sửa Order trong Compass.

Reviews filter `{rating:4}`: reviewText có nhãn trình diễn, orderId trỏ đơn COMPLETED/PAID. Public API ẩn owner/order IDs và che tên.

## 4. Aggregation và index

Orders → Aggregations → Text mode → paste array Top5/Revenue → **Run**. Canonical pipelines ở `database/aggregations`. File Compass có sẵn: `database/evidence/phase07c-top-products.compass.txt` và `phase07c-revenue-day.compass.txt`.

Các file này dùng fixed seed window `[2026-07-03,2026-10-01)`:10.103.259.022VND/434units. Không so số tuyệt đối với Dashboard30ngày. Khi đối chiếu, lấy from/to trong Network của Dashboard rồi bind `$match.completedAt` bằng đúng hai Date đó. Không coi `$date` dạng object chưa parse là BSONDate.

Top5: match COMPLETED+PAID/date → sort nhãn snapshot → unwind items → group Product/quantity/lineTotal → sort → limit5 → project. Revenue dùng completedAt/dateTrunc Asia/Ho_Chi_Minh, sum subtotal-discount. Không shipping hoặc `$lookup` giá Product hiện tại. Không dùng preview sample làm kết quả đầy đủ.

Products → Indexes: xem `ix_products_category_price`. Explain query category/status/price, sort price/_id. Không drop/create index khi demo. [Evidence07B](phase-07b-performance-review.md) dùng benchmark riêng30.000Products/10.000Orders: cùng20kết quả, COLLSCAN30.000docs → IXSCAN20docs/20keys; full repository còn count/lookup/facet. Nếu máy này không có benchmark, mở raw receipt và nói rõ đó là evidence đã đo, không giả chạy live.

## 5. Compass Export/Import an toàn

Canonical Extended JSON đã chuẩn bị trong `.local/defense-final/compass-export/` gồm7JSON arrays và metadata. File chứa User hash/snapshot địa chỉ, chỉ giữ private.

1. Trong local `ecommerce_defense.products`, bỏ filter → Export Data → JSON → chọn Extended JSON/Canonical nếu bản Compass hỗ trợ. Lưu trong `.local`, không ghi đè seed/source. Kiểm tra `$oid`, `$date`, `$numberLong`.
2. Tạo database **mới, trống**, ví dụ `ecommerce_compass_import_20261020`, collection products. Nếu tên đã có dữ liệu, chọn tên mới; không xóa/replace collection cũ.
3. Add Data → Import JSON file → chọn products JSON array → Import. Làm tương tự với orders. Đây là slice kiểm chứng BSON/nesting, chưa có đủ references/validators/indexes để chạy ứng dụng.
4. Đối chiếu184Products/102Orders hoặc số thực trước export; mở ObjectId/Date/long và items nhúng. Không cho Flask kết nối DB slice này. Receipt PyMongo riêng đã xác minh full7collections/options/indexes.

Nếu Compass không có Canonical hoặc export làm mất kiểu, dùng file canonical đã chuẩn bị và nói rõ nguồn PyMongo. Không đánh dấu GUI export PASS nếu chỉ mở file. Nếu GUI lỗi, trình bày raw JSON/receipts và nói đúng fallback; không reset/reseed để làm check pass.

VNPAY Sandbox đã6/6SIT Đạt; gateway và ảnh CDN cần Internet. COD local không phụ thuộc gateway, nhưng chưa thay bằng chứng ngắt Internet toàn máy.
