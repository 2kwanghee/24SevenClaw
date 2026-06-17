---
route: /solutions/new (Step 5)
title: PM 구성 확인
category: page
status: implemented
version: 2.0.0
components:
  - src/components/solutions/wizard/steps/step-pm-composition.tsx
  - src/components/solutions/wizard/pm-composition-view.tsx
store: useSolutionWizardStore (read-only → setPM for pmSupportedPlatforms)
last_updated: 2026-06-15
---

## 목적
선택한 PM의 구성 요소(AI 에이전트, 스킬, 훅, MCP 서버, 플러그인)를 확인하고 진행 여부 결정. PM 지원 플랫폼 정보를 캐시하여 다음 플랫폼 선택 스텝에 전달.

---

## 레이아웃

```
┌────────────────────────────────────────────┐
│ [아바타] PM 이름          일치율 84%        │
│         도메인 배지                        │
├────────────────────────────────────────────┤
│                                            │
│  🤖 AI 에이전트 (3)                        │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ 에이전트1  │ │ 에이전트2  │ │ 에이전트3  │   │
│  │ [잠금]    │ │          │ │          │   │
│  └──────────┘ └──────────┘ └──────────┘   │
│                                            │
│  🔧 스킬 (5)                               │
│  [스킬1 필수] [스킬2] [스킬3] [스킬4]      │
│                                            │
│  ⚡ 훅 (2)                                │
│  [훅1 필수] [훅2]                          │
│                                            │
│  🌐 MCP 서버 (1)                           │
│  [MCP1]                                    │
│                                            │
│  🧩 플러그인 (0)                           │
│  (섹션 숨김)                               │
│                                            │
├────────────────────────────────────────────┤
│ ℹ️  이 구성으로 다음 단계에 진행합니다    │
│                                            │
│ [◀ PM 재선택] 또는 다음 버튼으로 진행      │
└────────────────────────────────────────────┘
```

---

## 스토리보드

1. 스텝 진입 → `pmProfiles.getComposition` + `pmProfiles.get` 병렬 호출
2. 로딩 중: 스켈레톤 UI (PM 헤더, 로딩 spinner)
3. 로드 완료: 5개 카테고리별 구성 요소 표시
   - 각 섹션은 접기/펴기 가능 (`isOpen` state)
   - 항목: name + slug + Required/Optional 배지 + 설명
4. PM 지원 플랫폼을 `setPM({ pmSupportedPlatforms })` 로 캐시
5. 에러 발생 시: 재시도 버튼 표시
6. "PM 재선택" → `goToStep(4)` (Step 4 PM 선택으로 돌아가기)
7. "다음" 버튼 → Step 6(에이전트) 이동

---

## 기능 요구사항

- [x] 선택된 PM 프로필 헤더 (아바타, 이름, 직책, 일치율 배지)
- [x] 5개 섹션: AI 에이전트, 스킬, 훅, MCP 서버, 플러그인
- [x] 각 섹션 아이콘 + 색상 구분 (정의됨: `CATEGORY_STYLE_CONFIG`)
- [x] 빈 섹션은 렌더링 안 함 (`items.length === 0` 체크)
- [x] 항목별 Required/Optional 배지
- [x] 접기/펴기 버튼 (기본 펼침)
- [x] PM 미선택 시 "PM 재선택" 버튼 + 유도 메시지
- [x] 로딩 상태: 스켈레톤 UI
- [x] 에러 상태: 재시도 버튼 (`retryCount` state)
- [x] PM 지원 플랫폼 캐시 (`pmSupportedPlatforms` 스토어)
- [x] `canProceed = true` (항상 진행 가능)
- [ ] 구성 요소 클릭 시 상세 설명 tooltip
- [ ] 구성 커스터마이징 (요소 추가/제거)

---

## 상태 관리

| 상태 | 타입 | 출처 | 용도 |
|------|------|------|------|
| `composition` | `Record<CategoryKey, PMCompositionResponse[]> \| null` | 로컬 state | 5개 카테고리별 구성 데이터 |
| `isLoading` | `boolean` | 로컬 state | API 로딩 상태 |
| `fetchError` | `string \| null` | 로컬 state | 에러 메시지 |
| `retryCount` | `number` | 로컬 state | 재시도 트리거 |
| `selectedPmProfileId` | `string \| null` | store | 선택한 PM ID |
| `pmSupportedPlatforms` | `string[]` | store | PM이 지원하는 플랫폼 목록 |

---

## API 연동

| 메서드 | 함수 | 트리거 | 설명 |
|--------|------|--------|------|
| `GET` | `pmProfiles.getComposition` | 스텝 진입 | 5개 카테고리별 구성 요소 조회 |
| `GET` | `pmProfiles.get` | 스텝 진입 (병렬) | PM 프로필 + `supported_platforms` 조회 |

---

## 접근성 / 반응형

- [x] `role="list"` — 각 섹션의 항목 목록
- [x] `aria-expanded` — 섹션 접기/펴기 버튼
- [x] `aria-controls` — 섹션 ID 참조
- [x] `aria-label` — 구성 섹션 설명
- [x] `aria-hidden` — 아이콘 숨김
- [x] 반응형 레이아웃 (px-4 py-3, border radius)

---

## 구현 노트

- `CATEGORY_STYLE_CONFIG`: agents/skills/hooks/mcp_servers/plugins 스타일 정의
- `CompositionSection` 컴포넌트: 접기/펴기 가능한 카테고리 섹션
- PM 미선택 시 `goToStep(PM_SELECTION_STEP)` 상수 사용 (값: 4)
- 번역 키: `wizard.step4.pmComposition` (note: step4 = wizard index 4)
- `useEffect` 의존성: `[token, selectedPmProfileId, retryCount]`
- 에러 상태에서 재시도 시 `setRetryCount((c) => c + 1)` 으로 트리거
- canProceed: **항상 true** (구성 검토만 하고 진행 필수)
