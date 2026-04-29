---
route: /projects/[id]/insights
title: 프로젝트 인사이트
status: implemented
version: 1.0.0
pages:
  - src/app/(dashboard)/projects/[projectId]/insights/page.tsx
components:
  - src/components/dashboard/automation-breakdown.tsx
  - src/components/dashboard/kpi-hero.tsx
  - src/components/dashboard/phase-velocity-chart.tsx
  - src/components/dashboard/value-comparison.tsx
  - src/components/dashboard/weekly-throughput.tsx
store: 없음 (TanStack Query)
last_updated: 2026-04-16
---

## 목적
AI 자동화 효과를 수치로 분석 — 자동화 분해, 속도, 처리량, 가치 비교를 시각화.

---

## 레이아웃

```
┌────────────────────────────────────────────────────┐
│ [KPI 히어로] 핵심 지표 요약                         │
├────────────────────────────────────────────────────┤
│                                                    │
│  ┌─────────────────┐  ┌─────────────────────────┐  │
│  │ 자동화 분해      │  │ 페이즈별 속도 차트       │  │
│  │ (파이/바 차트)   │  │ (라인 차트)              │  │
│  └─────────────────┘  └─────────────────────────┘  │
│                                                    │
│  ┌─────────────────┐  ┌─────────────────────────┐  │
│  │ 주간 처리량      │  │ 가치 비교                │  │
│  │ (바 차트)        │  │ (AI vs 수동 비용/시간)   │  │
│  └─────────────────┘  └─────────────────────────┘  │
│                                                    │
└────────────────────────────────────────────────────┘
```

---

## 기능 요구사항

- [x] KPI 히어로 (자동화율, ROI, 절감 시간)
- [x] 자동화 분해 차트
- [x] 페이즈별 속도 차트
- [x] 주간 처리량 차트
- [x] 가치 비교 (AI vs 수동)
- [ ] 기간 필터 (주간/월간/전체)
- [ ] 데이터 내보내기 (CSV/Excel)
- [ ] 벤치마크 비교 (업종 평균 대비)
