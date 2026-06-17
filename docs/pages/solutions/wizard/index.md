---
route: /solutions/new → /solutions/[sessionId]
title: 솔루션 생성 위저드 (컨테이너)
category: page
status: implemented
version: 2.0.0
pages:
  - src/app/(dashboard)/solutions/new/page.tsx
  - src/app/(dashboard)/solutions/[sessionId]/page.tsx
  - src/app/(dashboard)/solutions/new/layout.tsx
components:
  - src/components/solutions/wizard/solution-wizard-layout.tsx
  - src/components/solutions/wizard/solution-wizard-stepper.tsx
  - src/components/solutions/wizard/artifact-panel/wizard-artifact-panel.tsx
store: useSolutionWizardStore
types: src/types/solution-wizard.ts (SOLUTION_WIZARD_STEPS, getWizardSteps)
last_updated: 2026-06-15
---

## 목적
회사 정보 입력부터 프로젝트 생성까지 **12단계 위저드**를 통해 AI가 최적 솔루션을 자동 설계하고,
로컬에서 바로 개발을 시작할 수 있는 프로젝트(ZIP)를 생성한다.

> **[v2.0 변경 요약]**
> - 스텝 10 → **12단계**로 확장: **`os`(실행 환경)**, **`roi`(ROI 비교)** 2개 신규 추가
> - **라이브 프리뷰 패널(아티팩트 패널)** 도입 — 데스크탑(xl+)은 폼(좌)+프리뷰(우) split view, 모바일은 sheet
> - **온보딩 투어(Joyride)** 추가 — 첫 방문 자동 시작, 헬프(?) 버튼으로 재시작
> - **위저드 모드** 도입(`getWizardSteps(mode)`): `new`(기본, 본 문서) / `modernize`(기존 코드 현대화, 별도 플로우)
> - 스텝 레이블/설명이 **i18n**(`wizard.shell.steps.*`) 기반으로 전환
> - 이어하기(Resume) 다이얼로그 + 세션 복원

---

## 레이아웃

```
┌───────────────────────────────────────────────────────────────────────┐
│ 새 솔루션                                  [? 투어] [⤢ 프리뷰] [솔루션 목록 →] │
│ AI가 회사에 맞는 솔루션을 자동 설계합니다                                  │
├───────────────────────────────────────────────────────────────────────┤
│ [스텝1] → [스텝2] → ... → [스텝12]    (Stepper)                          │
│  ●──────────○────────○────── ... ──────○                                │
├──────────────────────────────────────────┬────────────────────────────┤
│  [현재 스텝 제목 / 설명]                    │  라이브 프리뷰 패널 (xl+)    │
│  ┌──────────────────────────────────────┐ │  ┌───────────────────────┐  │
│  │        <StepComponent />             │ │  │ 회사 청사진 / 단계별    │  │
│  │                                      │ │  │ 요약 (아코디언)         │  │
│  └──────────────────────────────────────┘ │  └───────────────────────┘  │
│  [← 이전]                       [다음 →]   │  (380px, sticky)            │
└──────────────────────────────────────────┴────────────────────────────┘
```

> - 데스크탑(xl+): `minmax(0,1fr) 380px` 2-컬럼 split view (폼 + 프리뷰 패널)
> - 모바일/태블릿(xl 미만): 프리뷰는 sheet(하단 드로어)로, 상단 ⤢ 버튼으로 토글
> - 모바일(sm 미만): Stepper → 프로그레스바 + "Step N / 12" 텍스트

---

## 스텝 구성 (SOLUTION_WIZARD_STEPS, mode='new')

> 정의: `src/types/solution-wizard.ts`. 레이블/설명은 i18n(`wizard.shell.steps.{id}`)로 표시.
> 스텝 컴포넌트 매핑·`canProceed`는 컨테이너 페이지(`solutions/[sessionId]/page.tsx`)에 위치.

