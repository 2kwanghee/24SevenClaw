# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[api] Catalog API 스키마 검증 + 하드코딩 값 seed 주입**
  > 요청사항: ## 목적

위저드 Step 6 동적화 전에 기존 하드코딩 값을 DB에 seed 데이터로 주입해 빈 목록 방지.

## 작업 범위

* `app/api/v1/catalog.py` 응답에 `id`, `label`, `description` 필드 포함 여부 검증, 누락 시 스키마 보강
* Alembic data migration: 기존 하드코딩 7 agents + 6 skills를 멱등하게 DB 삽입
  * agents: harness, architect, frontend, backend, qa, devops, security
  * skills: linear, telegram, github, slack, jira, notion
* `app/schemas/catalog.py` 필요 시 보강

## 완료 기준

* `GET /api/v1/catalog/agents` → 7개 항목 JSON 반환
* `GET /api/v1/catalog/skills` → 6개 항목 JSON 반환
* Alembic migration 재실행 시 중복 삽입 없음 (멱등)

## 선행 조건

없음 (24S-172와 병렬 가능이지만 순차 진행)

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-21 | Catalog API 스키마 검증 + seed 주입 | ✅ 완료 | agents.json 7항목, skills.json 6항목, CatalogItemResponse(id/label/description), 016 Alembic migration, 421/421 tests pass |