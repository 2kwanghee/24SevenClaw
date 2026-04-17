---
route: /solutions/new (Step 1)
title: 프로토타입 생성 (로딩 → 결과 확인)
status: implemented
version: 1.1.0
components:
  - src/components/solutions/wizard/steps/step-prototype-generation.tsx
store: useSolutionWizardStore → setGeneratedPrototypes, setIsGenerating, step1Done
last_updated: 2026-04-17
---

## 목적
백그라운드에서 AI가 솔루션 프로토타입 3종을 생성하는 동안 진행 상황을 시각적으로 표시하고, 완료 시 결과 카드를 보여준 뒤 사용자가 직접 "다음"을 클릭해 Step 2로 진행.

---

## 레이아웃

**생성 중 (skeleton → generating)**
```
┌─────────────────────────────────────────┐
│                                         │
│          ◉ (펄스 애니메이션)             │
│       [Loader2 스피너]                  │
│                                         │
│    "솔루션 프로토타입 생성 중..."         │
│    "회사 정보를 분석하여..."             │
│                                         │
│  ┌──────────────────────────────────┐   │
│  │ ✅ 회사 요구사항 분석 완료        │   │
│  │ ⟳  솔루션 아키텍처 설계 중...    │   │
│  │ ○  프로토타입 변형 생성          │   │
│  └──────────────────────────────────┘   │
│                                         │
│  ████████████░░░░ N% 완료              │
│                                         │
└─────────────────────────────────────────┘
```

**생성 완료 (ready)**
```
┌─────────────────────────────────────────┐
│  ✅ "3개의 프로토타입이 생성되었습니다"   │
│                                         │
│  ┌─────────────┐ ┌─────────────┐ ┌──────│
│  │ ★ 추천      │ │             │ │      │
│  │ [스택 배지…] │ │ [스택 배지…] │ │ [...] │
│  │ [아키텍처]   │ │ [아키텍처]   │ │      │
│  │ *이유 한줄* │ │ *이유 한줄* │ │      │
│  └─────────────┘ └─────────────┘ └──────│
│                                         │
│  "아래 다음 버튼을 클릭해                │
│   프로토타입을 확인하세요"               │
└─────────────────────────────────────────┘
```

---

## 스토리보드

**시나리오 1: 정상 생성 (신규)**
1. Step 1 진입 직후 `prototypeSessions.generatePrototypes` 호출
2. 3초 간격으로 `prototypeSessions.getStatus` 폴링 (최대 40회 = 2분)
3. 로딩 단계 메시지 순차 전환 (애니메이션)
4. status가 `completed`가 되면 프로토타입 목록 조회 (3개 반환, `EXPECTED_COUNT=3`)
5. `setGeneratedPrototypes` + `step1Done=true` → 카드 목록 ready 상태로 표시
6. "아래 다음 버튼을 클릭해 프로토타입을 확인하세요" 안내 메시지 표시
7. 사용자가 "다음" 클릭 → Step 2로 이동

**시나리오 2: 이전 버튼으로 Step 1 재진입**
1. 스토어에 이미 `generatedPrototypes` 데이터가 있음을 감지
2. API 재호출 없이 기존 카드를 즉시 ready 상태로 복원
3. `step1Done=true`로 다음 버튼 활성화
4. 사용자가 "다음" 클릭 → Step 2로 이동

**시나리오 3: 생성 실패**
- status가 `failed` → 에러 메시지 + 재시도 버튼
- 폴링 40회 초과 → 타임아웃 에러 + 재시도 버튼

---

## 기능 요구사항

- [x] 진입 즉시 프로토타입 생성 API 호출 (기존 결과 없을 때만)
- [x] 3초 간격 status 폴링 (최대 40회)
- [x] 로딩 단계 메시지 순차 표시 (3~4단계)
- [x] 프로그레스 바 (폴링 횟수 기반 추정)
- [x] 완료 시 프로토타입 목록 조회 후 카드 표시 (`EXPECTED_COUNT=3`)
- [x] 완료 후 "다음 버튼 클릭" 안내 메시지 표시
- [x] `canProceed = step1Done` (생성 완료 시 다음 버튼 활성화)
- [x] 이전 버튼으로 재진입 시 기존 카드 즉시 복원 (API 재호출 없음)
- [x] 실패/타임아웃 시 에러 UI + 재시도
- [ ] 예상 남은 시간 표시
- [ ] 생성 완료 토스트 알림

---

## API 연동

| 메서드 | 함수 | 트리거 | 설명 |
|--------|------|--------|------|
| `POST` | `prototypeSessions.generatePrototypes` | 스텝 진입 | 생성 시작 |
| `GET` | `prototypeSessions.getStatus` | 3초 폴링 | 상태 확인 |
| `GET` | `prototypeSessions.getPrototypes` | status=completed | 결과 조회 (구 `listPrototypes` → 변경됨) |

---

## 상태 관리

| 상태 | 타입 | 출처 | 용도 |
|------|------|------|------|
| `generatedPrototypes` | `Prototype[]` | `useSolutionWizardStore` | 생성된 프로토타입 목록 |
| `step1Done` | `boolean` | `useSolutionWizardStore` | 생성 완료 여부 (canProceed 결정) |
| `isGenerating` | `boolean` | `useSolutionWizardStore` | 폴링 중 여부 |

### 프로토타입 배리언트 구조

백엔드는 항상 3개(`EXPECTED_COUNT=3`)의 배리언트를 반환:

| 배리언트 인덱스 | 역할 | `is_recommended` |
|----------------|------|-----------------|
| 0 | 사용자 입력 스택 + 표준 아키텍처 (스택 미입력 시 최적 스택 자동 선택) | `true` |
| 1 | 대안 인기 스택 조합 | `false` |
| 2 | 다른 아키텍처 패턴 | `false` |

각 프로토타입에 저장되는 필드:
- `tech_stack`: 기술 스택 목록 (배지로 표시, 최대 5개 + 나머지 +N)
- `architecture_pattern`: 아키텍처 패턴 레이블
- `rationale`: 선택 이유 1줄 텍스트 (이탤릭 표시)
- `is_recommended`: 추천 여부 (true 시 ★ 추천 배지)

---

## 구현 노트

- `useEffect` cleanup으로 `clearInterval` 필수 (언마운트 시 폴링 중단)
- 세션 없을 때 Step 0으로 리다이렉트 처리
- **[v1.1]** 자동 이동 제거: 생성 완료 시 `nextStep()` 자동 호출 대신 `step1Done=true`로 설정하여 다음 버튼 활성화
- **[v1.1]** 이전 버튼 지원: `generatedPrototypes.length > 0`이면 폴링 건너뛰고 기존 카드 즉시 표시
- `EXPECTED_COUNT` 상수값: 4 → 3 수정 (백엔드 실제 반환값과 일치)
