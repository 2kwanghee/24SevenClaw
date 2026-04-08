#!/bin/bash
set -euo pipefail

# ═══════════════════════════════════════════════════
#  24SevenClaw — 전체 실행 스크립트
#  사용법: bash scripts/start-all.sh [--stop] [--status]
# ═══════════════════════════════════════════════════

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INFRA_DIR="$ROOT_DIR/24SevenClaw-infra/docker"
API_DIR="$ROOT_DIR/24SevenClaw-api"
WEB_DIR="$ROOT_DIR/24SevenClaw-web"

# 색상
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log()  { echo -e "${BLUE}[$1]${NC} $2"; }
ok()   { echo -e "${GREEN}  ✅ $1${NC}"; }
warn() { echo -e "${YELLOW}  ⚠️  $1${NC}"; }
fail() { echo -e "${RED}  ❌ $1${NC}"; exit 1; }

# ── 상태 확인 ──
show_status() {
    echo ""
    echo "═══════════════════════════════════════"
    echo "  24SevenClaw 서비스 상태"
    echo "═══════════════════════════════════════"
    echo ""

    # Docker
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q sevenclaw-db; then
        ok "PostgreSQL  :5432"
    else
        warn "PostgreSQL  (중지됨)"
    fi

    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q sevenclaw-redis; then
        ok "Redis       :6379"
    else
        warn "Redis       (중지됨)"
    fi

    # API
    if curl -sf http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        ok "API 서버    :8000"
    else
        warn "API 서버    (중지됨)"
    fi

    # Web
    if curl -sf http://localhost:3000 > /dev/null 2>&1; then
        ok "Web 서버    :3000"
    else
        warn "Web 서버    (중지됨)"
    fi
    echo ""
}

# ── 전체 중지 ──
stop_all() {
    echo ""
    log "STOP" "모든 서비스를 중지합니다..."

    # API 서버 (uvicorn)
    if pgrep -f "uvicorn app.main:app" > /dev/null 2>&1; then
        pkill -f "uvicorn app.main:app" 2>/dev/null || true
        ok "API 서버 중지"
    fi

    # Web 서버 (next dev)
    if pgrep -f "next dev" > /dev/null 2>&1; then
        pkill -f "next dev" 2>/dev/null || true
        ok "Web 서버 중지"
    fi

    # Docker API 컨테이너
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q sevenclaw-api; then
        docker stop sevenclaw-api > /dev/null 2>&1 || true
        ok "Docker API 컨테이너 중지"
    fi

    # Docker 인프라
    cd "$INFRA_DIR" 2>/dev/null && docker compose down > /dev/null 2>&1 || true
    ok "Docker 인프라 중지"

    echo ""
    exit 0
}

# ── 인자 처리 ──
case "${1:-}" in
    --stop)   stop_all ;;
    --status) show_status; exit 0 ;;
    --help|-h)
        echo "사용법: bash scripts/start-all.sh [옵션]"
        echo ""
        echo "옵션:"
        echo "  (없음)     전체 실행 (DB → Redis → API → Web)"
        echo "  --stop     모든 서비스 중지"
        echo "  --status   서비스 상태 확인"
        exit 0
        ;;
esac

echo ""
echo "═══════════════════════════════════════"
echo "  24SevenClaw 전체 실행"
echo "═══════════════════════════════════════"
echo ""

# ═══════════════════════════════════════
#  Step 1: 사전 조건 확인
# ═══════════════════════════════════════
log "Step 1/5" "사전 조건 확인"

command -v docker > /dev/null 2>&1 || fail "docker가 설치되지 않았습니다"
docker info > /dev/null 2>&1      || fail "docker 데몬이 실행 중이지 않습니다"
command -v uv > /dev/null 2>&1    || fail "uv가 설치되지 않았습니다 (pip install uv)"
command -v node > /dev/null 2>&1  || fail "node가 설치되지 않았습니다"
command -v npm > /dev/null 2>&1   || fail "npm이 설치되지 않았습니다"

ok "docker, uv, node, npm 확인 완료"

# ═══════════════════════════════════════
#  Step 2: Docker 인프라 (PostgreSQL + Redis)
# ═══════════════════════════════════════
log "Step 2/5" "Docker 인프라 시작 (PostgreSQL + Redis)"

# Docker API 컨테이너가 8000 포트를 점유하고 있으면 중지
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q sevenclaw-api; then
    warn "Docker API 컨테이너 점유 중 → 중지 (로컬 개발용)"
    docker stop sevenclaw-api > /dev/null 2>&1 || true
fi

cd "$INFRA_DIR"
docker compose up -d db redis 2>&1 | grep -v "^$" || true

