---
route: /solutions/new (Step 6)
title: 에이전트 선택
category: page
status: implemented
version: 2.0.0
components:
  - src/components/solutions/wizard/steps/step-solution-agents.tsx
store: useSolutionWizardStore → setAgents
last_updated: 2026-06-15
---

## 목적
PM 구성에 포함될 AI 에이전트, 스킬(ticket_source 단일 선택 필수 + 추가 스킬 다중), 훅, MCP 서버를 선택/조정. PM이 구성을 통해 잠근 항목은 해제 불가능하고 자동 선택됨.

---

## 레이아웃

```
┌────────────────────────────────────────────┐
│ 🔒 PM 구성 항목은 변경할 수 없습니다.       │
│ "PM 이름" 의 기본 구성을 따릅니다.          │
├────────────────────────────────────────────┤
│                                            │
│ 🤖 AI 에이전트 선택                        │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│ │ ☑ 에이전트1│ │ ☑ 에이전트2│ │ □ 에이전트3│    │
│ │ 설명       │ │ 설명 [잠금]  │ │ 설명      │    │
│ └──────────┘ └──────────┘ └──────────┘    │
│                                            │
│ 🔧 스킬 선택                               │
│ ▼ Ticket Source (필수 단일 선택)           │
│ ○ [스킬1] [스킬2] [스킬3 필수-잠금]       │
│ ▼ 추가 스킬 (다중 선택)                    │
│ ☑ [스킬A] ☑ [스킬B] □ [스킬C]             │
│                                            │
│ ⚡ 훅 선택                                 │
│ ☑ [훅1 필수] ☑ [훅2] □ [훅3]             │
│                                            │
│ 🌐 MCP 서버 선택                          │
│ ☑ [MCP1] ☑ [MCP2] □ [MCP3]              │
│                                            │
└────────────────────────────────────────────┘
```

---

## 스토리보드

1. 스텝 진입 → `pmProfiles.getComposition` 호출
   - PM 구성의 agents/skills/hooks/mcp_servers 목록을 `pmLocked` 에 저장
   - 잠긴 항목들을 현재 선택(`selectedAgents` 등)에 강제 병합
2. 카탈로그 훅 로드 (`useCatalogAgents`, `useCatalogSkills`, `useCatalogHooks`, `useCatalogMCPs`)
3. 세션이 있으면 `prototypeSessions.recommendComponents` 호출 (추천 자동 선택)
4. UI 렌더링
   - 상단 배너: PM 잠금 여부 / 추천 여부 / 일반 안내
   - 에이전트 그리드 (다중 선택, 잠금 항목 비활성)
   - 스킬: **Ticket Source** 필수 단일 선택 + **추가 스킬** 다중 선택
   - 훅: 다중 선택 (required 훅 자동 체크·잠김)
   - MCP 서버: 다중 선택 (required 서버 자동 체크·잠김)
5. 사용자 선택 → `setAgents({ selectedAgents, selectedSkills, selectedHooks, selectedMcps })`
6. canProceed 조건 검증:
   - `agents` 로딩 완료 (최소 1개)
   - `ticket_source` 스킬 정확히 1개 선택
7. "다음" 클릭 → Step 7(플랫폼 선택) 이동

---

## 기능 요구사항

### 에이전트
- [x] 다중 선택 (체크박스)
- [x] PM 잠금 항목 자동 선택 + 비활성화 (`pmLocked.agents`)
- [x] PM 잠금 배지 (`PmLockBadge`)

### 스킬
- [x] **Ticket Source** 카테고리: 필수 단일 선택 (radio 그룹)
  - `selectTicketSource(skillId)` 핸들러
  - 다른 ticket_source 선택 시 기존 제거 (잠금 제외)
  - 다른 ticket_source가 PM 잠금이면 변경 불가
- [x] **추가 스킬** (다른 카테고리): 다중 선택 (체크박스)
- [x] 각 스킬 env_var 배지 표시
- [x] PM 잠금 항목 자동 선택 + 비활성화

