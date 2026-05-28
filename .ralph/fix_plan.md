# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P2: 기능 요구사항

- [x] **[backend] Phase 3 — 카탈로그/PM 영문 컬럼 + ZIP 영문화**
  > 요청사항: ## 목표

카탈로그(agents/skills/mcp_servers/hooks) + PM 프로필에 영문 컬럼 추가하고, ZIP 생성 시 사용자 locale에 따라 `body_md_ko`/`body_md_en` 선택하여 출력한다.

## 변경 파일

### 마이그레이션

* `clickeye-api/alembic/versions/040_i18n_catalog_pm.py` (신규):
  * `agents/skills/mcp_servers/hooks`: + `name_en`, `description_en`, `body_md_en`
  * `pm_profiles`: + `name_en`, `title_en`, `description_en`, `bio_long_en`
  * 기존 한국어 컬럼은 보존 (fallback)

### 모델/스키마

* `clickeye-api/app/models/{pm_profile,registry}.py` (또는 분리 모델 파일들) — `_en` 필드 추가
* `clickeye-api/app/schemas/{registry,pm_profile}.py` — 응답 직전 `localize(item, locale)` 헬퍼 또는 스키마 분기. `name_en or name` fallback 패턴

### ZIP 생성

* `clickeye-api/app/engine/generator.py` — `render_body(item, locale)` 함수에 locale 매개변수 추가. `body_md_en` 존재 시 사용, 없으면 `body_md` fallback
* `clickeye-api/app/engine/catalog.py` — `prefetch_for_generator`에 locale 전달
* `clickeye-api/app/engine/templates/docs/api-keys/*.{ko,en}.md` (분리) — Anthropic/Linear 키 발급 가이드 영문 작성

### 시드 스크립트

* `clickeye-api/scripts/seed_i18n_translations.py` (신규):
  * 핵심 \~10개 항목 수동 영문 시드 (harness, backend, fullstack, ai-critique, tdd-smart-coding, github, linear, postgres, harness-gate, commit-session)
  * 멱등 — 재실행 가능

## 검증

1. alembic up/down 양방향 무손실 동작
2. en 사용자가 위저드에서 PM atlas 선택 시 카드 description이 영문 (en 누락 항목은 한국어 fallback)
3. en 사용자 ZIP 다운로드 → `.claude/agents/backend.md` 본문 영문 (en 입력된 경우)
4. 영문 미입력 카탈로그는 ko `body_md`가 그대로 사용됨 (부분 한국어 허용)

## 의존성

* 선행: [CE-256](https://linear.app/flow-ops/issue/CE-256/backend-phase-2-userlanguage-apperror-claude-locale-분기) (Phase 2 백엔드 다국어 — user.language 필드 필요)
* 후속 CE-258이 본 이슈에 의존

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-05-28 | [backend] Phase 3 — 카탈로그/PM 영문 컬럼 + ZIP 영문화 | ✅ | 마이그레이션 040, _en 컬럼, locale 파라미터, EN 가이드, 시드스크립트 |