| 인덱스 | id | 레이블 | 컴포넌트 | canProceed 조건 |
|--------|-----|--------|----------|----------------|
| 0 | company | 회사 정보 | `StepCompanySolution` | 회사명·주력제품·비즈니스유형 입력 + 솔루션 요청 ≥ 10자 (`step0Valid`) |
| 1 | generation | 솔루션 생성 | `StepPrototypeGeneration` | `step1Done` (생성 폴링 완료) |
| 2 | prototypes | 프로토타입 | `StepPrototypeSelection` | `selectedPrototypeId` 존재 |
| 3 | pm-recommendation | PM 추천 | `StepPMRecommendation` | `step3Done` (추천 완료) |
| 4 | pm-selection | PM 선택 | `StepPMSelection` | `selectedPmProfileId` 존재 |
| 5 | pm-composition | PM 구성 | `StepPMComposition` | 항상 true |
| 6 | agents | 에이전트 | `StepSolutionAgents` | 에이전트 ≥ 1 **AND** ticket_source 스킬 1개 선택 |
| 7 | platform | 플랫폼 | `StepSolutionPlatform` | `platformId` 존재 |
| 8 | **os** | **실행 환경** | `StepSolutionOs` | `osId` 존재 *(신규)* |
| 9 | env | 환경변수 | `StepSolutionEnv` | ANTHROPIC_API_KEY 입력(또는 보류) + Linear/Notion 검증 invalid 아님 |
| 10 | **roi** | **ROI 비교** | `StepSolutionRoi` | `roi.result` 존재 *(신규)* |
| 11 | confirm | 최종 확인 | `StepConfirmation` | Linear/Notion 검증 invalid 아님 (submit) |

> **modernize 모드**(별도): `repo-connect → repo-select → diagnose → diagnosis-review → pm-recommendation
> → pm-selection → pm-composition → agents → platform → env → confirm` 11단계. 본 문서 범위 밖.

---

## 스토리보드

**시나리오 1: 정상 플로우 (신규 진입)**
1. `/solutions/new` 진입 → (최근 7일 미완료 세션 있으면 **이어하기 다이얼로그**) → store `reset()`
2. Step 0: 회사정보 + 솔루션 요청 입력 → 우측 프리뷰에 **회사 청사진**(Claude 분석) 실시간 표시 → "다음"
3. `organizations.upsert` → `prototypeSessions.create` → sessionId 저장 → URL `/solutions/{sessionId}`로 `router.replace`
4. Step 1: 프로토타입 생성 폴링 → 완료 시 카드 reveal + `step1Done=true` → "다음"
5. Step 2: 프로토타입 카드(또는 비교표)에서 1개 선택 → "다음"
6. Step 3: PM 추천 자동 호출 → 완료 시 `step3Done=true` → "다음"
7. Step 4~7: PM 선택 → PM 구성 확인 → 에이전트/스킬/훅/MCP → 플랫폼
8. Step 8: **실행 환경(OS)** 선택 (WSL2)
9. Step 9: 환경변수/API 키 입력 (Anthropic 필수, Linear/Notion 라이브 검증)
10. Step 10: **ROI 비교** 자동 산출(전통 팀 vs ClickEye 비용·기간)
11. Step 11: 최종 확인 → "이대로 진행" → `finalize` → 프로젝트 생성 → **설치 가이드 모달** → `/projects/{id}`

**시나리오 2: 세션 복원 / 이어하기**
- `/solutions/[sessionId]` 직접 진입 시 세션·조직 정보 복원. `status=completed`면 프로토타입 복원 후 Step 2로, 아니면 Step 1(폴링)로 이동.

**시나리오 3: 이전 버튼 네비게이션**
- 이전 버튼은 모든 스텝에서 동작. Step 1/3로 돌아오면 `step1Done`/`step3Done` 리셋 → 저장된 결과 즉시 복원(API 재호출 없음) → 다시 "다음" 필요.

---

## 기능 요구사항

### 위저드 컨테이너
- [x] 12단계(mode='new') 스텝 배열 정의 및 순서 관리 (`getWizardSteps('new')`)
- [x] 스텝별 `canProceed` 조건 분기
- [x] Step 1/3 완료 시 `step1Done`/`step3Done` → 다음 버튼 활성화(자동 이동 없음)
- [x] 이전 버튼: `prevStep()` 시 Step 1/3 done 플래그 리셋
- [x] Step 0 완료 시 조직/세션 API 호출 후 `router.replace`로 URL 교체
- [x] 마지막 스텝 제출 시 `finalize` 후 설치 가이드 모달 → 프로젝트 페이지 이동
- [x] 이어하기(Resume) 다이얼로그 (최근 미완료 세션 감지)
- [x] 라이브 프리뷰 패널 + 온보딩 투어

### 레이아웃 컴포넌트 (SolutionWizardLayout)
- [x] 헤더 (모드별 타이틀/서브타이틀 + 투어·프리뷰토글·솔루션목록 버튼)
- [x] Stepper + 아티팩트 패널 임베드(데스크탑 split / 모바일 sheet)
- [x] 스텝 제목/설명 i18n 동적 표시
- [x] 이전/다음 버튼 상태 관리(disabled, 로딩 아이콘: "분석 중..."/"생성 중...")
- [x] `mode` prop ('new'|'modernize') — 기본 'new'
- [x] 스텝 전환 시 제목 엘리먼트로 포커스 이동(접근성)

