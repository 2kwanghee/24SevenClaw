# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P2: 기능 요구사항

- [x] **[api] 산출물 상태머신 자동 전이 트리거**
  > 요청사항: ## 개요

오케스트레이터 단계 전이 시 연결된 Artifact의 상태를 자동으로 갱신하는 트리거를 구현한다.

## 범위

### orchestrator_service.py 수정

* `_transition_phase()`: `approved` 전이 시 연결된 Artifact(SubTask.artifact_id) 자동 `approved` 전이

### review_pipeline_service.py 수정

* `merge()`: 병합 후 SubTask → `completed`, Artifact → `reviewed` 자동 전이

### artifact_service.py 확장

* `bulk_transition(artifact_ids, target_status, actor_type, message)` 메서드 추가

## 완료 조건

- [x] approved 전이 시 Artifact 자동 갱신 확인
- [x] merge 후 SubTask + Artifact 상태 갱신 확인
- [x] bulk_transition 메서드 테스트
- [x] 기존 수동 전이와 충돌 없음 확인

## 크기: M | 독립적 — 병렬 작업 가능

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|