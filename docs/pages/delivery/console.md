---
title: 딜리버리 콘솔 (인게이지먼트)
category: page
status: implemented
version: 1.0.0
route: /delivery/[engagementId]
pages:
  - src/app/(dashboard)/delivery/[engagementId]/page.tsx
components:
  - src/components/delivery/console-header.tsx
  - src/components/delivery/delivery-stepper.tsx
  - src/components/delivery/issue-board.tsx
  - src/components/delivery/review-list.tsx
  - src/components/delivery/cost-card.tsx
  - src/components/delivery/governance-policy-panel.tsx
  - src/components/delivery/mock-mode-toggle.tsx
store: useMockMode (목업 토글), useRBACStore (권한)
last_updated: 2026-07-22
related:
  - src/app/(dashboard)/delivery/[engagementId]/page.tsx
  - src/hooks/use-orchestrator.ts
  - src/hooks/use-llm-ledger.ts
  - src/hooks/use-governance.ts
---

## 목적

ClickEye의 메인 콘솔. 사용자는 인게이지먼트별 딜리버리 진행 상황을 실시간으로 추적하고, 세션 선택, 이슈 보드, 검토 대기, 원가 계산, 거버넌스 정책을 통합 관리한다. Mock 모드로 데모 데이터 확인 가능.

---

## 레이아웃

