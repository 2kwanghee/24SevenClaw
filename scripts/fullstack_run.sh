#!/usr/bin/env bash
# ClickEye 풀스택 런처 — bash 한 줄로 전체 스택을 멱등하게 기동한다.
#
# 기동 대상(run_guide 1~3단계를 한 스크립트로):
#   ① 클라우드면  docker compose --profile full up -d db redis migrate webhook [api]
#                 migrate 는 one-shot 으로 `alembic upgrade head` 를 적용한다(멱등).
#   ② API         :8000 을 이미 누가 서비스하면 그대로 인정하고, 아니면 compose api 를 띄운다
#                 (run_guide 1단계의 호스트 uvicorn 경로와 컨테이너 경로를 모두 지원)
#   ③ 웹          clickeye-web dev 서버(:3000, next dev --webpack)
#   ④ 실행면      webhook-doctor.sh 위임 — 호스트 워커(webhook_worker.py) + ngrok 예약 도메인
#   ⑤ cron        정본(scripts/clickeye_cron.txt)과 등록 crontab 대조 — 보고만, 자동 변경 없음
#
# 사용법:
#   bash scripts/fullstack_run.sh              # 전체 기동 (멱등 — 이미 떠 있으면 SKIP)
#   bash scripts/fullstack_run.sh --check      # 진단만, 아무것도 바꾸지 않음
#   bash scripts/fullstack_run.sh --stop       # 이 스크립트가 띄운 것만 정지
#   bash scripts/fullstack_run.sh --restart-web # 웹 dev 서버만 강제 재기동(멱등 생략 무시)
#   bash scripts/fullstack_run.sh --no-web     # 웹 dev 서버 제외
#   bash scripts/fullstack_run.sh --no-webhook # 실행면 전체 제외(워커·ngrok)
#   bash scripts/fullstack_run.sh --no-ngrok   # 터널만 제외
#   bash scripts/fullstack_run.sh --help
#
# 종료 코드:
#   0  전 요소 정상        1  하나 이상 실패(부분 기동)        2  전제 미충족(docker 없음 등)
#
# 설계 규칙:
#   · fail-fast 하지 않는다 — 한 요소가 실패해도 나머지를 계속 올리고 요약에서 실패를 명시한다
#     (부분 기동이 전무보다 낫고, 무엇이 빠졌는지 보이는 것이 더 중요하다)
#   · 남의 것을 건드리지 않는다 — --stop 은 ClickEye 소유(compose 프로젝트 + 이 레포 cwd)만
#     정지한다. hawkeye-*·infraeye3-* 등 타 프로젝트 컨테이너·ngrok 은 대상이 아니다
#   · 기동 로직을 복제하지 않는다 — 실행면은 webhook-doctor.sh, 마이그레이션은 compose migrate
#
# 관련: docs/spec/run_guide.md (3-5-1 재부팅 복구) · CE-351(부팅 자동 복구는 그 티켓의 몫)

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT" || exit 2
mkdir -p logs .run

COMPOSE_DIR="$PROJECT_ROOT/clickeye-infra/docker"
WEB_DIR="$PROJECT_ROOT/clickeye-web"
WEB_PID_FILE=".run/web.pid"
WEB_LOG="logs/web-dev.log"
CRON_CANON="$PROJECT_ROOT/scripts/clickeye_cron.txt"

# 컨테이너 healthy 대기 상한(초). 최초 빌드가 끼면 compose up 자체가 더 걸리므로 up 이후만 잰다.
HEALTH_WAIT=120
WEB_WAIT=90

API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-3000}"
WEBHOOK_PORT="${WEBHOOK_PORT:-9876}"
API_HEALTH="http://localhost:${API_PORT}/api/v1/health"

# ── 색상·출력 (webhook-doctor.sh 관례 계승) ──
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
step() { printf "\n%s[%s]%s %s\n" "$C_BLU" "$1" "$C_NC" "$2"; }

# ── 요약 수집 (요소명|상태|비고) ──
SUMMARY=()
FAILED=0
record() {   # record <요소> <ok|skip|fail|warn> <비고>
    SUMMARY+=("$1|$2|$3")
    [[ "$2" == "fail" ]] && FAILED=1
    return 0
}

usage() { sed -n '2,32p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

MODE="run"        # run | check | stop
NO_WEB=false
NO_WEBHOOK=false
NO_NGROK=false
RESTART_WEB=false
for arg in "$@"; do
    case "$arg" in
        --check)      MODE="check" ;;
        --stop)       MODE="stop" ;;
        --restart-web) RESTART_WEB=true ;;
        --no-web)     NO_WEB=true ;;
        --no-webhook) NO_WEBHOOK=true ;;
        --no-ngrok)   NO_NGROK=true ;;
        --help|-h)    usage; exit 0 ;;
        *)            err "알 수 없는 옵션: $arg"; sub "사용법: --help"; exit 2 ;;
    esac
