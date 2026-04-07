# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P2: 기능 요구사항

- [x] **[engine] Gemini CLI 플랫폼 템플릿**
  > 요청사항: ## 목표

Gemini CLI 플랫폼용 PlatformAdapter 구현

## 작업 내용

* .gemini/ 디렉토리 구조 정의
* GeminiAdapter 구현 (PlatformAdapter 인터페이스)
* 에이전트 .md 템플릿을 Gemini 형식으로 변환
* .gemini/settings.json 생성기
* .gemini/agents/ 경로 매핑
* 기존 Handlebars 템플릿 재활용 + Gemini 전용 변수

## 사이즈: M

## 일정: 04-18

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|