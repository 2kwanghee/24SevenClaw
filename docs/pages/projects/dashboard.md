---
route: /projects/[id]/dashboard
title: 프로젝트 대시보드
category: page
status: implemented
version: 1.0.0
pages:
  - src/app/(dashboard)/projects/[projectId]/dashboard/page.tsx
components:
  - src/components/dashboard/kpi-hero.tsx
  - src/components/dashboard/artifact-status-chart.tsx
  - src/components/dashboard/quality-metrics.tsx
  - src/components/dashboard/project-timeline.tsx
  - src/components/dashboard/ai-team-activity.tsx
store: 없음 (TanStack Query)
last_updated: 2026-04-16
---

## 목적
프로젝트의 진행 상황, KPI, 품질 지표, AI 팀 활동을 한눈에 파악하는 종합 대시보드.

---

## 레이아웃

```
┌──────────────────────────────────────────────────────────┐
│  [KPI 히어로] 자동화율 87% / 완료 태스크 42 / 성공률 94% │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────────────┐  ┌──────────────────────────┐  │
│  │ Artifact 상태 차트    │  │ 품질 지표                │  │
│  │ (도넛 차트)           │  │ (레이더 차트)             │  │
│  └──────────────────────┘  └──────────────────────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐    │
│  │ 프로젝트 타임라인 (페이즈별 진행 바)              │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
│  ┌──────────────────────────────────────────────────┐    │
│  │ AI 팀 활동 피드                                   │    │
│  └──────────────────────────────────────────────────┘    │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## 기능 요구사항

- [x] KPI 히어로 (자동화율, 완료 태스크, 성공률, 코드 라인)
- [x] Artifact 상태 차트 (도넛)
- [x] 품질 지표 (레이더/방사형 차트)
- [x] 프로젝트 타임라인 (페이즈별)
- [x] AI 팀 활동 피드
- [ ] 기간 필터 (7일 / 30일 / 전체)
- [ ] 차트 드릴다운 (클릭 시 상세)
- [ ] PDF/이미지 내보내기
- [ ] 실시간 업데이트 (WebSocket)

---

## API 연동

| 메서드 | 함수 | 트리거 | 설명 |
|--------|------|--------|------|
| `GET` | `apiClient.projects.getReport` | 진입 | 종합 리포트 조회 |
