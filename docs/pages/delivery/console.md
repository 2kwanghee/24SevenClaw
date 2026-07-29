---
title: 딜리버리 콘솔 (인게이지먼트)
category: page
status: needs-revision   # I-14 IA 변경 확정 — 구현은 별도 승인 후
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
last_updated: 2026-07-29
related:
  - src/app/(dashboard)/delivery/[engagementId]/page.tsx
  - src/hooks/use-orchestrator.ts
  - src/hooks/use-llm-ledger.ts
  - src/hooks/use-governance.ts
---

> ## IA 변경 (I-14 · 2026-07-29) — 목록/사이드바 반영 완료, 상세 탭은 미반영
>
> **적용됨**
> - `layout.tsx` `navItems`에서 `/projects` 제거 (라우트·페이지는 유지)
>   — 온보딩 투어 앵커 `data-tour="projects-link"`는 `/delivery` 항목으로 이전
> - `/delivery` 목록을 벤토 카드 → **리스트 + 우측 슬라이드 패널**로 교체
> - 행 클릭은 **선택**이며 진입이 아니다. 진입은 패널의 `진입하기`(→ `/delivery/[id]`)로만.
>   보조 링크 `프로젝트 개요`(→ `/projects/[id]`)
> - 세션·서브태스크는 **선택된 1건만 지연 조회** (목록에서 N+1 방지)
>
> **미반영 (후속)**
> - 프로젝트 상세의 8탭 컨텍스트 바(기존 4 + 신규 4) — 신규 4탭 페이지가 아직 없다
> - 요약 패널 컴포넌트 분리 (`src/components/delivery/`로 추출)
>
> **데이터 실측 — 와이어프레임과 다른 부분**
>
> | 요약 항목 | 상태 | 근거 |
> |---|---|---|
> | 현재 단계 | 구현 | `useSessionList` → `session.phase` |
> | 서브태스크 진행 | 구현(파생) | `useSessionSummary` → `subtasks[].status` 집계. **티켓이 아니라 서브태스크 기준**으로 라벨링 |
> | 마지막 활동 | 구현 | `project.updated_at` |
> | 진행률 % | 파생만 가능 | 전용 진행률 필드가 없다. 서브태스크 완료 비율로 표시 |
> | 외부연동 blocker | **불가** | `HumanIntegrationGate` 미구현 (Stage 1) |
> | 구독 시트 | **불가** | `src/lib/api-client.ts`에 seat 타입·호출 0건 |
>
> 불가 2종은 "도입 후 제공" 자리표시로만 노출하고 값을 추정하지 않는다.
>
> **타임스탬프는 상대 시각("2분 전")이 아니라 결정적 UTC 절대 시각으로 표시한다.**
> 이유: 상대 시각과 `toLocaleString()`은 `Date.now()`·타임존에 의존해 SSR 결과와 클라이언트
> 결과가 달라져 하이드레이션 불일치를 만든다. 이를 `mounted` 게이트로 우회하려 하면
> 이 프로젝트의 `react-hooks` 규칙(효과 내 동기 `setState` 금지 — **lint error**)에 걸리고,
> 렌더 중 `Date.now()` 호출도 `react-hooks/purity` 대상이다. ISO 문자열을 그대로 자르는
> `formatUtc()`는 세 문제를 모두 피한다. 상대 시각이 필요하면 별도 클라이언트 전용
> 컴포넌트로 분리해야 한다(후속 과제).
>
> ---
>
> ### 원래 결정 내용 (참고)
>
> **딜리버리가 단일 진입점이 된다.** 사이드바 1뎁스의 `프로젝트` 메뉴를 제거한다.
>
> 근거 — 두 메뉴가 같은 엔티티의 같은 목록을 중복 노출하고 있었다:
> - `engagement` 모델이 API에 없다 (`grep -rlni "engagement" clickeye-api/app` → 0건)
> - `delivery/[engagementId]/page.tsx:75` — `const projectId = engagementId;`
> - `delivery/page.tsx:20` — `useProjects()` (= `/projects`와 동일 훅·동일 목록)
> - `delivery/[engagementId]/page.tsx:260` — 이미 `/projects/[id]/ai-team`을 자식처럼 링크
>
> 변경 내용:
> 1. **`/delivery` 목록을 벤토 카드 → 리스트(행)로.** 행 클릭 시 즉시 진입하지 않고
>    **우측 슬라이드 패널**에 요약을 띄운다. 진입은 패널의 `진입하기`로만.
>    (쇼핑몰식 "상품 클릭 → 즉시 진입" 구조를 의도적으로 배제)
> 2. 슬라이드 패널 요약 5종 — 현재 단계+진행률 / 티켓 진행(완주·검증) / 마지막 활동 시각 /
>    현재 막힌 것(blocker) / **어떤 구독 시트로 진행 중인지**
> 3. 프로젝트 상세 = 기존 4탭(콘솔·개요·AI팀·계약) + 신규 4탭(매니페스트·실행·외부연동·배포)
> 4. **`/projects/*` 라우트는 삭제하지 않는다** — 기존 URL·북마크 유지. 사이드바 노출만 정리
> 5. 디자인은 최대한 심플한 컨설팅 스타일(각진 모서리·헤어라인 규칙·tabular 숫자,
>    색은 기존 토큰 유지)
>
> 시각 기준선: `docs/wireframes/multiproject-delivery.html` (딜리버리 목록 화면)
> `엔게이지먼트`↔`프로젝트` 용어 이원화는 부채로 남긴다 — i18n 키·라우트명이 함께 바뀐다.

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
