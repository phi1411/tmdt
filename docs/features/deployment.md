# Deployment Render + Atlas

## Goal
Deploy demo Novamart trên Render/Atlas, giữ local offline và schema v1. Người dùng đã cho upload DB và chuẩn bị deploy; repository GitHub/compute plan đang được hỏi, chưa publish hay dùng credit khi chưa chốt.
## Actors
Chủ dự án cấu hình hosting; Customer/Admin dùng cùng API/UI đã có.
## Functional Requirements
Flask WSGI runtime riêng; production config không tự đọc .envlocal; SRVAtlas/expected replica/PRIMARY/sessions; React build có APIbase theo môi trường; Render static SPAfallback và backendhealth.
## Business Rules
Không đổi pricing/snapshot/lifecycle/revenue/schema. COD/VNPAYdisabled. Local/testing vẫnrs0; production dùng expectedReplicaSetAtlas explicit, không bỏ kiểm tra transaction topology. Không bootstrap/reseed/expiryworker trong startup.
## Permission
Giữ JWT/live DB role/status/ownership; chỉ deployer quản lý secret/hosting. Không credential trong git/VITE_ hoặc receipt.
## API
Giữ toàn bộ `/api/v1` và envelope, không endpoint mới. Health200/503 cũ; frontend build-timeAPIbase là HTTPS backendpublicURL+/api/v1,localdefault/api/v1. ExactHTTPS frontendCORSorigin.
## Data
Atlasnovamart_demo đã upload6collections; local/benchmark không write. Runtime source `backend/app/config.py`, `backend/serve.py`, requirements-render; FE `src/api/client.ts`, vite-env; rootrender.yaml. Dependencies factory/MongoConnection health/canonical aggregation paths; scripts/demo currentrehearsal và deploymentchecks.
## Validation
Production cần explicit SRVAtlasURI/expected replica/DB/JWT/origin; rejectdirectConnection/wrongreplica/nonAtlasURI. PORT1..65535; .envlocal không kế thừa khi APP_ENV=production được đặt trong process environment. Local/test strictguards giữ nguyên. FEAPIbase do deployer nhập theo hướng dẫn: default /api/v1 hoặc HTTPS backend + /api/v1; client chỉ chuẩn hóa slash cuối, không tự kiểm tra domain của build-time setting.
## Edge Cases
ColdstartFree,DBnetworkallowlist/DNS/TLS/authfailure,CORSorigin sai,SPAdeeplinks,secretmissing,serverrestart. Fixture có/không ảnh; offlinebrowserdeny ảnh ngoài không ngănCOD. Giữ bài test ảnh rỗng riêng trên exact testclone.
## Security
Waitress phục vụ WSGI,debugfalse; secretRenderenv riêng. Không ProxyFix tùy tiện, limiter vẫn dùng socketIP nên cần kiểm thử sauproxy; không giả SLA/productionsecuritycomplete. Plan mặc địnhFree,không tự chọnpaid. CredentialAtlas chỉ ignored.local/Renderdashboard.
## UI Behavior
React giữ giao diện cũ; APIbase thay theo buildenv. Mobile/Desktop,Orderhistory/Admin giữnguyên. Externalimagefails có thể là giới hạn offline,không claim ảnhonline hiển thị khi chặninternet.
## Acceptance Criteria
Fullbackendtests +strictbuild +rehearsalnew PASS; realWSGI/productionAtlas health/readAPI; no DBmutation ngoài ownedtestfixture. Renderblueprint valid. PublicURL nghiệm thu chỉ khi có repo/hosting thật và smokeđạt,không gọi chuẩn bịlocal làdeployPASS.
## Testing Checklist
- Config development/testing regression và production failclosed/precedence/PORT/CORS.
- Full suite,real rs0rehearsal cóảnh/ảnhtrống/invalidURL,snapshot/COD/Admin/offlinebrowser.
- ProductionWSGIstartup/readAtlas/FEbase/staticSPAblueprint và private-envscan.
- GitHub/Render publicdeploy và HTTP/E2E trênURLpublic: pendingthôngtintài khoản/repo.
