# MongoDB performance — PHASE07B

Chạy từ workspace root, MongoDB local rs0 phải đang PRIMARY. Reuse `.venv` đã bootstrap cho backend/DB tooling, không dependency mới.

```powershell
./.venv/Scripts/python.exe -X utf8 scripts/performance/benchmark.py all
./.venv/Scripts/python.exe -X utf8 scripts/performance/verify_safety.py
```

`all` tạo hoặc verify/reuse BENCHMARK DATASET mặc định30.000Products/10.000Orders, rồi đo6query variants. `setup --products 50000 --orders 15000` chỉ setup; `run` chỉ đo dataset đã sở hữu. Default5warm-ups/30samples mỗi mode; modes true pre-build, natural, named index, planner unhinted. Runtime/shuffle/cursor materialization/explain/result hashes lưu đầy đủ.

True pre-build giữ11unique invariant indexes và `_id_`, chỉ bỏ3read indexes **trong ecommerce_benchmark** nếu đã có. Sau đó tạo3index đúng manifest: category-price/type-price/qualified-completed. Không thay dev indexes hoặc dữ liệu. Hai Product selections dùng query parser/sort/projection thật; hai full-api pipelines capture trực tiếp ProductRepository.list; Revenue/Top5 dùng DashboardRepository/canonical artifacts.

Kiểm chứng cleanup/re-setup và BSON reproducibility, đồng thời chạy lại toàn bộ phép đo:

```powershell
./.venv/Scripts/python.exe -X utf8 scripts/performance/benchmark.py reproduce
```

Giữ database benchmark sau lần nghiệm thu để dùng Compass07C. Cleanup tùy chọn khi không cần dataset nữa:

```powershell
./.venv/Scripts/python.exe -X utf8 scripts/performance/benchmark.py cleanup
```

Cleanup chỉ đúng6collections thuộc database literal `ecommerce_benchmark`, sau khi marker/workspace/topology/full BSON hashes/validators/index keys đều match. Evidence được giữ. Existing unmarked/foreign contents/indexes từ chối cleanup; không reset db khác. Exclusive `.local/performance/run.lock` chặn hai runner; sau crash chỉ gỡ lock khi PID đã dừng. Setup không bypass validators.

User/category/product/order đều synthetic, deterministic seed20261008/anchor2026-10-01. Sample User hash không phục vụ benchmark login; không copy dev credentials/PII. Orders COD gồm60%COMPLETED+PAID,10%mỗi PENDING/CONFIRMED/SHIPPING/CANCELLED; prices snapshots97%current, long VND, stock1000 trừ net reservations, refs/arithmetic được kiểm tra. Dataset này không là180Products/100Orders dummy data chính thức của đề.

[Review07B](../../docs/phase-07b-performance-review.md), [feature spec](../../docs/features/performance-benchmark.md), [evidence](../../docs/evidence/performance/README.md). Single-node/local/warm-cache/synthetic không chứng minh production/concurrency/write throughput; report chỉ mô tả các phép đo đã chạy.