```
┌─────────────────────────────────────────────────────────────┐
│ 우측 상단 [Mock 모드 토글]                                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ A. 콘솔 헤더 (인게이지먼트명 · 현재 페이즈 · 싱크 버튼)    │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ENG-204 | 빌드 중 (building) [Linear 싱크 →]           │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ 세션 탭 [세션명 · 페이즈 배지]                              │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ [SEE-001 drafting] [SEE-002 reviewing] [...]           │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ 2열 그리드 (좌 메인 / 우 레일):                              │
│ ┌────────────────────┐  ┌──────────────────┐              │
│ │                    │  │ D. 비용 카드     │              │
│ │ B. 스텝퍼 (5단계)  │  │ (LLM 원장)       │              │
│ │ intake→...→merge   │  │                  │              │
│ │                    │  │ E. 검토 대기     │              │
│ │ C. 이슈 보드       │  │ (승인 필요)      │              │
│ │ (린별 칩)          │  │                  │              │
│ │                    │  │ F. 거버넌스      │              │
│ │ E. 검토 대기       │  │ (정책·override)  │              │
│ │ (round list)       │  │                  │              │
│ └────────────────────┘  └──────────────────┘              │
│                                                             │
│ 스코프 푸터 (현재/미래)                                     │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ ⚫ 현재 스코프: ... │ ⚪ 미래 스코프: ...                │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 스토리보드

**시나리오 1: 정상 콘솔 로드**
1. `/delivery/ENG-123` 진입
2. 프로젝트·세션 조회 → 첫 세션 자동 선택
3. 선택 세션의 요약(phase, subtasks) 조회
4. A(헤더) + B(스텝퍼) + C(보드) + D(비용) + E(검토) + F(정책) 렌더링
5. Mock 모드는 토글로 픽스처 데이터 전환

**시나리오 2: 세션 전환**
1. 세션 탭 [SEE-002]를 클릭
2. 상태 업데이트 (activeSessionId → SEE-002)
3. 새 세션의 보드/검토 데이터 재조회

**시나리오 3: Linear 싱크**
1. [Linear 싱크 →] 버튼 클릭
2. `syncLinearStates.mutate()` 호출
3. 로딩 상태(isPending) 표시 후 완료

**시나리오 4: 권한 제한**
1. RBAC 로드 후 `settings:manage` 없으면 비용 카드는 "제한됨" 상태
2. 거버넌스 정책은 항상 조회 가능 (공개 정보)

---

## 기능 요구사항

### 필수 기능
- [x] Mock 모드 토글 (픽스처 데이터 ↔ 실 API)
- [x] 콘솔 헤더 (인게이지먼트명, 페이즈, Linear 싱크)
- [x] 세션 탭 인터페이스 (다중 세션 선택)
- [x] 스텝퍼 (5단계: intake→plan→build→review→merge)
- [x] 이슈 보드 (Kanban 스타일, subtasks 칩)
- [x] 검토 대기 (review rounds, 승인 버튼)
- [x] 비용 카드 (LLM 원장, 권한 제어)
- [x] 거버넌스 정책 (SSOT, override 표시)
- [x] 스코프 푸터 (현재/미래 영역 표시)
- [x] 에러 상태 (프로젝트 없음, 세션 없음, API 에러)
- [x] 로딩 상태 (스켈레톤)

### 선택/개선 사항
- [ ] 실시간 업데이트 (WebSocket)
- [ ] 이슈 칩 클릭 → 상세 보기
- [ ] 페이즈별 자동 진행 (auto-progress 플로우)
- [ ] 비용 차트 드릴다운
- [ ] 검토 히스토리

---

## 상태 관리

| 상태 | 타입 | 출처 | 용도 |
|------|------|------|------|
| `selectedSessionId` | `string` | 로컬 (useState) | 현재 선택 세션 |
| `projectData` | `Project` | `useProject()` | 인게이지먼트 정보 |
| `sessionsData` | `SessionList` | `useSessionList()` | 세션 목록 |
| `summaryData` | `SessionSummary` | `useSessionSummary()` | 세션 요약 (phase, subtasks) |
| `teamStatesData` | `TeamState[]` | `useLinearTeamStates()` | Linear 팀 상태 |
| `reviewDataRaw` | `ReviewRound[]` | `useReviewRounds()` | 검토 라운드 |
| `ledgerData` | `LlmLedgerSummary` | `useLlmLedgerSummary()` | LLM 원장 (권한: settings:manage) |
| `policyData` | `GovernancePolicy` | `useGovernancePolicy()` | 거버넌스 정책 (공개) |
| `overridesData` | `ContractOverride[]` | `useProjectOverrides()` | 계약 override (프로젝트별) |
| `mockMode` | `boolean` | `useMockMode()` | Mock 데이터 사용 여부 |
| `rbacLoaded` | `boolean` | `useRBACStore()` | 권한 로드 완료 |

---

## API 연동

| 메서드 | 엔드포인트 | 트리거 | 설명 |
|--------|-----------|--------|------|
| `GET` | `/api/v1/projects/{projectId}` | 페이지 로드 | 인게이지먼트 조회 |
| `GET` | `/api/v1/projects/{projectId}/sessions` | 페이지 로드 | 세션 목록 |
| `GET` | `/api/v1/sessions/{sessionId}/summary` | 세션 선택 | 세션 요약 |
| `GET` | `/api/v1/sessions/{sessionId}/team-states` | 페이지 로드 | Linear 팀 상태 |
| `GET` | `/api/v1/sessions/{sessionId}/review-rounds` | 페이지 로드 (auto-progress 페이즈만) | 검토 라운드 |
| `POST` | `/api/v1/sessions/{sessionId}/sync-linear` | [Linear 싱크] 클릭 | Linear 상태 동기화 |
| `GET` | `/api/v1/projects/{projectId}/llm-ledger/summary` | 페이지 로드 (settings:manage만) | LLM 원장 |
| `GET` | `/api/v1/governance/policy` | 페이지 로드 | 거버넌스 정책 |
| `GET` | `/api/v1/projects/{projectId}/contracts/overrides` | 페이지 로드 | 계약 override |

---

## 접근성 / 반응형

- [x] 세션 탭: `role="tablist"` / `aria-selected`
- [x] 비용 카드 권한 제한: `aria-label` "제한된 콘텐츠"
- [x] 에러 알림: `AlertTriangle` 아이콘 + 설명 텍스트
- [x] 로딩 상태: 스켈레톤 맥락 제공
- [x] 모바일: 2열 그리드 → 단일 열 (lg 기준)
- [x] 다크 모드: 모든 컬러 토큰 사용

---

## 구현 노트

- **Mock 모드**: `useMockMode().enabled` 따라 실 API 쿼리 비활성화, 픽스처로 대체. 로딩/에러 플래그도 false로 눌러 분기 제거.
- **세션 비어있음**: 첫 진입 시 세션이 없으면 `/projects/{projectId}/ai-team` 링크로 안내.
- **자동 진행 페이즈**: `AUTO_PROGRESS_PHASES = ["drafting", "reviewing", "integrating", "approved", "transitioning"]` 에서만 검토 라운드 조회.
- **권한 제어**: 비용 카드는 `settings:manage` 필수. 거버넌스 정책은 공개.
- **세션 쿼리 키**: Mock ON이면 빈 문자열로 쿼리 비활성화.
