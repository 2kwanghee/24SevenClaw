#!/usr/bin/env bash
# Webhook Doctor — Linear Webhook 환경 자동 진단·정리·기동·검증.
#
# 사용법:
#   bash scripts/webhook-doctor.sh             # 기본: 진단 → 자체 정리 → 기동 → 검증
#   bash scripts/webhook-doctor.sh --check     # 진단만 (변경 없음)
#   bash scripts/webhook-doctor.sh --stop      # 자체 webhook+ngrok 정리
#   bash scripts/webhook-doctor.sh --force     # 타 프로젝트 점유도 종료 후 기동
#   bash scripts/webhook-doctor.sh --no-ngrok  # webhook만 기동 (ngrok skip)
#   bash scripts/webhook-doctor.sh --help      # 도움말
#
# 환경변수 (.env):
#   WEBHOOK_PORT      webhook 서버 포트 (기본 9876)
#   NGROK_DOMAIN      ngrok reserved 도메인 (없으면 understandingly-...-raymundo.ngrok-free.dev)
#   NGROK_WEB_PORT    ngrok 로컬 web UI 포트 (기본 4040)

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"
mkdir -p logs .run

# ── .env 로드 ──
if [[ -f .env ]]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
fi

PORT="${WEBHOOK_PORT:-9876}"
NGROK_WEB_PORT="${NGROK_WEB_PORT:-4040}"
NGROK_DOMAIN="${NGROK_DOMAIN:-understandingly-unforecasted-raymundo.ngrok-free.dev}"
WEBHOOK_PID_FILE=".run/webhook.pid"
NGROK_PID_FILE=".run/ngrok.pid"
WEBHOOK_LOG="logs/webhook.log"
NGROK_LOG="logs/ngrok.log"

# ── 색상 ──
if [[ -t 1 ]]; then
    C_RED=$'\033[31m'; C_GRN=$'\033[32m'; C_YEL=$'\033[33m'
    C_BLU=$'\033[34m'; C_DIM=$'\033[2m';  C_NC=$'\033[0m'
else
    C_RED=''; C_GRN=''; C_YEL=''; C_BLU=''; C_DIM=''; C_NC=''
fi
log()  { printf "%s[%s]%s %s\n" "$C_BLU" "$(date +%H:%M:%S)" "$C_NC" "$*"; }
ok()   { printf "%s  ✓%s %s\n" "$C_GRN" "$C_NC" "$*"; }
warn() { printf "%s  ⚠%s %s\n" "$C_YEL" "$C_NC" "$*"; }
err()  { printf "%s  ✗%s %s\n" "$C_RED" "$C_NC" "$*"; }
sub()  { printf "%s    %s%s\n" "$C_DIM" "$*" "$C_NC"; }

# ── 플래그 파싱 ──
MODE="default"   # default | check | stop
FORCE=false
NO_NGROK=false
for arg in "$@"; do
    case "$arg" in
        --check)    MODE="check" ;;
        --stop)     MODE="stop" ;;
        --force)    FORCE=true ;;
        --no-ngrok) NO_NGROK=true ;;
        --help|-h)
            grep -E "^# " "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) err "알 수 없는 옵션: $arg (사용법: --help)"; exit 2 ;;
    esac
done

# ── 진단 유틸 ──
proc_cwd() { readlink "/proc/$1/cwd" 2>/dev/null || echo ""; }

