---
route: /solutions/new
title: 솔루션 생성 위저드 (컨테이너)
status: implemented
version: 1.1.0
pages:
  - src/app/(dashboard)/solutions/new/page.tsx
  - src/app/(dashboard)/solutions/new/layout.tsx
components:
  - src/components/solutions/wizard/solution-wizard-layout.tsx
  - src/components/solutions/wizard/solution-wizard-stepper.tsx
store: useSolutionWizardStore
last_updated: 2026-04-17
---

## 목적
회사 정보 입력부터 프로젝트 생성까지 10단계 위저드를 통해 AI가 최적 솔루션을 자동 설계.

---

## 레이아웃

```
┌──────────────────────────────────────────────────────────────┐
│ 새 솔루션                              [솔루션 목록 →]        │
│ AI가 회사에 맞는 솔루션을 자동 설계합니다                      │
├──────────────────────────────────────────────────────────────┤
│ [스텝1] → [스텝2] → [스텝3] → ... → [스텝10]   (Stepper)     │
│  ●──────────○────────○─────────○──────────○                  │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  [현재 스텝 제목]                                             │
│  [현재 스텝 설명]                                             │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │                                                        │  │
│  │           <StepComponent />                           │  │
│  │                                                        │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│ [← 이전]                                    [다음 →]         │
└──────────────────────────────────────────────────────────────┘
```

> 모바일 (sm 미만): Stepper → 프로그레스바 + "Step N / 10" 텍스트

---

## 스텝 구성 (SOLUTION_WIZARD_STEPS)

| 인덱스 | id | 레이블 | 컴포넌트 | canProceed 조건 |
|--------|-----|--------|----------|----------------|
| 0 | company | 회사 정보 | `StepCompanySolution` | 필수 필드 모두 입력 + solutionRequest ≥ 50자 |
| 1 | generation | 솔루션 생성 | `StepPrototypeGeneration` | `step1Done === true` (생성 완료 후 수동 진행) |
| 2 | prototypes | 프로토타입 | `StepPrototypeSelection` | selectedPrototypeId 존재 |
| 3 | pm-recommendation | PM 추천 | `StepPMRecommendation` | `step3Done === true` (추천 완료 후 수동 진행) |
| 4 | pm-selection | PM 선택 | `StepPMSelection` | selectedPmProfileId 존재 |
| 5 | pm-composition | PM 구성 | `StepPMComposition` | 항상 true |
| 6 | agents | 에이전트 | `StepSolutionAgents` | selectedAgents.length > 0 |
| 7 | platform | 플랫폼 | `StepSolutionPlatform` | platformId 존재 |
| 8 | env | 환경변수 | `StepSolutionEnv` | 항상 true |
| 9 | confirm | 최종 확인 | `StepConfirmation` | — (submit) |

---

## 스토리보드

**시나리오 1: 정상 플로우 (신규 진입)**
1. `/solutions/new` 진입 → store `reset()` 호출
2. Step 0: 회사정보 + 솔루션 요청 입력 → "다음" 클릭
3. `organizations.upsert` → `prototypeSessions.create` → sessionId 저장
4. URL이 `/solutions/{sessionId}`로 `router.replace` 전환
5. Step 1: 프로토타입 생성 중... (자동 폴링) → 완료 시 카드 목록 표시 + `step1Done=true` → "다음" 클릭으로 Step 2 이동
6. Step 2: 프로토타입 카드 중 하나 선택 → "다음"
7. Step 3: PM 추천 중... (자동 호출) → 완료 시 카드 목록 표시 + `step3Done=true` → "다음" 클릭으로 Step 4 이동
8. Step 4: PM 카드 선택 → "다음"
9. Step 5: PM 구성 확인 → "이대로 진행"
10. Step 6~8: 에이전트/플랫폼/환경변수 설정
11. Step 9: 최종 확인 → "이대로 진행" → `prototypeSessions.finalize` → `/projects/{id}` 이동

**시나리오 2: 에러 복구**
- Step 0 API 실패 → 에러 배너 + 재시도 버튼 표시
- 재시도 버튼 클릭 → `handleStep1Next` 재호출

