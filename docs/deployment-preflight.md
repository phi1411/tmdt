# Deployment preflight —14/10/2026

**Follow-up Render preparation:** production config/Waitress/Atlas expected replica set và build-time frontend API URL đã triển khai, xem [review](render-deployment-review.md) và [hướng dẫn](render-deployment-guide.md). Full backend674PASS, rehearsal với ảnh mới12PASS, production WSGI→Atlas19HTTP PASS, blueprint schema PASS. Local/Atlas/benchmark không bị ghi ngoài phạm vi; test clone đã cleanup. Chưa tạo service/public deploy, chưa commit/push hoặc dùng credit; các giới hạn cấu hình cũ bên dưới là lịch sử preflight trước follow-up này.

Trạng thái: chuẩn bị deploy demo COD; chưa chọn hosting/domain, chưa provision hoặc publish. Local MongoDB/Flask/React đang hoạt động. Không commit/push hoặc copy secrets sang dịch vụ bên ngoài.

**Cập nhật14/10/2026:** người dùng đã chọn hướng miễn phí Render+Atlas và yêu cầu upload DB. [Atlas upload PASS](atlas-database-upload-review.md): novamart_demo có đầy đủ6collections/validators/indexes,exactBSONvàaggregationkhớp,localunchanged. Các ghi chú preflight ban đầu bên dưới giữ lịch sử; Flask/React/Render vẫn chưa deploy,application config chưa chuyểnAtlas.

## Điểm chặn UI đã sửa

AdminProductFormPage cho Brand trống theo API contract, bỏ HTMLrequired và guard nonempty. Đã tái hiện trước sửa trên DEMO-FAS-022 và xác minh sau sửa browser gửi PATCH với brand="". Request mutation được intercept tại browser trong phép kiểm tra này; DB không ghi, full dev fingerprint giữ nguyên. Đây là kiểm tra submit frontend, không phải một checkout/end-to-end production mới.

`npm run build` sau sửa PASS: TypeScript strict/Vite2237modules,16.32s;JS868.35kB/gzip237.16kB, còn chunk-size warning. Full backend gần nhất vẫn658PASS ở follow-up07D; không chạy lại backend suite vì không sửa backend. Source manifest07D-fix là evidence lịch sử trước thay đổi Brand này.

## Các việc cần làm theo nơi deploy đã chọn

- Flask hiện chạy qua backend/run.py development server; deployment cần WSGI server/hosting runtime riêng. Theo [Flask deployment](https://flask.palletsprojects.com/en/stable/deploying/), không đưa development server lên phục vụ public.
- Frontend production assets cần static host/reverse proxy với SPA fallback và `/api/v1` forward tới Flask. Vite dev/preview proxy localhost hiện tại chỉ phục vụ máy dev.
- Config hiện khóa MongoDB replica set tênrs0, không cho directConnection; APP_ENV chỉ nhận development/testing. Cần quyết định runtime deployment và cách cấu hình trước khi sửa có tests; không tự đổi schema hoặc chuyển Atlas.
- MongoDB cần đáp ứng transaction của checkout/stock/order và có storage bền vững. [MongoDB transactions](https://www.mongodb.com/docs/manual/core/transactions/) hỗ trợ replica set/sharded cluster; chọn standalone sẽ không đáp ứng luồng hiện hữu. Giữ rs0 là phương án ít thay đổi nhất nếu có server phù hợp.
- Environment/JWT/admin credentials cho bản public phải tách khỏi .env và tài khoản demo local đã dùng; cấu hình exact origin/HTTPS theo domain được chọn. Không đưa secrets vào VITE_ hoặc bundle.
- DB deployment riêng: bootstrap validators/indexes và dữ liệu demo có ownership; không reset/reseed ecommerce_dev đang có dữ liệu cần giữ.
- VNPAY_ENABLED=false cho demoCOD tới khi merchant/publicIPN được cấu hình và kiểm thử riêng. Không tuyên bố VNPAYLivePASS.
- Sau deploy chạy health,CustomerCOD/Admin/snapshot/security và kiểm traDB trên chínhURL public; giữ checklistCompass/timing/offlineOS cho buổi bảo vệ local.

Đang chờ thông tin nơi deploy (VPS/server hoặc managed hosting), ngân sách và domain nếu đã có. Chưa mua tài nguyên hoặc thay đổi hạ tầng bên ngoài.
