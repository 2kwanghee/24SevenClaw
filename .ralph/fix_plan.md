# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[api] Phase 3 — To-Be 아키텍처 디자인 단계 구현 (설계 문서 + 갭 매트릭스)**
  > 요청사항: ## 목표

요구사항(Phase 2) + AS-IS 분석(Phase 1)을 입력으로 **목표 아키텍처 설계 산출물**을 생성하는 단계를 신설한다.

## As-Is 근거

* 현재는 권장안(Recommendation) 목록이 to-be의 대용이며 설계 문서/다이어그램 산출물이 없음
* `CodebaseAnalysis.dep_graph` 미구현 → as-is 구조 시각화 불가

## 작업 내용

1. `tobe-architecture.md` 생성 (LLM): 목표 스택 구성, 계층 구조, Mermaid 다이어그램(as-is ↔ to-be), 랜딩존(디렉토리/인프라 구성) 정의
2. **갭 매트릭스** 생성: 영역(코드/의존성/DB/인프라/테스트)별 as-is → to-be 변경 항목 + 전환 방식(리호스트/리플랫폼/리팩터)
3. `dep_graph` 최소 구현: manifest 기반 모듈 의존성 그래프 채움 (Mermaid 소스로 재사용)
4. 산출물 phase_artifacts 저장 + 조회 API, deep-thinker(Opus) 위임 규칙은 복잡도 ≥0.7일 때만

## 완료 조건

* requirements 승인 후 tobe phase 전이, `tobe-architecture.md` + `gap-matrix.json` 산출
* LLM 키 미설정 시 정적 갭 매트릭스(outdated/EOL 기반)로 폴백
* 단위 테스트 동반

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-07-06 | [api] Phase 3 — To-Be 아키텍처 디자인 단계 구현 | 완료 | `manifest.build_dependency_graph` 최소 구현 + `CodebaseAnalysis.dep_graph` 저장, `services/modernize/tobe.py` 신설(LLM+deterministic fallback, 복잡도≥0.7 시 opus 모델 격상), `GET/POST phase-artifacts` 엔드포인트 추가(requirements 승인 시 tobe 자동 생성+phase 전이). 단위 테스트 38건 통과, 무관 40건 실패는 기존 환경 이슈(사전 확인 완료, 회귀 아님) |