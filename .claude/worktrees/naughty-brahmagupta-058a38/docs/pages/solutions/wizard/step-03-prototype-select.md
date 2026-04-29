---
route: /solutions/new (Step 2)
title: 프로토타입 선택
status: implemented
version: 1.1.0
components:
  - src/components/solutions/wizard/steps/step-prototype-selection.tsx
  - src/components/solutions/wizard/prototype-card.tsx
  - src/components/solutions/wizard/prototype-preview.tsx
store: useSolutionWizardStore → selectPrototype
last_updated: 2026-04-17
---

## 목적
AI가 생성한 솔루션 프로토타입 후보 중 하나를 선택해 이후 PM 추천의 기반으로 사용.

---

## 레이아웃

```
┌─────────────────────────────────────────────────────────┐
│ [안내 배너] AI가 3개의 솔루션 후보를 생성했습니다.        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────┐ │
│  │ ★ 추천 (노란배지) │  │                 │  │          │ │
│  │ [SaaS] 배지      │  │ [REST API] 배지  │  │ [배지…]  │ │
│  │ 프로토타입 제목   │  │ 프로토타입 제목  │  │ 제목     │ │
│  │                 │  │                 │  │          │ │
│  │ [아키텍처 레이블] │  │ [아키텍처 레이블] │  │ [아키텍처] │ │
│  │ *이유 한줄 텍스트* │ │ *이유 한줄 텍스트* │ │ *이유…*  │ │
│  │                 │  │                 │  │          │ │
│  │ React Next.js   │  │ Vue Nuxt Go     │  │ Django   │ │
│  │ +2              │  │ Postgres        │  │ FastAPI  │ │
│  │                 │  │                 │  │          │ │
│  │  ✅ 선택됨       │  │  > 선택         │  │  > 선택  │ │
│  └─────────────────┘  └─────────────────┘  └──────────┘ │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 프로토타입 카드 구성 요소

| 요소 | 표시 방식 | 비고 |
|------|----------|------|
| 추천 배지 | 노란색 ★ 배지, 카드 상단 우측 | `is_recommended=true`인 카드에만 표시 |
| 기술 스택 | 작은 배지 나열, 최대 5개 + "+N" | `tech_stack` 필드 |
| 아키텍처 패턴 | 회색 레이블 텍스트 | `architecture_pattern` 필드 |
| 선택 이유 | 1줄 이탤릭 텍스트 | `rationale` 필드 |
| 선택 상태 | emerald 테두리 + 체크 아이콘 | 클릭 시 단일 선택 |

---

## 스토리보드

**시나리오 1: 정상 선택**
1. 생성된 프로토타입 카드 목록 표시 (3개, Variant 0=추천 배지)
2. 카드 클릭 → 선택 하이라이트 + 체크 아이콘
3. `selectPrototype(id)` → `canProceed = true`
4. "다음" 클릭 → Step 3 이동

**시나리오 2: 빈 상태**
- 생성된 프로토타입 없음 → "생성 결과가 없습니다" + 재시도 버튼

---

## 기능 요구사항

- [x] 프로토타입 카드 그리드 (sm: 1열 / md: 3열)
- [x] 카드 선택 하이라이트 (emerald 테두리 + 체크 아이콘)
- [x] 추천 배지 (★ 노란색, `is_recommended=true` 카드)
- [x] 기술 스택 배지 (최대 5개 표시, 초과분 "+N")
- [x] 아키텍처 패턴 레이블 (`architecture_pattern`)
- [x] 선택 이유 1줄 이탤릭 텍스트 (`rationale`)
- [x] 빈 상태 UI
- [x] 단일 선택만 허용
- [ ] 프로토타입 상세 보기 모달 (확장 프리뷰)
- [ ] 프로토타입 재생성 버튼 (마음에 안 들 때)

---

## 상태 관리

| 상태 | 타입 | 출처 |
|------|------|------|
| `generatedPrototypes` | `Prototype[]` | `useSolutionWizardStore` |
| `selectedPrototypeId` | `string \| null` | `useSolutionWizardStore` |

---

## 배리언트 역할 정의

| 배리언트 | 역할 | 특징 |
|----------|------|------|
| Variant 0 | 사용자 입력 스택 기반 + 표준 아키텍처 | `is_recommended=true`, ★ 추천 배지 |
| Variant 1 | 대안 인기 스택 조합 | `is_recommended=false` |
| Variant 2 | 다른 아키텍처 패턴 | `is_recommended=false` |

---

## 구현 노트

- `PrototypePreview` 컴팩트 모드: 카드 내 임베드
- `ui_structure` 필드 있으면 UI 구조 뷰, 없으면 기술스택 다이어그램 표시
- **[v1.1]** 기술 스택 배지: 5개 초과 시 나머지를 "+N" 텍스트로 축약
- **[v1.1]** `is_recommended=true`인 카드에 노란색 ★ 배지 표시 (항상 Variant 0)