### Stepper (SolutionWizardStepper)
- [x] 완료 스텝 체크마크, 현재 스텝 강조, 미래 스텝 회색
- [x] 데스크톱: 수평 스텝 + 연결선 / 모바일: 프로그레스바 + "N / 12"
- [x] 클릭/키보드(←→) 네비게이션 — 현재 이하(완료) 스텝만 이동

### 아티팩트 패널 (WizardArtifactPanel)
- [x] 데스크탑(xl+) sticky split view / 모바일 sheet(토글)
- [x] 현재 스텝 자동 확장(아코디언) + 지난 스텝 요약 접기/펼치기
- [x] company 스텝: **회사 청사진**(Claude 분석 — primary tag·복잡도·타깃·기능·기술스택)
- [x] 그 외 스텝: 단계별 요약(StepSummaryView)
- [x] generation/pm-recommendation(처리 단계)은 프리뷰 제외

---

## 상태 관리

| 상태 | 타입 | 스토어 | 용도 |
|------|------|--------|------|
| `currentStep` | `number` | `useSolutionWizardStore` | 현재 스텝 인덱스(0~11) |
| `data` | `SolutionWizardData` | `useSolutionWizardStore` | 위저드 전체 데이터(company/prototypes/pm/agents/platform/os/env/roi) |
| `mode` | `'new' \| 'modernize'` | `useSolutionWizardStore` | 위저드 모드 |
| `isGenerating` | `boolean` | `useSolutionWizardStore` | AI 생성/분석 중 여부 |
| `step0Valid` | `boolean` | `useSolutionWizardStore` | Step 0 폼 유효성 |
| `step1Done` / `step3Done` | `boolean` | `useSolutionWizardStore` | 생성/PM추천 완료 플래그(이전 시 리셋) |
| `createdProjectId` | `string \| null` | `useSolutionWizardStore` | finalize 성공 후 프로젝트 ID(설치 모달 트리거) |
| `envValidation` | `EnvValidationState` | `useSolutionWizardStore` | Linear/Notion 키 검증 상태 |
| `previewByStep` / `previewLoadingStep` / `previewErrorByStep` / `previewPanelOpen` | — | `useSolutionWizardStore` | 아티팩트 패널 프리뷰 상태 |
| `error` / `isSubmitting` | — | 로컬 state(page) | API 에러 / 제출 로딩 |

---

## API 연동 (컨테이너 레벨)

| 메서드 | 함수 | 트리거 | 설명 |
|--------|------|--------|------|
| `POST` | `organizations.upsert` | Step 0 "다음" | 조직 생성/업데이트 |
| `POST` | `prototypeSessions.create` | Step 0 "다음" | 프로토타입 세션 생성 → sessionId |
| `POST` | `/api/solutions/{sessionId}/finalize` | Step 11 제출 | (Next 프록시 → FastAPI) 프로젝트 생성 + ZIP |
| `POST` | `integrations.registerInitialTasks` | finalize 후(선택) | Linear/Notion 초기 태스크 등록(fire-and-forget) |

> 스텝 내부 API(생성 폴링·PM 추천·ROI 계산·키 검증 등)는 각 스텝 문서 참조.

---

## 접근성 / 반응형

- [x] `aria-label`(이전/다음/투어/프리뷰토글), `aria-busy`(로딩), `role="group"`(네비)
- [x] `aria-labelledby` 스텝 콘텐츠 섹션, 스텝 전환 시 제목 포커스 이동
- [x] 모바일 프로그레스바 + 프리뷰 sheet
- [ ] 스텝 이동 시 `aria-live` 진행률 알림

---

## 구현 노트

- Step 0 완료 시 `router.replace` 사용(뒤로가기 히스토리 오염 방지)
- `onNextStep` prop: Step 0만 커스텀 핸들러(조직/세션 생성), 나머지는 내부 `nextStep()`
- 스텝 레이블/설명은 `SOLUTION_WIZARD_STEPS`(구조) + i18n(`wizard.shell.steps.*`)(표시)로 분리
- 위저드 모드는 `getWizardSteps(mode)`로 분기 — `new`는 기존 `SOLUTION_WIZARD_STEPS`와 동일
- **[v1 제거 완료]** `/projects/new`(Wizard v1) 및 관련 컴포넌트 삭제. 본 위저드가 유일한 프로젝트 생성 경로.
</content>
