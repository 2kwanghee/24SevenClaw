# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[P1][engine] /24SeventStart 슬래시 커맨드 + 온보딩 스크립트 생성**
  > 요청사항: ## 목표

ZIP 다운로드 후 Claude Code에서 `/24SeventStart` 한 줄로 로컬 개발 파이프라인 셋업 완료.

## 작업 범위

### 신규 파일

* `24SevenClaw-api/app/engine/templates/commands/24seven-start.md.j2`

### 수정 파일

* `24SevenClaw-api/app/engine/generator.py` — `generate_all()`에 `_emit_start_command()` 추가

### 동작 내용 (마크다운 지시사항)

1. `.env` 파일 존재 확인 → 없으면 `.env.example` 복사
2. 필수 키 목록 검증 (`ANTHROPIC_API_KEY`, `LINEAR_API_KEY`, `LINEAR_TEAM_ID` 등)
3. 누락된 키에 대해 `docs/api-keys/*.md` 가이드 링크 안내
4. 사용자에게 대화형으로 입력 요청 (한 번에 한 키씩 질문)
5. 모든 키 완료 시 "24SevenClaw 솔루션 셋업 완료" 메시지

### 플랫폼별 경로

* Claude Code: `.claude/commands/24SeventStart.md`
* Gemini CLI: `.gemini/commands/24SeventStart.md`
* Cursor: `.cursor/commands/24SeventStart.md`
* Codex: `AGENTS.md`에 절차 삽입

## 재사용

* `app/engine/env_generator.py:get_env_var_definitions()` — 필수 키 목록 소스

## 완료 조건

* ZIP 내 `.claude/commands/24SeventStart.md` 존재 확인
* Claude Code에서 `/24SeventStart` 실행 시 누락 키 대화형 요청 동작

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-18 | [P1][engine] /24SeventStart 커맨드 | ✅ 완료 | generator.py + 24seven-start.md.j2 구현 확인, 테스트 11/11 통과 |