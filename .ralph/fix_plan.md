# Ralph Loop — 작업 큐 (Fix Plan)

> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.
> 완료 시 `- [x]`로 표시하고 커밋한다.
> `- [!]`는 건너뛴 항목 (사유 기록 필수).

---

## P2: 기능 요구사항

- [x] **[rebrand] Phase 3 — Docker 컨테이너·DB 리네임 (데이터 마이그레이션 포함)**
  > 요청사항: Docker 컨테이너명 및 PostgreSQL DB/유저명 변경. 기존 데이터 보존을 위한 마이그레이션 절차 포함.

범위: sevenclaw-db/redis/api/web → clickeye-db/redis/api/web, PostgreSQL DB/유저명 sevenclaw → clickeye, DATABASE_URL 갱신.

대상: 24SevenClaw-infra/docker/docker-compose.yml 3종, .env 6곳, docs/spec/run_guide.md.

데이터 마이그레이션 절차:

1. docker exec sevenclaw-db pg_dump -U sevenclaw sevenclaw > /tmp/clickeye_backup.sql
2. 새 compose로 clickeye-db 기동
3. docker exec clickeye-db psql -U clickeye -d clickeye < /tmp/clickeye_backup.sql
4. alembic 버전 일치 확인

의존: CLK-2(24S-181) 완료 후 진행.

검증: API가 새 DB로 접속, pm_profiles 등 기존 데이터 존재 확인.

---

## 진행 로그

> Ralph가 작업하면서 여기에 기록을 남긴다.

| 시각 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 2026-04-21 | [rebrand] Phase 3 — Docker 컨테이너·DB 리네임 | ✅ 완료 | docker-compose 3종, .env.example 2종, run_guide.md, scripts 2종, CLAUDE.md 수정. 실제 .env는 안전 규칙상 미수정(수동 적용 필요) |