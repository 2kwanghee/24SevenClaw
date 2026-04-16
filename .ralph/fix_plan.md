# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[api] Organization/Project 모델 확장**
  > 요청사항: 기존 모델에 필드 추가.

Organization:

* main_product VARCHAR(500)
* business_type VARCHAR(100)
* company_description TEXT

Project:

* prototype_session_id UUID FK(prototype_sessions, SET NULL)
* pm_profile_id UUID FK(pm_profiles, SET NULL)
* project_type VARCHAR(30) DEFAULT 'legacy'

기존 스키마(schemas/organization.py)도 함께 확장.

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-16 | [api] Organization/Project 모델 확장 | ✅ | business_type VARCHAR(100), project_type VARCHAR(30) DEFAULT 'legacy', 마이그레이션 011 |