### 훅
- [x] 다중 선택 (체크박스)
- [x] required 훅 자동 체크·잠김
- [x] PM 잠금 항목 비활성화

### MCP 서버
- [x] 다중 선택 (체크박스)
- [x] required 서버 자동 체크·잠김
- [x] PM 잠금 항목 비활성화

### 상태 관리
- [x] PM 구성 로드 시 자동 적용 (ref: `didPmLoad`)
- [x] 프로토타입 기반 추천 자동 선택 (ref: `didAutoSelect`)
- [x] 카탈로그 로딩 상태 관리

### UI
- [x] 상단 배너: PM 잠금 / 추천 안내 / 일반 안내 (조건부)
- [x] 에러 알림 (각 카탈로그 fetch 실패)
- [x] 로딩 스켈레톤 (에이전트, 스킬)

### 검증
- [x] `canProceedAgentsStep`: agents 로딩 완료 ∧ selectedAgents ≥ 1 ∧ ticket_source 정확히 1개

---

## 상태 관리

| 상태 | 타입 | 출처 | 용도 |
|------|------|------|------|
| `selectedAgents` | `string[]` | store | 선택한 에이전트 ID 목록 |
| `selectedSkills` | `string[]` | store | 선택한 스킬 ID 목록 (ticket_source + 추가 포함) |
| `selectedHooks` | `string[]` | store | 선택한 훅 ID 목록 |
| `selectedMcps` | `string[]` | store | 선택한 MCP 서버 ID 목록 |
| `pmLocked` | `PmLockedSlugs` | 로컬 state | PM이 잠금한 항목 (agents/skills/hooks/mcps) |
| `catalogRecommended` | `{ agents: string[]; skills: string[] }` | 로컬 state | 프로토타입 기반 추천 목록 |

---

## API 연동

| 메서드 | 함수 | 트리거 | 설명 |
|--------|------|--------|------|
| `GET` | `pmProfiles.getComposition` | 스텝 진입 | PM 구성의 agents/skills/hooks/mcp_servers 조회 |
| `POST` | `prototypeSessions.recommendComponents` | 스텝 진입 | 프로토타입 기반 컴포넌트 추천 |
| **Catalog Hooks** | `useCatalogAgents`, `useCatalogSkills`, `useCatalogHooks`, `useCatalogMCPs` | 스텝 진입 | 카탈로그 데이터 조회 (TanStack Query) |

---

## 접근성 / 반응형

- [x] 에이전트 그리드: `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3`
- [x] 스킬 섹션: 구분된 heading
- [x] 훅/MCP: 다중 선택 체크박스
- [x] 잠금 배지: `title` attribute + 색상 시각화
- [x] 로딩 상태: `aria-busy`, `aria-hidden` (스켈레톤)

---

## 구현 노트

- **Ticket Source 단일 선택**: PM이 다른 ticket_source를 잠금했으면 그 선택은 유지, 사용자는 변경 불가
- **PM 잠금 정책**: `pmLocked` 에 포함된 slug는 `toggleAgent` / `toggleSkill` / `toggleHook` / `toggleMcp` 에서 조기 반환 (함수 첫 줄)
- **추천 자동 선택**: `didAutoSelect` ref로 한 번만 호출 (stale closure 방지)
- **자동 체크**: required 항목은 store 초기화 시 자동 포함 (PM 구성 또는 카탈로그에서)
- 번역 키: `wizard.step5.agents` (note: step5 = wizard index 5)
- `useEffect` 의존성: `[selectedPmProfileId, token]` (PM 로드), `[sessionId, token]` (추천)
- canProceed: `canProceedAgentsStep` 함수로 검증 (agents 로딩 ∧ selectedAgents ≥ 1 ∧ ticket_source exactly 1)
- env_var 배지: 스킬이 `env_vars` 배열을 가지면 각 변수명을 배지로 표시
