#!/usr/bin/env bash
# runner_dispatcher.sh — 워크스페이스별 전용 러너 스폰·감시·회수 디스패처 v1 (P5/CE-346).
#
# 매핑 원장(.ralph/workspaces.json)과 시트 원장(.ralph/seats.json)을 읽어, 시트가 배정된
# mapped 워크스페이스마다 전용 러너(auto_dev_pipeline.sh --once)를 자기 clone 안에서
# 백그라운드로 띄운다. CE-339(키별 락) · CE-345(시트 원장)가 만든 "병행 허용 조건" 위에서
# 실제 병행을 만들어내는 층이다.
#
#   틱마다: 죽은 러너 마커 회수 → 스폰 산정(시트·라이브니스·Queued·캡) → 스폰
#
# 산정 규칙(모두 통과해야 스폰):
#   ① 매핑 원장 status == "mapped"
#   ② 시트 원장에 workspace_key 배정이 있고 그 시트 status == "active"
#   ③ 그 키로 이미 실행 중인 러너가 없다(.ralph/dispatch/<key>.pid + kill -0 + cmdline = 멱등)
#   ③-b 그 **시트**를 쓰는 러너가 없다(파이프라인 .seat_lock 은 clone-로컬이라 clone 간
#       배타가 안 된다 — 시트 단위 배타는 이 층이 담당한다)
#   ④ (라이브 러너 + 이번 틱 스폰) < active 시트 총수 (캡)
#   ⑤ 해당 접두사의 Queued 이슈가 실제로 있다(linear_watcher --check-only, 파일 무기록)
#
# git 격리는 워크스페이스별 로컬 clone 이 담당한다(scripts/runner_clone.sh). 이 스크립트는
# PRIMARY 저장소의 git 상태를 **절대** 건드리지 않는다 — 인터랙티브 작업과 공존하기 위한
# 불변식이다. 파이프라인 본체(auto_dev_pipeline.sh)도 수정 없이 env 로만 조립된다.
#
# 사용법:
#   bash scripts/runner_dispatcher.sh          # cron: */5 9-18 * * 1-5
#
# env:
#   FLOWOPS_RUNNER_DISPATCH        — 이중 opt-in 마스터 토글(미설정=SKIP exit 0, 회귀 0)
#   FLOWOPS_RUNNER_DISPATCH_DRYRUN — 스폰 대상만 출력하고 clone·스폰을 하지 않는다
#   RUNNER_CLONE_ROOT              — clone 루트 (기본 $HOME/.clickeye-runners)
#   DISPATCH_STALE_HOURS           — 이 시간을 넘겨 살아있는 러너에 경고(기본 6, 강제 종료 없음)
#   WATCHER_BIN                    — Queued 사전확인 실행 파일 경로 오버라이드(테스트 주입용,
#                                    단일 경로만 — 인자 동봉 불가)
#   DISPATCH_PROC_MATCH            — 마커 PID 신원 확인 문자열(기본 auto_dev_pipeline)
#
# 로그: 이 스크립트는 stdout 에만 기록한다. `logs/dispatcher.log` 는 cron 리다이렉트가
#   만든다(스크립트가 같은 파일에 직접 쓰면 cron 실행 시 이중 기록이 된다).
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

source "$PROJECT_DIR/scripts/pipeline_config.sh" 2>/dev/null || true

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [dispatch] $*"; }

# ── ① 이중 opt-in 게이트 ────────────────────────────────────────────────────
# is_enabled 는 미설정 시 true 이므로 값 존재까지 함께 본다(미설정 = off = 회귀 0).
if ! { is_enabled "FLOWOPS_RUNNER_DISPATCH" 2>/dev/null && [ -n "${FLOWOPS_RUNNER_DISPATCH:-}" ]; }; then
  echo "[dispatch] SKIP: FLOWOPS_RUNNER_DISPATCH 미설정/비활성"
  exit 0
fi

