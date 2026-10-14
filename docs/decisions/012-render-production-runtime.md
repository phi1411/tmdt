# ADR012 — Production runtime riêng cho Render/Atlas

Deployment follow-up14/10/2026: owner supplied GitHub repository phi1411/tmdt, approved storing Atlas URI/new JWT in Render and then explicitly chose paid backend for a one-month demo using $50credit. Current blueprint uses `0.5c-512mb` ($7/month shown by Render),Singapore; Static Site and Atlas remain free. Earlier Free default below is historical. Credit balance $50 and expiry01/10/2027 were verified in the active workspace before provisioning. A service remains billable until suspended/deleted; it does not automatically expire after one month. No scheduled stop has been created.

14/10/2026, người dùng cho chuẩn bị deploy sau Atlas upload. Bổ sung APP_ENVproduction, explicit expected Atlas replica set qua SRV thay vì ép tênrs0 trên cloud; development/testing không đổi. Production không tự đọc .envlocal, cần secret/DB/HTTPSorigin, vẫn enforce PRIMARY/sessions/expectedset. Không thay collection/schema/businesslogic. Readiness config tests và realAtlasread-only cần PASS.

Waitress productionWSGI hỗ trợ cảWindows/Linux để kiểm thử entrypoint trênmáyhiện tại; dependencydeploy riêng, không sửa lockruntime cũ. Render backend build tại reporoot để include database/aggregations; frontendStaticSite có APIbase buildenv và SPArewrite. BlueprintFree mặc định cho tới khi người dùng chốtcomputeplan. Không thêmworker/paidDB/extraresource.

Local/Atlas live documents không mutation khi thửruntime. Full backend suite dùng owned ecommerce_test; rehearsalcloneexactcleanup và fingerprint. Publicdeploymentpending GitHubURL/Renderaccountactions; không commit/push/provisiontựsuyđoán.
