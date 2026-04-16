# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[api] Alembic 마이그레이션 4개 작성**
  > 요청사항: 순서대로 마이그레이션 작성 + 적용.

1. add_prototype_session_tables (prototype_sessions, prototypes)
2. add_pm_profile_tables (pm_profiles, pm_compositions, pm_metrics, pm_ratings)
3. extend_organization_fields (3개 컬럼)
4. extend_project_fields (3개 컬럼)

`alembic revision --autogenerate` → `alembic upgrade head` 검증.

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-16 | [api] Alembic 마이그레이션 4개 적용 | ✅ | 006-011 + c255febcea16 적용, 337 tests passed |