# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P2: 기능 요구사항

- [x] **[24S-142/P1] DB migration 013 + Registry Admin API**
  > 요청사항: ## 작업 내용

* `alembic/versions/013_registry_body_md_and_pm_overrides.py` 신규 — `agents/skills/mcp_servers`에 `body_md TEXT NULL`, `pm_profiles`에 `markdown_body TEXT NULL` 추가
* `app/models/registry.py`, `app/models/pm_profile.py` 컬럼 매핑
* `app/schemas/registry_admin.py` 신규 — `AgentCreate/Update/Response`, `SkillCreate/Update/Response`, `MCPServerCreate/Update/Response`
* `app/services/registry_admin_service.py` 신규 — CRUD + slug 중복 방지
* `app/api/v1/registry_admin.py` 신규 — `GET/POST /admin/agents`, `PUT/DELETE /admin/agents/{id}` + skill/mcp-servers 동일 구조, `Depends(require_permission("pm:manage"))`
* `app/api/v1/router.py` 라우터 등록
* `tests/test_registry_admin_api.py` 신규 — 성공/인증실패/유효성검사 각 3개

## 완료 기준

`alembic upgrade head && alembic downgrade -1 && alembic upgrade head` 통과 + pytest 통과

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-17 | [24S-142] Migration 014 + pm_profile.markdown_body + test_registry_admin_api.py | ✅ | 381 passed |