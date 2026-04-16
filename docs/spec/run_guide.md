# 서비스 실행 가이드

## 전제 조건

PostgreSQL, Redis가 실행 중이어야 합니다.

```bash
# 상태 확인
pg_isready
redis-cli ping   # PONG 응답이면 정상

# 실행 안 됐을 경우
sudo service postgresql start
sudo service redis-server start
```

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

# API 서버 실행
uv run uvicorn app.main:app --reload --port 8000
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

## 포트 정리

| 서비스 | 포트 |
|--------|------|
| API (FastAPI) | 8000 |
| Web (Next.js) | 3000 |
| PostgreSQL | 5432 |
| Redis | 6379 |
