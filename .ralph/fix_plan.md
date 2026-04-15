# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P1: 기능 요구사항

- [x] **[web] 가치 대시보드 KPI 시각화**
  > 요청사항: ## 개요

24Seven 사용의 가치를 고객이 체감할 수 있는 KPI 대시보드를 구현한다.

## 선행 조건

* \[api\] KPI 메트릭 엔드포인트 완료 필수

## 범위

### 새 페이지

* (dashboard)/projects/\[projectId\]/insights/page.tsx: KPI 인사이트

### 새 컴포넌트

* components/dashboard/kpi-hero.tsx: 자동화율, 리뷰점수, 산출물수 카운터 카드
* components/dashboard/value-comparison.tsx: 기존 vs 24Seven 시간 비교
* components/dashboard/phase-velocity-chart.tsx: 단계별 평균 소요시간 바 차트
* components/dashboard/automation-breakdown.tsx: AI vs 사람 파이 차트
* components/dashboard/weekly-throughput.tsx: 주간 처리량 스파크라인

### 기존 페이지 강화

* app/page.tsx 랜딩: "실제 고객 지표" 섹션 추가
* project-card.tsx: 미니 KPI 스트립 추가

### 새 훅: hooks/use-project-kpi.ts

## 완료 조건

- 5개 차트 컴포넌트 렌더링
- 랜딩 페이지 지표 섹션 표시
- 프로젝트 카드 KPI 스트립
- 반응형 + 다크모드 대응

## 크기: L

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|