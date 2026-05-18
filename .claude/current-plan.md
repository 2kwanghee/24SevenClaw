## 목표
위저드 7단계(case 6, 에이전트 단계)에서 "티켓 소스 필수" 게이트가, PM 잠금으로 Linear가 MCP 서버로만 들어있는 경우를 인식하지 못해 다음 버튼이 비활성화되는 버그 수정.

## 원인
- 카탈로그(integrations.json): `linear`는 `category=ticket_source` 의 skill 로 등록.
- pm_compositions.json: `linear`는 `component_type=mcp_server` 의 MCP 로 등록.
- step-solution-agents.tsx 의 PM composition 자동 채우기 useEffect: `comp.mcp_servers` → `selectedMcps`, `comp.skills` → `selectedSkills` 로 분리 저장.
- 결과: 사용자가 PM 선택 시 `selectedMcps` 에는 "linear" 가 들어가지만 `selectedSkills` 에는 안 들어감.
- canProceed case 6 검사가 `selectedSkills` 만 보고 ticket_source 충족 여부 판정 → 게이트 닫힘.

## 변경 파일 목록
- `clickeye-web/src/app/(dashboard)/solutions/new/page.tsx`:
  - case 6: ticketSource 충족 여부를 `selectedSkills` + `selectedMcps` 양쪽에서 검사
- `clickeye-web/src/app/(dashboard)/solutions/[sessionId]/page.tsx`:
  - 동일
- `clickeye-web/src/components/solutions/wizard/steps/step-solution-agents.tsx`:
  - `ticketSourceSkills.map` 의 isSelected/isLocked 도 selectedMcps/pmLocked.mcps 양쪽 검사
  - "티켓 소스 미선택" 경고도 양쪽 검사
  - selectTicketSource 도 mcp 잠금 보호 추가 (안전성)

## 구현 단계
1. 두 페이지의 case 6 검사 로직 보강
2. step-solution-agents.tsx UI 표시 + 안내 경고 + 클릭 가드 보강
3. typecheck + lint

## 예상 영향 범위
- PM 이 Linear/Notion 을 MCP 서버로만 잠금한 케이스에서 정상 진행
- 기존 PM 이 skill 로 잠근 케이스도 그대로 동작 (양쪽 OR 조건)
- 사용자가 ticket_source 를 자유 선택한 케이스도 변동 없음
- UI 잠금/선택 표시가 게이트와 일관 동작

## STATUS: APPROVED
