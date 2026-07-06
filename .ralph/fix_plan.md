# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [ ] **[contracts/api] Modernize 6단계 Phase 데이터 모델 확장 (requirements/tobe/plan/preflight)**
  > 요청사항: ## 목표

현재 `ModernizeSession.status`(pending→cloning→analyzing→recommending→ready→finalized)를 6단계 워크플로(asis / requirements / tobe / plan / preflight / execute)를 표현할 수 있는 Phase 모델로 확장한다.

## As-Is 근거

* `app/models/modernize_session.py` — phase 개념 없음, scenario 3종(versionup/refactor/language_migrate)만 존재
* `app/models/codebase_analysis.py` — `dep_graph` 선언만 되고 미사용, `target_stack` 미활용
* 산출물 저장 구조가 CodebaseAnalysis(1:1) + Recommendation(N)뿐 → 단계별 산출물 테이블 부재

## 작업 내용

1. contracts 레포에 Phase enum + 단계별 산출물(artifact) 스키마 정의 (Contract 우선 원칙)
2. `modernize_sessions`에 `current_phase` 추가, 신규 테이블 `modernize_phase_artifacts` (session_id, phase, artifact_type, content_md, content_json, approved_at)
3. 구조화 요구사항 스키마: 현재 스택(DB 종류/버전, 런타임, 프레임워크, 인프라) ↔ 목표 스택 쌍
4. Alembic migration (비침습: 신규 생성 + nullable 컬럼 추가만, downgrade 완전 복원)
5. `app/schemas/modernize.py` Pydantic 스키마 동기화 + openapi.json/generated 갱신 (contract-drift 게이트 대응)

## 완료 조건

* 기존 파이프라인 회귀 0 (기존 status 흐름 유지, phase는 병행 도입)
* 마이그레이션 up/down 검증, 스키마 단위 테스트

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|