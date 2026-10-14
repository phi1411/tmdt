# Upload MongoDB Atlas —14/10/2026

**ATLAS DATABASE UPLOAD PASS.** Người dùng yêu cầu upload sau khi tạo Cluster0 và cung cấp kết nối. Database đích: **novamart_demo**, replica set được Atlas khám phá: atlas-uczcqo-shard-0. Migration theo [ADR-011](decisions/011-atlas-demo-database.md); không đổi schema ứng dụng hoặc kết nối local.

## Kết quả thực tế

| Collection | Local snapshot | Atlas | Canonical BSON documents |
| --- | ---: | ---: | --- |
| users |42|42|Equal|
| categories |5|5|Equal|
| products |182|182|Equal|
| carts |1|1|Equal|
| orders |101|101|Equal|
| payment_attempts |30|30|Equal|

Đây là corpus live hiện tại, gồm seed/tài khoản được giữ/fixture07C, không phải reseed mới hoặc dataset benchmark. Giữ nguyên ObjectId, BSONDateUTC, long tiềnVND, password hashes và embedded snapshots. Không đưa documents/passwordhash/address/credential vào public evidence.

Preflight thật: SRVDNS/ping/writablePRIMARY/logicalsessions PASS; database đích chưa có collection. Tạo6canonical validators strict/error và14declared+6_id_indexes, insert nguyên sáu collection trong **một transaction snapshot/majority đã commit** trên Atlas thật. Sau đó đọc lại đầy đủ để kiểm tra count/digest/canonical BSON từng collection; canonical schema/index audit PASS, mọi orphan/reference mismatch bằng0.

Chạy ba pipeline canonical trên cả nguồn/đích: sales-summary, revenue-day, top-products; outputs hoàn toàn bằng nhau. Không `$lookup` Product để tính lịch sử và không sửa timestamps hay giá snapshot.

Full fingerprint local trước/sau bằng nhau: `c526acf3e22d27355a14a876656ffb3377ed3fda69a116b7947e07616094ac5d`. Baseline migration được chụp từ dữ liệu hiện tại trước upload; không ghi đè baseline lịch sử07D. Dev không bị viết/reset/reseed; benchmark/test/sampleAtlas không phải target của script. Không drop/delete hoặc overwrite database có sẵn.

## Evidence và vận hành

[Receipt migration](../database/evidence/atlas-demo-upload.json); script `scripts/deploy/upload_atlas_database.py` mặc định dry-run, `--apply` mới ghi. Exact host/DB allowlist, private ownership journal/sourcebackup trước write; resume từ chối corpus khác hoặc dữ liệu đích không khớp. Source snapshot read-only transaction, destination insert transaction; không chạy seed/expiry worker.

Credential, journal và fullsourcebackup chỉ ở ignored `.local/atlas-upload/`; không in URIcredential, không commit/push. Local `.env` và application config giữ nguyên. Không cần chạy lại658pytest vì backend/application không sửa; các checks thật của migration được ghi trong receipt.

Trên Atlas: **Data Explorer → Refresh → novamart_demo** để xem sáu collections.

## Bước tiếp theo

**Chỉ DB đã lên cloud; Flask/React chưa được deploy.** Backend config hiện vẫn khóa localrs0, cần bổ sung cấu hình deployment cho Atlas cùng productionWSGI/Renderport,frontendAPI/SPA routes,environment riêng và kiểm thử publicCOD. Không coi việc uploadDB là nghiệm thu các bước này. VNPAY_ENABLEDfalse/liveSandboxBLOCKED giữ nguyên. Chưa commit/push hoặc tạo Render service trong task này.
