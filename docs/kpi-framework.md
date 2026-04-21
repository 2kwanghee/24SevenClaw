# KPI 정량화 프레임워크

**작성일**: 2026-04-13
**관련**: AI Team 보고서 §6 기대효과, Appendix KPI 정량화
**상태**: 설계 완료 (구현 대기)

---

## 1. 개요

AI Team 운영 모델의 효과를 정량적으로 측정하기 위한 KPI 프레임워크.
보고서 §6의 5대 기대효과(업무 속도, 품질, 피로도, 의사결정, 운영 표준화)를
측정 가능한 지표로 정의하고, 기존 API 인프라의 수집 포인트를 활용한다.

### 설계 원칙

- **기존 인프라 활용**: OrchestratorSession, ReviewRound, Artifact, PhaseEvent 등 이미 구축된 이벤트 기반 추적 활용
- **자동 수집 우선**: 수동 입력 없이 API 미들웨어 + 이벤트 리스너로 자동 수집
- **점진적 확장**: Phase 1(핵심 5개) → Phase 2(파생 지표) → Phase 3(예측 분석)

---

## 2. 측정 지표 정의

### 2.1 핵심 지표 (Phase 1)

| # | 카테고리 | 지표명 | 정의 | 단위 | 수집 주기 |
|---|----------|--------|------|------|-----------|
| K1 | 업무 속도 | **처리 시간** (Cycle Time) | 요청(requested) → 완료(completed) 평균 소요 시간 | 분 | 세션 완료 시 |
| K2 | 업무 속도 | **처리량** (Throughput) | 단위 시간당 완료된 서브태스크 수 | 건/일 | 일별 집계 |
| K3 | 품질 | **결함율** (Defect Rate) | 검증(validating) 단계 실패 비율 | % | 세션 완료 시 |
| K4 | 품질 | **리뷰 통과율** (First-Pass Rate) | 교차 리뷰 1회 통과(merged) 비율 | % | 리뷰 완료 시 |
| K5 | 효율 | **AI 활용률** (AI Utilization) | AI 자동 처리(actor_type=agent) vs 수동 개입(actor_type=user) 비율 | % | 일별 집계 |

### 2.2 파생 지표 (Phase 2)

| # | 카테고리 | 지표명 | 정의 | 산출 방법 |
|---|----------|--------|------|-----------|
| D1 | 업무 속도 | 단계별 체류 시간 | 각 Phase별 평균 소요 시간 | PhaseEvent.entered_at → exited_at |
| D2 | 품질 | 평균 리뷰 점수 | 교차 리뷰 평균 점수 (0-100) | ReviewRound.review_score 평균 |
| D3 | 품질 | 평균 수정 횟수 | 산출물당 상태 전이 횟수 | ArtifactEvent count per artifact |
| D4 | 효율 | 산출물 릴리즈율 | released / total artifacts | Artifact 상태 집계 |
| D5 | 리스크 | 리스크 탐지율 | 세션당 평균 리스크 플래그 수 | OrchestratorSession risks 집계 |
| D6 | 운영 | 파이프라인 성공률 | 정상 완료 세션 / 전체 세션 | Session phase=completed 비율 |

---

## 3. 수집 포인트 설계

### 3.1 기존 인프라 매핑

현재 API에 이미 구현된 이벤트 소스를 KPI에 매핑한다.