DRYRUN=0
if is_enabled "FLOWOPS_RUNNER_DISPATCH_DRYRUN" 2>/dev/null && [ -n "${FLOWOPS_RUNNER_DISPATCH_DRYRUN:-}" ]; then
  DRYRUN=1
fi

# ── ② 틱 중첩 방지 ──────────────────────────────────────────────────────────
DISPATCH_DIR="$PROJECT_DIR/.ralph/dispatch"
mkdir -p "$DISPATCH_DIR"

if ! command -v flock >/dev/null 2>&1; then
  log "SKIP: flock 없음 — 틱 중첩을 막을 수 없어 디스패치하지 않는다(fail-closed)"
  exit 0
fi
exec 9>"$DISPATCH_DIR/.dispatch_lock"
if ! flock -n 9; then
  log "SKIP: 이전 틱이 아직 실행 중"
  exit 0
fi

WS_LEDGER="$PROJECT_DIR/.ralph/workspaces.json"
SEAT_LEDGER="$PROJECT_DIR/.ralph/seats.json"
CLONE_ROOT="${RUNNER_CLONE_ROOT:-$HOME/.clickeye-runners}"
STALE_HOURS="${DISPATCH_STALE_HOURS:-6}"
[[ "$STALE_HOURS" =~ ^[0-9]+$ ]] || STALE_HOURS=6
STALE_SEC=$((STALE_HOURS * 3600))

# Queued 사전확인 명령. 기본값은 배열 리터럴로 구성해 PROJECT_DIR 에 공백이 있어도 깨지지
# 않는다. WATCHER_BIN 오버라이드는 **단일 실행 파일 경로**로 취급한다(공백 포함 가능,
# 인자 동봉 불가) — 워드 분할을 하지 않기 위한 의도적 제약이다.
if [ -n "${WATCHER_BIN:-}" ]; then
  WATCHER_CMD=("$WATCHER_BIN")
else
  WATCHER_CMD=("python3" "$PROJECT_DIR/scripts/linear_watcher.py")
fi

# 마커 PID 신원 확인용 패턴 — /proc/<pid>/cmdline 에 이 문자열이 있어야 우리 러너로 인정한다.
PROC_MATCH="${DISPATCH_PROC_MATCH:-auto_dev_pipeline}"

# ── ③ 회수 — 죽은 러너 마커 정리 + 라이브니스 집계 ──────────────────────────
# 마커 형식: "<pid> <스폰 epoch> <seat_id>". 회수는 순수 정리 작업이므로 DRYRUN 에서도 한다.
LIVE_COUNT=0
LIVE_KEYS=" "
LIVE_SEATS=" "
REAPED=0
NOW="$(date +%s)"

# PID 재사용 판정: kill -0 만으로는 "그 PID 가 **우리 러너**인지" 를 알 수 없다(마커가 오래
# 남은 사이 OS 가 PID 를 재사용하면 남의 프로세스를 러너로 오인해 영구 스킵된다).
# /proc 를 읽을 수 있으면 cmdline 으로 신원을 확인하고, 못 읽으면 판단을 보류(=생존 인정)한다
# — 확인 불가를 회수 근거로 삼지 않는다.
is_our_runner() {  # is_our_runner <pid>
  local pid="$1" cmdline="/proc/$1/cmdline"
  [ -r "$cmdline" ] || return 0          # /proc 없음(비리눅스 등) → 보류
  tr '\0' ' ' < "$cmdline" 2>/dev/null | grep -qF "$PROC_MATCH"
}

