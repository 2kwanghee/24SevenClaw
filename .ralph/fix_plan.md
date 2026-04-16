# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[api] PM 프로필/구성/평가 모델 구현**
  > 요청사항: SQLAlchemy 모델 신규 작성.

* app/models/pm_profile.py: id, name, slug(UNIQUE), avatar_url, title, description, domain, specialties(JSON), personality(JSON), is_active
* app/models/pm_composition.py: id, pm_id(FK CASCADE), component_type, component_slug, component_name, config(JSON), display_order, is_required
* app/models/pm_metrics.py: id, pm_id(FK CASCADE UNIQUE), usage_count, completed_projects, avg_rating, total_ratings, success_rate, avg_completion_days
* app/models/pm_rating.py: id, pm_id(FK), user_id(FK), session_id(FK), rating(1\~5), comment

models/**init**.py에 등록.

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-16 | [api] PM 프로필/구성/평가 모델 구현 | ✅ | pm_profile.py 재설계, pm_composition/metrics/rating.py 신규, 마이그레이션 010, 테스트 337개 전부 통과 |