```
┌─────────────────────────────────────────────────────────────┐
│  KPI 수집 아키텍처                                           │
│                                                             │
│  ┌──────────────────┐    ┌──────────────────┐               │
│  │ OrchestratorSvc  │───►│ PhaseEvent       │──► K1, D1, D6│
│  │ (세션 생명주기)    │    │ (단계 전이 이력)   │               │
│  └──────────────────┘    └──────────────────┘               │
│                                                             │
│  ┌──────────────────┐    ┌──────────────────┐               │
│  │ SubTask          │───►│ SubTask.status   │──► K2, K5    │
│  │ (작업 단위)       │    │ + actor_type     │               │
│  └──────────────────┘    └──────────────────┘               │
│                                                             │
│  ┌──────────────────┐    ┌──────────────────┐               │
│  │ ReviewPipeline   │───►│ ReviewEvent      │──► K4, D2    │
│  │ (교차 리뷰)       │    │ + review_score   │               │
│  └──────────────────┘    └──────────────────┘               │
│                                                             │
│  ┌──────────────────┐    ┌──────────────────┐               │
│  │ ArtifactSvc      │───►│ ArtifactEvent    │──► K3, D3, D4│
│  │ (산출물 관리)      │    │ (상태 전이 이력)   │               │
│  └──────────────────┘    └──────────────────┘               │
│                                                             │
│                     ┌──────────────────┐                    │
│                     │ KPI Aggregator   │ ◄── 신규 구현       │
│                     │ (일별 스냅샷)     │                    │
│                     └────────┬─────────┘                    │
│                              │                              │
│                     ┌────────▼─────────┐                    │
│                     │ kpi_snapshots    │ ◄── 신규 테이블     │
│                     │ (시계열 저장)     │                    │
│                     └──────────────────┘                    │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 수집 포인트별 상세

#### CP-1: 세션 생명주기 (OrchestratorService)

| 이벤트 | 수집 데이터 | 연결 KPI |
|--------|-----------|---------|
| `session.created` | session_id, created_at | K1 시작점 |
| `phase.transitioned` | from_phase, to_phase, timestamp, actor_type | K1, K5, D1 |
| `session.completed` | completed_at, final_phase | K1 종료점, D6 |
| `risk.detected` | risk_type, severity | D5 |

**수집 방법**: `OrchestratorService.transition_phase()` 내부에서 PhaseEvent 생성 시 자동 기록 (이미 구현됨)

#### CP-2: 서브태스크 (SubTask)

| 이벤트 | 수집 데이터 | 연결 KPI |
|--------|-----------|---------|
| `subtask.completed` | completed_at, role, actor_type | K2, K5 |
| `subtask.created` | total count per session | K2 분모 |

**수집 방법**: SubTask status 변경 시 자동 기록 (이미 구현됨)

#### CP-3: 교차 리뷰 (ReviewPipeline)

| 이벤트 | 수집 데이터 | 연결 KPI |
|--------|-----------|---------|
| `review.submitted` | review_score, review_type | D2 |
| `review.merged` | first_round (boolean) | K4 |
| `review.rejected` | rejection_count | K4 역산 |

**수집 방법**: `ReviewPipelineService` 이벤트 기록 (이미 구현됨)

#### CP-4: 산출물 (ArtifactService)

| 이벤트 | 수집 데이터 | 연결 KPI |
|--------|-----------|---------|
| `artifact.transitioned` | from_status, to_status, actor_type | D3, D4 |
| `artifact.validated_fail` | validation 단계 실패 | K3 |
| `artifact.released` | released count | D4 |

**수집 방법**: `ArtifactService.transition_status()` 내부에서 ArtifactEvent 생성 시 자동 기록 (이미 구현됨)

### 3.3 신규 구현 필요 항목

#### KPI 스냅샷 테이블 (kpi_snapshots)

일별 집계를 위한 시계열 테이블. 기존 이벤트 테이블에서 집계하여 저장한다.

```python
# clickeye-api/app/models/kpi.py (향후 구현)
class KPISnapshot(Base):
    __tablename__ = "kpi_snapshots"

    id: Mapped[uuid.UUID]
    project_id: Mapped[uuid.UUID]         # FK → projects
    snapshot_date: Mapped[date]           # 집계 기준일
    period_type: Mapped[str]              # "daily" | "weekly" | "monthly"

    # K1: 처리 시간
    avg_cycle_time_minutes: Mapped[float | None]
    median_cycle_time_minutes: Mapped[float | None]
    p95_cycle_time_minutes: Mapped[float | None]

    # K2: 처리량
    subtasks_completed: Mapped[int]
    sessions_completed: Mapped[int]

    # K3: 결함율
    validation_total: Mapped[int]
    validation_failed: Mapped[int]
    defect_rate: Mapped[float | None]     # validation_failed / validation_total

    # K4: 리뷰 통과율
    reviews_total: Mapped[int]
    reviews_first_pass: Mapped[int]
    first_pass_rate: Mapped[float | None] # reviews_first_pass / reviews_total

    # K5: AI 활용률
    actions_by_agent: Mapped[int]
    actions_by_user: Mapped[int]
    ai_utilization: Mapped[float | None]  # actions_by_agent / total_actions

    # D2: 평균 리뷰 점수
    avg_review_score: Mapped[float | None]

    # D4: 산출물 릴리즈율
    artifacts_total: Mapped[int]
    artifacts_released: Mapped[int]

    # D5: 리스크 탐지
    risks_detected: Mapped[int]

    # D6: 파이프라인 성공률
    pipeline_success_rate: Mapped[float | None]

    created_at: Mapped[datetime]
