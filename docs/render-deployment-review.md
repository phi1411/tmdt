# Render preparation và rehearsal với ảnh mới —14/10/2026

**DEPLOYMENT PREPARATION PASS; PUBLIC DEPLOYMENT PENDING.** Đã chuẩn bị cấu hình deploy và kiểm chứng runtime thật kết nối Atlas. Chưa tạo Render service, chưa dùng credit, chưa commit/push; repository chưa có remote GitHub. Không gọi các kiểm tra local này là nghiệm thu website public.

## Kết quả thực chạy

| Hạng mục | Kết quả |
| --- | --- |
| Full backend suite | **674passed /0failed /0errors /0skipped**,109.419sJUnit |
| Production config tests mới |16cases;658tests cũ cùng PASS |
| TypeScript strict + local production build |PASS,2237modules;13.63s; còn chunk-size warning |
| Build với HTTPS API URL riêng |PASS,14.59s; URL có trong bundle riêng; local bundle giữ default `/api/v1` |
| Browser rehearsal ảnh mới |**12checks PASS**,164HTTP:160×200,3×201,1×422 cố ý;0page errors |
| Chart visual sau animation |PASS:5pie sectors,2area paths,5bars;desktop1440 không overflow |
| Waitress production → Atlas |**19HTTP checks PASS**,không ghi DB |
| Render blueprint |PASS theo JSON Schema chính thức; chưa gọi validation API/tạo service Render |
| Cleanup |6collections test rỗng;dev/benchmark exact fingerprints giữ nguyên |
| Atlas integrity |Fingerprint trước/sau production smoke trùng;6validators/14declared+6_id_indexes;0orphans |
| Secret scan |Không tìm thấy các secret local/Atlas đã biết trong candidate source/docs/evidence; các đường dẫn private/build/dependencies được Git ignore |
| Local services cuối |5001health200;5173HTTP200;test5002/5174 và production-probe5003 đã dừng |

Không chạy lại toàn bộ22Admin/32Customer/25nhóm07A trong follow-up này. Evidence07A giữ lịch sử; phạm vi regression mới là12nhóm demo dưới đây và674backendtests. Không claim zero console/network errors toàn hệ thống: browser runner đo page errors và API responses; ảnh ngoài bị chặn có chủ ý trong offline drill.

## Rehearsal và snapshot

Hai Product07C hiện có ảnh CDN do thay đổi được người dùng báo trước; không còn giả định `images=[]` trên live fixture. Current runner `scripts/demo/verify_final_rehearsal_fix.py` mặc định namespace `phase07d-images`, giữ evidence07D/07D-fix cũ. Runner07D ban đầu là artifact lịch sử tái hiện lỗi trước sửa.

Rehearsal chạy production React bundle5174 → cùng Flask source5002 → exact owned clone `ecommerce_test/rs0`:

- Customer/Admin login;3ProductType hiển thị attributes; ảnh thật tải thành công ở luồng có mạng.
- URL ảnh sai gửi nguyên input, nhận422, Product không bị đổi.
- Kiểm tra riêng Product không ảnh trên clone: Web lưu được `images=[]`, sau đó khôi phục ảnh gốc; không sửa live fixture để kiểm thử trường hợp này.
- Hai Product → Cart → COD; subtotal10.200.000,ship30.000,total10.230.000.
- Admin Web đổi điện thoại10→12triệu, giữ nguyên ảnh/attributes/stock; đọc Order qua API và Web vẫn giữ giá10triệu và snapshot items/customer/address. Không dùng API fallback cho thao tác đổi giá.
- Customer cancel một lần, hoàn kho; Web khôi phục giáA.
- Đơn tiếp theo confirm→ship→complete; revenue+10.200.000 và units+2, không cộng phí ship.
- Dashboard đủ5API200 và SVG charts; browser cold-cache chặn HTTP(S) ngoài loopback vẫn login/COD/cancel PASS.

Đơn COMPLETED chỉ nằm trong clone test và được xóa đúng ownership sau kiểm thử; không đảo trạng thái hoặc ép tồn kho live. Live fixture giữ giáA,stock20mỗi Product,Cart rỗng. Dev và Atlas cùng counts:42Users/5Categories/182Products/1Cart/101Orders/30PaymentAttempts. Account cần giữ và fixture07C đều được giữ nguyên; không reset/reseed/drop.

## Thay đổi phục vụ deployment

- `backend/app/config.py`: thêm production env tách localdotenv; AtlasSRV/expected replica/TLS/HTTPSorigin/PORT validation. Development/testing vẫn khóa localrs0, không đổi schema hoặc nghiệp vụ.
- `backend/serve.py`, `requirements-render.txt`: Waitress3.0.2 và tzdata2025.2 cho deployment; original locks giữ nguyên. Không seed/expiry worker khi startup.
- `frontend/src/api/client.ts`, `vite-env.d.ts`: API URL build-time qua `VITE_API_BASE_URL`; default local giữ `/api/v1`, bỏ slash cuối để ghép path đúng.
- `render.yaml`: backend Free rõ ràng, static frontend, secret nhập ngoài source, healthcheck và SPA rewrite. Backend root giữ canonical aggregation files.
- Thêm16configtests và read-only production verifier; cập nhật rehearsal/helpers/docs/ADR012, không thêm endpoint/feature.

Hai lỗi trong lượt chạy verifier đầu là giả định sai của script mới (Product list DTO là array, public detail dùng slug). Đã sửa verifier theo contract và chạy lại đầy đủ19HTTP thành công; không sửa API để khớp script.

## Giới hạn và bước tiếp

Chờ URL repository GitHub và lựa chọn compute của chủ dự án. Blueprint giữ Free mặc định; chưa kích hoạt paid service. [Hướng dẫn deploy](render-deployment-guide.md) có build/start/env/CORS/network/SPA và checklist public smoke. Cần kiểm tra trên Render thật: Linux build/runtime, outbound IP allowlist Atlas, HTTPS/CORS, SPA deep links, proxy/rate limiter và Customer/Admin journeys. WSGI check hiện là Windows local gọi Atlas qua mạng, không phải Render public.

VNPAY_ENABLED=false; không claim Live Sandbox PASS. Compass GUI, rehearsal5/10phút của3SV và ngắt mạng OS vẫn cần làm thủ công như các review trước; browser external-deny không thay thế offline host rehearsal.

## Evidence

- [JUnit](../backend/evidence/render-prep-pytest.xml), [summary](../backend/evidence/render-prep-summary.json), [production WSGI](../backend/evidence/render-prep-runtime.json), [blueprint](../backend/evidence/render-blueprint-validation.json).
- [Browser](../database/evidence/phase07d-images-browser.json), [charts](../database/evidence/phase07d-images-chart-visual.json), [integrity](../database/evidence/phase07d-images-integrity.json), [environment](../database/evidence/phase07d-images-environment.json), [queries](../database/evidence/phase07d-images-queries.json), [test outcomes](../database/evidence/phase07d-images-test-outcomes.json).
- Private journals/config/credentials ở ignored `.local`; không chiếu hoặc upload những file đó lên GitHub.