done

# --restart-web 은 "정지 후 기동" 행위다. 아무것도 바꾸지 않는 --check 나 웹을 아예 빼는
# --no-web 과 함께 오면 **조용히 무시하지 않는다** — 재기동을 기대한 사용자가 낡은 서버를
# 계속 보게 되는 것이 이 플래그가 없애려는 바로 그 증상이기 때문이다(CE-374).
if $RESTART_WEB; then
    if [[ "$MODE" != "run" ]]; then
        err "--restart-web 은 --${MODE} 와 함께 쓸 수 없습니다"
        sub "--${MODE} 는 기동하지 않습니다. 재기동만 원하면 --restart-web 단독으로 실행하세요."
        exit 2
    fi
    if $NO_WEB; then
        err "--restart-web 과 --no-web 은 모순입니다(재기동 vs 제외)"
        sub "웹만 재기동: bash scripts/fullstack_run.sh --restart-web"
        exit 2
    fi
fi

# ── 공용 헬퍼 ────────────────────────────────────────────────────────────────

# 개행·공백을 제거한 첫 토큰만 남긴다. docker inspect 는 대상이 없을 때 빈 줄을 내보내며
# 실패하므로(실측), 이걸 거치지 않으면 상태 문자열에 개행이 섞여 출력이 깨진다.
trim1() { tr -d '\r' | tr '\n' ' ' | awk '{print $1}'; }

port_pid() {   # 주어진 포트의 LISTEN PID (없으면 빈 문자열)
    ss -ltnp 2>/dev/null \
        | awk -v p=":$1\$" '$4 ~ p {print $NF}' \
        | grep -oE 'pid=[0-9]+' | head -1 | sed 's/pid=//'
}

proc_cwd() { readlink -f "/proc/$1/cwd" 2>/dev/null || echo "?"; }

