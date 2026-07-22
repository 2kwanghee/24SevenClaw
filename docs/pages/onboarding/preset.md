---
route: /onboarding/preset
title: 프리셋 선택
category: page
status: implemented
version: 1.0.0
pages:
  - src/app/(dashboard)/onboarding/preset/page.tsx
components:
  - src/components/presets/preset-card.tsx
  - src/components/presets/natural-language-input.tsx
store: usePresets (커스텀 훅)
last_updated: 2026-07-22
---

## 목적
성숙도 진단 결과 기반으로 추천 프리셋을 선택하거나 자연어로 설정을 입력해 빠르게 프로젝트 시작.

---

## 레이아웃

```
┌──────────────────────────────────────────────────┐
│ 추천 프리셋                                       │
│                                                  │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐    │
│  │ Starter    │ │Intermediate│ │  Advanced  │    │
│  │ [배지: 추천]│ │            │ │            │    │
│  │ 에이전트 2  │ │ 에이전트 4  │ │ 에이전트 7  │    │
│  └────────────┘ └────────────┘ └────────────┘    │
│                                                  │
│  ─── 또는 자연어로 설명 ───                       │
│  ┌────────────────────────────────────────────┐  │
│  │ "SaaS 스타트업, 풀스택 개발 필요..."         │  │
│  └────────────────────────────────────────────┘  │
│  [AI 설정 생성하기]                               │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

## 기능 요구사항

- [x] 성숙도별 프리셋 카드 (Starter / Intermediate / Advanced)
- [x] 자연어 입력 + AI 설정 자동 생성
- [x] 프리셋 선택 → 에이전트/스킬/파이프라인 자동 적용
- [ ] 프리셋 미리보기 (선택 전 구성 보기)
- [ ] 커스텀 프리셋 저장

---

## 구현 노트

- 성숙도 진단(`/onboarding/maturity`) 이후 진입하는 것이 권장 플로우
- `usePresets` 훅으로 프리셋 데이터 조회 및 상태 관리 (TanStack Query)
