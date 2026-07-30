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

# ── 컨테이너 모드 충돌 가드 (CE-338) ──
# 수신부는 compose 서비스(clickeye-webhook)로 옮겨졌다. 컨테이너가 9876 을 퍼블리시한
# 상태에서 호스트 서버를 띄우면 포트가 충돌해 한쪽이 죽거나 컨테이너가 restart 루프에
# 빠진다. 컨테이너가 살아 있으면 기동하지 않고 안내만 한다.
if docker compose -f clickeye-infra/docker/docker-compose.yml ps -q webhook 2>/dev/null | grep -q .; then
    echo "[SKIP] webhook 컨테이너가 실행 중입니다 — 호스트 서버를 띄우지 않습니다(9876 충돌 방지)." >&2
    echo "       상태: docker compose -f clickeye-infra/docker/docker-compose.yml ps webhook" >&2
    echo "       로그: docker logs --tail 50 clickeye-webhook" >&2
    echo "       호스트 단독 모드가 필요하면 먼저 컨테이너를 내리세요(down webhook)." >&2
    exit 0
fi

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
