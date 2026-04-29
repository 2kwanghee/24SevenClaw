#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(dirname "$SCRIPT_DIR")"

echo "🔍 24SevenClaw 서비스 상태 확인"
echo ""

cd "$INFRA_DIR/docker"

# Docker 서비스 상태
echo "📦 Docker 서비스:"
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "  ❌ Docker Compose 서비스 없음"
echo ""

# PostgreSQL
echo -n "🐘 PostgreSQL: "
if docker compose exec -T db pg_isready -U clickeye > /dev/null 2>&1; then
  echo "✅ 정상"
else
  echo "❌ 연결 불가"
fi

# Redis
echo -n "🔴 Redis: "
if docker compose exec -T redis redis-cli ping > /dev/null 2>&1; then
  echo "✅ 정상"
else
  echo "❌ 연결 불가"
fi

# API 서버
echo -n "🚀 API 서버 (localhost:8000): "
if curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
  echo "✅ 정상"
else
  echo "⚠️ 미실행"
fi

# Web 서버
echo -n "🌐 Web 서버 (localhost:3000): "
if curl -s http://localhost:3000 > /dev/null 2>&1; then
  echo "✅ 정상"
else
  echo "⚠️ 미실행"
fi

echo ""
