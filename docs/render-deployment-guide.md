# Deploy Novamart lên Render + Atlas

Người dùng đã chọn backend **$7/tháng** cho demo trong một tháng, dùng credit Render; `render.yaml` hiện dùng `0.5c-512mb`,Singapore. Static Site và Atlas vẫn miễn phí. Credit trong workspace đã kiểm tra là$50. Atlas `novamart_demo` đã có dữ liệu; không chạy seed/import lại khi deploy app. Trạng thái public thực tế xem review deployment mới nhất; cấu hình không tự chứng minh deploy thành công.

## Repository

Cần repository GitHub chứa source hiện tại: backend, frontend và `database/aggregations`/validators/index definitions. Checkpoint05AB cũ chưa chứa toàn bộ sản phẩm; nhiều thay đổi hiện chưa commit. Kiểm tra staged files và secrets trước commit. Không đưa `.env`, `.local`, credentials, virtualenv, node_modules, cache, DB export hoặc log lên GitHub; `.gitignore` đang loại các mục này.

## Backend

Render → **New → Web Service** → chọn repository/branch:

| Trường | Giá trị |
| --- | --- |
| Name | `novamart-api` hoặc tên duy nhất bạn chọn |
| Language | Python |
| Root Directory | để trống |
| Build Command | `pip install -r backend/requirements-render.txt` |
| Start Command | `python backend/serve.py` |
| Instance Type | $7/month,0.5CPU/512MB, theo lựa chọn chủ dự án |
| Health Check Path | `/api/v1/health` |

Environment backend:

| Key | Giá trị |
| --- | --- |
| PYTHON_VERSION | `3.12.14` |
| APP_ENV | `production` |
| MONGODB_URI | URI Atlas riêng từ ignored `.local/atlas-upload/connection.json`; nhập trong Render, không trong source |
| MONGODB_REPLICA_SET | `atlas-uczcqo-shard-0` (cluster hiện tại đã xác minh) |
| MONGODB_DB | `novamart_demo` |
| MONGODB_TIMEOUT_MS | `15000` |
| JWT_SECRET | secret mới tối thiểu32byte, khác local; Blueprint có thể generate |
| JWT_ISSUER | `novamart-api` |
| JWT_AUDIENCE | `novamart-web` |
| FRONTEND_ORIGIN | URL HTTPS frontend chính xác; khi chưa biết dùng origin tạm `https://pending.example.invalid`, rồi thay ngay khi có URL thật |
| VNPAY_ENABLED | `false` |

Không cấu hình `MONGODB_TEST_DB`, local rs0, `API_HOST=127.0.0.1` hoặc PORT cố định trên Render. Render cấp PORT; production bind `0.0.0.0`, không tự đọc local `.env`. Không thêm expiry worker trên seed. Backend build từ repository root vì Dashboard đọc canonical pipelines ở `database/aggregations`.

Atlas → Network Access: cho phép các **outbound IP/CIDR của backend Render** (xem dashboard service), rồi kiểm tra health. IP máy local đã thêm trước đó không tự cho phép Render. Không bỏ TLS/topology guard để né startup failure.

## Frontend

Render → **New → Static Site** → cùng repository/branch:

| Trường | Giá trị |
| --- | --- |
| Root Directory | `frontend` |
| Build Command | `npm ci && npm run build` |
| Publish Directory | `dist` |
| NODE_VERSION | `24.15.0` |
| VITE_API_BASE_URL | URL backend thật + `/api/v1`, định dạng `https://<backend>.onrender.com/api/v1` |

Redirects/Rewrites: Source `/*`, Destination `/index.html`, Action **Rewrite**. React Router cần giữ đường dẫn hiện tại.

Khi có URL frontend, đặt `FRONTEND_ORIGIN` backend thành chính origin đó, không dấu `/` cuối hoặc path; save/redeploy backend. Nếu đổi `VITE_API_BASE_URL`, frontend phải build lại. Không đưa URI MongoDB/JWT/mật khẩu vào `VITE_`.

Có thể dùng **New → Blueprint** với `render.yaml` thay việc tạo thủ công. Các trường `sync:false` cần nhập lần đầu; origin tạm phải được sửa thành URL Render thật. Schema validation local đã PASS; Render vẫn cần kiểm tra repo, region, runtime và account khi tạo service.

## Nghiệm thu URL thật

- Health200; Customer/Admin login, `/auth/me`; Guest401/Customer403 khi gọi Admin.
- Home/catalog/detail có ảnh; refresh trực tiếp các deep links không bị hosting404.
- Cart → địa chỉ → quote → COD → Order → cancel; ownership giữ nguyên.
- Dashboard đủ5reports; CRUD fixture; Admin confirm → ship → complete. Không hoàn tất live Order rồi ép stock về cũ.
- Snapshot giữ giá lúc mua sau đổi giá Product; không CORS/console error; API dùng backend HTTPS thật, không localhost; kiểm tra mobile.
- Ghi exact IDs của smoke artifacts và cleanup đúng phạm vi; không reset/reseed Atlas/local. Chỉ chạy smoke mutation khi đã xác định ownership/cleanup.

Chỉ kết luận **PUBLIC DEPLOYMENT PASS** sau các bước này. Hiện WSGI local kết nối Atlas đã được kiểm tra; Render Linux/public TLS/proxy chưa nghiệm thu. VNPAY Live Sandbox chưa PASS và đang disabled.

Nếu chuyển về Free, backend có cold start. Gói trả phí tiếp tục tính tiền cho tới khi suspend/delete; muốn dùng một tháng thì chủ dự án cần dừng service khi kết thúc. Chưa tạo lịch tự dừng. Bundle còn chunk-size warning. Auth limiter hiện per-process/socket IP, cần kiểm tra qua proxy Render trước khi kết luận security public; chưa đổi proxy trust/auth strategy trong lần chuẩn bị này.

Nguồn: [Render Blueprint](https://render.com/docs/blueprint-spec), [Deploy Flask](https://render.com/docs/deploy-flask), [Flask Waitress](https://flask.palletsprojects.com/en/stable/deploying/waitress/).