**시나리오 3: 이전 버튼 네비게이션**
- 이전 버튼은 모든 스텝에서 동작
- Step 1로 돌아올 때: `step1Done` 플래그 리셋 → 기존 생성 카드 복원(ready 상태) → 사용자가 다시 "다음" 클릭해야 진행
- Step 3으로 돌아올 때: `step3Done` 플래그 리셋 → 기존 추천 카드 복원(ready 상태) → 사용자가 다시 "다음" 클릭해야 진행
- Step 1/3 복원 시 API 재호출 없음 (스토어에 저장된 결과 재사용)

---

## 기능 요구사항

### 위저드 컨테이너
- [x] 10단계 스텝 배열 정의 및 순서 관리
- [x] 스텝별 `canProceed` 조건 분기
- [x] Step 1 생성 완료 시 `step1Done=true` → 다음 버튼 활성화 (자동 이동 제거)
- [x] Step 3 추천 완료 시 `step3Done=true` → 다음 버튼 활성화 (자동 이동 제거)
- [x] 이전 버튼: `prevStep()` 호출 시 `step1Done`/`step3Done` 플래그 리셋
- [x] Step 0 완료 시 조직/세션 API 호출 후 URL 교체
- [x] 마지막 스텝 제출 시 `finalize` 후 프로젝트 페이지 이동
- [x] 에러 배너 + 재시도 버튼
- [x] Step 5 전용 "이대로 진행" 버튼 레이블

### 레이아웃 컴포넌트 (SolutionWizardLayout)
- [x] 헤더 (타이틀 + 솔루션 목록 링크)
- [x] Stepper 임베드
- [x] 스텝 제목/설명 동적 표시
- [x] 이전/다음 버튼 상태 관리 (disabled, 로딩 아이콘)
- [x] `isGenerating` 상태 시 "분석 중..." 표시
- [x] 스텝 전환 시 제목 엘리먼트로 포커스 이동 (접근성)

### Stepper (SolutionWizardStepper)
- [x] 완료 스텝 체크마크, 현재 스텝 강조, 미래 스텝 회색
- [x] 데스크톱: 수평 스텝 + 연결선
- [x] 모바일: 프로그레스바 + "N / 10" 텍스트
- [x] 클릭 가능 스텝 (현재 이하만 이동 가능)
- [x] 키보드 좌우 화살표 네비게이션
- [ ] 스텝 클릭 시 이동 가능 여부 시각 표시 (커서 변화)

---

## 상태 관리

| 상태 | 타입 | 스토어 | 용도 |
|------|------|--------|------|
| `currentStep` | `number` | `useSolutionWizardStore` | 현재 스텝 인덱스 |
| `data` | `SolutionWizardData` | `useSolutionWizardStore` | 위저드 전체 데이터 |
| `isGenerating` | `boolean` | `useSolutionWizardStore` | AI 생성 중 여부 |
| `error` | `string \| null` | 로컬 state | API 에러 메시지 |
| `isSubmitting` | `boolean` | 로컬 state | 제출 로딩 상태 |

---

## API 연동

| 메서드 | 함수 | 트리거 | 설명 |
|--------|------|--------|------|
| `POST` | `organizations.upsert` | Step 0 "다음" | 조직 생성/업데이트 |
| `POST` | `prototypeSessions.create` | Step 0 "다음" | 프로토타입 세션 생성 |
| `POST` | `prototypeSessions.finalize` | Step 9 제출 | 프로젝트 생성 완료 |

---

## 접근성 / 반응형

- [x] `aria-label` — 이전/다음 버튼
- [x] `aria-busy` — 로딩 상태 버튼
- [x] `role="group"` — 네비게이션 버튼 그룹
- [x] `aria-labelledby` — 스텝 콘텐츠 섹션
- [x] 스텝 전환 시 제목으로 포커스 이동
- [x] 모바일 프로그레스바
- [ ] 스텝 이동 시 `aria-live` 영역으로 진행률 알림

---

## 구현 노트

- Step 0 완료 시 `router.replace` 사용 (뒤로가기 히스토리 오염 방지)
- `onNextStep` prop: Step 0만 커스텀 핸들러, 나머지는 내부 `nextStep()` 사용
- **[v1 제거 완료]** `/projects/new` (Wizard v1) 및 관련 컴포넌트(`components/projects/wizard/`, `stores/wizard-store.ts`, `types/wizard.ts`) 삭제. 이 위저드가 유일한 프로젝트 생성 경로.
