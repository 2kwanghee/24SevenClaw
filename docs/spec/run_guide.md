# 서비스 실행 가이드

## 전제 조건

PostgreSQL, Redis를 Docker로 띄웁니다.

```bash
cd /mnt/c/workspace/24SevenClaw/24SevenClaw-infra/docker

# DB + Redis 컨테이너 실행 (백그라운드)
docker compose up -d db redis

# 상태 확인
docker compose ps
# sevenclaw-db, sevenclaw-redis 모두 healthy 상태여야 정상
```

> API까지 컨테이너로 띄우려면 `--profile full` 옵션 추가:
> ```bash
> docker compose --profile full up -d
> ```

---

## 1단계: API 서버 실행

```bash
cd /mnt/c/workspace/24SevenClaw/24SevenClaw-api

# 의존성 설치 (최초 1회)
uv sync

# DB 마이그레이션 적용
uv run alembic upgrade head

# 시드 데이터 로딩 (PM 프로필 초기 데이터, 최초 1회)
uv run python scripts/seed_pm_data.py

# API 서버 실행 (--host 0.0.0.0: WSL2에서 Windows 브라우저 접근 허용)
uv run uvicorn app.main:app --reload --port 8000 --host 0.0.0.0
```

서버 기동 후 → **http://localhost:8000/docs** (Swagger UI)

---

## 2단계: 웹 프론트엔드 실행

```bash
cd /mnt/c/workspace/24SevenClaw/24SevenClaw-web

# 의존성 설치 (최초 1회)
npm install

# 개발 서버 실행
npm run dev
```

브라우저 → **http://localhost:3000**

---

## 3단계: 주요 기능 확인 포인트

### Swagger UI (http://localhost:8000/docs)

| 기능 | 메서드 | 경로 |
|------|--------|------|
| PM 프로필 목록 | GET | `/api/v1/pm-profiles/` |
| PM 프로필 상세 + 메트릭 | GET | `/api/v1/pm-profiles/{id}` |
| PM 구성 조회 | GET | `/api/v1/pm-profiles/{id}/composition` |
| PM 추천 | POST | `/api/v1/pm-profiles/recommend` |
| PM 평가 등록 | POST | `/api/v1/pm-profiles/{id}/rate` |
| PM 메트릭 조회 | GET | `/api/v1/pm-profiles/{id}/metrics` |
| 프로토타입 세션 생성 | POST | `/api/v1/prototype-sessions/` |
| 프로토타입 세션 목록 | GET | `/api/v1/prototype-sessions/` |

### 웹 UI (http://localhost:3000)

- Solution Wizard v2 — 7단계 위저드 흐름
- PM 시스템 UI (추천 · 구성 · 평가)
- 프로토타입 UI
- AI Team 3계층 운영 대시보드
- 가치 대시보드 KPI 시각화
- 성숙도 온보딩 흐름

---

## 4단계: DB 직접 접속 및 확인

### PostgreSQL 접속

```bash
# 컨테이너 안으로 들어가서 psql 실행
docker exec -it sevenclaw-db psql -U sevenclaw -d sevenclaw
```

접속 후 주요 확인 명령어:

```sql
-- 테이블 목록 확인
\dt

-- 테이블 스키마 확인
\d <테이블명>

-- 데이터 확인 예시
SELECT * FROM pm_profiles LIMIT 10;
SELECT * FROM prototype_sessions ORDER BY created_at DESC LIMIT 5;

-- 마이그레이션 이력 확인 (Alembic)
SELECT * FROM alembic_version;

-- psql 종료
\q
```

한 줄 쿼리 실행 (컨테이너 진입 없이):

```bash
docker exec -it sevenclaw-db psql -U sevenclaw -d sevenclaw -c "\dt"
docker exec -it sevenclaw-db psql -U sevenclaw -d sevenclaw -c "SELECT * FROM alembic_version;"
```

### Redis 접속 및 확인

```bash
# 컨테이너 안에서 redis-cli 실행
docker exec -it sevenclaw-redis redis-cli

# 저장된 키 목록
KEYS *

# 특정 키 값 확인
GET <key>

# 캐시 전체 초기화 (주의: 개발 환경에서만)
FLUSHDB
```

한 줄 실행:

```bash
docker exec -it sevenclaw-redis redis-cli KEYS "*"
docker exec -it sevenclaw-redis redis-cli PING   # PONG 응답이면 정상
```

### 컨테이너 로그 확인

```bash
# DB 로그
docker logs sevenclaw-db --tail 50

# Redis 로그
docker logs sevenclaw-redis --tail 50
```

---

## 포트 정리

| 서비스 | 포트 |
|--------|------|
| API (FastAPI) | 8000 |
| Web (Next.js) | 3000 |
| PostgreSQL | 5432 |
| Redis | 6379 |
