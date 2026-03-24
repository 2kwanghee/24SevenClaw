# 24SevenClaw - Daily TODO

> Claude가 이 파일을 참고하여 순차적으로 개발한다.
> 작업 완료 시 `[x]` 표시. 하루 마감 시 `/endwork` 명령으로 아카이브.

---

## 오늘: 2026-03-24 (월) — Day 2: FastAPI 스켈레톤 + DB 연결

### 1. Docker 환경 확인 (infra)
- [x] `docker-compose.yml`에서 PostgreSQL 16 + Redis 7 정상 기동 확인
- [x] API 컨테이너에서 DB 접속 가능 여부 확인
- [x] `.env.example`에 DB 연결 문자열 템플릿 추가 (DATABASE_URL, REDIS_URL)

### 2. FastAPI 앱 완성 (api)
- [x] `app/main.py` — CORS, lifespan(startup/shutdown), 라우터 마운트 확인
- [x] `app/config.py` — Pydantic Settings에 DATABASE_URL, REDIS_URL, SECRET_KEY 등 환경변수 정의
- [x] `app/database.py` — async engine + async sessionmaker + get_db 의존성
- [x] `app/api/v1/health.py` — GET /health (DB ping + Redis ping 포함)
- [x] health 엔드포인트 수동 테스트 (curl 또는 httpx)

### 3. Alembic 마이그레이션 설정 (api)
- [x] `alembic.ini` — sqlalchemy.url을 env에서 읽도록 수정
- [x] `alembic/env.py` — async 마이그레이션 설정 (run_migrations_online async)
- [x] `alembic/env.py` — target_metadata에 Base.metadata 연결
- [x] `app/models/__init__.py` — 모든 모델 import 집중 (autogenerate용)

### 4. Users 테이블 마이그레이션 (api)
- [x] `app/models/user.py` — User 모델 확인/보강 (id, email, password_hash, is_active, created_at, updated_at)
- [x] `alembic revision --autogenerate -m "create_users_table"` 실행
- [x] `alembic upgrade head` 실행
- [x] DB에 users 테이블 생성 확인 (psql 또는 SQLAlchemy inspect)

### 5. 테스트 인프라 (api)
- [x] `tests/conftest.py` — 테스트용 async DB 세션 fixture (SQLite in-memory 또는 test DB)
- [x] `tests/test_health.py` — health 엔드포인트 테스트 작성
- [x] `uv run pytest --tb=short -q` 통과 확인

### 6. 린트/타입체크 (api)
- [x] `uv run ruff check .` 통과
- [x] `uv run mypy app/` 통과 (또는 주요 에러 수정)

### 7. 마무리
- [x] 변경사항 정리 + 커밋 (`[api] FastAPI 스켈레톤 + DB 연결 + Alembic 마이그레이션`)
- [x] PjPlan.md Day 2 상태 업데이트 (✅)
