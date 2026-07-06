# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[api] Phase 2 — 현대화 요구사항 분석 단계 구현 (구조화 스펙 수집·정제)**
  > 요청사항: ## 목표

현재 `goals_text` 자유 텍스트 + 시나리오 라디오뿐인 요구사항 입력을, **구조화된 현대화 요구사항 분석 단계**로 격상한다.

## As-Is 근거

* `modernize.py` 세션 생성 시 `goals_text`가 LLM 컨텍스트로만 전달되고 요구사항 산출물이 없음
* `target_stack`(JSON) 필드는 스키마에만 있고 파이프라인 미활용
* refactor / language_migrate 시나리오는 시스템 프롬프트만 다른 껍데기 (`recommendations.py:55-68`)

## 작업 내용

1. 요구사항 수집 API: 현재 스택(AS-IS 분석 결과 자동 프리필) ↔ 목표 스택 입력
   * DB: MariaDB / MySQL / MSSQL / Oracle / PostgreSQL 등 → 목표 DB
   * 런타임/언어 버전, 프레임워크, 배포 형태(VM 리호스트 / 컨테이너 리플랫폼)
2. metaprompt 방식 LLM 정제: goals_text + 구조화 입력 → `requirements.md` + `requirements.json` 산출물 생성·저장 (phase_artifacts)
3. 요구사항 유형 태깅 (versionup / db_migrate / language_migrate / replatform / refactor) — 이후 에이전트 매핑(CE-291)의 입력이 됨
4. 시나리오 3종을 요구사항 태그 기반으로 재정의, fallback 로직 정비

## 완료 조건

* 세션이 asis 완료 후 requirements phase로 전이, 산출물 조회 API 제공
* LLM 키 미설정 시에도 구조화 입력만으로 산출물 생성 (기존 fallback 원칙 유지)
* 단위 테스트 동반

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-07-06 | [api] Phase 2 — 현대화 요구사항 분석 단계 구현 | 완료 | `requirements_svc.py` 신규(as-is 유추/태그 계산/scenario 재정의/metaprompt 정제+fallback), `POST·GET /modernize/sessions/{id}/requirements` 엔드포인트, pipeline `asis→requirements` phase 전이, contracts `RequirementTag` 동기화. pytest 44 passed, ruff/mypy clean, tsc --noEmit clean |