#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(dirname "$SCRIPT_DIR")"
ROOT_DIR="$(dirname "$INFRA_DIR")"

echo "========================================="
echo "  24SevenClaw 개발 환경 셋업"
echo "========================================="

# 1. Docker Compose 시작
echo ""
echo "🔄 Docker 서비스를 시작합니다..."
cd "$INFRA_DIR/docker"
docker compose up -d

# 2. PostgreSQL 준비 대기
echo "⏳ PostgreSQL 준비 대기 중..."
until docker compose exec -T db pg_isready -U clickeye > /dev/null 2>&1; do
  sleep 1
done
echo "✅ PostgreSQL 준비 완료"

# 3. Redis 준비 대기
echo "⏳ Redis 준비 대기 중..."
until docker compose exec -T redis redis-cli ping > /dev/null 2>&1; do
  sleep 1
done
echo "✅ Redis 준비 완료"

# 4. API DB 마이그레이션 (api 레포가 있을 때만)
API_DIR="$ROOT_DIR/24SevenClaw-api"
if [ -d "$API_DIR" ] && [ -f "$API_DIR/alembic.ini" ]; then
  echo ""
  echo "🔄 DB 마이그레이션 실행 중..."
  cd "$API_DIR"
  uv run alembic upgrade head
  echo "✅ 마이그레이션 완료"
fi

echo ""
echo "========================================="
echo "  ✅ 개발 환경이 준비되었습니다!"
echo "========================================="
echo ""
echo "  PostgreSQL: localhost:5432 (clickeye/devpassword)"
echo "  Redis:      localhost:6379"
echo ""
echo "  API 서버:   cd 24SevenClaw-api && uv run uvicorn app.main:app --reload"
echo "  Web 서버:   cd 24SevenClaw-web && npm run dev"
echo ""
