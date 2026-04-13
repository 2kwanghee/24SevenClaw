# 24S-68: 보고 자동화 + 대시보드 시각화

## 구현 결과

### API (24SevenClaw-api)
| 파일 | 설명 |
|------|------|
| `app/schemas/report.py` | 리포트 응답 스키마 (ArtifactStatusCount, PhaseTimelineEntry, QualityMetrics, AITeamActivity, ProjectReportResponse) |
| `app/services/report_service.py` | ReportService — 프로젝트별 산출물/타임라인/품질/AI활동 집계 |
| `app/api/v1/reports.py` | GET /reports/project/{id} 엔드포인트 |
| `app/api/v1/router.py` | reports_router 등록 |
| `tests/test_reports.py` | 5개 테스트 (빈 리포트, 산출물 포함, 인증 실패, 404, 오케스트레이터 포함) |

### Web (24SevenClaw-web)
| 파일 | 설명 |
|------|------|
| `src/lib/api-client.ts` | 리포트 타입 + apiClient.projects.report() 추가 |
| `src/hooks/use-project-report.ts` | useProjectReport() TanStack Query 훅 |
| `src/components/dashboard/artifact-status-chart.tsx` | 산출물 상태별 수평 바 차트 |
| `src/components/dashboard/project-timeline.tsx` | 단계 타임라인 (수직) |
| `src/components/dashboard/quality-metrics.tsx` | 품질 메트릭 6개 카드 그리드 |
| `src/components/dashboard/ai-team-activity.tsx` | AI 팀 활동 로그 (스크롤) |
| `src/app/(dashboard)/projects/[projectId]/dashboard/page.tsx` | 대시보드 페이지 |
| `src/app/(dashboard)/projects/[projectId]/page.tsx` | 프로젝트 상세에 "대시보드" 링크 추가 |

### 테스트 결과
- API: 240/240 통과 (신규 5개 포함)
- Web: ESLint 통과, TypeScript 통과, Next.js 빌드 성공

### 남은 이슈
- Linear 연동 데이터 표시는 Linear MCP API 연동이 별도로 필요 (현재 스코프 외)
