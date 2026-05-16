#!/usr/bin/env bash
# Webhook 서버 + ngrok 종료 — 본 프로젝트 프로세스만 대상.
# 사용법: bash scripts/stop-webhook.sh
set -uo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

is_our() {
    local cwd; cwd="$(readlink "/proc/$1/cwd" 2>/dev/null || echo "")"
    [[ "$cwd" == "$PROJECT_ROOT" || "$cwd" == "$PROJECT_ROOT"/* ]]
}

stop_pid_file() {
    local f="$1" name="$2"
    if [[ -f "$f" ]]; then
        local pid; pid="$(cat "$f" 2>/dev/null)"
        if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null && echo "$name 종료 (PID $pid, .pid 파일)"
        fi
        rm -f "$f"
    fi
}

stop_pid_file ".run/webhook.pid" "Webhook 서버"
stop_pid_file ".run/ngrok.pid"   "ngrok"

# 잔여: 본 프로젝트 cwd만 종료 (타 프로젝트 보호)
killed_wh=false
for pid in $(pgrep -f "webhook_server\.py" 2>/dev/null); do
    if is_our "$pid"; then
        kill "$pid" 2>/dev/null && echo "Webhook 서버 잔여 종료 (PID $pid)" && killed_wh=true
    fi
done

killed_ng=false
for pid in $(pgrep -f "ngrok (http|start|tcp|tls)" 2>/dev/null); do
    if is_our "$pid"; then
        kill "$pid" 2>/dev/null && echo "ngrok 잔여 종료 (PID $pid)" && killed_ng=true
    fi
done

$killed_wh || echo "Webhook 서버 잔여 없음"
$killed_ng || echo "ngrok 잔여 없음"
