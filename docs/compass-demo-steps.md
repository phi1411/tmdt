# Compass — thao tác bảo vệ NovaMart

Cho SV3 điều khiển, SV1/SV2 giải thích. Máy đã có Compass1.49.15; bước Documents/Filter, Aggregations/Text/Run và Explain tham chiếu [MongoDB query](https://www.mongodb.com/docs/compass/query/filter/), [pipeline editor](https://www.mongodb.com/docs/compass/create-agg-pipeline/), [Explain](https://www.mongodb.com/docs/compass/query-plan/). Native helper hiện không chụp/điều khiển cửa sổ được; các bước này **cần nhóm chạy thử GUI và tick trước buổi bảo vệ**, không phải evidence GUI đã PASS.

## 1. Kết nối đúng local

1. Mở **MongoDB Compass**. Không chọn saved Atlas connection hoặc RESTART để update sát giờ demo.
2. Click **Add new connection** ở Welcome hoặc dấu+ bên CONNECTIONS.
3. Trong ô **URI / Connection String**, thay bằng `mongodb://localhost:27017/?replicaSet=rs0`.
4. Nếu có Name, nhập `NovaMart local rs0`; click **Connect**. Nếu muốn lưu favorite, dùng Save & Connect với URI local không credentials.
5. Ở sidebar, mở rộng connection local, click **ecommerce_dev**. Không chọn ecommerce_test (worker riêng), ecommerce_roundtrip hoặc database benchmark để xem nghiệp vụ.
6. Mở sẵn products và orders thành hai workspace tabs nếu UI có nút+; một cửa sổ duy nhất vẫn đủ, click collection trong sidebar để chuyển. Không Insert/Edit/Delete document trong Compass; mọi nghiệp vụ ghi qua API/Web.

## 2. Ba document Polymorphic

1. Click **products → Documents**.
2. Click ô **Filter**, chọn hết nội dung, paste:

```javascript
{sku: {$in: ["DEMO-ELE-001", "DEMO-FAS-001", "DEMO-HOM-019"]}}
```

3. Click **Find**. Phải có3documents; nếu đang có limit cũ khác, mở **Options**, đặt Limit3 hoặc bỏ limit.
4. Chọn **List view** hoặc **JSON view** ở vùng Documents. Với List view, click mũi tên cạnh `attributes` và `images` để mở nested fields; không click pencil Edit.
5. Chỉ sáu field chung `name,price,categoryId,productType,stock,images` ở cả3document.
6. Điện tử `DEMO-ELE-001`: mở attributes ram8GB/storage256GB/chipDemo CPU A. Thời trang `DEMO-FAS-001`: sizesS/M/L/XL, colorsBlue/White/Black, materialCotton. Gia dụng **DEMO-HOM-019 Hand Blender**: power800W/capacity1L/voltage220V. Không chọn DEMO-HOM-001 (giường, có bộ thuộc tính khác).
7. Nếu cần cho xem validator, mở tab **Validation**, chỉ discriminator/oneOf và money BSONlong; không sửa/lưu validation rule.

Lời nói20giây: “Ba ngành cùng collection products, dùng productType để chọn cấu trúc attributes. Các field bán hàng vẫn chung, nhưng RAM của điện tử khác sizes/colors của thời trang và power/voltage của gia dụng. Đây là Polymorphic Schema có validator, không phải JSON tùy tiện.”

## 3. Tìm Order vừa đặt và chứng minh snapshot

1. SV1 dùng Web Customer `defense07c@example.test` đặt COD hai fixture theo [script5phút](demo-script-5min.md). Copy **orderCode** từ trang thành công/chi tiết, không dùng seed Order rồi nói vừa đặt.
2. Compass sidebar click **orders → Documents**; bỏ filter/sort/limit cũ.
3. Paste `{orderCode: "MÃ_VỪA_COPY_TỪ_WEB"}` vào Filter; thay bằng mã thật, click **Find**, phải đúng1document. Đây là placeholder cần điền tại demo, không có mã live được hardcode.
4. Mở `items` rồi item điện thoại. Chỉ `productId,productName,sku,priceAtPurchase,quantity,selectedAttributes,categoryId,categoryName,productType,lineTotal,attributesSnapshot`.
5. Mở item áo: selectedAttributes sizeM/colorBlack; giải thích SKU có một pool tồn chung, không quản lý stock riêng từng size.
6. Mở `customerSnapshot` và `shippingAddress`; là bản chụp lúc mua, không cần lookup User/Product để khôi phục hóa đơn.
7. Product riêng điện thoại có A=10.000.000VND; áo200.000VND, quantity1mỗi dòng; subtotal10.200.000, shipping30.000 theo cấu hình hiện tại, total10.230.000. Nếu shipping config khác, dùng **quote/Order thực**, không ép giá trị từ script.
8. SV1 chuyển Web Admin Product edit, đổi **chỉ price** điện thoại thành 12.000.000, lưu, không sửa stock/category/attributes. Giữ hai browser/profile Customer/Admin riêng; frontend hiện phục hồi token từ sessionStorage khi reload, nhưng khi token hết hạn phải login lại.
9. Trở lại Compass products, Filter `{sku:"DEFENSE-07C-ELE"}`, Find→price12.000.000. Trở lại orders, Find lại đúng orderCode→item.priceAtPurchase vẫn10.000.000 và lineTotal10.000.000; Web Customer mở lại đơn cũ vẫn giáA.
10. Sau khi đã trình bày: restore bằng Web price10.000.000 hoặc `prepare_defense.py restore`. Hủy đơn demo còn PENDING/CONFIRMED để trả kho; không sửa Order snapshot, không cộng stock thủ công. Nếu đã COMPLETED, restore giữ lịch sử/thực bán và không ép hủy.

Standby khi hết thời gian: lấy mã rehearsal API trong `database/evidence/phase07c-rehearse.json → snapshotProof.orderCode`. Đây là đơn COD **API rehearsal**, đã CANCELLED và Product đã restoreA; nói đúng nguồn, không gọi là Web checkout sống. Seed `DEMO-2026-0001` vẫn có historical10triệu/current12triệu, là bằng chứng seed dự phòng, không phải đơn vừa tạo.

## 4. Top5 và Revenue trong Aggregations

1. Chọn **orders**, click tab **Aggregations**; nếu có pipeline cũ, mở blank pipeline mới, không sửa pipeline được worker khác lưu.
2. Click toggle **</> Text** thay vì **{} Stages**.
3. Mở file `database/evidence/phase07c-top-products.compass.txt` bằng editor ngoài Compass, copy **toàn bộ array từ [ đến ]**, paste vào Text editor. File không có $merge/$out/write stages.
4. Click **Run** ở góc phải pipeline builder; không dựa vào Preview sample10documents làm final result. Nếu chỉ1stage khi paste, kiểm tra đang Text mode.
5. Mở **Output Options → Expand all fields** nếu muốn xem productId/productName/quantity/revenue. Phải5rows, top đầu quantity12 trong fixed seed window.
6. Chỉ `$match` COMPLETED+PAID/date completedAt; `$sort` đầu chọn nhãn snapshot mới nhất; `$unwind` tách items; `$group` theo productId; `$sort` quantity/revenue/ID; `$limit:5`; `$project` DTO. Không có $lookup Product.
7. Nếu cần Revenue, thay Text editor bằng `phase07c-revenue-day.compass.txt`, **Run**. $match lọc đúng sales; $group bucket ngày Asia/Ho_Chi_Minh và sum subtotal-discount; $sort theo bucket. Pipeline output là **raw populated buckets**, Dashboard có thêm bucket0 ở backend nên rowCount có thể khác.
8. Fixed seed range của hai file là `[2026-07-03T00:00:00Z,2026-10-01T00:00:00Z)`; revenue tổng10.103.259.022VND/434units. Dashboard **30ngày qua** dùng range khác, không so số tuyệt đối hai range. Muốn đối chiếu chính xác: Browser DevTools **Network → Fetch/XHR → /admin/dashboard/top-products → Payload/Query String Parameters**, copy from/to; thay hai ISODate ở $match cùng values và Run lại. Revenue dùng cùng range, cả hai timezone/dateBasis không đổi.
9. Có file Extended JSON `.ejson` để PyMongo/import, còn `.compass.txt` dùng ISODate cho editor shell syntax. Nếu bản Compass không nhận ISODate khi paste, dùng Stage view $match với Date theo parser của bản đó; tuyệt đối không để `$date` thành nested business object rồi gọi result0 là đúng.

## 5. Performance chính — dùng đúng evidence PHASE07B

PHASE07B đã bàn giao trong lúc chuẩn bị 07C: [review](phase-07b-performance-review.md), [BEFORE/AFTER và latency](evidence/performance/benchmark-summary.md). Dataset `ecommerce_benchmark` là synthetic 30.000 Product/10.000 Order riêng, không phải seed theo barem và không dùng checkout. 07C đã replay cùng query ở chế độ chỉ đọc, không chạy lại 720 latency samples hoặc tạo/drop index.

1. Sau phần snapshot/aggregation ở **ecommerce_dev**, click database **ecommerce_benchmark → products → Documents**. Nói rõ đang chuyển sang bộ dữ liệu benchmark; không nhầm hai DB.
2. Paste Filter:

```javascript
{status:"ACTIVE",productType:"ELECTRONICS",categoryId:ObjectId("9f279f9b19426a6a465cfd3a"),price:{$gte:2000000,$lte:5000000}}
```

3. **Options → Sort** `{price:1,_id:1}`, **Limit** `20` → **Find**. Đây là Product selector; full repository còn Category lookup/count/facet nên có chi phí khác.
4. Click **Indexes** để chỉ `ix_products_category_price`: status/category equality trước, rồi price/_id hỗ trợ range và stable sort. Quay **Documents → Explain → Visual Tree / Raw Output** để xem planner hiện tại.
5. Để chạy đúng projection và forced plans đã đo, mở **>_ MONGOSH / Open MongoDB Shell**, paste toàn file `database/evidence/phase07c-benchmark-index.mongodb.js`, Enter. File dùng `getSiblingDB("ecommerce_benchmark")` rõ ràng, chỉ explain; không có mutation.
6. Chỉ ba metric trong output: natural `nReturned=20, totalDocsExamined=30000, totalKeysExamined=0`; named `nReturned=20, totalDocsExamined=20, totalKeysExamined=20`. Plans COLLSCAN/SORT và IXSCAN/FETCH; ordered IDs bằng nhau trong receipt 07C.
7. Nói “không dùng index cho truy vấn” với natural hint; index vẫn tồn tại. **True pre-build** trước suitable read index là evidence 07B `before-index.json`, không giả rằng 07C vừa drop index; unique constraint indexes vẫn được giữ.
8. Nếu hỏi latency, mở bảng 07B: Category selector natural p50/p95 29,103/42,596 ms, named 1,200/3,077 ms; 5 warmups/30 samples mỗi mode, local warm cache. Không lấy selector làm latency HTTP hay frontend; full repository named đọc 96 document để count/page, không phải 20.
9. Nếu hỏi Dashboard performance, raw aggregation explain 07B dùng window 7 ngày với 152 qualified Order: scan 10.000 → 152, Revenue 7 rows/Top5 5 rows. Không trộn range này với seed window hay Dashboard 30 ngày của dev. Kết thúc performance quay về **ecommerce_dev** nếu còn xem nghiệp vụ.

## 6. Index dự phòng trên dev / executionStats

1. Click **products → Indexes**, chỉ compound `ix_products_category_price`; không drop/create index trong demo.
2. **Documents → Filter**:

```javascript
{categoryId:ObjectId("4ad126c3ebc4fb3918f084d4"),status:"ACTIVE",price:{$gte:1000000,$lte:20000000}}
```

3. Mở **Options**, Sort=`{price:1,_id:1}`, Limit=`10`; Find. Nếu dữ liệu/máy khác, lấy categoryId từ file current `phase07c-query-verification.json`, không dùng ID máy này một cách mù quáng.
4. Click **Explain** trong query bar (bản cũ có thể có tab Explain Plan). Chọn **Visual Tree**, mở node IXSCAN/FETCH và xem **Raw Output** cho executionStats. Planner unhinted không bị ép phải chọn index; đối chiếu current evidence trước buổi bảo vệ.
5. So sánh forced plans đáng tin nhất: mở **>_ MONGOSH / Open MongoDB Shell** ở thanh dưới Compass; paste file `database/evidence/phase07c-index.mongodb.js` rồi Enter. Nếu shell chưa enabled, không thay security/settings sát giờ: dùng saved raw evidence và thừa nhận shell chưa rehearsal.
6. File chỉ find/hint/explain; `hint({$natural:1})` ép **không dùng index cho query**, collection vẫn có index. Named hint ép **ix_products_category_price**; không có dropIndex.
7. Chỉ winningPlan và3chỉ số: natural COLLSCAN+SORT, nReturned10/docs182/keys0; indexed IXSCAN+FETCH+LIMIT, nReturned10/docs10/keys10 tại rehearsal07C.10orderedIDs hai run giống nhau. Đừng nói IXSCAN không đọc document: FETCH còn đọc10docs.
8. executionTimeMillis của các lần dev 07C là 0–1 ms; đây là độ phân giải millis/độ lớn dataset, không “vô hạn lần nhanh hơn”. Dev explain dùng khi không mở được benchmark; số 182/10 không trộn với 30.000/20 của PHASE07B. Dùng report 07B cho latency đã đo.

## Dấu hiệu dừng / fallback

Không kết nối local, không thấy6collections hoặc query khác kỳ vọng: dừng phần tương ứng, chạy checklist/compare artifact; không reset data. Compass không thao tác được trên máy bảo vệ: trình bày file raw explain/aggregation JSON, nói rõ fallback đã chạy PyMongo/API, không gọi là Compass live PASS. Giữ COD local làm luồng chính; VNPAY không bắt buộc khi LIVE SANDBOX BLOCKED.
