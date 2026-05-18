## 목표
직전 case 6 게이트 수정의 동작을 vitest 로 실측 검증한다. 검증을 깔끔히 하기 위해 IIFE 로직을 helper 함수로 추출하고, 두 페이지(new/[sessionId])는 helper 를 호출하도록 정리한다.

## 변경 파일 목록
- `clickeye-web/src/lib/wizard-gates.ts`: **신규** — `canProceedAgentsStep(agents, ticketSourceSkillIds)` helper. skillsData loading 분기는 호출부에서 처리.
- `clickeye-web/src/app/(dashboard)/solutions/new/page.tsx`: case 6 를 helper 호출로 교체
- `clickeye-web/src/app/(dashboard)/solutions/[sessionId]/page.tsx`: 동일
- `clickeye-web/src/lib/__tests__/wizard-gates.test.ts`: **신규** — 6 시나리오 검증
  1. selectedAgents 비어있음 → false
  2. ticket_source 아무것도 없음 → false
  3. PM Linear skill 잠금(selectedSkills) → true
  4. **PM Linear MCP 잠금(selectedMcps) → true** (사용자 보고 케이스)
  5. 사용자가 Notion skill 직접 선택 → true
  6. 모든 컴포넌트 ticket_source 없음 → false

## 구현 단계
1. helper 추출 + 시그니처 확정
2. 두 페이지 case 6 → helper 호출 (skillsLoading/!skillsData 분기는 페이지에 유지)
3. 테스트 작성 + npm test 실행
4. typecheck + lint

## 예상 영향 범위
- 동작 변화 없음(로직 동일, 위치만 helper 로 이동)
- 두 페이지 중복 제거 + 테스트 가능 형태로 정리
- vitest 결과로 사용자 케이스 결정적 검증

## STATUS: APPROVED
