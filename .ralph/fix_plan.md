# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[api] Phase 4 — 현대화 계획 수립 단계 구현 (태스크 DAG + 웨이브/마일스톤)**
  > 요청사항: ## 목표

권장안을 **의존성 있는 실행 계획**으로 격상한다: 태스크 간 선후관계(DAG) + 웨이브(마일스톤) 묶음 + 각 태스크에 담당 에이전트 지정.

## As-Is 근거

* `ModernizeRecommendation`에 priority/effort/risk만 있고 권장안 간 선후관계 없음
* LLM 요약의 "phasing" 텍스트가 유일한 계획 (`llm_summary.py`)
* 재분석 시 `_upsert_recommendations`가 전체 삭제·재삽입 → finalize 후 Linear 매핑/사용자 편집 유실 (`pipeline.py:232-236`)

## 작업 내용

1. Recommendation에 `depends_on`(rec idx 배열) + `wave`(정수) + `assigned_agent` 필드 추가 ([CE-284](https://linear.app/flow-ops/issue/CE-284/contractsapi-modernize-6단계-phase-데이터-모델-확장) 스키마 기반)
2. 계획 생성 로직: 갭 매트릭스 + 권장안 → DAG 구성 (예: DB 스키마 변환 → 데이터 이관 → 앱 코드 수정 → 검증), 사이클 검출
3. `modernization-plan.md`(웨이브별 태스크 목록/예상 공수/리스크) + `plan.json`(오케스트레이터 실행용 기계 포맷 — CE-290 입력) 산출
4. 재분석 시 사용자 편집·Linear 매핑 보존하는 diff-merge upsert로 개선

## 완료 조건

* tobe 승인 후 plan phase 전이, plan.json이 DAG 검증(위상정렬 가능) 통과
* 기존 finalize(Linear 등록)가 wave/depends_on을 blockedBy 관계로 반영
* 단위 테스트 동반

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-07-06 | [api] Phase 4 — 계획 수립 단계 | 완료 | `ModernizeRecommendation`에 depends_on/wave/assigned_agent 추가(마이그레이션 043) + `plan_builder`(순수 DAG/위상정렬/agent 추론 함수) + `plan_generation`(tobe 승인 전제조건 검사 → plan.json/modernization-plan.md 생성 → current_phase='plan' 전이) 신규. `_upsert_recommendations`를 idx 기준 diff-merge로 전환해 재분석 시 selected/priority/Linear 매핑 보존. finalize에서 depends_on을 Linear `blocks` 관계로 반영(best-effort, `create_issue_relation` 추가). openapi.json 재생성. 단위테스트 25건 추가, 전체 스위트 회귀 없음(기존 40건 실패는 모두 무관한 사전 존재 실패로 확인). |