is_our_proc() {
    local cwd; cwd="$(proc_cwd "$1")"
    [[ "$cwd" == "$PROJECT_ROOT" || "$cwd" == "$PROJECT_ROOT"/* ]]
}

port_owner_pid() {
    # 주어진 포트의 LISTEN PID 반환 (없으면 빈 문자열).
    ss -ltnp 2>/dev/null \
        | awk -v p=":$1\$" '$4 ~ p {print $NF}' \
        | grep -oE 'pid=[0-9]+' \
        | head -1 \
        | sed 's/pid=//'
}

# 컨테이너 소유 PID 판정 (CE-338 잔여). WSL 의 docker 는 컨테이너 프로세스를 호스트
# PID 네임스페이스에 노출하므로, pgrep 만으로는 compose 수신부(clickeye-webhook)의
# webhook_server.py 를 "호스트 잔재"로 오탐한다. 실측(2026-08-04): PID 1598 이
# cgroup `…/docker-<id>.scope` 인데 잔재로 경고되고 --force 대상에 들어갔다 —
# 그대로 강제 종료하면 운영 중인 수신부를 죽인다. cgroup 으로 걸러낸다.
is_container_proc() {
    grep -qE '(docker-[0-9a-f]{12,}|/docker/|containerd)' "/proc/$1/cgroup" 2>/dev/null
}

list_webhook_pids() {
    # 호스트 프로세스만 반환한다(컨테이너 소유는 제외 — 컨테이너 상태는
    # webhook_container_running 이 별도로 본다).
    while IFS= read -r pid; do
        [[ -z "$pid" ]] && continue
        is_container_proc "$pid" && continue
        echo "$pid"
    done < <(pgrep -f "webhook_server\.py" 2>/dev/null | sort -u)
}

list_ngrok_pids() {
    # ngrok http / ngrok start / ngrok tcp 등 모든 모드
    {
        pgrep -f "ngrok (http|start|tcp|tls)" 2>/dev/null
        pgrep -x "ngrok" 2>/dev/null
    } | sort -u
}

# 수신부는 compose 서비스(clickeye-webhook 컨테이너)로 옮겨졌다. 컨테이너가 9876 을
# 퍼블리시 중이면 호스트 webhook_server.py 기동은 포트 충돌을 유발하므로, 진단·--fix
# 모두 컨테이너 상태를 먼저 본다.
webhook_container_running() {
    command -v docker >/dev/null 2>&1 || return 1
    [[ "$(docker inspect -f '{{.State.Running}}' clickeye-webhook 2>/dev/null)" == "true" ]]
}

# 호스트 실행 워커(큐 소비 담당) PID. 문자클래스로 자기매칭을 원천 차단.
list_worker_pids() {
    pgrep -f "[w]ebhook_worker.py" 2>/dev/null | sort -u
}

# 타 프로젝트 PID 분리
filter_other() {
    while IFS= read -r pid; do
        [[ -z "$pid" ]] && continue
        if ! is_our_proc "$pid"; then echo "$pid"; fi
    done
}
filter_self() {
    while IFS= read -r pid; do
        [[ -z "$pid" ]] && continue
        if is_our_proc "$pid"; then echo "$pid"; fi
    done
}

diagnose() {
    log "진단 시작"
    echo

    # 1. 포트 점유
    printf "%s[1/4]%s 포트 점유\n" "$C_BLU" "$C_NC"
    local p_main p_ngrok_web
    p_main="$(port_owner_pid "$PORT")"
    p_ngrok_web="$(port_owner_pid "$NGROK_WEB_PORT")"
    if [[ -n "$p_main" ]]; then
        if is_our_proc "$p_main"; then ok "포트 $PORT → PID $p_main (본 프로젝트)"
        else warn "포트 $PORT → PID $p_main (타 프로젝트: $(proc_cwd "$p_main"))"
        fi
    else
        sub "포트 $PORT → 점유 없음"
    fi
    if [[ -n "$p_ngrok_web" ]]; then
        if is_our_proc "$p_ngrok_web"; then ok "ngrok web $NGROK_WEB_PORT → PID $p_ngrok_web (본 프로젝트)"
        else warn "ngrok web $NGROK_WEB_PORT → PID $p_ngrok_web (타 프로젝트 ngrok: $(proc_cwd "$p_ngrok_web"))"
        fi
    else
        sub "ngrok web $NGROK_WEB_PORT → 점유 없음"
    fi
    echo

    # 2. 수신부(webhook 컨테이너) + 호스트 워커
    printf "%s[2/4]%s webhook 컨테이너 + 호스트 워커\n" "$C_BLU" "$C_NC"
    if webhook_container_running; then
        ok "컨테이너 clickeye-webhook 실행 중 (9876 수신부는 컨테이너 소유)"
        sub "로그: docker logs --tail 50 clickeye-webhook"
    elif command -v docker >/dev/null 2>&1; then
        warn "컨테이너 clickeye-webhook 미실행 — 기동: docker compose --profile full up -d webhook"
    else
        warn "docker 미설치 — 컨테이너 수신부 상태 확인 불가"
    fi
    # 호스트에 남아있는 webhook_server.py 는 이제 컨테이너와 9876 충돌을 일으키는 잔재다.
    local pid cwd cmd stray=false
    while IFS= read -r pid; do
        [[ -z "$pid" ]] && continue
        stray=true
        cwd="$(proc_cwd "$pid")"
        cmd="$(ps -p "$pid" -o args= 2>/dev/null | cut -c1-100)"
        warn "호스트 webhook_server.py 잔재 PID $pid (@ $cwd) — 컨테이너와 9876 충돌 위험: $cmd"
    done < <(list_webhook_pids)
    $stray || sub "호스트 webhook_server.py 잔재 없음(정상 — 수신부는 컨테이너)"
    # 호스트 워커(큐 소비) 생존 확인.
    local wseen=false
    while IFS= read -r pid; do
        [[ -z "$pid" ]] && continue
        wseen=true
        cmd="$(ps -p "$pid" -o args= 2>/dev/null | cut -c1-100)"
        ok "호스트 워커 webhook_worker.py PID $pid — $cmd"
    done < <(list_worker_pids)
    $wseen || warn "호스트 워커 webhook_worker.py 미실행 — 큐 소비 정지 상태(--fix 로 기동)"
    echo

    # 3. ngrok 프로세스
    printf "%s[3/4]%s ngrok 프로세스\n" "$C_BLU" "$C_NC"
    seen=false
    while IFS= read -r pid; do
        [[ -z "$pid" ]] && continue
        seen=true
        cwd="$(proc_cwd "$pid")"
        cmd="$(ps -p "$pid" -o args= 2>/dev/null | cut -c1-130)"
        if is_our_proc "$pid"; then ok "PID $pid (본 프로젝트) — $cmd"
        else warn "PID $pid (타 프로젝트 @ $cwd) — $cmd"
        fi
    done < <(list_ngrok_pids)
    $seen || sub "실행 중 ngrok 없음"
    echo

    # 4. Linear webhook 등록 매칭
    printf "%s[4/4]%s Linear webhook 등록 vs ngrok 도메인\n" "$C_BLU" "$C_NC"
    if python3 "$SCRIPT_DIR/webhook_doctor_linear_check.py" "$NGROK_DOMAIN" 2>&1; then
        :
    else
        warn "Linear 등록 확인 스킵 (네트워크/키 문제)"
    fi
    echo
}

# 자체 프로세스 정리
cleanup_self() {
    log "자체 webhook/ngrok 정리"
    local pid killed=0
    while IFS= read -r pid; do
        [[ -z "$pid" ]] && continue
        ok "kill PID $pid (본 프로젝트 webhook_server.py)"
        kill "$pid" 2>/dev/null && killed=$((killed+1))
    done < <(list_webhook_pids | filter_self)
    while IFS= read -r pid; do
        [[ -z "$pid" ]] && continue
        ok "kill PID $pid (본 프로젝트 ngrok)"
        kill "$pid" 2>/dev/null && killed=$((killed+1))
    done < <(list_ngrok_pids | filter_self)
    rm -f "$WEBHOOK_PID_FILE" "$NGROK_PID_FILE"
    [[ $killed -eq 0 ]] && sub "정리할 자체 프로세스 없음"
    sleep 1
}

# 타 프로젝트 정리 (--force)
cleanup_others() {
    log "타 프로젝트 webhook/ngrok 정리 (--force)"
    local pid
    while IFS= read -r pid; do
        [[ -z "$pid" ]] && continue
        warn "kill PID $pid (타 프로젝트 webhook_server.py @ $(proc_cwd "$pid"))"
        kill "$pid" 2>/dev/null || true
    done < <(list_webhook_pids | filter_other)
    while IFS= read -r pid; do
        [[ -z "$pid" ]] && continue
        warn "kill PID $pid (타 프로젝트 ngrok @ $(proc_cwd "$pid"))"
        kill "$pid" 2>/dev/null || true
    done < <(list_ngrok_pids | filter_other)
    sleep 1
}

start_webhook() {
    log "webhook 서버 기동 (포트 $PORT)"
    nohup python3 "$SCRIPT_DIR/webhook_server.py" --port "$PORT" \
        > "$WEBHOOK_LOG" 2>&1 &
    local pid=$!
    echo "$pid" > "$WEBHOOK_PID_FILE"
    ok "PID $pid → 로그: $WEBHOOK_LOG"
}

start_ngrok() {
    if $NO_NGROK; then sub "ngrok 건너뜀 (--no-ngrok)"; return 0; fi
    local ngrok_bin=""
    if command -v ngrok >/dev/null 2>&1; then
        ngrok_bin="$(command -v ngrok)"
    elif [[ -x "$HOME/bin/ngrok" ]]; then
        ngrok_bin="$HOME/bin/ngrok"
    else
        warn "ngrok 바이너리를 찾을 수 없음 — PATH 또는 ~/bin/ngrok에 설치 필요"
        return 0
    fi
    log "ngrok 기동 (도메인: $NGROK_DOMAIN)"
    nohup "$ngrok_bin" http "$PORT" --url="https://$NGROK_DOMAIN" \
        --log=stdout --log-format=logfmt > "$NGROK_LOG" 2>&1 &
    local pid=$!
    echo "$pid" > "$NGROK_PID_FILE"
    ok "PID $pid → https://$NGROK_DOMAIN (로그: $NGROK_LOG)"
}

verify() {
    log "검증"
    sleep 3

    # webhook 프로세스
    local wh_pid; wh_pid="$(cat "$WEBHOOK_PID_FILE" 2>/dev/null || echo "")"
    if [[ -n "$wh_pid" ]] && kill -0 "$wh_pid" 2>/dev/null; then
        ok "webhook 서버 PID $wh_pid 살아있음"
    else
        err "webhook 서버 시작 실패 — 로그 확인: tail $WEBHOOK_LOG"
        return 1
    fi

    # 로컬 health
    local local_resp
    local_resp="$(curl -s -m 3 "http://localhost:$PORT/health" 2>/dev/null || echo "")"
    if [[ "$local_resp" == *'"status"'*'"ok"'* ]]; then
        ok "로컬  /health  → $local_resp"
    else
        err "로컬  /health  실패: $local_resp"
        return 1
    fi

    if $NO_NGROK; then return 0; fi

    # ngrok 프로세스
    local ng_pid; ng_pid="$(cat "$NGROK_PID_FILE" 2>/dev/null || echo "")"
    if [[ -n "$ng_pid" ]] && kill -0 "$ng_pid" 2>/dev/null; then
        ok "ngrok PID $ng_pid 살아있음"
    else
        err "ngrok 시작 실패 — 로그 확인: tail $NGROK_LOG"
        sub "흔한 원인: reserved 도메인($NGROK_DOMAIN)이 다른 프로세스/세션에 점유됨"
        sub "조치: bash scripts/webhook-doctor.sh --force"
        return 1
    fi

    # 외부 health
    local ext_resp
    ext_resp="$(curl -s -m 5 "https://$NGROK_DOMAIN/health" 2>/dev/null || echo "")"
    if [[ "$ext_resp" == *'"status"'*'"ok"'* ]]; then
        ok "외부  /health  → $ext_resp"
    else
        warn "외부  /health  응답 없음/이상 — ngrok 터널 기동까지 1-3초 더 걸릴 수 있음"
        sub "다시 확인: curl https://$NGROK_DOMAIN/health"
    fi
}

# 호스트 워커 기동(큐 소비). 이미 살아있으면 건드리지 않는다.
start_worker() {
    if [[ -n "$(list_worker_pids)" ]]; then
        ok "호스트 워커 이미 실행 중 — 재기동 생략"
        return 0
    fi
    log "호스트 워커 기동 (webhook_worker.py)"
    nohup python3 "$SCRIPT_DIR/webhook_worker.py" >> "$PROJECT_ROOT/logs/webhook-worker.log" 2>&1 &
    ok "PID $! → 로그: logs/webhook-worker.log"
}

# 컨테이너 수신부 모드 검증: 호스트 pid 대신 /health(컨테이너 퍼블리시) + 워커 생존.
verify_container() {
    log "검증(컨테이너 수신부 + 호스트 워커)"
    sleep 2
    local resp
    resp="$(curl -s -m 3 "http://localhost:$PORT/health" 2>/dev/null || echo "")"
    if [[ "$resp" == *'"status"'*'"ok"'* ]]; then
        ok "로컬 /health → $resp"
    else
        err "로컬 /health 실패: $resp (컨테이너 상태: docker logs --tail 50 clickeye-webhook)"
        return 1
    fi
    [[ -n "$(list_worker_pids)" ]] && ok "호스트 워커 생존" || { err "호스트 워커 미기동"; return 1; }
    return 0
}

# ════════════════════════════════════════════════════
echo "═══════════════════════════════════════════════════"
echo "  Webhook Doctor — ClickEye Linear Webhook"
echo "═══════════════════════════════════════════════════"
echo

case "$MODE" in
    check) diagnose; exit 0 ;;
    stop)  cleanup_self; ok "정리 완료"; exit 0 ;;
esac

# default flow
diagnose

# 타 프로젝트 점유 시 충돌 처리
OTHERS_WH="$(list_webhook_pids | filter_other)"
OTHERS_NG="$(list_ngrok_pids | filter_other)"
if [[ -n "$OTHERS_NG" ]]; then
    err "타 프로젝트의 ngrok이 살아있습니다. reserved 도메인($NGROK_DOMAIN) 점유 충돌이 발생할 수 있습니다."
    if $FORCE; then
        cleanup_others
    else
        sub "타 프로젝트 ngrok 정리 후 진행하려면: bash scripts/webhook-doctor.sh --force"
        exit 3
    fi
elif [[ -n "$OTHERS_WH" ]]; then
    warn "타 프로젝트 webhook_server.py 가 살아있음 (포트가 다르면 충돌 아님)."
    $FORCE && cleanup_others || sub "건드리지 않습니다. 강제 종료하려면: --force"
fi

if webhook_container_running; then
    # 컨테이너가 9876 을 소유한다. 호스트 webhook_server 를 띄우면 바인딩 충돌 →
    # 호스트 서버 기동을 생략하고, 잔재 정리 + 워커·ngrok(호스트→컨테이너 터널)만 보장한다.
    log "수신부는 컨테이너(clickeye-webhook) 담당 — 호스트 webhook_server 기동 생략(9876 충돌 방지)"
    cleanup_self
    start_worker
    start_ngrok
    verify_container
    RC=$?
else
    # 컨테이너 미기동 → 레거시 호스트 단독 경로(회귀 0). 큐를 쓰지 않으므로 워커는 띄우지 않는다.
    cleanup_self
    start_webhook
    start_ngrok
    verify
    RC=$?
fi

echo
if [[ $RC -eq 0 ]]; then
    log "완료. 사용 가능 명령"
else
    log "일부 검증 실패 — 위 메시지 확인"
fi
echo "  curl http://localhost:$PORT/health"
echo "  curl https://$NGROK_DOMAIN/health"
echo "  tail -f $WEBHOOK_LOG          # webhook 수신 로그"
echo "  bash scripts/auto_dev_pipeline.sh --once   # 수동 트리거"
echo "  bash scripts/webhook-doctor.sh --stop      # 정지"
echo

exit $RC
