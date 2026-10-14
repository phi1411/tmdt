# PHASE 06AB — DATABASE CLEANUP CHECKPOINT

Ngày 07/10/2026. **PHASE 06AB DATABASE INTEGRITY PASS.** Cleanup đã thực thi trên `ecommerce_dev` local rs0, có private backup và transaction snapshot/majority. Không reset/reseed, không sửa application logic, không làm feature/Frontend, không commit/push.

## 1. Identification và nguồn gốc

| Collection | Document chính xác | Kết luận / xử lý |
| --- | --- | --- |
| users | `6ac637d404fbb6846343e36a`, `khach_muy2lxi4@example.test` | Fixture E2E FE-01A; xóa 1 |
| carts | `6ac637e804fbb6846343e36c`, userId trên | Cart version3, items rỗng sau checkout; xóa 1 |
| orders | `6ac637f004fbb6846343e36e`, `ORD-6AC637F004FBB6846343E36E` | COD CANCELLED/UNPAID, version2; xóa 1 |
| payment_attempts | Không có theo userId hoặc orderId trên | Xóa 0; giữ cả 30 seed attempts |

Không xác định chỉ từ đuôi email `.test`. Bằng chứng cụ thể:

- [E2E runner](../frontend/tests/e2e-customer-verification.mjs:50) tạo email `khach_${Date.now().toString(36)}@example.test` cho khách demo.
- [E2E results](../frontend/tests/e2e-results.json:21) ghi đúng email; capturedOrder ghi đúng ID/code và total2029500VND. Flow đăng ký và hủy đơn qua POST/cancel200 đều PASS.
- [Review FE-01A](phase-fe-01a-integration-review.md:87) ghi cùng address/order ID, sản phẩm, quantity2, subtotal1999500 và COD cancellation.
- DB thực: User tạo12:15:16.251Z; Cart12:15:36.677Z; Order12:15:44.037Z; hủy/trả kho12:15:46.724Z ngày07/10/2026. Mốc này trùng phiên E2E phát sinh trong lúc checkpoint backend chạy. `stockReleasedAt=cancelledAt`; chưa nhận tiền, không review/provider attempt.

Đây là **artifact của Frontend FE-01A E2E cùng workspace, không phải fixture backend HTTP smoke06AB**; backend smoke ghi vào owned `ecommerce_test` và đã cleanup. Đủ bằng chứng là dữ liệu kiểm thử, nên yêu cầu hiện tại cho phép dọn mà không cần xóa/đụng đến các tài khoản khác. Chỉ đọc các artifact Frontend để đối chiếu nguồn gốc, không chạy hay sửa Frontend. SHA256 của các nguồn bằng chứng được lưu trong [cleanup evidence](../backend/evidence/phase06ab-db-cleanup.json).

## 2. Account giữ lại

`khachtest_1791374905461@example.test`, ID `6ac6363904fbb6846343e369`, được người dùng xác nhận chủ động tạo và yêu cầu giữ. Document giữ nguyên hoàn toàn trước/sau, gồm password hash/version/profile; public evidence chỉ ghi digest, không password hoặc hash thô. Account này không có Cart/Order/Payment Attempt liên quan.

## 3. Product/Category và tồn kho

Order chứa Product `fccf6cac7ecfce2486e5eb09`, SKU `DEMO-HOM-029`, quantity2, Category `7197a05f34d94cd99a58f60b`.

Stock đã được cancellation trả đủ và bằng seed inventory ledger: **97 trước/sau cleanup**. Không gọi cancel thêm, không tăng stock thêm2. Test để lại hai dấu vết metadata được đối chiếu source repository/seed manifest:

| Document | Trước cleanup | Sau cleanup |
| --- | --- | --- |
| Product trên | version4, updatedAt2026-10-07T12:15:46.724Z | version2, updatedAt2026-10-01T00:00:00Z |
| Category trên | version2, updatedAt2026-10-07T12:15:44.037Z | version1, updatedAt2026-07-02T00:00:00Z |

Checkout tăng Product.version và Category guard.version; cancellation tăng Product.version lần nữa. Đây là khôi phục đúng metadata trước fixture trên DB development trong housekeeping, không thay đổi rule version của application. Không sửa stock, price, attributes, snapshot hoặc các Product/Category khác. Phép tính cleanup trong memory khớp **toàn bộ** fingerprint baseline trước khi cho phép ghi, bảo đảm không che một thay đổi seed chưa nhận diện.

## 4. Thực thi và giới hạn ghi

[Script cleanup](../scripts/backend/cleanup_phase06ab_database.py) mặc định dry run; checkpoint đã chạy lần lượt:

