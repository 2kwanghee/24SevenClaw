# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[zip] 오케스트레이터 스크립트 — modernize_pipeline.sh + orchestrator.py (단계 순차 실행)**
  > 요청사항: ## 목표

ZIP에 포함되는 **sh/py 오케스트레이터**를 구현한다. plan.json의 태스크 DAG를 순서대로 읽어 각 태스크에 지정된 에이전트·스킬을 호출하며 현대화를 수행한다. (R2, R3)

## As-Is 근거

* 현재 ZIP에 실행 스크립트가 전혀 없음. `.ralph/tasks/*.md`는 작업 지시 마크다운일 뿐
* 레포의 `auto_dev_pipeline.sh` / `ralph-loop` / harness 5단계 패턴이 재사용 가능한 선례

## 작업 내용

1. `scripts/modernize_pipeline.sh` (엔트리): 환경 점검(.env, git, agent CLI) → preflight-review.md 재확인 → [orchestrator.py](<http://orchestrator.py>) 기동
2. `scripts/orchestrator.py`:
   * `plan.json` 로드 → 위상정렬 → 웨이브 단위 순차 실행
   * 태스크별 `claude` (또는 선택 플랫폼 CLI) 호출: 지정 에이전트 + `.ralph/tasks/&lt;id&gt;.md` 프롬프트 주입
   * 태스크 완료 판정: 테스트/빌드 게이트 (harness-loop 패턴, 실패 시 MAX 5회 재시도)
   * **state 파일**(`.clickeye/state.json`)로 진행 상태 기록 → 중단 후 `--resume` 재개
   * `--dry-run` (호출 없이 실행 순서만 출력), `--only &lt;task-id&gt;`, `--wave &lt;n&gt;` 옵션
3. 모든 태스크 시작/종료/결과를 work-recorder 훅으로 기록 (CE-293 기록지침 연동 지점 마련)
4. 위험 태스크(HIGH)는 실행 전 y/N 확인 프롬프트

## 완료 조건

* 샘플 plan.json으로 dry-run/resume/게이트 실패 재시도 시나리오 pytest 검증
* ZIP에 스크립트 포함 + MODERNIZE_README 실행 가이드 현행화

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-07-06 | [zip] 오케스트레이터 스크립트 | 완료 | `plan_builder.py`(DAG 생성) + `orchestrator_templates/{orchestrator.py,modernize_pipeline.sh}`(위상정렬/웨이브 실행/게이트 재시도 MAX5/`--resume`/`--dry-run`/`--only`/`--wave`/HIGH risk confirm) + `zip_builder.py` 통합. pytest 61건(신규 33 + 회귀 28) 통과, ruff/mypy strict 클린 |