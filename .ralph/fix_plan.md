# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P2: 기능 요구사항

- [x] **03/26일 업무 진행**
  > 요청사항: PjPlan.md 파일에 있는 업무 리스트를 확인해.
`### Phase 0: 프로젝트 셋업 (Week 1-2) — 03-23 ~ 04-05` 업무중 미진행 된 아래 업무를 모두 진행하도록해. 전체적인 일정을 좀 당겨야 할 거 같아.

```
- [x] DB 스키마 전체 + 마이그레이션 — Day 6 (03-28) ✅ 03-27 완료
- [x] Projects CRUD (API + UI) — Day 7, 9 (03-29, 03-31) ✅ 03-27 완료
- [x] OpenAPI Contract 파이프라인 — Day 8 (03-30) ✅ 03-27 코드 완성 (실행은 수동)
- [x] 환경 강화 (에러 핸들링, 로깅, Rate Limiting) — Day 10 (04-01) ✅ 03-27 완료
- [x] Agent 기본 데몬 + WebSocket 연결 — Day 11-12 (04-02~03) ✅ 03-27 완료
- [x] E2E 통합 테스트 + Phase 0 마무리 — Day 13-14 (04-04~05) ✅ 03-27 완료
```

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 03-27 | DB 스키마 전체 + 마이그레이션 | ✅ | 9개 테이블 모델 + Alembic 002 마이그레이션 생성 |
| 03-27 | Projects CRUD (API + UI) | ✅ | API: 5개 엔드포인트, Web: 목록/생성/상세/편집/삭제 페이지 |
| 03-27 | OpenAPI Contract 파이프라인 | ✅ | export_openapi.py + pipeline.sh + generate-ts.sh 코드 완성 |
| 03-27 | 환경 강화 (에러/로깅/Rate Limit) | ✅ | AppError+unhandled handler, structlog JSON/Console, Redis Rate Limit 100req/60s |
| 03-27 | Agent 데몬 + WebSocket | ✅ | 데몬 main.py, WS client, Hub, dispatcher, handlers(stub), reporter |
| 03-27 | E2E 통합 테스트 | ✅ | conftest(SQLite) + auth 9건 + projects 8건 + health 2건 = 19 테스트 |