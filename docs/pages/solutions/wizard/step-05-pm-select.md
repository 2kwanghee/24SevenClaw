---
route: /solutions/new (Step 4)
title: PM 선택
category: page
status: implemented
version: 2.0.0
components:
  - src/components/solutions/wizard/steps/step-pm-selection.tsx
  - src/components/solutions/wizard/pm-profile-card.tsx
  - src/components/solutions/wizard/pm-composition-view.tsx
store: useSolutionWizardStore → setPM
last_updated: 2026-06-15
---

## 목적
AI가 추천한 PM 후보 목록에서 프로젝트를 이끌 PM을 선택. 일치율, 성과 지표, 추천 근거를 보고 결정.

---

## 레이아웃

```
┌───────────────────────────────────────────────────────────┐
│ ℹ️  선택한 프로토타입 기반으로 AI가 최적의 PM을 추천했습니다. │
├───────────────────────────────────────────────────────────┤
│                                                           │
│  ┌──────────────────────┐  ┌──────────────────────┐      │
│  │ [아바타] 이름          │  │ [아바타] 이름          │      │
│  │ 직책 / 도메인          │  │ 직책 / 도메인          │      │
│  │ ★★★★☆ 4.2           │  │ ★★★★★ 4.8           │      │
│  │ [일치율 84%]           │  │ [일치율 91%] ✨        │      │
│  │ ─────────────────── │  │ ─────────────────── │      │
│  │ 완료  사용  성공  일수 │  │ 완료  사용  성공  일수 │      │
│  │  12   34   89%  14  │  │  28   67   96%   9  │      │
│  │ ─────────────────── │  │ ─────────────────── │      │
│  │ "추천 근거 텍스트..."  │  │ "추천 근거 텍스트..."  │      │
│  │ [전문분야] [태그] +2   │  │ [전문분야] [태그]      │      │
│  │          [ 선택 ]     │  │  ✅ 선택됨             │      │
│  └──────────────────────┘  └──────────────────────┘      │
│                                                           │
│  ▼ 선택한 PM의 구성 요소 (선택 후 표시)                    │
│  ┌───────────────────────────────────────────────────┐    │
│  │ 🤖 AI 에이전트  ●●● / 🔧 스킬  ●●● / ...         │    │
│  └───────────────────────────────────────────────────┘    │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

---

## 스토리보드

**시나리오 1: 추천 목록 있음 (정상)**
1. Step 4 진입 → 스토어의 `recommendedItems` 읽음
2. 각 PM의 전체 프로필 병렬 조회 (`pmProfiles.get`)
3. 스켈레톤 → PM 카드 그리드 표시
4. 카드 클릭 → 선택 하이라이트 + `setPM({ selectedPmProfileId })`
5. `prototypeSessions.update` (낙관적 업데이트, fire-and-forget)
6. 선택 후 하단에 PM 구성 뷰 슬라이드 표시
7. "다음" 클릭 → Step 5 이동

**시나리오 2: 추천 목록 없음 (폴백)**
- `recommendedItems` 비어있으면 `prototypeSessions.recommendPMs` 재호출
- 세션도 없으면 일반 PM 목록 조회 (상위 6개, `is_active=true`)

---

## 기능 요구사항

- [x] 추천 결과 캐시 우선 사용 (스토어 `recommendedItems`)
- [x] 폴백: `prototypeSessions.recommendPMs` 재호출 / 일반 목록 조회
- [x] PM 전체 프로필 병렬 조회 (`pmProfiles.get`, `Promise.allSettled`)
- [x] 스켈레톤 카드 로딩 UI (추천 수만큼)
- [x] PM 카드: 아바타, 이름, 직책, 별점, 일치율 배지
- [x] PM 카드: 4개 지표 그리드 (사용빈도, 완료건수, 성공률, 평균완료일)
- [x] PM 카드: 추천 근거 인용구
- [x] PM 카드: 전문분야 태그 (최대 4개 + N 더보기)
- [x] 선택 시 하단 구성 요소 뷰 슬라이드 표시 (`PMCompositionView`)
- [x] 낙관적 업데이트 (세션 PATCH, 실패 무시)
- [x] 빈 상태 UI (`UserCircle2` 아이콘)
- [x] 추천 안내 배너 (`recommendBanner`)
- [ ] PM 상세 모달 (전체 프로필 보기)
- [ ] PM 비교 기능 (2개 나란히)
- [ ] 일치율 순 정렬 기본값

---

## 상태 관리

| 상태 | 타입 | 출처 | 용도 |
|------|------|------|------|
| `recommendedItems` | `PMRecommendedItem[]` | `useSolutionWizardStore` | 캐시된 추천 결과 |
| `selectedPmProfileId` | `string \| null` | `useSolutionWizardStore` | 선택한 PM ID |
| `sessionId` | `string \| null` | `useSolutionWizardStore` | 현재 세션 |
| `items` | `PMListItem[]` | 로컬 state | 표시할 PM 목록 |
| `isLoading` | `boolean` | 로컬 state | 로딩 상태 |

---

## API 연동

| 메서드 | 함수 | 트리거 | 설명 |
|--------|------|--------|------|
| `GET` | `pmProfiles.get` | 스텝 진입 (병렬) | PM 전체 프로필 조회 (지표 포함) |
| `POST` | `prototypeSessions.recommendPMs` | 폴백 | 추천 재호출 |
| `GET` | `pmProfiles.list` | 세션 없을 때 폴백 | 일반 목록 (`is_active=true`, `limit=6`) |
| `PATCH` | `prototypeSessions.update` | 카드 선택 | PM 선택 저장 (`selected_pm_id`) |

---

## 접근성 / 반응형

- [x] `role="list"` — PM 목록
- [x] `aria-busy="true"` — 로딩 그리드
- [x] `aria-label` — 로딩 그리드 설명
- [x] `aria-hidden="true"` — 스켈레톤 카드
- [x] sm: 1열 / md: 2열 그리드
- [x] 반응형 레이아웃 (gap-3, sm:grid-cols-2)
- [ ] PM 카드 키보드 선택 (Enter/Space)

---

## 구현 노트

- `toMetricResponse()` 헬퍼로 `PMProfileWithMetrics` → `PMMetricResponse` 변환
- 선택 후 구성 뷰는 `animate-in fade-in slide-in-from-bottom-2` 애니메이션
- 번역 키: `wizard.step4.pmSelect` (note: step4 = wizard index 4 = Step 4 UI 레이블)
- `useEffect` 의존성: `[token, sessionId]` (recommendedItems 제외 — stale closure 방지)
- canProceed: `selectedPmProfileId` 존재 여부
