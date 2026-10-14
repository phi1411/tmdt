# Bằng chứng PHASE03

## Atlas demo upload —14/10/2026

`atlas-demo-upload.json`: **ATLAS_DATABASE_UPLOAD_PASS** theo yêu cầu người dùng, destinationnovamart_demo.42Users/5Categories/182Products/1Cart/101Orders/30Attempts;6canonicalvalidators14declared+6_id_indexes,canonicalBSONdocumentsequal,0orphans,sales-summary/revenue-day/top-productsoutputs equal. Inserttransaction snapshot/majoritycommit trênAtlasthật;localfullfingerprintunchanged,capturec526acf... Khôngreset/reseed/delete/drop/sampleDBwrite;credential/sourcebackupignored.local. [Review](../../docs/atlas-database-upload-review.md),[ADR011](../../docs/decisions/011-atlas-demo-database.md). Backend/Frontend publicdeploy chưa thực hiện.

## Follow-up07D —14/10/2026

`phase07d-fix-summary.json` và [review bản sửa](../../docs/phase-07d-price-editor-fix-review.md): form Admin ảnh rỗng đã sửa, Web đổiA→B/snapshot giữA khôngAPIfallback;11checks/147HTTP(1expected422)/0pageerror,strictbuildPASS,fullpytestmới658pass/0fail/error/skip. `phase07d-fix-browser.json`, `phase07d-fix-chart-visual.json`, `phase07d-fix-environment.json`, `phase07d-fix-queries.json`, `phase07d-fix-test-outcomes.json`, `phase07d-fix-integrity.json` là evidence mới riêng;dev/benchmark fingerprints unchanged,testempty,canonical schema/index/orphansPASS. Compass input geometry lỗi nên GUI/timing/offlineOS vẫnmanualpending,VNPAYliveblocked. Không ghi đè receipts07D12/10.

## Bổ sung PHASE07C — 08/10/2026

`phase07c-prepare.json` (12 HTTP checks), `phase07c-rehearse.json` (20 checks, snapshot A→B giữ A, hủy hoàn kho), `phase07c-check.json` (readiness) và `phase07c-query-verification.json` (4 canonical pipelines/5 Dashboard API/dev explain) là evidence mới. `phase07c-benchmark-query.json` replay read-only query PHASE07B trên database benchmark riêng 30.000/10.000; không đo lại latency hoặc sửa index. Các file `*.compass.txt`, `*.ejson`, `*-index.mongodb.js` dùng cho rehearsal, không có write stage/index mutation.

Live dev sau fixture: 42 User/5 Category/182 Product/1 Cart rỗng/101 Order/30 attempts; dữ liệu gốc 41 User giữ nguyên khi loại đúng fixture sở hữu. Đơn API rehearsal đã CANCELLED, Product riêng restore A và stock 20. Compass GUI và Web timed flow chưa được nghiệm thu vì native helper lỗi; xem [readiness](../../docs/phase-07c-demo-readiness.md), [evidence index](../../docs/defense-evidence-index.md). Bằng chứng PHASE03 bên dưới giữ nguyên là lịch sử.

Các JSON được công cụ sinh từ MongoDB thật, canonical Extended JSON để bảo toàn BSON. Không sửa tay để làm đẹp số liệu.

- `seed-manifest-ecommerce_dev.json`: anchor/RNG, nguồn từng Product và inventory reconciliation; chứng minh đọc Product từ MongoDB để tạo snapshot.
- `verification.json`: topology/version/counts, validator accepts/rejections,11 duplicate constraints, indexes thực, hash/invariant/snapshot checks và tổng doanh thu.
- `aggregation-results.json`: parameters/pipelines đã chạy và toàn bộ output8báo cáo.
- `explain-baseline.json`: raw executionStats của planner/natural/named index trên cùng query.
- `reproducibility.json`: hai content digests bằng nhau sau reset+seed, trừ hash password có salt ngẫu nhiên.
- `roundtrip-results.json`:180 Product/100 Order giữ nguyên BSON sau export/import slice riêng.
- `image-url-checks.json`: HEAD đại diện ba ngành đều200; không kiểm availability toàn bộ media.
- `demo-queries.mongodb.js`: queries sinh từ canonical pipeline với ISODate; chưa rehearsal mongosh/Compass shell.

Đọc [setup](../../docs/mongodb-setup.md) để chạy lại. Report chỉ là bằng chứng một lần chạy; `verify_database.py` kiểm trạng thái DB hiện tại. Phase02 report tĩnh vẫn là lịch sử riêng. Không có evidence API/frontend/VNPAY integration hay performance benchmark toàn diện.
