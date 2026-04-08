# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[web+api] 추천 Reasoning — 각 추천 항목에 "왜 추천됨" 설명 추가**
  > 요청사항: ## 목표

추천 에이전트/스킬/파이프라인마다 "왜 이것을 추천하는가" 설명을 제공하여 AI가 분석/추론했다는 느낌을 준다.

## 현황

* recommend_service.py: 정적 규칙 해시맵 (AGENT_RULES, SKILL_RULES 등)
* 추천 응답에 reasoning 필드 전무 — ID 리스트만 반환
* 프론트에서 "추천" 배지만 표시, 근거 설명 없음

## 작업 내용

### API

* RecommendResponse 스키마에 reasoning 필드 추가 (각 항목별 1-2문장)
* recommend_service.py에 REASONING_RULES 딕셔너리 추가
* 추천 응답 예시:

  ```json
  {
    "agents": [{"id": "fullstack", "reasoning": "SaaS는 프론트+백엔드 통합이 필수이므로 풀스택 전문가가 효율적입니다"}],
    "summary": "SaaS 프로젝트에 최적화된 3명의 에이전트와 4개의 스킬을 추천합니다."
  }
  ```

### Web

* step-agents.tsx: 추천 에이전트 카드에 reasoning 툴팁/설명 표시
* step-skills.tsx: 추천 스킬 카드에 reasoning 표시
* step-pipelines.tsx: 추천 파이프라인에 reasoning + 조합 시너지 설명
* use-recommend.ts: 추천 응답에서 reasoning 데이터 저장
* wizard store의 Recommendations 타입 확장

## 사이즈: M

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|