```

#### KPI 집계 서비스 (KPIAggregator)

```python
# clickeye-api/app/services/kpi_service.py (향후 구현)
class KPIService:
    """일별 KPI 스냅샷을 생성하는 집계 서비스."""

    async def aggregate_daily(self, project_id: UUID, target_date: date) -> KPISnapshot:
        """해당일의 이벤트 데이터를 집계하여 KPISnapshot 생성."""
        ...

    async def get_trend(self, project_id: UUID, metric: str,
                        start_date: date, end_date: date) -> list[TrendPoint]:
        """지정 기간의 KPI 추이 데이터 반환."""
        ...

    async def get_baseline(self, project_id: UUID) -> BaselineMetrics:
        """프로젝트 최초 7일간 평균을 기준선으로 반환."""
        ...

    async def compare_to_baseline(self, project_id: UUID,
                                   current_date: date) -> ComparisonResult:
        """현재 KPI를 기준선 대비 개선율로 반환."""
        ...
```

#### KPI API 엔드포인트

```
GET /api/v1/kpi/project/{project_id}/snapshot?date={date}
    → 특정일 KPI 스냅샷

GET /api/v1/kpi/project/{project_id}/trend?metric={metric}&start={date}&end={date}
    → KPI 추이 (차트 데이터)

GET /api/v1/kpi/project/{project_id}/baseline
    → 기준선 메트릭

GET /api/v1/kpi/project/{project_id}/comparison
    → 기준선 대비 현재 개선율
```

---

## 4. 대시보드 연동 스펙

### 4.1 기존 대시보드 컴포넌트 확장

현재 `ProjectReportResponse`를 사용하는 대시보드에 KPI 섹션을 추가한다.

```
┌─────────────────────────────────────────────────────┐
│  프로젝트 대시보드 (/projects/{id}/dashboard)         │
│                                                     │
│  ┌───────────────────────────────────────────────┐  │
│  │ [기존] Quality Metrics (6개 카드)               │  │
│  └───────────────────────────────────────────────┘  │
│                                                     │
│  ┌───────────────────────────────────────────────┐  │
│  │ [신규] KPI 요약 카드                            │  │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐│  │
│  │  │ K1   │ │ K2   │ │ K3   │ │ K4   │ │ K5   ││  │
│  │  │처리  │ │처리량│ │결함율│ │리뷰  │ │AI    ││  │
│  │  │시간  │ │      │ │      │ │통과율│ │활용률││  │
│  │  │      │ │      │ │      │ │      │ │      ││  │
│  │  │ ▲12% │ │ ▲8%  │ │ ▼5%  │ │ ▲15% │ │ ▲20% ││  │
│  │  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘│  │
│  └───────────────────────────────────────────────┘  │
│                                                     │
│  ┌─────────────────────┐ ┌───────────────────────┐  │
│  │ [기존] Artifact      │ │ [신규] KPI 추이 차트   │  │
│  │ Status Chart         │ │ (7일/30일/90일)        │  │
│  └─────────────────────┘ └───────────────────────┘  │
│                                                     │
│  ┌─────────────────────┐ ┌───────────────────────┐  │
│  │ [기존] Timeline      │ │ [신규] 기준선 대비     │  │
│  │                      │ │ 개선율 게이지          │  │
│  └─────────────────────┘ └───────────────────────┘  │
│                                                     │
│  ┌───────────────────────────────────────────────┐  │
│  │ [기존] AI Team Activity                        │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### 4.2 신규 프론트엔드 컴포넌트

| 컴포넌트 | 파일 경로 | 데이터 소스 |
|----------|----------|-----------|
| `KPISummaryCards` | `components/dashboard/kpi-summary-cards.tsx` | `GET /kpi/.../snapshot` |
| `KPITrendChart` | `components/dashboard/kpi-trend-chart.tsx` | `GET /kpi/.../trend` |
| `BaselineGauge` | `components/dashboard/baseline-gauge.tsx` | `GET /kpi/.../comparison` |

### 4.3 API 클라이언트 타입 (TypeScript)

```typescript
// lib/api-client.ts 에 추가
interface KPISnapshot {
  project_id: string;
  snapshot_date: string;
  period_type: "daily" | "weekly" | "monthly";
  avg_cycle_time_minutes: number | null;
  subtasks_completed: number;
  sessions_completed: number;
  defect_rate: number | null;
  first_pass_rate: number | null;
  ai_utilization: number | null;
  avg_review_score: number | null;
  artifacts_released: number;
  artifacts_total: number;
  risks_detected: number;
  pipeline_success_rate: number | null;
}

interface KPITrendPoint {
  date: string;
  value: number;
}

interface BaselineComparison {
  metric: string;
  baseline_value: number;
  current_value: number;
  improvement_pct: number;  // 양수 = 개선, 음수 = 악화
  direction: "higher_is_better" | "lower_is_better";
}
```

