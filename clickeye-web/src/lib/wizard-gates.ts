/**
 * 솔루션 위저드 단계별 진행 게이트 헬퍼.
 *
 * 페이지 컴포넌트의 canProceed IIFE 가 복잡해지면서 일부 게이트는 helper 로 분리해
 * 단위 테스트 가능하게 만든다. skillsData 로딩 분기 등 React 상태 의존 분기는
 * 호출부에서 처리하고, 여기서는 순수 함수만 다룬다.
 */

export interface AgentsStepState {
  selectedAgents: string[];
  selectedSkills: string[];
  selectedMcps?: string[];
}

/**
 * Step 6 (에이전트 선택 단계) 진행 가능 여부.
 *
 * 통과 조건:
 *  - 에이전트가 1개 이상 선택됨
 *  - 카탈로그에 ticket_source 가 있다면, selectedSkills 또는 selectedMcps 중 하나에 매칭되는 ID 가 있음.
 *    (PM 이 동일 통합을 skill / mcp_server 어느 type 으로 잠궜든 인정)
 *
 * skillsData 로딩 분기는 호출부에서 처리한 뒤 ticketSourceSkillIds 를 넘긴다.
 */
export function canProceedAgentsStep(
  agents: AgentsStepState,
  ticketSourceSkillIds: string[],
): boolean {
  if (agents.selectedAgents.length === 0) return false;
  if (ticketSourceSkillIds.length === 0) return true;

  const selectedMcps = agents.selectedMcps ?? [];
  const hasTicketSource =
    agents.selectedSkills.some((s) => ticketSourceSkillIds.includes(s)) ||
    selectedMcps.some((m) => ticketSourceSkillIds.includes(m));
  return hasTicketSource;
}