shopt -s nullglob
for marker in "$DISPATCH_DIR"/*.pid; do
  m_key="$(basename "$marker" .pid)"
  m_pid=""; m_start=""; m_seat=""
  read -r m_pid m_start m_seat < "$marker" 2>/dev/null || true
  if [ -n "$m_pid" ] && kill -0 "$m_pid" 2>/dev/null && is_our_runner "$m_pid"; then
    LIVE_COUNT=$((LIVE_COUNT + 1))
    LIVE_KEYS="${LIVE_KEYS}${m_key} "
    # 구 형식 마커(seat_id 없음)도 읽히므로 빈 값을 그냥 넘긴다.
    if [ -n "$m_seat" ]; then LIVE_SEATS="${LIVE_SEATS}${m_seat} "; fi
    if [[ "$m_start" =~ ^[0-9]+$ ]] && [ $((NOW - m_start)) -gt "$STALE_SEC" ]; then
      log "WARN: 장기 실행 러너 — key=$m_key pid=$m_pid 경과=$(( (NOW - m_start) / 3600 ))h (강제 종료하지 않음)"
    fi
  elif [ -n "$m_pid" ] && kill -0 "$m_pid" 2>/dev/null; then
    rm -f "$marker"
    REAPED=$((REAPED + 1))
    log "회수: PID 재사용 감지(러너 아님) — key=$m_key pid=$m_pid"
  else
    rm -f "$marker"
    REAPED=$((REAPED + 1))
    log "회수: 종료된 러너 마커 정리 — key=$m_key pid=${m_pid:-?}"
  fi
done
shopt -u nullglob

# ── ④ 후보 산정 — 두 원장을 합쳐 TSV 로 뽑는다(stdlib python, 네트워크 없음) ─
# 출력: 첫 줄 "#SEATS<TAB><active 시트 수>",
#       이후 "<key><TAB><ticket_prefix><TAB><state><TAB><seat_id>"
#       state ∈ ok | no_seat | seat_inactive
#       진단 행: #BADKEY(키 문자 위반) · #BADPREFIX(접두사에 탭/개행) · #DUPKEY(키 중복)
LEDGER_TSV="$(python3 - "$WS_LEDGER" "$SEAT_LEDGER" <<'PY'
import json
import re
import sys


def load(path):
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


ws = load(sys.argv[1])
seats = load(sys.argv[2])
seat_meta = seats.get("seats") or {}
assignments = seats.get("assignments") or {}

active = sum(
    1 for s in seat_meta.values() if isinstance(s, dict) and s.get("status") == "active"
)
print(f"#SEATS\t{active}")

# 키는 파일 경로(.ralph/dispatch/<key>.pid)와 clone 경로로 합성되므로 문자를 제한한다.
key_re = re.compile(r"^[A-Za-z0-9_.-]+$")
seen = set()
for prefix, meta in sorted((ws.get("workspaces") or {}).items()):
    if not isinstance(meta, dict) or meta.get("status") != "mapped":
        continue
    key = str(meta.get("workspace_key") or "")
    if not key_re.match(key):
        print(f"#BADKEY\t{key}")
        continue
    # 접두사는 TSV 필드로 실려 나가므로 구분자를 품으면 필드가 어긋난다 — 스킵하고 알린다.
    if "\t" in prefix or "\n" in prefix or "\r" in prefix:
        print(f"#BADPREFIX\t{key}")
        continue
    if key in seen:
        # 같은 키에 접두사가 둘 이상이면 첫 항목만 러너를 갖는다. 조용히 버리면 탈락한
        # 접두사의 티켓이 영원히 수거되지 않으므로 진단 행으로 남긴다.
        print(f"#DUPKEY\t{key}")
        continue
    seen.add(key)
    seat_id = assignments.get(key)
    if not seat_id:
        state = "no_seat"
    elif (seat_meta.get(seat_id) or {}).get("status") != "active":
        state = "seat_inactive"
    else:
        state = "ok"
    print(f"{key}\t{prefix}\t{state}\t{seat_id or ''}")
PY
)" || LEDGER_TSV=""

ACTIVE_SEATS="$(sed -n 's/^#SEATS\t//p' <<< "$LEDGER_TSV" | head -n1)"
[[ "$ACTIVE_SEATS" =~ ^[0-9]+$ ]] || ACTIVE_SEATS=0

CANDIDATES=0
SPAWNED=0
SKIPPED=0

# 딜리버리 팀 ID(SI-Project) — 디스패처가 스폰하는 러너는 **항상 딜리버리**다(워크스페이스
# 모드 전용). 인테이크가 만든 티켓을 SIP 팀으로 발급/조회하도록 러너에 LINEAR_TEAM_ID 로
# 주입한다. 자체 개발 파이프라인은 디스패처를 거치지 않으므로 CE 팀(.env LINEAR_TEAM_ID)을
# 그대로 쓴다. .env 에 값이 없으면 주입하지 않는다(기존 동작 유지 = 회귀 0).
DELIVERY_TEAM_ID=""
if [ -f "$PROJECT_DIR/.env" ]; then
  DELIVERY_TEAM_ID="$(grep -E '^LINEAR_TEAM_ID_DELIVERY=' "$PROJECT_DIR/.env" 2>/dev/null | head -n1 | cut -d= -f2- | tr -d '[:space:]')" || DELIVERY_TEAM_ID=""
fi

# ── ⑤ 스폰 루프 ─────────────────────────────────────────────────────────────
while IFS=$'\t' read -r c_key c_prefix c_state c_seat; do
  [ -n "$c_key" ] || continue
  case "$c_key" in
    '#SEATS') continue ;;
    '#BADKEY')
      log "WARN: 허용되지 않는 workspace_key — 원장 항목 무시"
      continue
      ;;
    '#BADPREFIX')
      log "WARN: ticket_prefix 에 탭/개행이 있어 원장 항목 무시 — key=$c_prefix"
      continue
      ;;
    '#DUPKEY')
      log "WARN: workspace_key 중복 — 뒤 접두사 항목은 러너를 갖지 못한다(key=$c_prefix)"
      continue
      ;;
  esac
  CANDIDATES=$((CANDIDATES + 1))

  # ②-a 시트 배정/상태
  if [ "$c_state" = "no_seat" ]; then
    log "스킵: $c_key — 시트 미배정(seat_map.py assign 필요)"
    SKIPPED=$((SKIPPED + 1)); continue
  fi
  if [ "$c_state" = "seat_inactive" ]; then
    log "스킵: $c_key — 배정 시트가 active 아님"
    SKIPPED=$((SKIPPED + 1)); continue
  fi

  # ③ 라이브니스(멱등) — 이미 그 키로 러너가 돌고 있으면 다음 틱에 맡긴다
  if [[ "$LIVE_KEYS" == *" $c_key "* ]]; then
    log "스킵: $c_key — 러너 실행 중(멱등)"
    SKIPPED=$((SKIPPED + 1)); continue
  fi

  # ③-b 시트 배타 — 같은 시트를 쓰는 러너가 이미 살아 있으면 스폰하지 않는다.
  # 파이프라인의 `.seat_lock` 은 clone-로컬이라 clone 간 상호배제가 되지 않는다(실측).
  # 시트 단위 배타는 이 층(마커의 seat_id)과 seat_map 의 1:1 assign 가드가 함께 담당한다.
  if [ -n "$c_seat" ] && [[ "$LIVE_SEATS" == *" $c_seat "* ]]; then
    log "스킵: $c_key — 시트 $c_seat 를 쓰는 러너가 이미 실행 중(계정 중복 실행 방지)"
    SKIPPED=$((SKIPPED + 1)); continue
  fi

  # ④ 캡 — 동시 러너는 active 시트 수를 넘지 않는다(1시트:1러너).
  # Queued 사전확인(Linear API)보다 **앞에** 둔다 — 어차피 스폰 못 할 후보에 API 비용을
  # 치르지 않기 위해서다.
  if [ $((LIVE_COUNT + SPAWNED)) -ge "$ACTIVE_SEATS" ]; then
    log "스킵: $c_key — 시트 캡 도달(라이브 $LIVE_COUNT + 스폰 $SPAWNED / active $ACTIVE_SEATS)"
    SKIPPED=$((SKIPPED + 1)); continue
  fi

  # ⑤ Queued 사전확인 — 파일을 쓰지 않는 --check-only. 디스패처는 비차단이므로
  #    watcher 자체 오류(0/2 외 종료)는 경고 후 스킵한다.
  wrc=0
  "${WATCHER_CMD[@]}" --check-only --title-prefix "$c_prefix" >/dev/null 2>&1 || wrc=$?
  if [ "$wrc" -eq 2 ]; then
    log "스킵: $c_key — Queued 이슈 없음"
    SKIPPED=$((SKIPPED + 1)); continue
  elif [ "$wrc" -ne 0 ]; then
    log "WARN: $c_key — Queued 사전확인 실패(exit $wrc) → 이번 틱 스킵"
    SKIPPED=$((SKIPPED + 1)); continue
  fi

  if [ "$DRYRUN" = "1" ]; then
    log "[DRYRUN] 스폰 대상: $c_key (prefix=$c_prefix seat=$c_seat)"
    SPAWNED=$((SPAWNED + 1))
    if [ -n "$c_seat" ]; then LIVE_SEATS="${LIVE_SEATS}${c_seat} "; fi
    continue
  fi

  # ⑥ 스폰 — clone 프로비저닝 후 clone 안에서 파이프라인 1회 실행
  if ! bash "$PROJECT_DIR/scripts/runner_clone.sh" "$c_key" >/dev/null 2>&1; then
    log "WARN: $c_key — clone 프로비저닝 실패 → 스폰 보류"
    SKIPPED=$((SKIPPED + 1)); continue
  fi
  CLONE_DIR="$CLONE_ROOT/$c_key"
  RUNNER_LOG="$PROJECT_DIR/logs/runner_${c_key}_$(date +%Y%m%d_%H%M%S).log"
  mkdir -p "$PROJECT_DIR/logs"

  # fd 9(틱 락)는 자식에게 넘기지 않는다 — 넘기면 러너가 사는 동안 다음 틱이 전부
  # "이전 틱 실행 중"으로 오판돼 디스패치가 멈춘다.
  # `exec` 로 서브셸을 파이프라인으로 **치환**한다: 기록되는 PID 의 /proc cmdline 이 실제
  # 파이프라인이 되어 마커 신원 확인(is_our_runner)이 성립하고, 중간 셸도 하나 줄어든다.
  # FLOWOPS_ENV_KEEP_EXISTING: 공유 .env 가 아래 세 토글을 덮어쓰지 못하게 한다(권위 확보).
  # 딜리버리 팀 주입 — 값이 있을 때만. 파이프라인은 `[ -z LINEAR_TEAM_ID ]` 가드라 env 가 이긴다.
  team_env=()
  [ -n "$DELIVERY_TEAM_ID" ] && team_env=(LINEAR_TEAM_ID="$DELIVERY_TEAM_ID")
  ( cd "$CLONE_DIR" && exec env WORKSPACE_KEY="$c_key" WATCHER_TITLE_PREFIX="$c_prefix" \
      FLOWOPS_WORKSPACE=true FLOWOPS_SEAT_POOL=true FLOWOPS_SEAT_POOL_STRICT=true \
      FLOWOPS_ENV_KEEP_EXISTING=true \
      "${team_env[@]}" \
      bash scripts/auto_dev_pipeline.sh --once ) >> "$RUNNER_LOG" 2>&1 < /dev/null 9>&- &
  spawn_pid=$!
  printf '%s %s %s\n' "$spawn_pid" "$(date +%s)" "$c_seat" > "$DISPATCH_DIR/$c_key.pid"
  SPAWNED=$((SPAWNED + 1))
  if [ -n "$c_seat" ]; then LIVE_SEATS="${LIVE_SEATS}${c_seat} "; fi
  log "스폰: $c_key pid=$spawn_pid seat=$c_seat clone=$CLONE_DIR log=$RUNNER_LOG"
done <<< "$LEDGER_TSV"

log "틱 요약: 후보=$CANDIDATES 스폰=$SPAWNED 스킵=$SKIPPED 회수=$REAPED 라이브=$LIVE_COUNT active시트=$ACTIVE_SEATS$([ "$DRYRUN" = "1" ] && echo " (DRYRUN)" || true)"
exit 0
