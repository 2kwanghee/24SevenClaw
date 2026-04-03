# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[engine] 카탈로그 JSON 확장 (외부 스킬, 플랫폼, 파이프라인)**
  > 요청사항: ## 목표

CLI 카탈로그 JSON을 웹 서비스용으로 확장

## 작업 내용

* skills.json — 외부 도구 스킬 추가 (notion, slack, telegram, github, teams, database)
  * 각 스킬별 API 키 필드, .env 변수명 정의
* platforms.json 신규 생성 (claude-code, gemini-cli, codex, cursor)
  * 각 플랫폼별 설정 디렉토리, 에이전트 파일 위치, 설정 파일 경로
* pipelines.json 신규 생성 (harness, tdd, ai-critique, telegram, lint-gate, ralph-loop)

## 사이즈: S

## 일정: 04-07 \~ 04-08

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|