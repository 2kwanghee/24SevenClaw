# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P2: 기능 요구사항

- [x] **[P8][api+web] AI Team 화면 draft 제출 UI + Linear 동기화 트리거**
  > 요청사항: ## 목표

AI Team 화면에서 실제 draft 제출 UI + 사용자 로컬 Agent가 읽을 수 있는 Linear 동기화 힌트 노출.

## 수정 파일

* 24SevenClaw-web/src/components/ai-team/session-create-modal.tsx: decompose 완료 후 "AI 초안 생성" 버튼 추가
* 24SevenClaw-web/src/components/ai-team/subtask-card.tsx: draft_content 표시 + 제출 버튼
* 24SevenClaw-web/src/hooks/use-orchestrator.ts: submit_draft 훅 연결
* 24SevenClaw-api/app/api/v1/review_pipeline.py: linear_sync_hint 필드 응답에 포함

## 동작 흐름

1. decompose 완료 후 "AI 초안 생성" 버튼 클릭
2. P6의 generate_draft() 호출 → draft_content 자동 채워짐
3. 세션/서브태스크 생성 시 API 응답에 linear_sync_hint 포함
4. 사용자 로컬 Claude Code가 linear 스킬로 해당 힌트 읽어 Linear에 이슈 등록

## 완료 조건

* decompose 후 AI 초안 생성 버튼 클릭 시 draft_content 자동 채워짐
* API 응답에 linear_sync_hint 필드 포함
* npm run typecheck, ruff check 통과

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-17 | P8 AI Team draft UI + Linear sync | ✅ 완료 | generate-drafts 엔드포인트, useGenerateDrafts 훅, "AI 초안 생성" 버튼, LinearSyncHint 패널 |