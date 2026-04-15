# Ralph Loop — 구현 결과 정리

## 완료 항목

### [api] KPI 메트릭 집계 엔드포인트 확장

**변경 파일:**
| 파일 | 변경 내용 |
|------|----------|
| `app/schemas/report.py` | KPI 스키마 4개 추가 (PhaseDurationAvg, WeeklyThroughput, ProjectKPIResponse, PlatformSummaryResponse) |
| `app/services/report_service.py` | KPI 집계 메서드 6개 추가 (generate_project_kpi, generate_platform_summary + 4개 내부 헬퍼) |
| `app/api/v1/reports.py` | 엔드포인트 2개 추가 (GET projects/{id}/kpi, GET platform/summary) |
| `app/services/rbac_service.py` | superadmin에 `platform:view` 권한 추가 |
| `tests/test_reports.py` | KPI + 플랫폼 요약 테스트 7개 추가 |

**구현 내용:**
- **avg_phase_duration_seconds**: PhaseEvent 기반 세션별 연속 이벤트 간 duration 계산 → 단계별 평균
- **throughput_per_week**: 완료 SubTask를 ISO 주 단위 그룹핑 (SQLite 호환 Python 레벨 집계)
- **automation_rate**: 완료 SubTask / 전체 SubTask × 100
- **review_acceptance_rate**: 리뷰 후 수정 없이 수용된 Artifact (revision_count=0) 비율
- **platform/summary**: superadmin 전용 (`platform:view` 권한), 플랫폼 전체 집계

**테스트 결과:**
- 전체 315개 테스트 통과 (기존 308 + 신규 7)
- ruff check: 통과
- mypy: 통과

**남은 이슈:**
- 없음
