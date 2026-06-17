---
route: /solutions/new (Step 1)
title: 프로토타입 생성 (로딩 → 결과 확인)
category: page
status: implemented
version: 1.2.0
components:
  - src/components/solutions/wizard/steps/step-prototype-generation.tsx
store: useSolutionWizardStore → setGeneratedPrototypes, setIsGenerating, setStep1Done
last_updated: 2026-06-15
---

## 목적
회사 정보 기반으로 AI가 프로토타입 3종을 생성하는 동안 진행 상황을 시각적으로 표시. 완료 시 카드 목록을 reveal 애니메이션(350ms stagger)으로 표시한 뒤, 사용자가 "다음"을 클릭해 Step 2로 진행.

---

## 레이아웃

**생성 중 (skeleton → generating)**
```
┌─────────────────────────────────────────┐
│                                         │
│  [Loader2 스피너]  "생성 중..."          │
│  "회사 정보 분석 중"                    │
│  3 / 3 (진행도)                        │
│                                         │
│  ████████░░░░░░░░░░ 40% 완료            │
│                                         │
│  ┌─────────────────────────────────┐   │
│  │ ⟳ 생성 중...   [skeleton card]  │   │
│  │ ⟳ 생성 중...   [skeleton card]  │   │
│  │ ⟳ 생성 중...   [skeleton card]  │   │
│  └─────────────────────────────────┘   │
│                                         │
│  "잠시만 기다려주세요..."               │
│                                         │
└─────────────────────────────────────────┘
```

**생성 완료 (ready)**
```
┌─────────────────────────────────────────┐
│                                         │
│  ✅ "프로토타입 생성 완료"                │
│  3 / 3 (진행도)                        │
│                                         │
│  ████████████████████ 100% 완료         │
│                                         │
│  ┌──────────────┐ ┌─────────────┐ ┌──┐ │
│  │ ★ 추천       │ │             │ │  │ │
│  │ [배지...]    │ │ [배지...]    │ │  │ │
│  │ [아키텍처]   │ │ [아키텍처]   │ │  │ │
│  │ *이유 한줄*  │ │ *이유 한줄*  │ │  │ │
│  └──────────────┘ └─────────────┘ └──┘ │
│                                         │
│  "아래 다음 버튼을 클릭해               │
│   프로토타입을 확인하세요"              │
│                                         │
└─────────────────────────────────────────┘
```

---

## 스토리보드

**시나리오 1: 정상 생성 (신규)**
1. Step 1 진입 직후 `prototypeSessions.generatePrototypes` 호출
2. 3초 간격으로 `prototypeSessions.getStatus` 폴링 (최대 40회 = 2분)
3. skeleton 카드 표시
4. status가 `completed` → `prototypeSessions.getPrototypes` 호출하여 3개 프로토타입 조회
5. 정량 지표 저장: estimatedWeeksMin/Max, teamSizeMin/Max, complexityScore, scalabilityScore, monthlyCost, skillRequirements, matchReasoning 등
6. 카드 reveal 애니메이션: 350ms stagger로 skeleton → generating → ready로 순차 전환
7. `setGeneratedPrototypes` + `setStep1Done(true)` → 다음 버튼 활성화
8. "아래 다음 버튼을 클릭해 프로토타입을 확인하세요" 안내 표시
9. 사용자 "다음" 클릭 → Step 2로 이동

**시나리오 2: 이전 버튼으로 Step 1 재진입**
1. 스토어에 이미 `generatedPrototypes` 데이터 있음을 감지
2. API 재호출 없이 기존 카드를 즉시 ready 상태로 복원
3. `setStep1Done(true)` + `setIsGenerating(false)` → 다음 버튼 활성화
4. 사용자 "다음" 클릭 → Step 2로 이동

**시나리오 3: 생성 실패**
- status=`failed` → 에러 UI + 재시도 버튼
- 폴링 40회 초과 → 타임아웃 에러 + 재시도 버튼
- 503 Service Unavailable → "관리자가 이 기능을 비활성화했습니다" 메시지

---

## 기능 요구사항

- [x] 진입 직후 프로토타입 생성 API 호출 (기존 결과 없을 때만)
- [x] 3초 간격 status 폴링 (최대 40회 = 2분)
- [x] 카드 상태: skeleton → generating → ready (350ms stagger)
- [x] 프로그레스 바 (readyCount / totalCount %)
- [x] 완료 시 프로토타입 목록 조회 + 정량 지표 저장
- [x] 완료 후 "다음 버튼 클릭" 안내 메시지
- [x] `canProceed = step1Done` (생성 완료 시 다음 버튼 활성화)
- [x] 이전 버튼 재진입 시 기존 카드 즉시 복원 (API 재호출 금지)
- [x] 실패/타임아웃 시 에러 UI + 재시도
- [x] 503 관리자 비활성화 상태 처리
- [ ] 예상 남은 시간 표시

---

## API 연동

| 메서드 | 함수 | 트리거 | 설명 |
|--------|------|--------|------|
| `POST` | `prototypeSessions.generatePrototypes` | 스텝 진입 | 생성 시작 |
| `GET` | `prototypeSessions.getStatus` | 3초 폴링 | 상태 확인 |
| `GET` | `prototypeSessions.getPrototypes` | status=completed | 결과 조회 (정량 지표 포함) |

---

## 상태 관리

| 상태 | 타입 | 출처 | 용도 |
|------|------|------|------|
| `generatedPrototypes` | `Prototype[]` | `useSolutionWizardStore` | 생성된 프로토타입 목록 + 정량 지표 |
| `step1Done` | `boolean` | `useSolutionWizardStore` | 생성 완료 여부 (canProceed 결정) |
| `isGenerating` | `boolean` | `useSolutionWizardStore` | 폴링 중 여부 |

### 프로토타입 배리언트 구조

백엔드는 항상 3개(`EXPECTED_COUNT=3`)의 배리언트를 반환:

| 배리언트 | 역할 | `is_recommended` |
|----------|------|-----------------|
| Variant 0 | 사용자 입력 스택 + 표준 아키텍처 (미입력 시 최적 스택 자동) | `true` |
| Variant 1 | 대안 인기 스택 조합 | `false` |
| Variant 2 | 다른 아키텍처 패턴 | `false` |

각 프로토타입에 저장되는 필드:
- `techStack`: 기술 스택 목록 (배지, 최대 5개 + "+N")
- `architecturePattern`: 아키텍처 레이블
- `rationale`: 선택 이유 1줄 (이탤릭)
- `isRecommended`: 추천 여부 (★ 배지)
- **정량 지표 (Phase A)**: `estimatedWeeksMin/Max`, `teamSizeMin/Max`, `complexityScore`, `scalabilityScore`, `monthlyCostMinUsd/Max`, `maintenanceDifficulty`, `skillRequirements`, `matchReasoning`

---

## 구현 노트

- `useEffect` cleanup으로 `clearInterval` 필수 (언마운트 시 폴링 중단)
- StrictMode에서 중복 호출 방지: `startedSessionRef` 저장소로 동일 sessionId 재호출 차단
- race condition 방지: `variant_index` 기준으로 dedup하여 중복 행 제거
- **[v1.2]** 정량 지표 저장: `estimatedWeeks`, `teamSize`, `monthlyCost`, `maintenanceDifficulty` 등 모두 `setGeneratedPrototypes`에 저장
- **[v1.1]** 자동 이동 제거: 생성 완료 시 `nextStep()` 자동 호출 대신 `step1Done=true`로 설정하여 다음 버튼 활성화
- **[v1.1]** 이전 버튼 지원: `existingPrototypes.length > 0` 감지 시 API 재호출 안 함
