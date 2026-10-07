# Bằng chứng PHASE03

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
