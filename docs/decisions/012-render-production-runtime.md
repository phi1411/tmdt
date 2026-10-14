# ADR012 — Production runtime riêng cho Render/Atlas

14/10/2026, người dùng cho chuẩn bị deploy sau Atlas upload. Bổ sung APP_ENVproduction, explicit expected Atlas replica set qua SRV thay vì ép tênrs0 trên cloud; development/testing không đổi. Production không tự đọc .envlocal, cần secret/DB/HTTPSorigin, vẫn enforce PRIMARY/sessions/expectedset. Không thay collection/schema/businesslogic. Readiness config tests và realAtlasread-only cần PASS.

Waitress productionWSGI hỗ trợ cảWindows/Linux để kiểm thử entrypoint trênmáyhiện tại; dependencydeploy riêng, không sửa lockruntime cũ. Render backend build tại reporoot để include database/aggregations; frontendStaticSite có APIbase buildenv và SPArewrite. BlueprintFree mặc định cho tới khi người dùng chốtcomputeplan. Không thêmworker/paidDB/extraresource.

Local/Atlas live documents không mutation khi thửruntime. Full backend suite dùng owned ecommerce_test; rehearsalcloneexactcleanup và fingerprint. Publicdeploymentpending GitHubURL/Renderaccountactions; không commit/push/provisiontựsuyđoán.