---

## 5. 기준선(Baseline) 측정 방법

### 5.1 기준선 정의

프로젝트 최초 운영 7일간의 평균값을 기준선으로 설정한다.

| 조건 | 설명 |
|------|------|
| 측정 기간 | 프로젝트 첫 세션 생성일 ~ +7일 |
| 최소 데이터 | 세션 3건 이상 (미달 시 기준선 미확정) |
| 갱신 주기 | 설정 후 고정 (수동 리셋 가능) |
| 저장 위치 | `kpi_snapshots` 테이블 (period_type="baseline") |

### 5.2 지표별 기준선 산출

| 지표 | 기준선 산출 방법 | 방향 |
|------|---------------|------|
| K1 처리 시간 | 7일간 완료된 세션의 평균 cycle time | lower_is_better |
| K2 처리량 | 7일간 일평균 완료 서브태스크 수 | higher_is_better |
| K3 결함율 | 7일간 전체 검증 중 실패 비율 | lower_is_better |
| K4 리뷰 통과율 | 7일간 전체 리뷰 중 1회 통과 비율 | higher_is_better |
| K5 AI 활용률 | 7일간 전체 액션 중 AI 처리 비율 | higher_is_better |

### 5.3 개선율 산출

```
improvement_pct = ((current - baseline) / baseline) * 100

# direction 보정
if direction == "lower_is_better":
    improvement_pct = -improvement_pct  # 감소가 개선
```

### 5.4 목표 설정 가이드

| 지표 | 단기 목표 (1개월) | 중기 목표 (3개월) | 근거 |
|------|------------------|------------------|------|
| K1 처리 시간 | 기준선 대비 -15% | 기준선 대비 -30% | AI 학습 + 파이프라인 최적화 |
| K2 처리량 | 기준선 대비 +20% | 기준선 대비 +50% | 병렬 처리 + 자동화 확대 |
| K3 결함율 | 기준선 대비 -20% | 기준선 대비 -40% | 교차 리뷰 + 품질 게이트 강화 |
| K4 리뷰 통과율 | 기준선 대비 +10% | 기준선 대비 +25% | 프롬프트 개선 + 패턴 학습 |
| K5 AI 활용률 | 70% 이상 | 85% 이상 | 수동 개입 최소화 |

---

## 6. 구현 로드맵

### Phase 1: 핵심 지표 (현재 인프라로 즉시 가능)

기존 `ReportService`를 확장하여 K1~K5 실시간 계산.

- `ReportService.get_project_report()`에 KPI 필드 추가
- 기존 `quality_metrics` 확장 (first_pass_rate, ai_utilization 추가)
- 기존 대시보드 `QualityMetrics` 컴포넌트에 K1~K5 카드 추가

### Phase 2: 시계열 추적 (신규 테이블 필요)

일별 스냅샷 저장 + 추이 차트.

- `kpi_snapshots` 테이블 + Alembic 마이그레이션
- `KPIService` 집계 서비스 구현
- 일별 크론잡 또는 세션 완료 시 트리거
- KPI 추이 차트 컴포넌트 구현

### Phase 3: 기준선 + 비교 분석 (Phase 2 이후)

기준선 설정 + 개선율 대시보드.

- 기준선 자동 감지 로직
- 기준선 대비 비교 API
- 개선율 게이지 컴포넌트
- 목표 설정/관리 UI

---

## 7. 보고서 §6 기대효과 매핑

| 보고서 기대효과 | 측정 KPI | 대시보드 표현 |
|---------------|---------|-------------|
| 업무 속도 향상 | K1(처리시간), K2(처리량) | 추이 차트 + 기준선 대비 % |
| 품질 향상 | K3(결함율), K4(리뷰통과율), D2(리뷰점수) | 품질 카드 + 추이 |
| 피로도 감소 | K5(AI활용률), K2(처리량/인당) | AI 활용률 게이지 |
| 의사결정 효율 개선 | D1(단계별 체류시간), D6(파이프라인 성공률) | 타임라인 + 성공률 |
| 운영 표준화 | D5(리스크탐지율), D3(수정횟수 감소 추이) | 리스크 차트 |
