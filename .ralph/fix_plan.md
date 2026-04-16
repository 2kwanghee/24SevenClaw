# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[Phase 1] Solution Wizard v2 — DB + 백엔드 모델**
  > 요청사항: ## DB 스키마 + 백엔드 모델 구현

신규 테이블 6개 + 기존 테이블 확장 2개 + Alembic 마이그레이션 + Pydantic 스키마.

### 신규 모델

* prototype_sessions, prototypes
* pm_profiles, pm_compositions, pm_metrics, pm_ratings

### 기존 모델 확장

* organizations (main_product, business_type, company_description)
* projects (prototype_session_id, pm_profile_id, project_type)

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-16 | Phase 1: DB + 백엔드 모델 | ✅ | 신규 6테이블 + 기존 2테이블 확장 + Alembic 009 + Pydantic 스키마 |