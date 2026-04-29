#!/usr/bin/env bash
# Linear Webhook 서버 시작
#
# 사용법:
#   bash scripts/start-webhook.sh           # 백그라운드 기동 (터미널 종료 가능)
#   bash scripts/start-webhook.sh debug     # 포그라운드 — 로그 실시간 확인
#   bash scripts/start-webhook.sh debugger  # 동일
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"
mkdir -p logs .run

# .env 로드
if [[ -f .env ]]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
fi

# debug 파라미터 감지
DEBUG_MODE=false
for arg in "$@"; do
    case "${arg,,}" in debug|debugger) DEBUG_MODE=true ;; esac
done

# 기존 프로세스 정리
pkill -f "webhook_server.py" 2>/dev/null || true
sleep 1

if $DEBUG_MODE; then
    echo "[DEBUG] 포그라운드 모드 — Ctrl+C로 종료"
    echo "  포트  : ${WEBHOOK_PORT:-9876}"
    echo "  로그  : 터미널 직접 출력"
    echo ""
    exec python3 "$SCRIPT_DIR/webhook_server.py" --port "${WEBHOOK_PORT:-9876}"
fi

# ── 백그라운드 모드 ──
nohup python3 "$SCRIPT_DIR/webhook_server.py" \
    --port "${WEBHOOK_PORT:-9876}" \
    > logs/webhook.log 2>&1 &
WH_PID=$!
echo "$WH_PID" > .run/webhook.pid

echo "Webhook 서버 기동 완료 (PID: $WH_PID)"
echo "  로그 확인 : tail -f logs/webhook.log"
echo "  헬스 체크 : curl http://localhost:${WEBHOOK_PORT:-9876}/health"
echo "  종료      : bash scripts/stop-webhook.sh"
