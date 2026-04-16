# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[api] ClaudeService 구현 (Claude API 연동)**
  > 요청사항: app/services/claude_service.py 신규 작성.

Anthropic Python SDK (anthropic.AsyncAnthropic) 사용.

* analyze_solution(prompt, org_context) → 자연어 → 구조화 요구사항 JSON
* generate_ui_structure(requirements, variant_index) → UI 구조 JSON (메뉴, 페이지, 컬러)
* recommend_pm(requirements, prototype_style, pm_catalog) → PM 추천 + reasoning

프롬프트 엔지니어링 포함. 각 메서드별 시스템 프롬프트 정의.

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-16 | [api] ClaudeService 구현 | ✅ 완료 | anthropic SDK async 메서드 3개 + 테스트 19개 |