## 목표
위저드 Step 6 에이전트 단계에서 PM 잠금으로 ticket_source 한 개가 이미 선택된 경우, 다른 ticket_source 는 추가/변경 불가능해야 한다. (티켓 소스 단일 선택 정책 + PM 잠금 우선)

## 변경 파일 목록
- `clickeye-web/src/lib/wizard-gates.ts`:
  - `findLockedTicketSourceId(ticketSourceSkillIds, pmLockedSkills, pmLockedMcps)` 헬퍼 추가 (단위 테스트용)
- `clickeye-web/src/components/solutions/wizard/steps/step-solution-agents.tsx`:
  - ticket_source 버튼 렌더링: 다른 ticket_source 가 PM 잠금이면 `disabled` + cursor-not-allowed 스타일
  - `selectTicketSource` 함수에 가드 추가 — 다른 ticket_source 가 PM 잠금이면 early return
  - 안내 텍스트: 잠금 사유 표시 (어떤 PM 이 어떤 ticket_source 를 잠갔는지)
- `clickeye-web/src/lib/__tests__/wizard-gates.test.ts`:
  - `findLockedTicketSourceId` 시나리오 4 가지 추가

## 구현 단계
1. wizard-gates.ts 에 findLockedTicketSourceId 추가
2. step-solution-agents.tsx 의 ticketSourceSkills.map / selectTicketSource 보강
3. 테스트 추가
4. typecheck + lint + vitest

## 예상 영향 범위
- PM 잠금 ticket_source 가 있는 경우, 다른 ticket_source 버튼 자체가 클릭 불가
- PM 잠금이 없으면 기존 단일 선택 라디오 동작 그대로
- 게이트(canProceedAgentsStep) 동작 변화 없음 — 이미 OR 조건으로 통과

## STATUS: APPROVED
