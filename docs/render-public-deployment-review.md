# NovaMart public deployment —14/10/2026

**Public demo đã hoạt động:** [Website](https://novamart-web.onrender.com), [API health](https://novamart-api.onrender.com/api/v1/health). Đây là nghiệm thu deployment chức năng trong phạm vi kiểm tra dưới đây, không phải chứng nhận security toàn hệ thống.

## Hạ tầng và chi phí

- Render workspace hiện tại có$50credit, hạn01/10/2027; người dùng tự thêm thẻ và cho dùng paid backend cho demo một tháng.
- Backend `novamart-api`,Singapore,Python3.12.14/Waitress,compute `0.5c-512mb` được Render hiển thị$7/tháng. Service ID `srv-db7jd8dg1s2s73aovtag`.
- Frontend `novamart-web`,Render Static Site miễn phí,Node24.15.0,React production bundle. Service ID `srv-db7jdkavcj2c73dsht8g`.
- AtlasCluster0/`novamart_demo` giữ schema và dữ liệu hiện hữu. Secrets chỉ ở Render Environment/ignored `.local`, không lên GitHub.
- Paid backend tiếp tục tính tiền tới khi suspend/delete. Chưa tạo lịch tự dừng; chủ dự án cần dừng sau buổi demo/tháng sử dụng. Không mua domain, disk, paid database hoặc worker.

## Cấu hình và source

Source đã đẩy lên `https://github.com/phi1411/tmdt`,branch master. Backend live từ commit `a9117fb83b3e9b07ba3f3e2611cafb6e5e7110e7` (application logic giống checkpoint674PASS). Backend build từ repository root để đọc canonical aggregations; start `python backend/serve.py`,health `/api/v1/health`. Production expected Atlas replica set/TLS/PRIMARY/sessions được giữ.

Frontend `VITE_API_BASE_URL=https://novamart-api.onrender.com/api/v1`; backend `FRONTEND_ORIGIN=https://novamart-web.onrender.com`. Static rewrite `/* → /index.html` đã lưu. VNPAY_ENABLED=false; không khởi tạo expiry worker.

Sửa text nhỏ ở AdminLayout: bỏ tên `rs0` hardcoded khỏi badge để không mô tả sai replica set Atlas. Không đổi logic, API, schema, auth hoặc business rules. Strict TypeScript/build sau sửa PASS,2237modules/19.93s; còn chunk-size warning. Bản sửa cần manual frontend deploy vì repository public đang kết nối theo Public Git Repository, không qua Git Provider/Blueprint auto-deploy.

## Kiểm tra thật

**50HTTP checks PASS** trên API HTTPS public:

- Health,exact CORS allow và origin khác không được cấp allow-origin; Category/list/search/detail và3ProductType.
- Guest Admin401,Customer Admin403,invalidJWT401; CustomerB đọc Order củaA404.
- Register/login/profile/address; Cart→signed quote→COD Order,repeat same Idempotency-Key trả cùng Order.
- Payload client thêm total bị422. Snapshot items/customer/address/totals giữ nguyên sau sửa Product100k→120k và tên mới.
- Customer cancel/replay không hoàn kho hai lần. Order thứ hai Admin confirm→ship→complete,COMPLETED/PAID.
- Dashboard đủ5reports; revenue tăng120.000,không cộng shipping.

Public HTTP script mutate chỉ fixture mới có journal và unique owner/category/SKU. Cleanup transaction xóa đúng1User/1Cart/2Orders/1Product/1Category,0attempts; Atlas full fingerprint trước/sau cùng `b2c2c64f...`,counts42Users/5Categories/182Products/1Cart/101Orders/30Attempts.6validators/14declared+6_id_indexes và0orphans; không reset/reseed/drop hoặc sửa seed/fixture07C để cleanup. Fingerprint local được kiểm tra riêng; fingerprint giữa hai deployment không so trực tiếp do collection metadata khác nhau.

Static HTTP checks: `/`, `/products`, `/login`, `/admin/dashboard` đều200 và cùng SHA256 index.html; bundle dùng API HTTPS thật. Browser thật: Catalog182Products,16ảnh ở trang đầu tải thành công,chi tiết Product/attributes; Admin login bằng UI,Dashboard KPI/Top5/SVG charts hiển thị,không overflow ở viewport quan sát. Đây là browser smoke, không chạy lại toàn bộ Customer/Admin E2E UI suite trên public; checkout/lifecycle/snapshot public được kiểm tra qua HTTP thật.

Fullbackend674PASS và12nhóm browser regression trên owned test clone đã có trong [review chuẩn bị](render-deployment-review.md); không gán các kết quả local đó thành public UI E2E mới.

## Các lỗi tạm thời và giới hạn

- Lượt public HTTP đầu bị `RemoteDisconnected` khi POST address. Exact cleanup đã PASS trước khi chạy lại; lượt mới hoàn tất50HTTP. Không có bằng chứng đã sửa nguyên nhân mạng.
- Một lần browser `Failed to fetch` trong giai đoạn triển khai; reload sau đó Catalog tải đủ dữ liệu. Không claim zero network/console errors xuyên toàn phiên.
- Render UI từng lỗi tải giá trị env ẩn; lượt save đó không thành công. Đã reload, mở riêng giá trị origin, nhập đúng URL và Save and deploy; deployment mới Live và CORS HTTP xác nhận đúng origin.
- Npm audit lúc build ghi **9vulnerabilities:5high/4moderate**,gồm chuỗi Tailwind/build tooling và React Router. Fix được npm đề xuất có major upgrades; chưa thực hiện migration ngoài scope deploy. Không claim production-security-clean. Private full audit lưu `.local/render-deployment/npm-audit.json`; cần follow-up dependency review trước sử dụng ngoài demo. [React Router advisory](https://github.com/advisories/GHSA-wrjc-x8rr-h8h6), [braces advisory](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm).
- Auth limiter vẫn per-process/socketIP sau Render proxy; chưa thêm distributed limiter/ProxyFix hoặc nghiệm thu abuse/load test.
- VNPAY Live Sandbox chưa kiểm thử,đangdisabled. Compass/human timing/offlineOS vẫn là các gate bảo vệ local trong review07D.

## Evidence

[Public HTTP/cleanup](../backend/evidence/render-public-smoke.json), [SPA/bundle/CORS](../backend/evidence/render-public-static.json), [backend674JUnit](../backend/evidence/render-prep-pytest.xml). Private screenshots/journals và receipt lần HTTP lỗi được giữ ở ignored `.local/render-deployment`; không chứa secrets trong evidence public.
