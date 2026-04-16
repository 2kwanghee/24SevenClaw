# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[api] PMService 구현 (추천/구성/평가)**
  > 요청사항: app/services/pm_service.py 신규 작성.

* recommend(session_id, prototype_id) → 도메인 필터 → 전문분야 유사도 → Claude 시맨틱 매칭 → 평가지표 가중정렬 → 상위 3\~5명
* get_profile(pm_id) → PM 상세 + metrics
* get_composition(pm_id) → agent/skill/hook/mcp_server/plugin 구성
* rate_pm(pm_id, user_id, session_id, rating, comment) → 평가 등록 + pm_metrics 자동 갱신
* list_profiles(domain, specialty, limit) → PM 목록 필터링

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-16 | [api] PMService 구현 | ✅ 완료 | list_profiles specialty 필터, get_profile+metrics, recommend top3~5 가중정렬, get_composition 타입별 그룹화, /composition 엔드포인트 추가 |