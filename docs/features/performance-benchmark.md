# MongoDB performance benchmark — PHASE07B

## Goal

Tạo evidence MongoDB thật phục vụ barem: cùng query/kết quả, baseline COLLSCAN và compound-index IXSCAN, docs/keys examined và explain executionStats. Dataset lớn riêng, không sửa business application hoặc dữ liệu demo.

## Actors

Nhóm sinh viên chạy script local và dùng báo cáo để bảo vệ; không endpoint công khai.

## Functional Requirements

Sinh BENCHMARK DATASET reproducible: mặc định30.000Products/10.000Orders,30Categories/40Users synthetic, carts/payment_attempts rỗng. So sánh Product category/type price sort, Revenue day và Top5 canonical. Warm-up5/repeats30, lưu raw explains, result hashes, p50/p95 client monotonic latency, index audit/storage. Có setup/run/cleanup CLI, kiểm tra ownership và lock để tránh hai runner cùng ghi.

## Business Rules

Giữ BR-CATALOG/BR-REPORT và schema v1. Revenue chỉ COMPLETED+PAID/completedAt, subtotal-discount, không shipping/current Product lookup. Benchmark không mô phỏng checkout ledger hoặc gateway; synthetic stock không là nghiệm thu invariant giao dịch. Product query theo allowlist/sort của backend thật. Các comparisons cố định cùng dataset/filter/projection/sort/limit hoặc pipeline; không kết luận tốc độ từ seed180/100.

## Permission

Chỉ database literal `ecommerce_benchmark`, loopback27017/rs0 PRIMARY và private marker trỏ đúng workspace. Dev chỉ đọc fingerprint/audit. Không reset/reseed/drop index dev/test/roundtrip; cleanup benchmark chỉ đúng collections đã sở hữu và verified hashes.

## API

Không thay REST/API contract. CLI `scripts/performance/benchmark.py setup|run|all|cleanup|reproduce`, `--products`, `--orders` cho setup/all, `--warmups`, `--repeats` cho run/all/reproduce. Reproduce verified cleanup→setup cùng config→BSON hash equality→full measurements. Exit nonzero khi guard, validator, result equality, plan hoặc dev integrity fail. Evidence tại `docs/evidence/performance/`; chạy lại không cần thao tác MongoDB thủ công.

## Data

Source `scripts/performance/benchmark.py`, `perf_common.py`, `dataset.py`, `verify_safety.py`; reuse canonical samples/validators/index manifest từ database và backend ProductRepository/query schema/DashboardRepository. Direct dependencies PyMongo/bson/Flask runtime đã có, DB tooling normalization/ownership conventions và fingerprint helper. Deterministic seed/anchor/IDs/long money; synthetic Users không copy dev credential/PII, sample hash không phục vụ benchmark login. Tạo sáu collection cùng canonical validators; unique indexes chỉ benchmark, ba read indexes đo được. Full dev fingerprint before/after gồm docs/options/indexes; nguồn baseline là lúc bắt đầu07B, không tự ép lại historical40Users.

## Validation

Products10.000..50.000, Orders2.000..20.000; warmups>=3/repeats>=30. Insert không bypassDocumentValidation. Check counts/IDs/unique/type/money/timestamps/references/arithmetic, pipeline oracle và canonical hashes. Baseline giải thích rõ no suitable index trước build và natural hint sau build; indexed hint lẫn planner unhinted. Phân biệt cursor/root nReturned với final aggregation rows.

## Edge Cases

Existing unowned DB/marker mismatch/changed benchmark data/parallel runner→refuse write. Dataset đã setup thì verify manifest và reuse, không overwrite silently. Cleanup giữ evidence và private baseline, không xóa dữ liệu foreign. Dev thay đổi trong command fingerprint window→command fail; thay đổi ngoài window được ghi riêng, không revert thay người dùng/worker khác. Timings0ms/optimizer SBE/root group vẫn lưu raw tree, không giả định một explain shape.

## Security

Không secret/credentials/raw dev documents vào public evidence; source manifest hash, runtime host/version/topology/counts hợp lệ. Không network payment/CDN; localhost DB only. Lock/markers không cấp quyền reset một database khác.

## UI Behavior

Không frontend thay đổi. Báo cáo tiếng Việt, bảng BEFORE/AFTER dễ đọc, talk track30–60giây. Compass screenshots thuộc07C.

## Acceptance Criteria

Real MongoDB executionStats cho ít nhất hai Product queries, Revenue và Top5; COLLSCAN/IXSCAN assertions và equal results; canonical validators/schema/revenue/application source giữ nguyên; dev fingerprint unchanged trước/sau từng benchmark command. Shared dev changes sau phép đo được ghi riêng, không claim bất biến toàn phiên. Audit KEEP/CANDIDATE/REMOVE chỉ theo evidence, không tự apply/remove dev indexes. Báo rõ warm cache/synthetic/single-node/local timings và write/storage trade-off. Không claim toàn pipeline indexed.

## Testing Checklist

- [x] Setup validates/reproduces dataset and verifies ownership/ref/shape/money.
- [x] True before-index/natural/indexed/unhinted results equal; real explains and repeated latency.
- [x] Revenue/Top5 oracle and full Product repository pipeline equality.
- [x] Index audit/storage and dev fingerprint/source hashes unchanged.
- [x] Guard refusals/owned cleanup/re-setup roundtrip actually checked.
- [x] Review/evidence/talk track completed; stop for review.