# 이 레포에서 뜬 프로세스인지(cwd 가 PROJECT_ROOT 이하). 판독 불가(권한/컨테이너)는 false.
is_ours() {
    local cwd; cwd="$(proc_cwd "$1")"
    [[ "$cwd" == "$PROJECT_ROOT" || "$cwd" == "$PROJECT_ROOT"/* ]]
}

container_state() {
    local s; s="$(docker inspect -f '{{.State.Status}}' "$1" 2>/dev/null | trim1)"
    echo "${s:-absent}"
}
container_health() {
    local h
    h="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$1" 2>/dev/null | trim1)"
    echo "${h:-absent}"
}
container_desc() { echo "$(container_state "$1")/$(container_health "$1")"; }

# healthcheck 가 있으면 healthy, 없으면 running 을 정상으로 본다.
container_up() {
    local st hl
    st="$(container_state "$1")"; hl="$(container_health "$1")"
    [[ "$st" == "running" ]] && { [[ "$hl" == "healthy" || "$hl" == "none" ]]; }
}

wait_container() {   # wait_container <이름> <상한초>
    local name="$1" limit="$2" waited=0
    while (( waited < limit )); do
        container_up "$name" && return 0
        [[ "$(container_state "$name")" == "exited" ]] && return 1
        sleep 3; waited=$((waited+3))
    done
    return 1
}

worker_pids() { pgrep -f "[w]ebhook_worker.py" 2>/dev/null | sort -u; }
web_pids()    { pgrep -f "[n]ext dev" 2>/dev/null | sort -u; }

# 이 레포 소유 PID 만 남긴다(타 프로젝트의 동명 프로세스 보호).
filter_ours() {
    local pid
    while IFS= read -r pid; do
        [[ -z "$pid" ]] && continue
        is_ours "$pid" && echo "$pid"
    done
}

# curl 은 접속 실패 시에도 %{http_code} 로 "000" 을 출력하면서 exit 非0 이다. 여기에
# `|| echo 000` 을 덧붙이면 "000000" 이 되어 "000 이 아니면 준비됨" 판정을 오통과한다(실측).
# 따라서 폴백을 붙이지 않고, 항상 3자리로 잘라 정규화한다.
http_code() {
    local c; c="$(curl -s -o /dev/null -m 5 -w "%{http_code}" "$1" 2>/dev/null)"
    c="$(printf '%s' "$c" | tr -dc '0-9')"
    c="${c:0:3}"
    printf '%s\n' "${c:-000}"
}
api_serving() { [[ "$(http_code "$API_HEALTH")" == "200" ]]; }

# 표시 폭 기준 좌측 정렬. printf %-Ns 는 **바이트** 기준이라 한글(3바이트/2칸) 라벨에서
# 컬럼이 깨진다(실측). ASCII 는 1칸, 그 외는 2칸으로 세어 직접 패딩한다.
pad() {   # pad <문자열> <목표폭>
    local s="$1" want="$2" w=0 i ch
    for (( i=0; i<${#s}; i++ )); do
        ch="${s:i:1}"
        if [[ "$ch" == [[:ascii:]] ]]; then w=$((w+1)); else w=$((w+2)); fi
    done
    printf "%s" "$s"
    while (( w < want )); do printf " "; w=$((w+1)); done
}

# ── 0. 전제 확인 ─────────────────────────────────────────────────────────────

check_prereq() {
    local fatal=0

    if ! command -v docker >/dev/null 2>&1; then
        err "docker 없음 — 이 스크립트는 compose 로 클라우드면을 띄웁니다"; fatal=1
    elif ! docker info >/dev/null 2>&1; then
        err "docker 데몬 미응답 — Docker Desktop/서비스를 먼저 시작하세요"; fatal=1
    else
        ok "docker 데몬 응답"
    fi

    local missing=()
    for c in node npm python3; do command -v "$c" >/dev/null 2>&1 || missing+=("$c"); done
    if ((${#missing[@]})); then warn "미설치 CLI: ${missing[*]} — 해당 요소는 건너뜁니다"
    else ok "node/npm/python3 확인"; fi

    command -v ngrok >/dev/null 2>&1 || warn "ngrok 없음 — 터널 없이 로컬만 동작(Linear 이벤트 미수신)"

    # WEBHOOK_SECRET: compose 는 required:false 라 조용히 통과하고 서버가 fail-closed 로 거부한다.
    # 스크립트가 먼저 검사해 "왜 webhook 이 안 뜨는지" 를 미리 알린다.
    local wenv="$PROJECT_ROOT/clickeye-infra/managed/webhook.env"
    if [[ ! -f "$wenv" ]]; then
        warn "clickeye-infra/managed/webhook.env 없음 — 수신부가 기동을 거부합니다(fail-closed)"
        sub "webhook.env.example 을 복사하고 Linear Signing Secret 을 WEBHOOK_SECRET 에 넣으세요"
    elif ! grep -qE '^WEBHOOK_SECRET=.+' "$wenv"; then
        warn "webhook.env 에 WEBHOOK_SECRET 값이 비어 있음 — 수신부가 기동을 거부합니다"
    else
        ok "WEBHOOK_SECRET 주입 경로 확인"
    fi

    (( fatal )) && return 2
    return 0
}

# ── 1. 클라우드면 (compose) ──────────────────────────────────────────────────
# API 는 두 경로가 공존한다(run_guide 1단계 = 호스트 uvicorn, compose = api 컨테이너).
# 이미 :8000 을 누가 서비스하고 있으면 그것을 인정하고 compose api 는 건드리지 않는다.

start_cloud() {
    step "1/5" "클라우드면 기동 (db · redis · migrate · webhook [· api])"

    local services=(db redis migrate webhook)
    local api_mode="container" api_note=""
    local p; p="$(port_pid "$API_PORT")"

    if api_serving; then
        if [[ "$(container_state clickeye-api)" == "running" ]]; then
            api_mode="container"; api_note="컨테이너 clickeye-api"
            ok "API 이미 서비스 중 — 컨테이너 경로"
            services+=(api)   # 이미 running 이면 up -d 가 그대로 유지(멱등)
        else
            api_mode="host"; api_note="호스트 프로세스 PID ${p:-?}"
            ok "API 이미 서비스 중 — 호스트 경로 (PID ${p:-?} @ $( [[ -n "$p" ]] && proc_cwd "$p" ))"
            sub "compose api 는 띄우지 않습니다(포트 $API_PORT 중복 바인딩 방지)"
        fi
    elif [[ -n "$p" ]]; then
        api_mode="blocked"; api_note="포트 $API_PORT 선점(PID $p), 헬스 미응답"
        warn "포트 $API_PORT 를 PID $p 가 선점했으나 $API_HEALTH 가 200 이 아닙니다"
        sub "$(ps -p "$p" -o args= 2>/dev/null | cut -c1-110)"
        sub "그 프로세스를 정리한 뒤 재실행하세요(자동 종료하지 않습니다): kill $p"
    else
        services+=(api)
        sub "API 미서비스 → compose api 포함"
    fi

    local pending=() c
    for c in clickeye-db clickeye-redis clickeye-webhook; do
        container_up "$c" || pending+=("$c")
    done
    [[ "$api_mode" == "container" ]] && { container_up clickeye-api || pending+=("clickeye-api"); }

    log "docker compose --profile full up -d ${services[*]}"
    if ! (cd "$COMPOSE_DIR" && docker compose --profile full up -d "${services[@]}" 2>&1 | sed 's/^/    /'); then
        err "compose up 실패 — 위 출력 확인"
    fi
    ((${#pending[@]} == 0)) && sub "기동 대상 전부 이미 정상(멱등 — 재기동 없음)"

    # migrate 는 one-shot(restart: "no"). 실패하면 스키마가 코드보다 낡은 채로 도는 것이므로
    # 반드시 결과를 확인한다.
    local mst mrc
    mst="$(container_state clickeye-migrate)"
    if [[ "$mst" == "running" ]]; then
        sub "마이그레이션 진행 중 — 완료 대기"
        local waited=0
        while [[ "$(container_state clickeye-migrate)" == "running" ]] && (( waited < HEALTH_WAIT )); do
            sleep 3; waited=$((waited+3))
        done
        mst="$(container_state clickeye-migrate)"
    fi
    if [[ "$mst" == "exited" ]]; then
        mrc="$(docker inspect -f '{{.State.ExitCode}}' clickeye-migrate 2>/dev/null | trim1)"
        if [[ "$mrc" == "0" ]]; then
            ok "마이그레이션 적용 완료 (migrate exit 0)"
            record "마이그레이션" ok "alembic upgrade head"
        else
            err "마이그레이션 실패 (migrate exit $mrc)"
            # 가장 흔한 원인: 이미지에 구운 alembic/versions 가 DB 리비전보다 낡음.
            # (DB 는 호스트에서 최신까지 올라가 있는데 컨테이너 이미지는 그 리비전을 모르는 상태)
            if docker logs --tail 20 clickeye-migrate 2>&1 | grep -q "Can't locate revision"; then
                sub "원인: 이미지에 구운 alembic/versions 가 DB 리비전보다 낡음(이미지 재빌드 필요)"
                sub "조치: (cd clickeye-infra/docker && docker compose --profile full build migrate api)"
                record "마이그레이션" fail "이미지 낡음(리비전 미보유)"
            else
                sub "로그: docker logs clickeye-migrate"
                record "마이그레이션" fail "migrate exit $mrc"
            fi
        fi
    else
        warn "migrate 컨테이너 상태 불명($mst) — 스키마 최신 여부 미확인"
        record "마이그레이션" warn "상태 $mst"
    fi

    local label
    for c in clickeye-db clickeye-redis clickeye-webhook; do
        label="${c#clickeye-}"
        if wait_container "$c" "$HEALTH_WAIT"; then
            ok "$c $(container_desc "$c")"
            record "$label" ok "$(container_desc "$c")"
        else
            err "$c 기동 실패 ($(container_desc "$c")) — docker logs $c"
            record "$label" fail "$(container_desc "$c")"
        fi
    done

    # API 판정은 포트가 200 을 주는지로 한다(컨테이너/호스트 경로 공통).
    case "$api_mode" in
        blocked) record "api" fail "$api_note" ;;
        host)    record "api" ok "$api_note" ;;
        container)
            if wait_container clickeye-api "$HEALTH_WAIT"; then
                ok "clickeye-api $(container_desc clickeye-api)"
            else
                warn "clickeye-api $(container_desc clickeye-api) — 헬스 응답으로 재판정"
            fi
            if api_serving; then record "api" ok "컨테이너 clickeye-api"
            else record "api" fail "$(container_desc clickeye-api), 헬스 미응답"; fi
            ;;
    esac

    local code; code="$(http_code "$API_HEALTH")"
    [[ "$code" == "200" ]] && ok "API $API_HEALTH → 200" || err "API $API_HEALTH → $code"

    # ── dockerproxy (운영 패널 전용, --profile ops) ──────────────────────────────
    # api 는 raw docker.sock 을 쥐지 않고 이 read-only 프록시(POST=0)를 경유해 컨테이너를
    # 조회한다(app/services/ops/docker_client.py). profiles:[ops] 라 위 --profile full
    # 기동에서 빠지므로 여기서 명시적으로 올린다. 없으면 운영 패널의 컨테이너 모니터링만
    # 안 되고 딜리버리(무인 체인·API·웹)에는 영향이 없다 — 따라서 실패해도 fail-fast 하지
    # 않고 요약에 fail 로만 표시한다(부분 기동 우선 규칙).
    log "docker compose --profile ops up -d dockerproxy"
    if ! (cd "$COMPOSE_DIR" && docker compose --profile ops up -d dockerproxy 2>&1 | sed 's/^/    /'); then
        err "dockerproxy compose up 실패 — 운영 패널 컨테이너 모니터링만 영향(딜리버리 무관)"
    fi
    # dockerproxy 는 healthcheck 가 없어 running 이면 정상(container_up 이 health none 을 통과).
    if wait_container clickeye-dockerproxy "$HEALTH_WAIT"; then
        ok "clickeye-dockerproxy $(container_desc clickeye-dockerproxy)"
        record "dockerproxy" ok "$(container_desc clickeye-dockerproxy)"
    else
        err "clickeye-dockerproxy $(container_desc clickeye-dockerproxy) — 운영 패널 컨테이너 조회 불가(딜리버리 무관)"
        record "dockerproxy" fail "$(container_desc clickeye-dockerproxy)"
    fi
}

# ── 2. 웹 dev 서버 ───────────────────────────────────────────────────────────

start_web() {
    step "2/5" "웹 dev 서버 (:$WEB_PORT)"

    if $NO_WEB; then
        sub "--no-web → 생략"; record "웹" skip "--no-web"; return 0
    fi
    if ! command -v npm >/dev/null 2>&1; then
        warn "npm 없음 — 생략"; record "웹" skip "npm 미설치"; return 0
    fi

    # --restart-web: 멱등 생략 앞에서 우리 것만 내린다. dev 서버는 오래 살아 있는 동안
    # 워킹트리가 바뀌면(브랜치 전환·cron 의 checkout) 컴파일 캐시가 어긋난 채 계속
    # 서비스한다 — 실측 2026-08-05 에 9시간 32분 된 서버가 낡은 코드를 내려주고 있었고,
    # 재실행·브라우저 강제 새로고침 둘 다 듣지 않았다(CE-374).
    # filter_ours 를 반드시 거친다 — 타 프로젝트의 `next dev` 를 죽이지 않는다.
    if $RESTART_WEB; then
        local killed=0 rpid
        while IFS= read -r rpid; do
            [[ -z "$rpid" ]] && continue
            ok "kill PID $rpid (--restart-web)"
            kill "$rpid" 2>/dev/null && killed=$((killed+1))
        done < <(web_pids | filter_ours)
        rm -f "$WEB_PID_FILE"
        if (( killed )); then
            # 프로세스가 **사라질 때까지** 기다린다. 포트 해제만 보면 안 된다 — SIGTERM 직후
            # 부모가 죽어 포트는 즉시 풀리지만 자식(node)이 잠깐 생존하고, 그걸 아래 멱등
            # 생략이 "이미 실행 중"으로 잡아 새 서버를 띄우지 않는다(실측 2026-08-05:
            # HTTP 000 — 이 플래그가 없애려던 증상이 그대로 재현됐다).
            local w=0
            while (( w < 15 )); do
                [[ -z "$(web_pids | filter_ours | head -1)" && -z "$(port_pid "$WEB_PORT")" ]] && break
                sleep 1; w=$((w+1))
            done
            # 유예 후에도 남으면 SIGKILL. 남긴 채 진행하면 멱등 생략이 낡은 서버를 정상으로
            # 보고해 플래그가 무력화된다.
            local lp
            while IFS= read -r lp; do
                [[ -z "$lp" ]] && continue
                warn "PID $lp 가 SIGTERM 후에도 생존 — SIGKILL"
                kill -9 "$lp" 2>/dev/null && sleep 1
            done < <(web_pids | filter_ours)
            sub "기존 서버 ${killed}개 정지 (대기 ${w}초)"
        else
            sub "정지할 기존 서버 없음 — 새로 기동합니다"
        fi
    fi

    local existing; existing="$(web_pids | filter_ours | head -1)"
    if [[ -n "$existing" ]]; then
        ok "이미 실행 중 — PID $existing (멱등 생략)"
        record "웹" ok "PID $existing (기존)"
        return 0
    fi

    local p; p="$(port_pid "$WEB_PORT")"
    if [[ -n "$p" ]]; then
        warn "포트 $WEB_PORT 를 다른 프로세스가 선점: PID $p @ $(proc_cwd "$p")"
        sub "건드리지 않습니다. 정리 후 재실행하세요."
        record "웹" fail "포트 $WEB_PORT 선점(PID $p)"
        return 1
    fi

    # 최초 1회만 의존성 설치(멱등). 경로에 한글이 있으면 Turbopack 이 패닉하므로 dev 스크립트의
    # --webpack 은 의도된 설정이다 — 바꾸지 말 것(run_guide 2단계 경고).
    if [[ ! -d "$WEB_DIR/node_modules" ]]; then
        log "node_modules 없음 — npm install 1회 실행(수 분 소요, 로그: $WEB_LOG)"
        if ! (cd "$WEB_DIR" && npm install >>"$PROJECT_ROOT/$WEB_LOG" 2>&1); then
            err "npm install 실패 — tail -50 $WEB_LOG"
            record "웹" fail "npm install 실패"
            return 1
        fi
        ok "npm install 완료"
    fi

    log "npm run dev 기동"
    (cd "$WEB_DIR" && setsid --fork nohup npm run dev >>"$PROJECT_ROOT/$WEB_LOG" 2>&1)
    sleep 3
    local pid; pid="$(web_pids | filter_ours | head -1)"
    [[ -n "$pid" ]] && echo "$pid" > "$WEB_PID_FILE"

    local waited=0 code="000"
    while (( waited < WEB_WAIT )); do
        code="$(http_code "http://localhost:$WEB_PORT/")"
        [[ "$code" != "000" ]] && break
        sleep 3; waited=$((waited+3))
    done

    if [[ "$code" != "000" ]]; then
        ok "http://localhost:$WEB_PORT → $code (PID ${pid:-?})"
        record "웹" ok "HTTP $code, PID ${pid:-?}"
    else
        err "웹 dev 서버 응답 없음(${WEB_WAIT}초) — tail -50 $WEB_LOG"
        record "웹" fail "무응답 ${WEB_WAIT}s"
    fi
}

# ── 3. 무인 체인 실행면 (webhook-doctor 위임) ────────────────────────────────

start_exec_plane() {
    step "3/5" "무인 체인 실행면 (호스트 워커 + ngrok)"

    if $NO_WEBHOOK; then
        sub "--no-webhook → 생략"; record "워커" skip "--no-webhook"; record "ngrok" skip "--no-webhook"; return 0
    fi

    # 기동 로직은 doctor 가 권위(중복 구현 금지). 컨테이너 수신부 감지·컨테이너 PID 오탐 제외·
    # 예약 도메인 고정·Linear 등록 대조가 모두 그쪽에 있다.
    local doctor_args=()
    if $NO_NGROK; then
        doctor_args+=("--no-ngrok")
    elif pgrep -f "[n]grok http $WEBHOOK_PORT" >/dev/null 2>&1; then
        # doctor 는 기동 전 자체 ngrok 을 kill 하고 다시 띄운다 → 멀쩡한 터널에 순간 단절이
        # 생긴다. 이미 살아 있으면 터널을 건드리지 않도록 --no-ngrok 으로 넘긴다(멱등).
        doctor_args+=("--no-ngrok")
        sub "ngrok 이 이미 살아 있어 터널은 건드리지 않습니다(--no-ngrok 위임)"
    fi
    bash "$SCRIPT_DIR/webhook-doctor.sh" "${doctor_args[@]+"${doctor_args[@]}"}" 2>&1 | sed 's/^/    /' \
        || warn "webhook-doctor 일부 검증 실패 — 위 출력 확인"

    local wp; wp="$(worker_pids | head -1)"
    if [[ -n "$wp" ]]; then
        ok "호스트 워커 PID $wp"; record "워커" ok "PID $wp"
    else
        err "호스트 워커 미기동"; record "워커" fail "미기동"
    fi

    if $NO_NGROK; then
        record "ngrok" skip "--no-ngrok"
    elif pgrep -f "[n]grok http $WEBHOOK_PORT" >/dev/null 2>&1; then
        ok "ngrok 터널 생존"; record "ngrok" ok "터널 생존"
    else
        err "ngrok 미기동 — Linear 이벤트가 도달하지 못합니다(폴링 cron 만 남음)"
        record "ngrok" fail "미기동"
    fi
}

# ── 4. cron 대조 (보고만) ────────────────────────────────────────────────────

check_cron() {
    step "$1" "cron 정본 대조 (보고만 — 자동 등록하지 않음)"

    if ! command -v crontab >/dev/null 2>&1; then
        warn "crontab 없음 — 영구 자동 기동 미설정"; record "cron" warn "crontab 미설치"; return 0
    fi
    if [[ ! -f "$CRON_CANON" ]]; then
        warn "정본 없음: $CRON_CANON"; record "cron" warn "정본 파일 부재"; return 0
    fi

    local missing
    missing="$(comm -23 \
        <(grep -v '^#' "$CRON_CANON" | grep -v '^[[:space:]]*$' | sort) \
        <(crontab -l 2>/dev/null | grep -v '^#' | grep -v '^[[:space:]]*$' | sort))"

    if [[ -z "$missing" ]]; then
        ok "등록 crontab 이 정본을 전부 포함"
        record "cron" ok "정본 일치"
    else
        warn "정본에만 있는 줄 $(printf '%s\n' "$missing" | wc -l)개 — 미등록"
        printf '%s\n' "$missing" | head -3 | while IFS= read -r l; do sub "${l:0:100}"; done
        sub "등록: (crontab -l 2>/dev/null; cat scripts/clickeye_cron.txt) | crontab -"
        record "cron" warn "미등록 줄 존재"
    fi

    local cst; cst="$(systemctl is-active cron 2>/dev/null | trim1)"
    [[ "$cst" == "active" ]] && ok "cron.service active" || warn "cron.service 상태: ${cst:-unknown}"
}

# ── 5. 요약 ──────────────────────────────────────────────────────────────────

print_summary() {
    step "$1" "요약"
    local row name state note icon
    printf "    %s%s%s\n" "$C_DIM" "$(pad 요소 14)$(pad 상태 6)비고" "$C_NC"
    for row in "${SUMMARY[@]}"; do
        IFS='|' read -r name state note <<< "$row"
        case "$state" in
            ok)   icon="${C_GRN}✓${C_NC}" ;;
            fail) icon="${C_RED}✗${C_NC}" ;;
            warn) icon="${C_YEL}⚠${C_NC}" ;;
            *)    icon="${C_DIM}-${C_NC}" ;;
        esac
        printf "    %s%b     %s\n" "$(pad "$name" 14)" "$icon" "$note"
    done

    echo
    echo "  접속"
    echo "    웹        http://localhost:$WEB_PORT"
    echo "    API 문서  http://localhost:$API_PORT/docs"
    echo "    웹훅      http://localhost:$WEBHOOK_PORT/health"
    echo
    echo "  로그"
    echo "    tail -f logs/webhook-worker.log    # 큐 소비 → 파이프라인 디스패치"
    echo "    docker logs -f clickeye-webhook    # Linear 이벤트 수신·적재"
    echo "    tail -f $WEB_LOG"
    echo
    echo "  정지: bash scripts/fullstack_run.sh --stop"

    # 활성 절차의 선행 조건은 이 스크립트 범위 밖이지만, 무인 체인을 켜려면 필요하므로 알린다.
    if ! grep -qE '^CLICKEYE_SERVICE_KEY=.+' "$PROJECT_ROOT/.env" 2>/dev/null; then
        echo
        warn "CLICKEYE_SERVICE_KEY 미설정 — 다프로젝트 활성(run_guide 3-6 2단계)은 진행 불가 (CE-350)"
    fi
}

# ── 진단 모드 ────────────────────────────────────────────────────────────────

do_check() {
    step "1/5" "전제"
    check_prereq

    step "2/5" "컨테이너"
    local c label
    for c in clickeye-db clickeye-redis clickeye-api clickeye-webhook; do
        # api 는 호스트 경로(run_guide 1단계)가 정상 운영 형태이므로 컨테이너 부재를 실패로
        # 보지 않는다. 어느 경로로 서비스되는지는 아래 "api경로" 행이 말해준다.
        label="${c#clickeye-}"; [[ "$c" == "clickeye-api" ]] && label="api컨테이너"
        if container_up "$c"; then
            ok "$c — $(container_desc "$c")"
            record "$label" ok "$(container_desc "$c")"
        else
            warn "$c — $(container_desc "$c")"
            record "$label" warn "$(container_desc "$c")"
        fi
    done

    step "3/5" "호스트 프로세스 · 엔드포인트"
    local wp web p
    wp="$(worker_pids | head -1)"
    [[ -n "$wp" ]] && { ok "워커 PID $wp"; record "워커" ok "PID $wp"; } \
                   || { warn "워커 미기동"; record "워커" warn "미기동"; }
    if pgrep -f "[n]grok http $WEBHOOK_PORT" >/dev/null 2>&1; then
        ok "ngrok 생존"; record "ngrok" ok "생존"
    else
        warn "ngrok 미기동"; record "ngrok" warn "미기동"
    fi
    web="$(web_pids | filter_ours | head -1)"
    [[ -n "$web" ]] && { ok "웹 PID $web"; record "웹" ok "PID $web"; } \
                    || { warn "웹 미기동"; record "웹" warn "미기동"; }

    if api_serving; then
        p="$(port_pid "$API_PORT")"
        if [[ "$(container_state clickeye-api)" == "running" ]]; then
            ok "API 서비스 중 — 컨테이너 경로"; record "api경로" ok "컨테이너"
        else
            ok "API 서비스 중 — 호스트 경로 (PID ${p:-?})"; record "api경로" ok "호스트 PID ${p:-?}"
        fi
    else
        warn "API 미서비스"; record "api경로" warn "미서비스"
    fi

    sub "API      $API_HEALTH → $(http_code "$API_HEALTH")"
    sub "웹훅     http://localhost:$WEBHOOK_PORT/health → $(http_code "http://localhost:$WEBHOOK_PORT/health")"
    sub "웹       http://localhost:$WEB_PORT/ → $(http_code "http://localhost:$WEB_PORT/")"

    check_cron "4/5"
    print_summary "5/5"
}

# ── 정지 모드 ────────────────────────────────────────────────────────────────

do_stop() {
    # --no-web / --no-webhook 은 정지에도 적용된다(그 요소만 살려두고 나머지를 내릴 때).
    step "1/3" "호스트 프로세스 정지 (이 레포 소유만)"

    local pid killed=0
    if $NO_WEBHOOK; then
        sub "--no-webhook → 워커·ngrok 유지"
    else
        # doctor 의 --stop 은 webhook_server·ngrok 만 정리하고 워커는 남긴다 → 워커는 여기서 정지.
        bash "$SCRIPT_DIR/webhook-doctor.sh" --stop 2>&1 | sed 's/^/    /'
        while IFS= read -r pid; do
            [[ -z "$pid" ]] && continue
            ok "kill PID $pid (호스트 워커)"
            kill "$pid" 2>/dev/null && killed=$((killed+1))
        done < <(worker_pids | filter_ours)
        (( killed )) || sub "정지할 워커 없음"
    fi

    killed=0
    if $NO_WEB; then
        sub "--no-web → 웹 dev 서버 유지"
    else
        while IFS= read -r pid; do
            [[ -z "$pid" ]] && continue
            ok "kill PID $pid (웹 dev 서버)"
            kill "$pid" 2>/dev/null && killed=$((killed+1))
        done < <(web_pids | filter_ours)
        (( killed )) || sub "정지할 웹 서버 없음"
        rm -f "$WEB_PID_FILE"
    fi

    step "2/3" "컨테이너 정지 (ClickEye compose 프로젝트만)"
    warn "db 를 내립니다 — 다른 세션이 API/DB 를 쓰고 있으면 함께 끊깁니다"
    (cd "$COMPOSE_DIR" && docker compose --profile full stop db redis api webhook 2>&1 | sed 's/^/    /')

    step "3/3" "결과"
    local c
    for c in clickeye-db clickeye-redis clickeye-api clickeye-webhook; do
        sub "$c → $(container_state "$c")"
    done
    # pgrep -c 는 미매칭 시 "0" 을 출력하면서 exit 1 이므로 `|| echo 0` 을 붙이면 "0\n0" 이
    # 되어 출력에 빈 줄이 섞인다(실측). trim1 로 첫 토큰만 남긴다.
    sub "잔존 워커/웹/ngrok: $(worker_pids | wc -l)/$(web_pids | filter_ours | wc -l)/$(pgrep -cf "[n]grok http $WEBHOOK_PORT" 2>/dev/null | trim1)"
    echo
    log "정지 완료. 재기동: bash scripts/fullstack_run.sh"
    warn "호스트 uvicorn(run_guide 1단계로 직접 띄운 API)은 이 스크립트가 띄운 게 아니라 정지 대상이 아닙니다"
}

# ── 본체 ─────────────────────────────────────────────────────────────────────

printf "%s══════════════════════════════════════════════════%s\n" "$C_BLU" "$C_NC"
printf "  ClickEye 풀스택 런처 — 모드: %s\n" "$MODE"
printf "%s══════════════════════════════════════════════════%s\n" "$C_BLU" "$C_NC"

case "$MODE" in
    check) do_check; exit $FAILED ;;
    stop)  do_stop;  exit 0 ;;
esac

step "0/5" "전제 확인"
check_prereq
if (( $? == 2 )); then
    echo; err "전제 미충족 — 기동을 중단합니다"
    exit 2
fi

start_cloud
start_web
start_exec_plane
check_cron "4/5"
print_summary "5/5"

echo
if (( FAILED )); then
    log "부분 기동 — 위 요약의 ✗ 항목을 확인하세요"
else
    log "전 요소 정상 기동"
fi
exit $FAILED
