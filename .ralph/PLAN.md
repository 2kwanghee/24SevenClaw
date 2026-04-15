# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P2: 기능 요구사항

- [ ] **[api] KPI 메트릭 집계 엔드포인트 확장**
  > 요청사항: ## 개요

기존 ReportService를 확장하여 KPI 메트릭 집계 엔드포인트를 추가한다. 24Seven 사용의 가치를 정량적으로 보여주기 위한 데이터 기반.

## 범위

### report_service.py 확장

* avg_phase_duration_seconds: PhaseEvent 기반 단계별 평균 소요시간
* throughput_per_week: 주간 완료 태스크 수
* automation_rate: AI 자동처리 비율 (SubTask.actor_type)
* review_acceptance_rate: 초안 수용률

### 새 엔드포인트

* GET /api/v1/reports/projects/{id}/kpi: 프로젝트 KPI
* GET /api/v1/reports/platform/summary: 플랫폼 전체 요약 (superadmin)

## 완료 조건

- 4개 KPI 메트릭 집계 로직
- 엔드포인트 동작 + 테스트
- platform/summary superadmin 권한 체크

## 크기: M | 독립적 — 병렬 작업 가능

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|