# PostgreSQL 대기
echo -n "  ⏳ PostgreSQL 대기"
for i in $(seq 1 30); do
    if docker compose exec -T db pg_isready -U sevenclaw > /dev/null 2>&1; then
        echo ""
        ok "PostgreSQL 준비 완료 (:5432)"
        break
    fi
    echo -n "."
    sleep 1
    if [ "$i" -eq 30 ]; then
        echo ""
        fail "PostgreSQL 시작 실패 (30초 타임아웃)"
    fi
done

# Redis 대기
echo -n "  ⏳ Redis 대기"
for i in $(seq 1 30); do
    if docker compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        echo ""
        ok "Redis 준비 완료 (:6379)"
        break
    fi
    echo -n "."
    sleep 1
    if [ "$i" -eq 30 ]; then
        echo ""
        fail "Redis 시작 실패 (30초 타임아웃)"
    fi
done

# ═══════════════════════════════════════
#  Step 3: API 의존성 + DB 마이그레이션
# ═══════════════════════════════════════
log "Step 3/5" "API 의존성 설치 + DB 마이그레이션"

cd "$API_DIR"

# 의존성 설치 (이미 있으면 빠르게 스킵)
uv sync --quiet 2>&1 || uv sync 2>&1
ok "API 의존성 설치 완료"

# 마이그레이션
uv run alembic upgrade head 2>&1
ok "DB 마이그레이션 완료"

# ═══════════════════════════════════════
#  Step 4: API 서버 시작 (백그라운드)
# ═══════════════════════════════════════
log "Step 4/5" "API 서버 시작 (:8000)"

# 기존 uvicorn 프로세스 정리
if pgrep -f "uvicorn app.main:app" > /dev/null 2>&1; then
    warn "기존 API 서버 프로세스 발견 → 중지"
    pkill -f "uvicorn app.main:app" 2>/dev/null || true
    sleep 1
fi

# 포트 8000 점유 확인
if ss -tlnp 2>/dev/null | grep -q ":8000 "; then
    fail "포트 8000이 다른 프로세스에 의해 점유 중입니다. 확인 후 재실행하세요."
fi

cd "$API_DIR"
nohup uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 > "$ROOT_DIR/.logs/api.log" 2>&1 &
API_PID=$!

# API 서버 준비 대기
echo -n "  ⏳ API 서버 대기"
for i in $(seq 1 20); do
    if curl -sf http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        echo ""
        ok "API 서버 준비 완료 (PID: $API_PID)"
        break
    fi
    echo -n "."
    sleep 1
    if [ "$i" -eq 20 ]; then
        echo ""
        fail "API 서버 시작 실패. 로그 확인: cat .logs/api.log"
    fi
done

# ═══════════════════════════════════════
#  Step 5: Web 서버 시작 (백그라운드)
# ═══════════════════════════════════════
log "Step 5/5" "Web 서버 시작 (:3000)"

cd "$WEB_DIR"

# npm 의존성 확인
if [ ! -d "node_modules" ]; then
    log "npm" "의존성 설치 중... (최초 1회)"
    npm ci --silent 2>&1
fi
ok "Web 의존성 확인 완료"

# 기존 next dev 정리
if pgrep -f "next dev" > /dev/null 2>&1; then
    warn "기존 Web 서버 프로세스 발견 → 중지"
    pkill -f "next dev" 2>/dev/null || true
    sleep 1
fi

nohup npm run dev > "$ROOT_DIR/.logs/web.log" 2>&1 &
WEB_PID=$!

# Web 서버 준비 대기
echo -n "  ⏳ Web 서버 대기"
for i in $(seq 1 30); do
    if curl -sf http://localhost:3000 > /dev/null 2>&1; then
        echo ""
        ok "Web 서버 준비 완료 (PID: $WEB_PID)"
        break
    fi
    echo -n "."
    sleep 1
    if [ "$i" -eq 30 ]; then
        echo ""
        warn "Web 서버 대기 타임아웃 (빌드 중일 수 있음, 로그: .logs/web.log)"
    fi
done

# ═══════════════════════════════════════
#  완료
# ═══════════════════════════════════════
echo ""
echo "═══════════════════════════════════════"
echo -e "  ${GREEN}✅ 전체 실행 완료!${NC}"
echo "═══════════════════════════════════════"
echo ""
echo "  🗄️  PostgreSQL   http://localhost:5432"
echo "  📮  Redis        http://localhost:6379"
echo "  🔧  API 서버     http://localhost:8000      (Swagger: /docs)"
echo "  🌐  Web 서버     http://localhost:3000"
echo ""
echo "  📋  로그 확인:"
echo "      API: tail -f .logs/api.log"
echo "      Web: tail -f .logs/web.log"
echo ""
echo "  🛑  전체 중지: bash scripts/start-all.sh --stop"
echo "  📊  상태 확인: bash scripts/start-all.sh --status"
echo ""
