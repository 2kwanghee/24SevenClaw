---
route: /solutions/new (Step 2)
title: 프로토타입 선택 (카드 뷰 / 비교표 뷰)
category: page
status: implemented
version: 1.2.0
components:
  - src/components/solutions/wizard/steps/step-prototype-selection.tsx
  - src/components/solutions/wizard/prototype-card.tsx
  - src/components/prototypes/prototype-comparison-table.tsx
  - src/components/prototypes/metric-badges.tsx
  - src/components/solutions/wizard/prototype-preview.tsx
store: useSolutionWizardStore → selectPrototype
last_updated: 2026-06-15
---

## 목적
AI가 생성한 3개 프로토타입 후보 중 하나를 선택. **카드 뷰** (기본)와 **비교표 뷰** (정량 지표)를 토글하여 사용자가 최적 선택지를 비교 분석 후 결정할 수 있도록 지원.

---

## 레이아웃 (카드 뷰 기본)

```
┌─────────────────────────────────────────────────────────────┐
│ 안내 배너 + [카드] [비교표] 뷰 토글                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐ │
│  │ ★ 추천 (노란배) │ │                │ │                │ │
│  │                │ │                │ │                │ │
│  │ 프로토타입 제목  │ │ 프로토타입 제목  │ │ 프로토타입 제목  │ │
│  │ [SaaS] 배지     │ │ [REST API] 배지 │ │ [배지...]      │ │
│  │                │ │                │ │                │ │
│  │ 아키텍처: ...   │ │ 아키텍처: ...   │ │ 아키텍처: ...   │ │
│  │ *이유 한줄*     │ │ *이유 한줄*     │ │ *이유 한줄*     │ │
│  │                │ │                │ │                │ │
│  │ React Next.js  │ │ Vue Nuxt Go    │ │ Django         │ │
│  │ PostgreSQL +2  │ │ PostgreSQL     │ │ FastAPI        │ │
│  │                │ │                │ │                │ │
│  │ 📊 예상 4주     │ │ 📊 예상 6주     │ │ 📊 예상 3주     │ │
│  │ 👥 팀 3-4명    │ │ 👥 팀 4-5명    │ │ 👥 팀 2-3명    │ │
│  │ 💵 $3K-5K/mo   │ │ 💵 $5K-8K/mo   │ │ 💵 $2K-3K/mo   │ │
│  │ 🔧 복잡도 7/10  │ │ 🔧 복잡도 8/10  │ │ 🔧 복잡도 5/10  │ │
│  │ 📈 확장성 8/10  │ │ 📈 확장성 9/10  │ │ 📈 확장성 6/10  │ │
│  │ 🛠️ 필요역량 ...  │ │ 🛠️ 필요역량 ...  │ │ 🛠️ 필요역량 ...  │ │
│  │                │ │                │ │                │ │
│  │ ✅ 선택됨       │ │ > 선택         │ │ > 선택         │ │
│  │  (emerald 테)  │ │ (기본)         │ │ (기본)         │ │
│  └────────────────┘ └────────────────┘ └────────────────┘ │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 레이아웃 (비교표 뷰)

```
┌──────────────────────────────────────────────────────────────────┐
│ [카드] [비교표] 토글 — [비교표] 활성화                             │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  행\열          │ Variant 0 ★    │ Variant 1       │ Variant 2   │
│  ────────────────┼────────────────┼─────────────────┼─────────────│
│  아키텍처        │ microservices  │ monolith        │ serverless  │
│  예상 기간       │ 4주            │ 6주             │ 3주         │
│  팀 규모         │ 3-4명          │ 4-5명           │ 2-3명       │
│  월 비용         │ $3K-5K         │ $5K-8K          │ $2K-3K      │
│  복잡도 점수     │ 7/10           │ 8/10 ★ 최고     │ 5/10        │
│  확장성 점수     │ 8/10           │ 9/10 ★ 최고     │ 6/10        │
│  유지보수 난이도 │ 높음           │ 매우 높음       │ 중간        │
│  기술 스택       │ React, Node.js │ Django, PostSQL │ AWS Lambda  │
│  필요 역량       │ fullstack, ... │ backend, ...    │ serverless, │
│  회사 적합도     │ ★ 높음         │ 중간            │ 낮음        │
│  장점            │ 확장성·성능    │ 엔터프라이즈    │ 빠른 출시   │
│  단점            │ 복잡성·비용    │ 초기 복잡도     │ 성능 제약   │
│                  │                │                │             │
│  선택하기        │ ✅ 선택됨      │ [ 선택하기 ]    │ [ 선택하기] │
│                  │  (emerald 배경)│                │             │
└──────────────────────────────────────────────────────────────────┘
```

---

## 스토리보드

**시나리오 1: 카드 뷰에서 선택**
1. 생성된 프로토타입 3개 카드 표시 (Variant 0=★ 추천 배지)
2. 카드 클릭 → `selectPrototype(id)` + lowast optimistic update (PATCH /prototype-sessions/{id})
3. 선택된 카드: emerald 테두리 + 체크 아이콘 하이라이트
4. `canProceed = selectedPrototypeId` → "다음" 버튼 활성화
5. "다음" 클릭 → Step 3으로 이동

**시나리오 2: 비교표 뷰에서 선택**
1. [비교표] 버튼 클릭 → 정량 지표 행-열 비교 UI 표시
2. 열 헤더(프로토타입 이름) 클릭 → 해당 프로토타입 선택
3. 선택된 열: emerald 배경 + ★ 강조
4. [선택하기] 버튼 → `selectPrototype` 호출
5. "다음" 버튼 활성화 → Step 3으로 이동

**시나리오 3: 빈 상태**
- 생성된 프로토타입 없음 → "생성 결과가 없습니다" 메시지

---

## 기능 요구사항

### 카드 뷰
- [x] 프로토타입 카드 그리드 (sm: 1열 / md:~lg: 3열)
- [x] 카드 선택 하이라이트 (emerald 테두리 + 체크 아이콘)
- [x] ★ 추천 배지 (노란색, `is_recommended=true`)
- [x] 기술 스택 배지 (최대 5개 표시, 초과분 "+N")
- [x] 아키텍처 패턴 레이블 (`architecture_pattern`)
- [x] 선택 이유 1줄 이탤릭 (`rationale`)
- [x] **정량 지표 표시**:
  - 예상 기간 (주): EstimatedWeeksBadge
  - 팀 규모 (명): TeamSizeBadge
  - 월 비용 ($): MonthlyCostBadge
  - 유지보수 난이도: MaintenanceBadge
  - 복잡도 점수 (0-10): ScoreBar
  - 확장성 점수 (0-10): ScoreBar
  - 필요역량 칩: skillRequirements

### 비교표 뷰
- [x] 행: 지표 (아키텍처·기간·팀·비용·복잡도·확장성·유지보수·기술스택·역량·회사적합도·장단점)
- [x] 열: 프로토타입 (Variant 0~2)
- [x] "best" 항목 ★ 강조 (예: 최단 기간, 최저 비용)
- [x] 열 헤더 클릭으로 프로토타입 선택 가능
- [x] 단일 선택만 허용

### 공통
- [x] Optimistic update: UI 즉시 반영, API는 fire-and-forget
- [x] 선택 후 `canProceed = selectedPrototypeId` → 다음 버튼 활성화
- [x] 빈 상태 UI

---

## 상태 관리

| 상태 | 타입 | 출처 | 설명 |
|------|------|------|------|
| `generatedPrototypes` | `Prototype[]` | `useSolutionWizardStore` | 생성된 프로토타입 목록 |
| `selectedPrototypeId` | `string \| null` | `useSolutionWizardStore` | 선택된 프로토타입 ID |
| `expandedId` | `string \| null` | local state | 프리뷰 확대 대상 ID |
| `viewMode` | `"cards" \| "compare"` | local state | 뷰 모드 토글 |

---

## API 연동

| 메서드 | 함수 | 트리거 | 설명 |
|--------|------|--------|------|
| `PATCH` | `prototypeSessions.update` | 프로토타입 선택 | optimistic update (fire-and-forget) |

---

## 정량 지표 배지 컴포넌트

`metric-badges.tsx` export:
- `EstimatedWeeksBadge`: 예상 주수 (estimatedWeeksMin~Max)
- `TeamSizeBadge`: 팀 규모 (teamSizeMin~Max)
- `MonthlyCostBadge`: 월 비용 (monthlyCostMinUsd~Max)
- `MaintenanceBadge`: 유지보수 난이도 (difficulty enum)
- `ScoreBar`: 점수 바 (complexity/scalability, 0-10)
- `hasAnyMetric()`: 지표 유무 판정 함수

---

## 구현 노트

- **[v1.2]** 정량 지표 표시: 모든 badge 컴포넌트가 null-safe하게 fallback 기본값 제공
- **[v1.2]** 비교표 뷰 신규: `PrototypeComparisonTable` 컴포넌트가 모든 정량 지표를 행으로 표시
- **[v1.2]** 열 헤더 선택: 비교표에서 프로토타입 열을 클릭해도 선택 가능
- Optimistic update: sessionId + token 없으면 UI만 반영
- PrototypePreview: 카드 내 compact 모드로 임베드 (ui_structure 또는 tech diagram)
- 기술 스택 배지: 5개 초과 시 나머지를 "+N" 텍스트로 축약