```powershell
.venv/Scripts/python.exe scripts/backend/cleanup_phase06ab_database.py
.venv/Scripts/python.exe scripts/backend/cleanup_phase06ab_database.py --apply
```

Dry run PASS trước mutation. Script kiểm tra local writable rs0, ownership marker/project/DB, provenance E2E, liên kết chính xác, state/version/timestamps, stock ledger, schema/index canonical và projected fingerprint khớp baseline41Users. Private backup chỉ gồm 3 document xóa +2 document khôi phục tại ignored `.local/phase06ab-db-cleanup-backup.ejson`; không export toàn DB hoặc ghi credentials ra public evidence.

Một transaction readConcern=snapshot/writeConcern=majority kiểm tra full documents fingerprint chưa đổi, update đúng2metadata với version/updatedAt predicates, delete theo đúng3ObjectId. Kiểm tra fingerprint sau mutation ngay trong transaction trước commit; mismatch/assertion sẽ abort. Không delete_many, drop, collMod, rebuild index hoặc gọi seed. Baselines cũ và evidence06AB trước cleanup giữ nguyên. Script nhận diện trạng thái đã sạch và trả ALREADY_CLEAN/noWrites khi kiểm tra lại.

## 5. Counts và fingerprint sau cleanup

| Collection | Trước | Sau | Baseline phù hợp |
| --- | ---: | ---: | ---: |
| users | 42 | 41 | 40 seed +1 account được giữ |
| categories | 3 | 3 | 3 |
| products | 180 | 180 | 180 |
| carts | 1 | 0 | 0 |
| orders | 101 | 100 | 100 |
| payment_attempts | 30 | 30 | 30 |

Fingerprint bao gồm toàn bộ documents/counts của6collections, collection options/validators và indexes, không chỉ đếm document:

- Trước cleanup: `347c71bdc799e828bceeb197d9a9f3ea45624449a387aca239abb18538792f73`.
- Sau cleanup: **`f8c36f1872e7de3b42ae7e949e16e6f2a81fbdca20a24eeb3789033c358b50ce`**, khớp chính xác original `.local/phase06ab-before.json`, không ghi đè baseline.
- Chỉ loại account được giữ khỏi phép tính **trong memory**, fingerprint phần còn lại là `3cb02b86dae359fe469356c818205b8ddc2e83768862d9f3c47776a79657c6a6`, khớp historical seed/worker baseline40Users. Không xóa account đó trên DB.

Như vậy toàn bộ seed documents, options, validators, indexes còn nguyên; account được giữ là khác biệt có chủ ý duy nhất. Kết luận PASS là integrity sau cleanup với baseline phù hợp, không sửa lịch sử thành tuyên bố DB chưa từng có external writes trong phiên06AB.

## 6. Validators/indexes/orphans và source

- 6 validators khớp canonical JSON; validationLevel=strict/validationAction=error giữ nguyên.
- 14 declared/applied indexes +6 `_id_` giữ đúng names/key order/options, gồm unique/partial options theo canonical artifact. Không thêm/drop/rebuild.
- Không còn target User/Cart/Order, không có target Payment Attempt. Global audit: Cart không có User=0; Cart item thiếu Product=0; Order thiếu User=0; Order item thiếu Product=0; Attempt thiếu User/Order=0; Attempt ownership mismatch=0; Product thiếu Category=0.
- `ecommerce_test`: cả6collections vẫn rỗng; không tạo fixture mới.
- Backend/app, backend/tests và API contract SHA256 manifest giữ nguyên. Không cần chạy lại658 backend tests cho task chỉ cleanup dữ liệu; kết quả suite06AB vẫn là evidence lịch sử của cùng source. Kiểm tra hiện tại là transaction +full fingerprint/schema/reference audit và kiểm tra lại trạng thái đã sạch, không dùng test-suite count để suy ra integrity.

## 7. Files và điểm dừng

Tạo script cleanup, `backend/evidence/phase06ab-db-cleanup.json` và review này; cập nhật AGENTS/evidence index và thêm follow-up vào review06AB để đóng pending data review. Không ghi đè evidence06AB/FE-01A cũ; những artifact đó ghi nhận trạng thái kiểm thử trước cleanup.

**PHASE 06AB DATABASE INTEGRITY PASS.** Pending housekeeping của06AB đã được giải quyết bằng provenance và cleanup có đối chiếu baseline. LIVE SANDBOX BLOCKED vẫn giữ nguyên, không thuộc task cleanup. Dừng tại checkpoint; không feature mới, application change, commit hoặc push.
