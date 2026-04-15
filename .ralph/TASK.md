# Ralph Loop — 구현 결과

## [web] AI Team 3계층 운영 대시보드 UI

### 변경 파일

| 파일 | 유형 | 설명 |
|------|------|------|
| `24SevenClaw-web/src/lib/api-client.ts` | 수정 | 오케스트레이터/리뷰 파이프라인 타입 + API 메서드 추가 |
| `24SevenClaw-web/src/hooks/use-orchestrator.ts` | 신규 | TanStack Query 훅 (세션, 서브태스크, 리뷰, 뮤테이션) |
| `24SevenClaw-web/src/components/ai-team/subtask-card.tsx` | 신규 | SubTask 카드 (역할배지 + 상태 + 미리보기) |
| `24SevenClaw-web/src/components/ai-team/pipeline-stepper.tsx` | 신규 | 10단계 파이프라인 스테퍼 (데스크탑 가로 + 모바일 프로그레스 바) |
| `24SevenClaw-web/src/components/ai-team/review-diff-viewer.tsx` | 신규 | 리뷰 diff 뷰어 + 병합/거절 버튼 |
| `24SevenClaw-web/src/components/ai-team/session-create-modal.tsx` | 신규 | 세션 생성 모달 (폼 → decompose → 서브태스크 확인 → 배정 확정) |
| `24SevenClaw-web/src/app/(dashboard)/projects/[projectId]/ai-team/page.tsx` | 신규 | 3계층 대시보드 페이지 |
| `24SevenClaw-web/src/app/(dashboard)/projects/[projectId]/page.tsx` | 수정 | 프로젝트 상세에 "AI Team" 링크 추가 |

### 구현 내용

1. **3계층 레이아웃 렌더링**
   - 상단 (사람): 프로젝트 단계 배지, 리스크 플래그, 승인 버튼 (validating 단계)
   - 중단 (PM AI): 10단계 파이프라인 스테퍼, prompt_template 뷰어, 리스크 칩
   - 하단 (AI Team): SubTask 카드 그리드 (역할배지 + 상태 + 미리보기)

2. **세션 생성 + decompose 플로우**
   - "새 작업 요청" 버튼 → 모달 → 제목/설명 입력 → 자동 decompose → 서브태스크 확인 → 배정 확정

3. **리뷰 diff 뷰어 + 병합/거절**
   - reviewing 단계에서 ReviewRound 목록 표시
   - 각 라운드: 초안, 리뷰 내용, diff 요약, 병합 결과 뷰
   - 액션: 초안 수락 / 리뷰 수락 / 거절 (사유 입력)

4. **30초 폴링 자동 갱신**
   - useSessionSummary, useReviewRounds에 refetchInterval: 30_000 설정

### 테스트 결과

- ESLint: 신규 파일 에러 없음 (기존 경고만)
- TypeScript: 신규 파일 타입 에러 없음 (기존 insights/page 에러만)
- Next.js build: 성공, `/projects/[projectId]/ai-team` 라우트 등록 확인

### 남은 이슈

- `insights/page.js` 관련 기존 TypeScript 에러 (본 작업과 무관)
- Figma 디자인 소스 없이 구현 (디자인 확정 후 미세 조정 필요)
