#!/usr/bin/env bash
# 자동 기능 개발 파이프라인 (v6 — 멀티 Agent 순차 실행)
#
# 워크플로우:
#   1. Linear Queued 이슈 1개 감지 → fix_plan 생성
#   2. [Claude] 메타프롬프트 정제(관측형 사전 정제, 기획+정제 일체) → PLAN.md 생성
#      (FLOWOPS_METAPROMPT=false 시 레거시 Gemini 기획으로 폴백)
#   3. 브랜치 생성 → [Claude] 구현(정제 스펙 prepend) → TASK.md 생성
#   4. [Codex] QA 리뷰 → REVIEW.md 생성
#   5. Linear 결과 보고 + PR 생성
#   6. 다음 Queued 이슈로 반복
#
# 사용법:
#   bash scripts/auto_dev_pipeline.sh
#   bash scripts/auto_dev_pipeline.sh --max-turns 5        # 시연용 (짧은 루프)
#   bash scripts/auto_dev_pipeline.sh --max-iterations 50
#   bash scripts/auto_dev_pipeline.sh --once                # 1개만 처리 후 종료
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# 모듈 토글 로드
source "$PROJECT_DIR/scripts/pipeline_config.sh" 2>/dev/null || true

# LINEAR_TEAM_ID 로드 — pipeline_config 는 FLOWOPS_* 만 export 하므로 여기서 보강.
# 거버넌스 evaluate 페이로드·LLM 머신 인제스트(P1.6)의 team→project 역매핑에 사용. 없으면 빈 값.
if [ -z "${LINEAR_TEAM_ID:-}" ] && [ -f "$PROJECT_DIR/.env" ]; then
  LINEAR_TEAM_ID="$(grep -E '^LINEAR_TEAM_ID=' "$PROJECT_DIR/.env" 2>/dev/null | head -n1 | cut -d= -f2- | tr -d '[:space:]')" || LINEAR_TEAM_ID=""
fi

LOCK_FILE=".ralph/.pipeline_lock"
TASK_MAPPING=".ralph/.task_mapping.json"

# ── [CE-367] 모델 티어 고정 — **별칭 금지, 정식 모델명만** ────────────────────
# 실측(2026-08-04, CLI 2.1.221): `--model sonnet` 별칭이 `claude-opus-4-8` 로 해석됐다.
# 별칭은 `--help` 가 "alias for the **latest** model" 이라 설명하는데 그 해석이 어긋난 것이며,
# 정식 모델명(`claude-sonnet-5`)은 정확히 해석된다. 다음 수단은 전부 별칭을 못 이겼다:
# ANTHROPIC_MODEL env · --settings(JSON/파일) · 프로젝트 .claude/settings.json ·
# CLAUDE_CONFIG_DIR 격리 · 전역 model 핀 제거(→ 전역 설정은 원인이 아니었다).
# 영향: 구현 1건이 의도(sonnet) 대비 캐시 읽기 2.5배·환산액 2.5배로 실행됐다(CE-366 vs CE-355).
# 모델 교체 시 갱신 지점을 한 곳으로 모으고 env 오버라이드를 허용한다. 티어 배정의 SSOT 는
# .claude/MODEL-ROUTING.md 다.
PIPELINE_MODEL_REFINE="${PIPELINE_MODEL_REFINE:-claude-sonnet-5}"
PIPELINE_MODEL_IMPL="${PIPELINE_MODEL_IMPL:-claude-sonnet-5}"

# ── [파생형 하네스] 워크스페이스 락 분리 + automap 초기 상태 (CE-339) ──
# 프로세스 시작 시점의 WORKSPACE_KEY(전용 러너가 env 로 지정)를 보존한다. automap 은
# 이 값이 비어 있을 때만(= self-repo/단일 러너) 이슈별로 WORKSPACE_KEY 를 채운다.
WORKSPACE_KEY_INITIAL="${WORKSPACE_KEY:-}"
# 락 분리: 전용 워크스페이스 러너(워크스페이스 모드 + WORKSPACE_KEY 명시)는 키별 락으로
# 서로 다른 워크스페이스의 병행 기동을 허용한다(동시 실행 1단계). self-repo/automap 단일
# 러너(키 미설정)는 기존 전역 락 파일명을 그대로 유지 = 무회귀.
if is_enabled "FLOWOPS_WORKSPACE" 2>/dev/null && [ -n "${FLOWOPS_WORKSPACE:-}" ] \
  && [ -n "$WORKSPACE_KEY_INITIAL" ]; then
  LOCK_FILE=".ralph/.pipeline_lock.${WORKSPACE_KEY_INITIAL}"
fi

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

# ── [파생형 하네스] 구현 대상 워크디렉터리 해석 (STEP A 도메인 프로파일 · STEP B cwd 공유) ──
# FLOWOPS_WORKSPACE 명시 활성 + WORKSPACE_KEY 설정 + workspaces/<key> 존재 시에만
# 해당 워크스페이스("남의 프로젝트")를, 그 외에는 self-repo($PROJECT_DIR)를 echo 한다.
# 순수 함수(로그·부작용 없음) — 호출부가 결과로 분기한다. 미설정=off → self-repo(회귀 0).
resolve_impl_workdir() {
  if is_enabled "FLOWOPS_WORKSPACE" 2>/dev/null && [ -n "${FLOWOPS_WORKSPACE:-}" ] \
    && [ -n "${WORKSPACE_KEY:-}" ] && [ -d "$PROJECT_DIR/workspaces/$WORKSPACE_KEY" ]; then
    # [CE-384] 물리 경로로 해석해 echo — 러너 clone 의 workspaces 심링크를 논리 경로($PWD)로
    # 통과시키면 집행면 게이트의 문자열 경계 판정(containment)이 claude 세션 cwd(물리)와
    # 어긋나 자기 워크스페이스 안의 cd 를 G-02 로 오탐한다(SIP-1 실측). 발원지에서 형태를
    # 통일하면 이후 cd·$PWD·CLAUDE_PROJECT_DIR·게이트 cwd 가 전부 같은 물리 경로가 된다.
    readlink -f "$PROJECT_DIR/workspaces/$WORKSPACE_KEY" 2>/dev/null \
      || printf '%s\n' "$PROJECT_DIR/workspaces/$WORKSPACE_KEY"
  else
    printf '%s\n' "$PROJECT_DIR"
  fi
}

# ── [고객 레포 딜리버리] IMPL_WORKDIR 대상 git 실행 (CE-347) ──
# 워크스페이스 모드에서 브랜치 생성·diff·push 대상을 고객 clone 으로 돌리는 유일한 통로.
# 자기레포 경로는 이 함수를 쓰지 않는다(safe_git 그대로 = 회귀 0). IMPL_WORKDIR 은
# 이터레이션 시작부에서 1회 해석·캐시된 값을 참조한다.
impl_git() {
  git -C "$IMPL_WORKDIR" "$@"
}

# ── [고객 레포 딜리버리] ClickEye 주입물 clone-로컬 제외 (CE-347 리뷰 G2/G6) ──
# workspace_provision.sh 가 고객 clone 에 심는 산출물(.claude/ · CLAUDE.md · 기본브랜치 메모)은
# 고객 레포 입장에서 untracked 다. 제외하지 않으면 ① 더러운 트리 판정이 항상 참이 되어 G2 의
# stash 가 하네스 프래그먼트를 걷어가고 ② 에이전트의 `git add -A` 가 이들을 고객 브랜치에
# 커밋한다(오염). 멱등이며 고객 레포의 추적 파일에는 영향이 없다(exclude 는 untracked 만 대상).
# 이 티켓 이전에 조달된 워크스페이스도 이 호출로 자기치유된다.
# 목록은 workspace_provision.sh 의 동일 목록과 짝을 이룬다 — 한쪽만 바꾸지 말 것.
ws_exclude_harness_artifacts() {
  local ex="$IMPL_WORKDIR/.git/info/exclude" p
  [ -d "$IMPL_WORKDIR/.git" ] || return 0
  mkdir -p "$IMPL_WORKDIR/.git/info" 2>/dev/null || return 0
  for p in '.clickeye_default_branch' '.claude/' 'CLAUDE.md' '.harness/'; do
    grep -qxF -- "$p" "$ex" 2>/dev/null || printf '%s\n' "$p" >> "$ex" 2>/dev/null || true
  done
}

# ── [CE-356] 구현 프롬프트 조립 (self-repo / 워크스페이스 분기) ──
# 순수 함수: 인자만 읽고 조립 결과를 stdout 으로 낸다(부작용·로그 없음 → 테스트 가능).
#
# 왜 분기가 필요한가(실측 2026-08-04, CE-355):
#   `.ralph/PROMPT.md` 는 `.ralph/PLAN.md`·`.ralph/fix_plan.md` 를 **상대경로**로 읽으라
#   지시하고 ClickEye 5개 레포 구조·`LoadMap_v3.md` 동기화를 전제한다. 구현 콜은
#   `cd "$IMPL_WORKDIR"`(고객 clone)에서 실행되므로 그 입력이 사라지고, 에이전트는
#   "계획 파일도 없고 기대한 레포 구조도 없다" 며 BLOCKED 로 끝냈다 → 커밋 0 → 딜리버리 실패.
#   따라서 워크스페이스 모드에서는 **계획을 프롬프트에 인라인**하고 self-repo 전제가 없는
#   전용 프롬프트(templates/harness-core/PROMPT.workspace.md)를 쓴다.
#
# self-repo 경로의 출력은 이전과 동일하다(회귀 0 — 테스트로 고정).
build_impl_prompt() {
  local workdir="$1" refined="$2" issue_key="$3" title="$4"
  local ws_prompt="$PROJECT_DIR/templates/harness-core/PROMPT.workspace.md"

  # ① self-repo — 기존 동작 그대로.
  if [ "$workdir" = "$PROJECT_DIR" ] || [ ! -f "$ws_prompt" ]; then
    if [ -s "$refined" ]; then
      printf '%s\n%s\n\n---\n\n%s\n' \
        "## 정제된 구현 스펙 (메타프롬프팅 결과 — 우선 참고)" \
        "$(cat "$refined")" "$(cat "$PROJECT_DIR/.ralph/PROMPT.md")"
    else
      cat "$PROJECT_DIR/.ralph/PROMPT.md"
    fi
    return 0
  fi

  # ② 워크스페이스 — 스펙을 인라인한다. 출처 우선순위: 정제 스펙 > PLAN.md > 제목만.
  #    PLAN.md 는 정제 실패 시 fix_plan 폴백본이 복사돼 있다(STEP A).
  local spec=""
  if [ -s "$refined" ]; then
    spec="$(cat "$refined")"
  elif [ -s "$PROJECT_DIR/.ralph/PLAN.md" ]; then
    spec="$(cat "$PROJECT_DIR/.ralph/PLAN.md")"
  fi
  if [ -z "$spec" ]; then
    # 빈 스펙으로 남의 저장소를 건드리게 하지 않는다 — 에이전트가 BLOCKED 로 끝내도록 명시.
    spec="(구현 스펙을 확보하지 못했다. 무엇을 만들어야 하는지 판단할 수 없으면 구현하지 말고
BLOCKED 로 보고하라.)"
  fi

  printf '%s\n\n- 티켓: %s\n- 제목: %s\n\n%s\n\n---\n\n%s\n' \
    "# 구현 스펙 (이번 작업의 전부 — 파일을 찾지 말고 이 내용을 따르라)" \
    "$issue_key" "$title" "$spec" "$(cat "$ws_prompt")"
}

# ── [고객 레포 딜리버리] 실패 공통 처리 (CE-347) ──
# 워크스페이스 딜리버리 경로의 실패는 전부 동일하게 처리한다: 로그 → 기존 실패 처리
# (재시도 복귀 또는 Backlog) → 실패 카운트. 호출부는 이 함수 뒤에 continue 한다.
# 고객 레포의 로컬 브랜치는 어떤 실패에서도 삭제하지 않는다(구현 결과 유실 0).
ws_delivery_fail() {
  local reason="$1"
  log "ERROR: 워크스페이스 딜리버리 실패 — ${reason} (${ISSUE_KEY})"
  if ! handle_task_failure "$ISSUE_KEY" "$ISSUE_ID" "$TASK_MODE" "워크스페이스 딜리버리: ${reason}"; then
    python3 scripts/linear_tracker.py update --issue-id "$ISSUE_ID" --status "Backlog" 2>/dev/null || true
    log "Linear 상태: Backlog (워크스페이스 딜리버리 실패)"
  fi
  FAILED=$((FAILED + 1))
}

# ── [시트 풀] 워크스페이스 배정 시트를 CLI 인증에 주입 (CE-345, opt-in — 미설정=off) ──
# 해석된 WORKSPACE_KEY 의 배정 시트(.ralph/seats.json)를 이 프로세스의 CLI 인증으로 주입한다.
# off/미배정/pending_login/disabled/상위 주입 존재 → 아무 것도 하지 않는다(현행 세션 = 폴백).
# 반드시 **서브셸 내부**에서 호출한다 — export 가 서브셸 로컬이라 이터레이션 간 누출이 없다.
# 반환 3 = STRICT 스킵 신호(호출부가 exit 97 로 변환).
apply_seat_env() {
  is_enabled "FLOWOPS_SEAT_POOL" 2>/dev/null && [ -n "${FLOWOPS_SEAT_POOL:-}" ] || return 0
  # with_seat.sh/project_runner 가 이미 시트를 주입했으면 존중(이중 시트 금지)
  if [ -n "${CLAUDE_CODE_OAUTH_TOKEN:-}" ] || [ -n "${CLICKEYE_SEAT_ID:-}" ]; then return 0; fi
  local key="${WORKSPACE_KEY:-}" desc
  desc="$(python3 "$PROJECT_DIR/scripts/seat_map.py" resolve \
           --resolve-key "$key" --output "$PROJECT_DIR/.ralph/seats.json" 2>/dev/null || true)"
  if [ -z "$desc" ]; then
    log "WARN: 시트 미배정 워크스페이스 '${key:-self}' — 기본 로그인 세션 폴백(운영 계정 사용 위험)"
    if [ "${FLOWOPS_SEAT_POOL_STRICT:-}" = "true" ]; then return 3; fi
    return 0
  fi
  eval "$desc"   # SEAT_ID / SEAT_TOKEN_FILE / SEAT_CONFIG_DIR 또는 SEAT_BLOCKED (경로만, 비밀 미포함)

  # 운영자가 한도도달·차단으로 내린 시트(disabled)는 STRICT 무관 차단 — 그 워크스페이스를
  # 기본 계정으로 돌리는 것은 원장 오귀속이므로 폴백보다 미실행이 옳다.
  if [ -n "${SEAT_BLOCKED:-}" ]; then
    log "WARN: 워크스페이스 '${key:-self}' 배정 시트가 ${SEAT_BLOCKED} 상태 — 단계 미실행(기본 계정 폴백 금지)"
    return 3
  fi

  # 자문(advisory) 시트 락: 다른 살아있는 러너가 같은 시트 점유 시 경고(STRICT 시 스킵).
  # PID 파일 기반이라 TOCTOU·PID 재사용을 막지 못한다 — v1 은 경고/스킵 수준의 advisory 이며
  # 엄밀한 상호배제는 시트별 원장 락(서버 경로)과 함께 온다.
  local seat_lock="$PROJECT_DIR/.ralph/.seat_lock.${SEAT_ID}" holder
  holder="$(cat "$seat_lock" 2>/dev/null || true)"
  if [ -n "$holder" ] && [ "$holder" != "$$" ] && kill -0 "$holder" 2>/dev/null; then
    log "WARN: 시트 '${SEAT_ID}' 를 다른 러너(PID ${holder})가 점유 중"
    if [ "${FLOWOPS_SEAT_POOL_STRICT:-}" = "true" ]; then return 3; fi
  fi

  # 인증 적재 — **성공한 경우에만** 시트를 표방한다. 토큰이 안 읽히거나 비었는데
  # CLICKEYE_SEAT_ID 만 붙이면 기본 계정으로 돌면서 원장엔 그 시트로 기록된다(오귀속).
  local injected="" seat_token=""
  if [ -n "${SEAT_TOKEN_FILE:-}" ] && [ -r "$SEAT_TOKEN_FILE" ]; then
    # 파일→env 만 경유(인자·로그 미기록). CRLF 저장분은 그대로 쓰면 인증이 깨지므로 제거.
    seat_token="$(tr -d '\r' < "$SEAT_TOKEN_FILE" 2>/dev/null || true)"
    if [ -n "$seat_token" ]; then
      export CLAUDE_CODE_OAUTH_TOKEN="$seat_token"
      injected="token"
    fi
    unset seat_token
  fi
  if [ -z "$injected" ] && [ -n "${SEAT_CONFIG_DIR:-}" ] && [ -d "$SEAT_CONFIG_DIR" ]; then
    export CLAUDE_CONFIG_DIR="$SEAT_CONFIG_DIR"
    injected="config_dir"
  fi
  if [ -z "$injected" ]; then
    unset SEAT_ID SEAT_TOKEN_FILE SEAT_CONFIG_DIR   # 시트 참칭 금지 — 미배정과 동일 취급
    log "WARN: 시트 인증 적재 실패(파일 미판독/빈 토큰) — 기본 로그인 세션 폴백(운영 계정 사용 위험)"
    if [ "${FLOWOPS_SEAT_POOL_STRICT:-}" = "true" ]; then return 3; fi
    return 0
  fi

  export CLICKEYE_SEAT_ID="$SEAT_ID"
  unset ANTHROPIC_API_KEY   # 인증 우선순위상 API 키가 시트 토큰을 이긴다(with_seat.sh 와 동일 불변식)
  echo "$$" > "$seat_lock" 2>/dev/null || true
  log "시트 주입: seat=${SEAT_ID} workspace=${key:-self} (${injected})"
  return 0
}

# ── [시트 풀] STRICT 스킵 라우팅 (CE-345) ──
# 시트를 확보하지 못해 단계를 **실행하지 않았을** 때, 빈 브랜치가 거버넌스·AUTO_MERGE 를 지나
# "완료"로 소진되는 것을 막고 기존 실패 처리 경로(재시도 복귀 / Backlog)로 되돌린다.
# 호출부는 이 함수 호출 뒤 continue 로 다음 이슈로 넘어간다.
seat_strict_skip() {
  local stage="$1"
  log "WARN: 시트 STRICT 스킵 — ${stage} 미실행 (${ISSUE_KEY})"
  safe_git checkout main 2>/dev/null || true
  if ! handle_task_failure "$ISSUE_KEY" "$ISSUE_ID" "$TASK_MODE" "시트 미확보로 ${stage} 미실행"; then
    python3 scripts/linear_tracker.py update --issue-id "$ISSUE_ID" --status "Backlog" 2>/dev/null || true
    log "Linear 상태: Backlog (시트 STRICT 스킵)"
  fi
  FAILED=$((FAILED + 1))
}

# ── [파생형 하네스 Tier 3a] 파이프라인 메트릭 기록 (opt-in — 미설정=off, 비차단) ──
# FLOWOPS_METRICS 이중 opt-in 시에만 단계 이벤트를 JSONL 원장에 append 한다. off 면
# no-op(python3 호출조차 안 함). 관측은 파이프라인을 절대 죽이지 않는다(|| true).
# 인자: <run_id> <event> <data_json>. 이 원장이 3b prompt-evolve 채점 입력이 된다.
record_metric() {
  is_enabled "FLOWOPS_METRICS" 2>/dev/null && [ -n "${FLOWOPS_METRICS:-}" ] || return 0
  # 상관 축(CE-363)을 함께 넘긴다 — 서버 원장이 티켓/프로젝트/워크스페이스로 묶을 수 있게.
  # 값이 없으면 pipeline_metrics.py 가 서버 전송을 생략한다(jsonl 기록은 항상 유지).
  python3 "$PROJECT_DIR/scripts/pipeline_metrics.py" \
    --run-id "$1" --event "$2" --data "$3" \
    --issue-key "${ISSUE_KEY:-}" \
    --workspace-key "${WORKSPACE_KEY:-}" \
    --project-id "${ITER_PROJECT_ID:-}" || true
}

# ── Git lock guard ──
# index.lock 대기 후 실행. 최대 15초 대기, 초과 시 stale lock 제거.
wait_for_git_lock() {
  local lock_file
  lock_file="$(git rev-parse --git-dir 2>/dev/null)/index.lock"
  local max_wait=15
  local waited=0

  while [ -f "$lock_file" ] && [ "$waited" -lt "$max_wait" ]; do
    sleep 1
    waited=$((waited + 1))
  done

  if [ -f "$lock_file" ]; then
    log "WARN: git index.lock이 ${max_wait}초 후에도 존재. stale lock 제거."
    rm -f "$lock_file"
  fi
}

safe_git() {
  wait_for_git_lock
  git "$@"
}

# ── [P1 완주 오케스트레이터] 실패 무유실 (docs/multiproject-delivery.md §6-1, D-13) ──
# FLOWOPS_COMPLETION 은 opt-in(미설정=off) — 거버넌스 트리아지와 동일 관례. off 면
# handle_task_failure 가 1을 반환해 기존 Backlog 경로가 그대로 수행된다(회귀 0).
FAILED_THIS_RUN=""   # 이번 런에서 실패한 키 목록(공백 구분) — 즉시 재수거 무한루프 방지

is_completion_enabled() {
  case "${FLOWOPS_COMPLETION:-}" in
    1|true|on|yes) return 0 ;;
    *) return 1 ;;
  esac
}

# 실패 처리. 반환 0 = 처리됨(토글 on: 재시도 복귀 또는 터미널 — 호출자는 기존 Backlog 경로를
# 건너뜀) / 1 = 미처리(토글 off — 호출자가 기존 Backlog 경로 수행).
handle_task_failure() {
  local issue_key="$1" issue_id="$2" task_mode="$3" reason="$4"
  is_completion_enabled || return 1
  FAILED_THIS_RUN="${FAILED_THIS_RUN} ${issue_key}"
  # record-failure 출력을 캡처(재시도 N/한도 문자열 포함) — 터미널 시 하위 태스크 본문에 재사용.
  # set -e 하에서 비정상 종료가 스크립트를 죽이지 않게 rc 를 분리 캡처한다.
  local rl_out rl_rc=0
  rl_out="$(python3 scripts/retry_ledger.py record-failure --issue "$issue_key" --reason "$reason" 2>&1)" || rl_rc=$?
  echo "$rl_out"
  if [ "$rl_rc" -eq 0 ]; then
    # exit 0 = 재시도 가능 → 원래 Queued 상태로 복귀. webhook _check_and_retrigger 가
    # Queued 계열만 조회하므로 이 복귀만으로 재수거된다(webhook 무변경).
    local back_state="DayQueued"
    [ "$task_mode" = "night" ] && back_state="NightQueued"
    python3 scripts/linear_tracker.py update --issue-id "$issue_id" --status "$back_state" 2>/dev/null || true
    log "완주 오케스트레이터: ${issue_key} → ${back_state} 복귀 (재시도 예약)"
    return 0
  fi
  # exit 3 = 한도 소진 · 터미널 → Backlog + 정지 코멘트. 최종 HALT 보고는 런 종료 시 일괄.
  python3 scripts/linear_tracker.py update --issue-id "$issue_id" --status "Backlog" 2>/dev/null || true
  python3 - "$issue_id" "$reason" <<'PY' 2>/dev/null || true
import sys
sys.path.insert(0, "scripts")
from linear_client import get_env, linear_request
issue_id, reason = sys.argv[1], sys.argv[2]
api_key, _ = get_env()
body = (
    "🛑 **완주 오케스트레이터 — 자동 재시도 한도 소진(정지)**\n\n"
    f"사람 개입이 필요합니다.\n마지막 실패 사유: {reason}"
)
linear_request(
    api_key,
    "mutation($issueId:String!,$body:String!){commentCreate(input:{issueId:$issueId,body:$body}){comment{id}}}",
    {"issueId": issue_id, "body": body},
)
PY
  log "완주 오케스트레이터: ${issue_key} 터미널 — Backlog + 정지 코멘트 (HALT 보고 대상)"
  # 막힘 지점을 원 티켓의 하위 태스크로 축적한다(CE-376 4b). 토글 off(미설정)면 회귀 0.
  # 재시도 가능 경로가 아니라 터미널(한도 소진)에서만 만든다 — 재시도마다 쌓이면 노이즈.
  if is_enabled "FLOWOPS_FAILURE_SUBTASK" 2>/dev/null; then
    local sub_title sub_body sub_out sub_rc=0
    sub_title="[막힘] ${issue_key} — ${reason:0:60}"
    sub_body="자동 파이프라인이 재시도 한도를 소진하여 정지했습니다. 사람의 판단이 필요합니다.

- 원 티켓: ${issue_key}
- 실패 사유: ${reason}
- 재시도: ${rl_out:-(미상)}
- 브랜치: ${BRANCH:-(미상)}
- 실행 ID: ${METRIC_RUN_ID:-(미상)}
- 로그: ${CLAUDE_LOG:-(미상)}"
    # 상태는 Wait — 사람이 보고 판단. Queued 계열로 만들면 재수거되어 무한 루프.
    sub_out="$(python3 scripts/linear_tracker.py task \
      --title "$sub_title" --summary "$sub_body" \
      --status Wait --parent "$issue_id" 2>&1)" || sub_rc=$?
    if [ "$sub_rc" -eq 0 ]; then
      log "완주 오케스트레이터: ${issue_key} 하위 태스크(막힘) 생성 — ${sub_out}"
    else
      log "WARN: ${issue_key} 하위 태스크 생성 실패(파이프라인 계속): ${sub_out}"
    fi
  fi
  return 0
}

# ── 파라미터 ──
MAX_ITERATIONS=30
MAX_TURNS=""
ONCE_MODE=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --max-iterations)
      MAX_ITERATIONS="$2"
      shift 2
      ;;
    --max-turns)
      MAX_TURNS="$2"
      shift 2
      ;;
    --once)
      ONCE_MODE=true
      shift
      ;;
    *)
      log "알 수 없는 옵션: $1"
      exit 1
      ;;
  esac
done

# ── 중복 실행 방지 ──
if [ -f "$LOCK_FILE" ]; then
  LOCK_PID=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
  if [ -n "$LOCK_PID" ] && kill -0 "$LOCK_PID" 2>/dev/null; then
    log "SKIP: 이전 파이프라인 실행 중 (PID: $LOCK_PID)"
    exit 0
  else
    log "WARN: 잔류 lock 파일 제거 (PID: $LOCK_PID 종료됨)"
    rm -f "$LOCK_FILE"
  fi
fi

echo $$ > "$LOCK_FILE"

cleanup() {
  rm -f "$LOCK_FILE"
  # [시트 풀] 자기 PID 가 잡고 있던 자문 시트 락만 회수(다른 러너의 락은 건드리지 않는다).
  for _seat_lock in "$PROJECT_DIR"/.ralph/.seat_lock.*; do
    [ -f "$_seat_lock" ] || continue
    [ "$(cat "$_seat_lock" 2>/dev/null || true)" = "$$" ] && rm -f "$_seat_lock"
  done
  safe_git checkout main 2>/dev/null || true
}
trap cleanup EXIT

log "======================================="
log "  자동 개발 파이프라인 v6 (멀티 Agent)"
log "  Gemini(기획) → Claude(구현) → Codex(QA)"
log "======================================="

# ── Linear Watcher 활성화 확인 ──
if ! is_enabled "FLOWOPS_LINEAR_WATCHER" 2>/dev/null; then
  log "SKIP: Linear Watcher 비활성화됨 (FLOWOPS_LINEAR_WATCHER=false)"
  exit 0
fi

# ── DB 확인 ──
if ! docker ps 2>/dev/null | grep -q sevenclaw-db; then
  log "DB 미실행. 시작합니다..."
  docker compose -f "$PROJECT_DIR/clickeye-infra/docker/docker-compose.yml" up -d db redis
  sleep 10
fi

# ── 이전 실행 결과 정리 ──
rm -f ".ralph/.pipeline_result.json"

# ── 순차 실행 루프 ──
COMPLETED=0
FAILED=0
COMPLETED_ISSUES=""  # NightQueued 일괄 알림용

while true; do
  log ""
  log "── DayQueued/NightQueued 이슈 감지 중... ──"

  # 1개만 가져오기
  # P5 다프로젝트: WATCHER_TITLE_PREFIX 설정 시 해당 프로젝트 티켓만 수집(러너 경유).
  # 미설정이면 기존 전체 수집 그대로(회귀 0).
  WATCHER_OUTPUT=$(python3 scripts/linear_watcher.py --per-task --limit 1 \
    ${WATCHER_TITLE_PREFIX:+--title-prefix "$WATCHER_TITLE_PREFIX"} 2>&1) || WATCHER_EXIT=$?
  WATCHER_EXIT=${WATCHER_EXIT:-0}

  echo "$WATCHER_OUTPUT"

  if [ "$WATCHER_EXIT" -eq 2 ]; then
    log "DONE: DayQueued/NightQueued 이슈 없음. 순차 실행 종료."
    break
  elif [ "$WATCHER_EXIT" -ne 0 ]; then
    log "ERROR: linear_watcher.py 실행 실패 (exit: $WATCHER_EXIT)"
    python3 scripts/telegram_notify.py --message "파이프라인 에러: linear_watcher 실행 실패" 2>/dev/null || true
    break
  fi

  # task_mapping에서 태스크 정보 추출
  if [ ! -f "$TASK_MAPPING" ]; then
    log "ERROR: $TASK_MAPPING 파일이 존재하지 않습니다."
    break
  fi

  TASK_INFO=$(python3 -c "
import json
with open('$TASK_MAPPING') as f:
    m = json.load(f)
for title, meta in m.items():
    mode = meta.get('mode', 'day')
    print(f\"{meta['identifier']}|{meta['issue_id']}|{meta['branch']}|{mode}|{title}\")
    break
")

  IFS='|' read -r ISSUE_KEY ISSUE_ID BRANCH TASK_MODE TITLE <<< "$TASK_INFO"

  # ── [파생형 하네스] 워크스페이스 automap (CE-339, opt-in — 미설정=off, 회귀 0) ──
  # 전용 러너(시작 시 WORKSPACE_KEY 존재)가 아닌 단일 러너에서만, 이슈 제목 접두사로
  # 매핑 원장(.ralph/workspaces.json)을 조회해 WORKSPACE_KEY 를 이슈별로 설정한다.
  # 해석은 workspace_map.py --resolve-title 가 단일 소스(mapped=소스 확보만 해석).
  # 미매핑/pending_source/원장 없음/조회 실패 → 빈 값 → self-repo(현행) 그대로. 실제
  # cwd 전환은 resolve_impl_workdir()가 FLOWOPS_WORKSPACE + 워크스페이스 존재로 게이트한다.
  if is_enabled "FLOWOPS_WORKSPACE_AUTOMAP" 2>/dev/null && [ -n "${FLOWOPS_WORKSPACE_AUTOMAP:-}" ] \
    && [ -z "$WORKSPACE_KEY_INITIAL" ]; then
    WORKSPACE_KEY="$(python3 "$PROJECT_DIR/scripts/workspace_map.py" \
      --resolve-title "$TITLE" --output "$PROJECT_DIR/.ralph/workspaces.json" 2>/dev/null || true)"
    if [ -n "${WORKSPACE_KEY:-}" ]; then
      log "automap: ${ISSUE_KEY} → 워크스페이스 ${WORKSPACE_KEY} (원장 매핑)"
    else
      log "automap: ${ISSUE_KEY} 미매핑 — self-repo 진행"
    fi
  fi

  # ── [CE-363] 이터레이션 프로젝트 축 1회 해석 ──
  # WORKSPACE_KEY 확정 지점에서 project_id 를 한 번만 해석해 재사용한다(메트릭 상관 축 +
  # 사용량 인제스트 CE-362 가 같은 값을 두 번 해석하지 않도록). self-repo(WORKSPACE_KEY 없음)
  # 는 프로젝트가 없으므로 빈 값 = 축 없이 진행(회귀 0).
  ITER_PROJECT_ID=""
  if [ -n "${WORKSPACE_KEY:-}" ]; then
    ITER_PROJECT_ID="$(python3 "$PROJECT_DIR/scripts/workspace_map.py" \
      --resolve-project "$WORKSPACE_KEY" \
      --output "$PROJECT_DIR/.ralph/workspaces.json" 2>/dev/null || true)"
  fi

  # ── [CE-358] 수주 접두사 fail-closed — 미매핑 수주 티켓을 self-repo 로 흘리지 않는다 ──
  # `[수주:xxxxxxxx] ` 접두사는 "이 티켓은 고객 프로젝트 것" 이라는 명시적 선언이다
  # (intake_issue.sh:174 가 인테이크 id 앞 8자로 붙인다). 그런데 automap 이 못 풀거나
  # workspaces/<key> 가 없으면 resolve_impl_workdir 이 **조용히 PROJECT_DIR 로 폴백**해
  # 고객 요구사항이 ClickEye 레포에 구현·머지된다(실측 확인한 폴백 경로).
  # 조달 누락은 운영자가 고칠 일이고, 그 사이 남의 요구사항이 우리 레포에 들어오는 것은
  # 어떤 경우에도 옳지 않다 → 폴백 대신 실패로 끊는다(재시도 원장 경유, 티켓 유실 없음).
  if printf '%s' "$TITLE" | grep -qE '^\[수주:[0-9a-zA-Z]{6,}\][[:space:]]'; then
    WS_PREFIX_KEY="$(printf '%s' "$TITLE" | sed -E 's/^\[수주:([0-9a-zA-Z]{6,})\].*/\1/')"
    if [ -z "${WORKSPACE_KEY:-}" ] || [ ! -d "$PROJECT_DIR/workspaces/${WORKSPACE_KEY}" ]; then
      log "ERROR: 수주 티켓인데 워크스페이스가 없다 — self-repo 폴백을 차단한다 (${ISSUE_KEY})"
      log "  접두사 키=${WS_PREFIX_KEY} / automap 해석=${WORKSPACE_KEY:-(없음)}"
      log "  조치: python3 scripts/workspace_map.py --list 로 상태 확인 →"
      log "        --set-source ${WS_PREFIX_KEY} <git-url> → scripts/workspace_provision.sh --key ${WS_PREFIX_KEY} --source <git-url>"
      # 실패 처분은 ws_delivery_fail 과 동일 관례: 재시도 원장이 되돌리지 못하면 Backlog.
      if ! handle_task_failure "$ISSUE_KEY" "$ISSUE_ID" "$TASK_MODE" \
        "수주 티켓 미조달: 워크스페이스 ${WS_PREFIX_KEY} 없음(self-repo 폴백 차단)"; then
        python3 scripts/linear_tracker.py update --issue-id "$ISSUE_ID" --status "Backlog" 2>/dev/null || true
        log "Linear 상태: Backlog (수주 티켓 미조달)"
      fi
      FAILED=$((FAILED + 1))
      continue
    fi
  fi

  # [P1 완주] 이번 런에서 이미 실패해 Queued 복귀된 이슈를 즉시 재수거하면 무한루프
  # → 런을 종료하고 webhook 재트리거(다음 런)로 이월한다. MIN_TRIGGER_INTERVAL 이 완충.
  if [ -n "$FAILED_THIS_RUN" ] && printf '%s\n' $FAILED_THIS_RUN | grep -qx "$ISSUE_KEY"; then
    log "완주 오케스트레이터: ${ISSUE_KEY} 는 이번 런에서 이미 실패 — 런 종료(다음 트리거로 이월)"
    break
  fi

  COMPLETED=$((COMPLETED + 1))
  log ""
  log "══════════════════════════════════════"
  log "  태스크 #$COMPLETED: $TITLE"
  log "  이슈: $ISSUE_KEY | 브랜치: $BRANCH"
  log "══════════════════════════════════════"

  # ── [Tier 3a 메트릭] 이슈 처리 1건의 run_id 생성(1회) + 최종 처분 기본값 ──
  METRIC_RUN_ID="${ISSUE_KEY}_$(date +%Y%m%d_%H%M%S)"
  RUN_OUTCOME="unknown"

  # ── Temporal 섀도우 트리거(CE-297, P1) ──
  # FLOWOPS_TEMPORAL 활성 시에만 거버넌스 결정을 미러링하는 ShadowDeliveryWorkflow 를
  # fire-and-forget 로 트리거한다. 부작용 0(머지/커밋/PR 없음), 비블로킹, 실패 무시 →
  # 기존 파이프라인 실제 경로를 막지 않고 병렬 대조 로깅만 한다. 미설정 시 아무 것도 안 함(회귀 0).
  if is_enabled "FLOWOPS_TEMPORAL" 2>/dev/null && [ -n "${FLOWOPS_TEMPORAL:-}" ]; then
    python3 "$PROJECT_DIR/scripts/temporal_shadow_trigger.py" \
      --issue-key "$ISSUE_KEY" --head "$BRANCH" >>"$CLAUDE_LOG" 2>&1 || true
  fi

  # ── [고객 레포 딜리버리 v1] 워크스페이스 git 리다이렉트 판정 (CE-347, opt-in — 미설정=off) ──
  # 워크스페이스 모드에서 구현 claude 는 고객 clone 에서 돌지만 브랜치·머지·push 는 ClickEye
  # 레포를 향해 있었다 → 고객 커밋이 아무 데도 나가지 않고 빈 머지가 "완료"로 소진됐다.
  # 이 토글이 명시 활성이고 구현 대상이 self-repo 가 아닐 때만 브랜치·검증·push 를 고객
  # clone 으로 돌린다. 미설정/자기레포 → 이후 모든 분기가 원본 경로 그대로(회귀 0).
  # IMPL_WORKDIR 은 여기서 1회 해석해 이터레이션 내내 재사용한다(STEP B 재해석과 동일 값).
  IMPL_WORKDIR="$(resolve_impl_workdir)"
  WS_DELIVERY=false
  CUST_BASE=""
  WS_ORIGIN=""
  if is_enabled "FLOWOPS_WORKSPACE_DELIVERY" 2>/dev/null && [ -n "${FLOWOPS_WORKSPACE_DELIVERY:-}" ] \
    && [ "$IMPL_WORKDIR" != "$PROJECT_DIR" ]; then
    WS_DELIVERY=true
  fi

  WS_GIT_LOG=""
  WS_POLICY="$PROJECT_DIR/templates/harness-core/governance-workspace.policy.json"
  WS_TIP_BEFORE=""
  if [ "$WS_DELIVERY" = true ]; then
    # [G5] 워크스페이스 git 진단 로그 — 실패 원인(git stderr)을 삼키지 않는다. CLAUDE_LOG 는
    # STEP B 에서야 정의되므로(브랜치 단계에서 참조하면 set -u 위반) 이터레이션 전용 파일을 쓴다.
    mkdir -p "$PROJECT_DIR/logs"
    WS_GIT_LOG="$PROJECT_DIR/logs/ws_delivery_${ISSUE_KEY}_$(date '+%Y%m%d_%H%M%S').log"
    log "워크스페이스 딜리버리 git 로그: $WS_GIT_LOG"

    # [G2/G6] ClickEye 주입물을 clone-로컬 제외에 등재(멱등, 자기치유). 더러운 트리 판정과
    # 오염 가드가 하네스 프래그먼트를 오탐하지 않게 하는 선행 조건이다.
    ws_exclude_harness_artifacts

    # 선행 검증 ① 고객 origin — 없으면 push 대상이 없으므로 착수 자체를 막는다(허상 방지).
    WS_ORIGIN="$(impl_git remote get-url origin 2>>"$WS_GIT_LOG" || true)"
    if [ -z "$WS_ORIGIN" ]; then
      ws_delivery_fail "고객 레포 origin 없음: $IMPL_WORKDIR"
      continue
    fi
    # [G8] 고객 origin 이 ClickEye 자신을 가리키면(오조달·runner_clone 잔재) push 가 PRIMARY 를
    # 겨냥한다 — 브랜치가 ClickEye 로 올라가고 고객에겐 아무 것도 안 간다. 착수 전 차단.
    WS_PRIMARY_ORIGIN="$(safe_git remote get-url origin 2>>"$WS_GIT_LOG" || true)"
    if [ "$WS_ORIGIN" = "$PROJECT_DIR" ] || [ "$WS_ORIGIN" = "file://$PROJECT_DIR" ] \
      || { [ -n "$WS_PRIMARY_ORIGIN" ] && [ "$WS_ORIGIN" = "$WS_PRIMARY_ORIGIN" ]; }; then
      ws_delivery_fail "고객 origin 이 ClickEye 레포를 가리킴(오조달 — push 대상 오류): $WS_ORIGIN"
      continue
    fi
    # 선행 검증 ② 고객 기본 브랜치 감지 3단(origin/HEAD → 조달 시 기록 파일 → 실패).
    # main 추측 금지 — 틀린 base 로 diff·push 하면 잘못된 딜리버리가 된다.
    CUST_BASE="$(impl_git symbolic-ref --short refs/remotes/origin/HEAD 2>>"$WS_GIT_LOG" \
      | sed 's#^origin/##' || true)"
    if [ -z "$CUST_BASE" ]; then
      # [G11] origin/HEAD 는 삭제·구버전 clone·부분 fetch 로 없을 수 있다. 원격에 물어 1회
      # 복구를 시도한 뒤 재판정한다(네트워크 실패는 무해 — 아래 기록 파일 폴백으로 진행).
      impl_git remote set-head -a origin >>"$WS_GIT_LOG" 2>&1 || true
      CUST_BASE="$(impl_git symbolic-ref --short refs/remotes/origin/HEAD 2>>"$WS_GIT_LOG" \
        | sed 's#^origin/##' || true)"
    fi
    if [ -z "$CUST_BASE" ] && [ -r "$IMPL_WORKDIR/.clickeye_default_branch" ]; then
      CUST_BASE="$(tr -d '[:space:]' < "$IMPL_WORKDIR/.clickeye_default_branch" 2>>"$WS_GIT_LOG" || true)"
    fi
    if [ -z "$CUST_BASE" ]; then
      ws_delivery_fail "고객 기본 브랜치 감지 실패(origin/HEAD 복구·.clickeye_default_branch 모두 실패): $IMPL_WORKDIR"
      continue
    fi
    # [G9] 중립 정책 파일 부재를 게이트 시점까지 끌고 가면 shim 이 exit 2 로 떨어져 원인이
    # "거버넌스 차단"으로 오표기된다. 거버넌스가 켜져 있을 때만 선행 확인(fail-closed).
    if is_enabled "FLOWOPS_GOVERNANCE" 2>/dev/null && [ ! -r "$WS_POLICY" ]; then
      ws_delivery_fail "워크스페이스 거버넌스 중립 정책 파일 없음/판독 불가: $WS_POLICY"
      continue
    fi
    log "워크스페이스 딜리버리: 대상=$IMPL_WORKDIR origin=$WS_ORIGIN 기본브랜치=$CUST_BASE"
  fi

  # 브랜치 생성/전환
  if [ "$WS_DELIVERY" = true ]; then
    # [R1/R3] 고객 clone 에서 기본 브랜치를 최신화한 뒤 태스크 브랜치를 만든다. STEP B 의
    # 구현 커밋이 이 브랜치에 얹히는 것이 이 티켓의 핵심 — ClickEye 쪽 checkout/pull 은
    # 이 경로에서 실행하지 않는다(PRIMARY 브랜치 무접촉).
    # [R2] 머지된 동명 브랜치 정리는 생략 — 고객 레포 브랜치는 삭제하지 않는다.

    # [G4] 이전 런이 detached HEAD 를 남겼으면(크래시·에이전트의 checkout --detach) 아래
    # checkout 이 그 커밋을 고아로 만든다. CUST_BASE 계보 밖일 때만 회수 브랜치로 보존한다
    # (계보 안이면 잃을 것이 없다). 보존 실패도 진행을 막지 않는다 — 경고로 드러낸다.
    if ! impl_git symbolic-ref -q HEAD >/dev/null 2>&1; then
      WS_ORPHAN_SHA="$(impl_git rev-parse HEAD 2>>"$WS_GIT_LOG" || true)"
      if [ -n "$WS_ORPHAN_SHA" ] \
        && ! impl_git merge-base --is-ancestor "$WS_ORPHAN_SHA" "$CUST_BASE" 2>>"$WS_GIT_LOG"; then
        WS_RESCUE_PRE="rescue/${ISSUE_KEY}-detached-$(date '+%Y%m%d_%H%M%S')"
        if impl_git branch "$WS_RESCUE_PRE" "$WS_ORPHAN_SHA" 2>>"$WS_GIT_LOG"; then
          log "WARN: 고객 clone 이 detached HEAD(${WS_ORPHAN_SHA}) — 회수 브랜치 ${WS_RESCUE_PRE} 보존 후 진행"
        else
          log "WARN: detached HEAD(${WS_ORPHAN_SHA}) 회수 브랜치 생성 실패 — 진행(상세: $WS_GIT_LOG)"
        fi
      fi
    fi

    # [G2] 에이전트가 미커밋 변경을 남기고 죽으면 checkout 이 영구히 막혀 그 워크스페이스의
    # 모든 후속 티켓이 실패한다(wedge). 지우지 않고 stash 로 비켜둔 뒤 진행한다 — 유실 0.
    # 복구: git -C <clone> stash list | grep clickeye-auto-preserve → git stash apply <ref>
    if [ -n "$(impl_git status --porcelain 2>>"$WS_GIT_LOG" || true)" ]; then
      WS_STASH_MSG="clickeye-auto-preserve ${ISSUE_KEY} $(date '+%Y%m%d_%H%M%S')"
      if impl_git stash push --include-untracked -m "$WS_STASH_MSG" >>"$WS_GIT_LOG" 2>&1; then
        log "WARN: 고객 clone 에 미커밋 변경 존재 — stash 보존 후 진행 ('${WS_STASH_MSG}'). 복구: git -C '$IMPL_WORKDIR' stash list"
      else
        ws_delivery_fail "고객 clone 미커밋 변경을 stash 로 보존하지 못함(유실 위험 — 수동 정리 필요): $IMPL_WORKDIR"
        continue
      fi
    fi

    # ── [CE-369] 인테이크 1건 = 고객 브랜치 1개 ──────────────────────────────
    # 이전 판은 티켓마다 `ralph/<ISSUE_KEY>` 를 고객 기본 브랜치에서 새로 분기했다. 머지는
    # 고객 몫(CE-347)이라 앞선 티켓 산출물이 기본 브랜치에 없으므로, **의존 티켓 체인이
    # 구조적으로 깨졌다** — 실측(CE-368): CE-366 이 만든 docs/INSTALL.md 를 후속 티켓이
    # 보지 못해 BLOCKED.
    #
    # 내부 브랜치명(BRANCH=ralph/<KEY>)은 **그대로 둔다** — 거버넌스 ticket-ref 가 브랜치명에서
    # `^[A-Z0-9]+-\d+$` 키를 추출하므로(pre_merge_gate.py) 인테이크 단위로 바꾸면 게이트가
    # 깨진다. 고객 레포에만 쓰는 별도 이름을 둔다: 고객 입장에서 "수주 1건 = 브랜치 1개".
    WS_BRANCH="clickeye/intake-${WORKSPACE_KEY}"

    # 원격 상태를 먼저 최신화한다 — 이 브랜치의 존재 여부가 base 를 결정한다.
    impl_git fetch origin --prune 2>>"$WS_GIT_LOG" || \
      log "WARN: 고객 origin fetch 실패 — 로컬 참조로 진행(상세: $WS_GIT_LOG)"

    if impl_git rev-parse --verify --quiet "refs/remotes/origin/${WS_BRANCH}" >/dev/null 2>&1; then
      # 같은 인테이크의 앞선 티켓이 이미 만든 브랜치 → 그 위에 얹는다(체인 성립).
      log "워크스페이스 딜리버리: 기존 인테이크 브랜치 위에 이어붙임 (origin/${WS_BRANCH})"
      if ! impl_git checkout -B "$WS_BRANCH" "origin/${WS_BRANCH}" 2>>"$WS_GIT_LOG"; then
        ws_delivery_fail "인테이크 브랜치 체크아웃 실패: ${WS_BRANCH} (상세: $WS_GIT_LOG)"
        continue
      fi
    else
      # 이 인테이크의 첫 티켓 → 고객 기본 브랜치에서 분기.
      if ! impl_git checkout "$CUST_BASE" 2>>"$WS_GIT_LOG"; then
        ws_delivery_fail "고객 기본 브랜치 checkout 실패: $CUST_BASE (상세: $WS_GIT_LOG)"
        continue
      fi
      if ! impl_git pull origin "$CUST_BASE" 2>>"$WS_GIT_LOG"; then
        ws_delivery_fail "고객 기본 브랜치 pull 실패(충돌/네트워크/권한): $CUST_BASE (상세: $WS_GIT_LOG)"
        continue
      fi
      log "워크스페이스 딜리버리: 인테이크 브랜치 신규 생성 (${WS_BRANCH} ← ${CUST_BASE})"
      if ! impl_git checkout -B "$WS_BRANCH" 2>>"$WS_GIT_LOG"; then
        ws_delivery_fail "고객 레포 인테이크 브랜치 생성 실패: ${WS_BRANCH} (상세: $WS_GIT_LOG)"
        continue
      fi
    fi
    # [G1] 이번 런의 시작 tip. R4 는 이 값 기준의 **델타**로 판정한다 — 재시도로 잔여 커밋이
    # 있는 브랜치를 재사용할 때, 이번 런이 빈손인데 지난 런 커밋 때문에 성공 처리되는 것을 막는다.
    WS_TIP_BEFORE="$(impl_git rev-parse HEAD 2>>"$WS_GIT_LOG" || true)"
    if [ -z "$WS_TIP_BEFORE" ]; then
      ws_delivery_fail "고객 clone HEAD 해석 실패(빈 레포?): $IMPL_WORKDIR (상세: $WS_GIT_LOG)"
      continue
    fi
  else
    safe_git checkout main 2>/dev/null || true
    safe_git pull origin main 2>/dev/null || true
    # 이미 머지된 동명 브랜치가 있으면 삭제 후 재생성
    if safe_git branch --merged main | grep -q "$BRANCH"; then
      log "WARN: 머지 완료된 브랜치 $BRANCH 삭제 후 재생성"
      safe_git branch -d "$BRANCH" 2>/dev/null || true
    fi
    safe_git checkout -b "$BRANCH" 2>/dev/null || safe_git checkout "$BRANCH" 2>/dev/null || {
      log "ERROR: 브랜치 생성 실패: $BRANCH"
      if ! handle_task_failure "$ISSUE_KEY" "$ISSUE_ID" "$TASK_MODE" "브랜치 생성 실패: $BRANCH"; then
        python3 scripts/linear_tracker.py update --issue-id "$ISSUE_ID" --status "Backlog" 2>/dev/null || true
        log "Linear 상태: Backlog (브랜치 생성 실패)"
      fi
      FAILED=$((FAILED + 1))
      continue
    }
  fi

  # fix_plan 준비
  mkdir -p ".ralph"
  cp ".ralph/tasks/${ISSUE_KEY}.md" ".ralph/fix_plan.md" 2>/dev/null || {
    log "ERROR: fix_plan 없음: .ralph/tasks/${ISSUE_KEY}.md"
    safe_git checkout main 2>/dev/null || true
    if ! handle_task_failure "$ISSUE_KEY" "$ISSUE_ID" "$TASK_MODE" "fix_plan 없음: .ralph/tasks/${ISSUE_KEY}.md"; then
      python3 scripts/linear_tracker.py update --issue-id "$ISSUE_ID" --status "Backlog" 2>/dev/null || true
      log "Linear 상태: Backlog (fix_plan 없음)"
    fi
    FAILED=$((FAILED + 1))
    continue
  }

  # 프론트엔드 UI/UX 작업 감지 → PROMPT에 에이전트 지침 주입
  UIUX_KEYWORDS="페이지|UI|컴포넌트|폼|대시보드|레이아웃|디자인|반응형|스타일|frontend|component|page"
  if grep -qiE "$UIUX_KEYWORDS" ".ralph/fix_plan.md" 2>/dev/null; then
    log "UI/UX 작업 감지: uiux-agent 지침 활성화"
    export RALPH_UIUX_MODE=true
  else
    export RALPH_UIUX_MODE=false
  fi

  # Linear 상태 → In Progress (1개만)
  python3 scripts/linear_tracker.py update --issue-id "$ISSUE_ID" --status "In Progress" 2>/dev/null || true
  log "Linear 상태: In Progress"

  # ── [STEP A] 메타프롬프트 정제 (관측형 사전 정제 — 기획+정제 일체) → PLAN.md ──
  # 거친 태스크 → 고품질 구현 스펙으로 정제 → .ralph/refined/{ISSUE}.md + PLAN.md + Linear 코멘트.
  # Claude 구독 세션(ANTHROPIC_API_KEY unset)으로 실행. FLOWOPS_METAPROMPT=false면 Gemini 레거시 폴백.
  mkdir -p "$PROJECT_DIR/logs"
  TASK_DESC=$(python3 -c "
import json
with open('$TASK_MAPPING') as f:
    m = json.load(f)
for title, meta in m.items():
    print(meta.get('description', ''))
    break
" 2>/dev/null || echo "")

  METAPROMPT_SKILL=".claude/skills/metaprompt/SKILL.md"
  REFINED_DIR=".ralph/refined"
  REFINED_FILE="$REFINED_DIR/${ISSUE_KEY}.md"
  mkdir -p "$REFINED_DIR"

  if is_enabled "FLOWOPS_METAPROMPT" 2>/dev/null && [ -f "$METAPROMPT_SKILL" ]; then
    log "── 메타프롬프트 정제 시작 ──"
    # 멱등성: 이미 정제된 스펙이 있으면 정제 콜 생략 (중복 토큰 방지)
    if [ ! -s "$REFINED_FILE" ]; then
      # SKILL.md 는 `---` YAML 프론트매터로 시작한다. 그 문자열이 claude 의 첫 인자 맨 앞에
      # 오면 CLI 가 옵션으로 파싱해 `error: unknown option '---…'` 로 즉시 죽는다 — 실측
      # (2026-08-04, logs/refine_CE-355_*.log): 정제가 **전 티켓에서 조용히 실패**하고
      # "fix_plan→PLAN 폴백" 으로 돌고 있었다(파이프라인은 계속 진행하므로 관측이 어려웠다).
      # 프론트매터를 떼고, 첫 줄이 항상 `#` 로 시작하도록 헤더를 앞세운다(이중 방어).
      METAPROMPT_BODY="$(awk '
        NR==1 && /^---[[:space:]]*$/ { fm=1; next }
        fm  && /^---[[:space:]]*$/   { fm=0; next }
        !fm
      ' "$METAPROMPT_SKILL")"
      REFINE_PROMPT="# 정제 지침 (metaprompt 스킬)

$METAPROMPT_BODY

---

# 정제 대상 태스크
- 이슈: $ISSUE_KEY
- 제목: $TITLE
- 설명:
$TASK_DESC

# fix_plan (참고)
$(cat .ralph/fix_plan.md 2>/dev/null || echo '(없음)')

위 metaprompt 지침에 따라 이 태스크를 '구현 스펙'으로 정제하라.
정제된 구현 스펙(마크다운)만 출력하라. 코드는 작성하지 마라."
      REFINE_LOG="$PROJECT_DIR/logs/refine_${ISSUE_KEY}_$(date '+%Y%m%d_%H%M%S').log"
      # Claude 구독 세션 사용 (API 크레딧 차감 방지)
      REFINE_RC=0
      ( unset ANTHROPIC_API_KEY
        # [시트 풀] 이 서브셸의 stdout 은 정제 산출물 전용 → 시트 로그는 stderr(REFINE_LOG)로.
        apply_seat_env >&2 || exit 97
        timeout "${REFINE_TIMEOUT:-600}" claude -p "$REFINE_PROMPT" \
          --model "$PIPELINE_MODEL_REFINE" \
          --dangerously-skip-permissions \
          </dev/null ) > "$REFINED_FILE" 2>>"$REFINE_LOG" || REFINE_RC=$?
      # 97 = 시트 STRICT 스킵(정제 미실행) → 티켓 무작업 소진 대신 실패 경로로 되돌린다.
      if [ "$REFINE_RC" = "97" ]; then
        rm -f "$REFINED_FILE"
        seat_strict_skip "STEP A 정제"
        continue
      fi
    else
      log "기존 정제 스펙 재사용: $REFINED_FILE"
    fi

    if [ -s "$REFINED_FILE" ]; then
      cp "$REFINED_FILE" .ralph/PLAN.md
      log "메타프롬프트 정제 완료 → $REFINED_FILE (PLAN.md 동기화)"
      # 정제 스펙을 Linear 코멘트로 기록 (실패 무시)
      python3 - "$ISSUE_ID" "$REFINED_FILE" <<'PY' 2>/dev/null || true
import sys
sys.path.insert(0, "scripts")
from linear_client import get_env, linear_request
issue_id, refined_file = sys.argv[1], sys.argv[2]
api_key, _ = get_env()
body = "🤖 **ClickEye 메타프롬프팅 — 정제된 구현 스펙**\n\n" + open(refined_file, encoding="utf-8").read()
linear_request(
    api_key,
    "mutation($issueId:String!,$body:String!){commentCreate(input:{issueId:$issueId,body:$body}){comment{id}}}",
    {"issueId": issue_id, "body": body},
)
PY
      log "Linear 코멘트 게시(정제 스펙)"

      # ── [파생형 하네스 Tier 2] 도메인 제약 누적 (opt-in — 미설정=off, 회귀 0) ──
      # 정제 산출물의 `## 도메인 제약` 섹션을 구현 대상 워크디렉터리의
      # .claude/CLAUDE.domain.md 에 티켓 키 마커로 멱등 병합. 섹션 부재 시 no-op.
      # 실패해도 파이프라인 비차단(|| WARN). 대상은 STEP B 와 동일 해석.
      if is_enabled "FLOWOPS_DOMAIN_PROFILE" 2>/dev/null && [ -n "${FLOWOPS_DOMAIN_PROFILE:-}" ]; then
        DP_TARGET="$(resolve_impl_workdir)"
        DP_OUT="$(python3 scripts/domain_profile_merge.py \
          --refined "$REFINED_FILE" --target "$DP_TARGET" --ticket "$ISSUE_KEY" 2>&1)" \
          && log "도메인 프로파일 병합: $DP_OUT" \
          || log "WARN: 도메인 프로파일 병합 실패(비차단): $ISSUE_KEY — $DP_OUT"
      fi
    else
      log "WARN: 메타프롬프트 정제 실패/빈 출력 — fix_plan→PLAN 폴백"
      rm -f "$REFINED_FILE"
      cp .ralph/fix_plan.md .ralph/PLAN.md 2>/dev/null || true
    fi
  elif is_enabled "FLOWOPS_GEMINI_PLAN" 2>/dev/null; then
    log "── Gemini 기획 시작 (레거시 폴백) ──"
    bash scripts/generate_plan_with_gemini.sh "$TITLE" "$TASK_DESC" \
      --fix-plan ".ralph/fix_plan.md" 2>&1 || {
      log "WARN: Gemini PLAN 생성 실패. fix_plan.md로 대체"
      cp .ralph/fix_plan.md .ralph/PLAN.md 2>/dev/null || true
    }
    log "Gemini PLAN 생성 완료"
  else
    log "SKIP: 기획 단계 비활성화 — fix_plan을 PLAN.md로 복사"
    cp .ralph/fix_plan.md .ralph/PLAN.md 2>/dev/null || true
  fi

  # ── [Tier 3a 메트릭] refine_done — 정제 사용/도메인 섹션/폴백 관측(비차단) ──
  M_REFINED=false; M_DOMAIN=false; M_FALLBACK=true
  if [ -s "$REFINED_FILE" ]; then
    M_REFINED=true; M_FALLBACK=false
    grep -q '## 도메인 제약' "$REFINED_FILE" 2>/dev/null && M_DOMAIN=true
  fi
  record_metric "$METRIC_RUN_ID" "refine_done" \
    "{\"refined\": $M_REFINED, \"domain_section\": $M_DOMAIN, \"fallback\": $M_FALLBACK}"

  # ── [STEP B] Claude 구현 (동기 — 완료까지 대기) ──
  CLAUDE_LOG="$PROJECT_DIR/logs/claude_${ISSUE_KEY}_$(date '+%Y%m%d_%H%M%S').log"
  mkdir -p "$PROJECT_DIR/logs"

  log "── Claude 구현 시작 ──"
  log "로그: $CLAUDE_LOG"

  export RALPH_MAX_ITERATIONS=$MAX_ITERATIONS
  rm -f .ralph/.iteration_count

  # ANTHROPIC_API_KEY를 unset — claude.ai 구독 세션 사용 (API 크레딧 차감 방지)
  unset ANTHROPIC_API_KEY

  # ── [파생형 하네스 Tier 1] 워크스페이스 cwd 전환 (opt-in — 미설정=off, 회귀 0) ──
  # 해석 로직은 resolve_impl_workdir()(상단 정의) 공유 — STEP A 도메인 프로파일과 동일 대상.
  # 프롬프트 조립보다 **먼저** 해석해야 한다 — 어느 프롬프트를 쓸지가 이 값으로 갈린다(CE-356).
  IMPL_WORKDIR="$(resolve_impl_workdir)"

  IMPL_PROMPT="$(build_impl_prompt "$IMPL_WORKDIR" "$REFINED_FILE" "$ISSUE_KEY" "$TITLE")"
  if [ "$IMPL_WORKDIR" != "$PROJECT_DIR" ]; then
    log "파생형 하네스: 구현 cwd → 워크스페이스 ${WORKSPACE_KEY} ($IMPL_WORKDIR)"
  fi

  M_IMPL_START=$(date +%s)   # [Tier 3a 메트릭] 구현 소요 관측용(동작 불변)
  # [시트 풀] fd 9 = 메인 로그(파이프 이전 stdout). 시트 로그를 여기로 보내 CLAUDE_LOG 의
  # stream-json 을 오염시키지 않는다(usage_ingest 등 후속 파서가 이 로그를 읽는다).
  IMPL_RC=0
  exec 9>&1
  ( cd "$IMPL_WORKDIR" && { apply_seat_env >&9 || exit 97; } && claude -p "$IMPL_PROMPT" \
    --model "$PIPELINE_MODEL_IMPL" \
    --dangerously-skip-permissions \
    --verbose \
    --output-format stream-json \
    ${MAX_TURNS:+--max-turns $MAX_TURNS} ) \
    2>&1 | tee "$CLAUDE_LOG" || IMPL_RC="${PIPESTATUS[0]:-1}"
  exec 9>&-
  # 97 = 시트 STRICT 스킵(구현 미실행) → 빈 브랜치를 완료로 소진시키지 않고 실패 경로로.
  if [ "$IMPL_RC" = "97" ]; then
    seat_strict_skip "STEP B 구현"
    continue
  elif [ "$IMPL_RC" != "0" ]; then
    log "WARN: Claude 실행 비정상 종료"
  fi

  log "Claude 구현 완료: $TITLE"

  # ── [CE-367] 실행 모델 검증 — 의도한 티어로 돌았는지 확인한다 ──
  # 별칭 오해석(sonnet→opus-4-8)은 **조용히** 일어났다. 원가가 배로 뛰는데 로그에 흔적이
  # 없었다. 이제 세션 init 이벤트의 실제 model 을 읽어 의도와 다르면 남긴다(비차단 — 관측만).
  ACTUAL_MODEL="$(python3 - "$CLAUDE_LOG" <<'PY' 2>/dev/null || true
import json, sys
try:
    with open(sys.argv[1], encoding="utf-8", errors="replace") as f:
        for line in f:
            if '"subtype":"init"' in line:
                print(json.loads(line).get("model") or "")
                break
except OSError:
    pass
PY
)"
  if [ -n "$ACTUAL_MODEL" ] && [ "$ACTUAL_MODEL" != "$PIPELINE_MODEL_IMPL" ]; then
    log "WARN: 실행 모델 불일치 — 의도=${PIPELINE_MODEL_IMPL} 실제=${ACTUAL_MODEL} (원가·한도 소진에 직접 영향, CE-367)"
    record_metric "$METRIC_RUN_ID" "model_mismatch" \
      "{\"intended\": \"$PIPELINE_MODEL_IMPL\", \"actual\": \"$ACTUAL_MODEL\"}"
  elif [ -n "$ACTUAL_MODEL" ]; then
    log "실행 모델 확인: ${ACTUAL_MODEL}"
  fi

  # ── [Tier 3a 메트릭] impl_done — 구현 소요(초)·워크디렉터리 종류 관측(비차단) ──
  M_IMPL_DUR=$(( $(date +%s) - M_IMPL_START ))
  M_IMPL_WD="self"; [ "$IMPL_WORKDIR" != "$PROJECT_DIR" ] && M_IMPL_WD="workspace"
  record_metric "$METRIC_RUN_ID" "impl_done" \
    "{\"duration_s\": $M_IMPL_DUR, \"workdir\": \"$M_IMPL_WD\"}"

  # ── [CE-328] 로컬 배치 사용량 → 서버 원장 인제스트(비차단, opt-in) ──
  # 명시적 opt-in 이중 체크(is_enabled + 비어있지 않음) + 서비스 URL 필수. 미설정=off → 회귀 0.
  # usage_ingest.py 자체가 모든 실패를 삼켜 exit 0 하지만, || true 로 이중 방어(파이프라인 불사).
  if is_enabled "FLOWOPS_USAGE_INGEST" 2>/dev/null && [ -n "${FLOWOPS_USAGE_INGEST:-}" ] \
    && [ -n "${FLOWOPS_GOVERNANCE_SERVICE_URL:-}" ]; then
    # ── [CE-362] 프로젝트 축 연결 ──
    # usage_ingest.py 는 CLICKEYE_PROJECT_ID env 로 프로젝트 축을 받는데 파이프라인이 그것을
    # 넘기지 않아, 인제스트를 켜도 project_id 가 NULL 로 들어갔다 → "프로젝트당 얼마 썼나" 를
    # 집계할 수 없다. 수락 시 생성된 Project id 는 이미 워크스페이스 원장에 있으므로
    # (machine/projects 폴링 산출물) 서버를 다시 조회하지 않고 원장에서 읽는다.
    # self-repo 이슈는 프로젝트가 없으므로 빈 값 = 기존과 동일(축 없이 기록).
    # [CE-363] 이미 이터레이션 시작에서 해석한 ITER_PROJECT_ID 를 재사용(중복 해석 제거).
    USAGE_PROJECT_ID="${ITER_PROJECT_ID:-}"
    CLICKEYE_PROJECT_ID="$USAGE_PROJECT_ID" python3 scripts/usage_ingest.py \
      --log "$CLAUDE_LOG" \
      --request-kind local_batch_implement \
      --task-id "$ISSUE_KEY" 2>>"$CLAUDE_LOG" || true
    log "사용량 인제스트 시도(비차단): ${ISSUE_KEY} project=${USAGE_PROJECT_ID:-(없음)}"
  fi

  # ── [R4 · 고객 레포 딜리버리] 구현 커밋 존재 확인 (CE-347) ──
  # 워크스페이스 경로에는 "빈 브랜치를 머지 성공으로 소진"하는 완충이 없다. 에이전트가 고객
  # clone 태스크 브랜치에 커밋을 남기지 않았으면 여기서 실패로 확정한다(자기레포 경로 무변경).
  if [ "$WS_DELIVERY" = true ]; then
    # [G4] detached HEAD 에서 구현이 이뤄지면 커밋이 태스크 브랜치 ref 에 얹히지 않는다 →
    # push 는 성공하지만 산출물은 나가지 않는다(허상 재발). 커밋을 회수 브랜치로 보존하고
    # 실패 처리한다(fail-closed).
    if ! impl_git symbolic-ref -q HEAD >/dev/null 2>&1; then
      WS_RESCUE="rescue/${ISSUE_KEY}-$(date '+%Y%m%d_%H%M%S')"
      impl_git branch "$WS_RESCUE" HEAD 2>>"$WS_GIT_LOG" || true
      ws_delivery_fail "구현이 detached HEAD 에서 이뤄져 인테이크 브랜치 ${WS_BRANCH} 에 얹히지 않음 — 회수 브랜치 ${WS_RESCUE} 로 보존"
      continue
    fi
    # [G1] 이번 런 델타로 판정 — 잔여 커밋이 있는 재사용 브랜치를 빈손 런이 소진하지 못하게.
    WS_COMMITS="$(impl_git rev-list --count "${WS_TIP_BEFORE}..HEAD" 2>>"$WS_GIT_LOG" || echo 0)"
    WS_COMMITS="${WS_COMMITS//[^0-9]/}"   # 비수치 출력(오류 문자열)은 0 으로 수축 = 실패 처리
    if [ "${WS_COMMITS:-0}" -le 0 ]; then
      # ── [CE-362 A] 무변경 완료(no-op) 처분 ──
      # 스펙이 의도적으로 "파일 변경 없음" 을 지시하는 티켓이 있다(설계·계약 확정형).
      # 실측(CE-359): 정제 스펙이 "실제 파일 작성은 제외 범위" 라 명시해 에이전트가 사실조사만
      # 하고 <promise>DONE</promise> 로 정상 종료했는데, 커밋 0 이라는 이유로 실패·Backlog 가
      # 됐다 — 에이전트는 스펙을 지켰고 파이프라인이 오판한 것이다.
      #
      # 완화의 안전핀은 ③ 워킹트리 클린이다. "파일을 만들었는데 커밋만 못 한" 진짜 실패는
      # 워킹트리가 더럽기 때문에 여기 걸리지 않고 아래 실패 경로로 간다.
      WS_DIRTY="$(impl_git status --porcelain 2>>"$WS_GIT_LOG" || echo "unknown")"
      if [ "${IMPL_RC:-1}" = "0" ] \
        && grep -q "promise>DONE<" "$CLAUDE_LOG" 2>/dev/null \
        && [ -z "$WS_DIRTY" ]; then
        log "워크스페이스 딜리버리: 무변경 완료(no-op) — 에이전트 DONE + 워킹트리 클린 + 커밋 0"
        log "  스펙이 파일 변경을 요구하지 않는 티켓으로 판단해 실패로 처리하지 않는다(${WS_BRANCH} 미push)"
        python3 scripts/linear_tracker.py update --issue-id "$ISSUE_ID" --status "Done" 2>/dev/null || true
        # 사람이 사후 감사할 수 있게 근거를 티켓에 남긴다 — 자동 판정만으로는 "게으른 DONE" 과
        # "정당한 no-op" 을 구분할 수 없다.
        python3 - "$ISSUE_ID" "$WS_BRANCH" <<'PY' 2>/dev/null || true
import sys
sys.path.insert(0, "scripts")
from linear_client import get_env, linear_request
issue_id, branch = sys.argv[1], sys.argv[2]
api_key, _ = get_env()
body = (
    "**무변경 완료(no-op)로 처분됨**\n\n"
    "무인 파이프라인이 이 티켓을 실행했고 에이전트가 `<promise>DONE</promise>` 로 정상 "
    "종료했으나, 대상 저장소에 커밋이 생기지 않았습니다(워킹트리도 클린).\n\n"
    "정제 스펙이 파일 변경을 요구하지 않는 티켓(설계·계약 확정형)으로 판단해 실패가 아닌 "
    "완료로 처분했습니다. 태스크 브랜치는 push 하지 않았습니다(보낼 변경이 없음).\n\n"
    f"- 태스크 브랜치: `{branch}` (미push)\n"
    "- 산출물이 있어야 할 티켓이었다면 이 처분이 오판입니다 — 스펙을 조정해 재점화하세요."
)
linear_request(
    api_key,
    "mutation($issueId:String!,$body:String!){commentCreate(input:{issueId:$issueId,body:$body}){comment{id}}}",
    {"issueId": issue_id, "body": body},
)
PY
        log "Linear 상태: Done (무변경 완료)"
        continue
      fi
      ws_delivery_fail "이번 런 구현 커밋 없음 (${WS_TIP_BEFORE}..HEAD, 브랜치 ${WS_BRANCH})$([ -n "$WS_DIRTY" ] && echo ' — 워킹트리에 미커밋 변경 존재(커밋 누락)')"
      continue
    fi
    # [G6] 하네스 산출물 오염 가드 — ralph PROMPT 가 에이전트에게 fix_plan 갱신·커밋을 지시하므로
    # WS cwd 에서 ClickEye 운영 파일이 고객 브랜치에 커밋될 수 있다. 발견 시 fail-closed.
    WS_DELTA_FILES="$(impl_git diff --name-only "${WS_TIP_BEFORE}..HEAD" 2>>"$WS_GIT_LOG" || true)"
    WS_POLLUTED="$(printf '%s\n' "$WS_DELTA_FILES" \
      | grep -E '(^|/)(\.ralph/|\.claude/|fix_plan\.md$|LoadMap_v3\.md$|TODO\.md$)' || true)"
    if [ -n "$WS_POLLUTED" ]; then
      ws_delivery_fail "하네스 산출물이 고객 브랜치에 커밋됨 — 오염 차단: $(printf '%s' "$WS_POLLUTED" | head -n5 | tr '\n' ' ')"
      continue
    fi
    log "워크스페이스 딜리버리: 이번 런 구현 커밋 ${WS_COMMITS}건 확인 (${WS_BRANCH})"
  fi

  # Claude 실행 후 TASK.md 자동 생성 (없으면)
  if [ ! -f .ralph/TASK.md ]; then
    log "TASK.md 자동 생성 (Claude 실행 결과 기반)"
    {
      echo "# TASK — ${TITLE}"
      echo ""
      echo "## 변경 파일"
      # [R5] 워크스페이스 경로는 고객 clone 의 기본 브랜치 기준 diff 로 채운다.
      if [ "$WS_DELIVERY" = true ]; then
        impl_git diff --name-only "$CUST_BASE" 2>/dev/null | while read -r f; do echo "- $f"; done
      else
        safe_git diff --name-only main 2>/dev/null | while read -r f; do echo "- $f"; done
      fi
      echo ""
      echo "## 구현 내용"
      echo "fix_plan.md 기반 자율 구현 완료"
      echo ""
      echo "## 테스트 결과"
      echo "(파이프라인 검증 참조)"
      echo ""
      echo "## 남은 이슈"
      grep -E "^\- \[[ !]\]" .ralph/fix_plan.md 2>/dev/null || echo "없음"
    } > .ralph/TASK.md
  fi

  # ── [STEP C] Codex QA 리뷰 → REVIEW.md ──
  if is_enabled "FLOWOPS_CODEX_REVIEW" 2>/dev/null; then
    log "── Codex QA 리뷰 시작 ──"
    QA_EXIT=0
    bash scripts/run_codex_review.sh 2>&1 || QA_EXIT=$?
    [ "$QA_EXIT" -ne 0 ] && log "WARN: Codex QA 리뷰 실패"
    log "Codex QA 리뷰 완료"
    # [Tier 3a 메트릭] qa_done — 리뷰 실행 여부·exit 관측(비차단)
    record_metric "$METRIC_RUN_ID" "qa_done" "{\"ran\": true, \"exit\": $QA_EXIT}"
  else
    log "SKIP: Codex QA 리뷰 비활성화 (FLOWOPS_CODEX_REVIEW=false)"
    record_metric "$METRIC_RUN_ID" "qa_done" "{\"ran\": false}"
  fi

  # Linear 결과 보고
  # [G3] 워크스페이스 딜리버리는 건너뛴다 — linear_reporter 는 **PRIMARY** 의 fix_plan 과 git
  # 요약을 읽으므로 WS 모드에선 항상 incomplete→Backlog 로 되돌리고 ClickEye 커밋 요약을
  # 코멘트해 티켓을 오도한다. WS 경로의 처분은 push 성공 시 명시 Done, 실패 시
  # ws_delivery_fail/handle_task_failure 가 확정한다.
  if [ "$WS_DELIVERY" = true ]; then
    log "워크스페이스 딜리버리: linear_reporter 생략(PRIMARY 기준 보고·오도 코멘트 방지)"
  else
    python3 scripts/linear_reporter.py --task-id "$ISSUE_KEY" 2>&1 || {
      log "WARN: Linear 결과 보고 실패"
    }
  fi

  # ── [거버넌스 게이트] 머지 직전 권위 검증+위험분류 (SSOT: scripts/pre_merge_gate.py) ──
  # direct-merge + push origin main 이 유일한 비보호 경로 → 여기가 권위 게이트. CI(ci.yml)는 미러.
  GATE_DECISION="direct"
  GATE_TIER="LOW"
  MERGED_DIRECT=false
  if is_enabled "FLOWOPS_GOVERNANCE" 2>/dev/null; then
    GATE_RC=0
    GATE_JSON=""

    # ── 거버넌스 판정 획득: HTTP 컨트롤 플레인 경유(선택) → 실패 시 로컬 shim 폴백 ──
    # FLOWOPS_GOVERNANCE_SERVICE_URL 이 설정된 경우에만 HTTP 서비스를 경유한다.
    # 미설정(빈 값)이면 이 블록 전체를 건너뛰어 기존 로컬 shim 경로 그대로 → 회귀 0.
    # [R7] 워크스페이스 딜리버리는 HTTP 서비스 경로를 타지 않는다 — 서비스는 ClickEye
    # 레포(base=main)와 ClickEye 정책을 전제하므로 남의 레포 판정에 쓸 수 없다.
    # 토글 off/자기레포에서는 조건이 참이라 기존 경로 그대로(회귀 0).
    if [ "$WS_DELIVERY" != true ] && [ -n "${FLOWOPS_GOVERNANCE_SERVICE_URL:-}" ]; then
      # 변경 파일 목록 계산(원격 호출자는 git 접근 불가 → 명시 전달). 커널과 동일 three-dot(merge-base) 사용.
      GATE_FILES=$(safe_git diff --name-only "main...${BRANCH}" 2>>"$CLAUDE_LOG" || true)
      # JSON 페이로드 구성(jq 우선, 없으면 python3 로 안전 직렬화)
      # linear_team_id(P1.6): 서버가 team→project 역매핑해 KB 인제스트에만 사용(하위호환 — 빈 값이면 null).
      if command -v jq >/dev/null 2>&1; then
        GATE_PAYLOAD=$(printf '%s\n' "$GATE_FILES" | jq -R . | jq -s --arg h "$BRANCH" --arg t "${LINEAR_TEAM_ID:-}" '{base:"main", head:$h, files:[.[]|select(.!="")], plan_text:null, linear_team_id:(if $t=="" then null else $t end)}' 2>>"$CLAUDE_LOG" || echo '')
      else
        GATE_PAYLOAD=$(GATE_BRANCH="$BRANCH" GATE_FILES="$GATE_FILES" GATE_TEAM="${LINEAR_TEAM_ID:-}" python3 -c 'import os,json;fs=[f for f in os.environ.get("GATE_FILES","").splitlines() if f];print(json.dumps({"base":"main","head":os.environ["GATE_BRANCH"],"files":fs,"plan_text":None,"linear_team_id":os.environ.get("GATE_TEAM") or None}))' 2>>"$CLAUDE_LOG" || echo '')
      fi
      GATE_URL="${FLOWOPS_GOVERNANCE_SERVICE_URL%/}/api/v1/governance/evaluate"
      # curl 실패(연결/타임아웃)가 set -e 로 스크립트를 죽이지 않게 rc 캡처. 응답 마지막 줄=HTTP 코드.
      GATE_HTTP_RESP=$(curl -sS -m "${FLOWOPS_GOVERNANCE_SERVICE_TIMEOUT:-10}" -w $'\n%{http_code}' \
        -X POST "$GATE_URL" \
        -H "Content-Type: application/json" \
        -H "X-Governance-Token: ${GOVERNANCE_SERVICE_TOKEN:-}" \
        -d "$GATE_PAYLOAD" 2>>"$CLAUDE_LOG") || GATE_HTTP_RESP=""
      GATE_HTTP_CODE=$(printf '%s' "$GATE_HTTP_RESP" | tail -n1)
      GATE_HTTP_BODY=$(printf '%s' "$GATE_HTTP_RESP" | sed '$d')
      if [ "$GATE_HTTP_CODE" = "200" ] && [ -n "$GATE_HTTP_BODY" ]; then
        GATE_JSON="$GATE_HTTP_BODY"
        log "거버넌스 게이트: HTTP 서비스 경유 성공 (url=$GATE_URL code=200)"
      else
        # 권위 게이트는 조용히 skip 금지 → WARN 후 로컬 shim 으로 판정 계속.
        log "WARN: 거버넌스 HTTP 서비스 호출 실패 (url=$GATE_URL code=${GATE_HTTP_CODE:-none}) → 로컬 shim 폴백"
      fi
    fi

    # HTTP 미사용(URL 미설정) 또는 HTTP 실패 → 로컬 shim(SSOT) 으로 판정(권위 게이트 유지).
    if [ -z "$GATE_JSON" ]; then
      if [ "$WS_DELIVERY" = true ]; then
        # [R7] 고객 clone 기준 판정 — ClickEye 계약면·고위험 경로 정책은 남의 레포에
        # 의미가 없으므로 중립 정책을 주입한다(실효 검증은 ticket-ref). block 처리는 동일.
        # [CE-369] 고객 브랜치는 인테이크 단위(WS_BRANCH)라 이슈 키를 담지 않는다. 게이트의
        # ticket-ref 는 head 이름에서 `^[A-Z0-9]+-\d+$` 키를 뽑으므로 head 로는 **티켓 브랜치
        # 이름**(BRANCH)을 넘기고, 변경 파일은 실제 고객 브랜치 델타를 --diff-files 로 준다.
        # 둘을 섞지 않으면 하나가 반드시 틀린다(키 추출 실패 또는 존재하지 않는 ref 조회).
        GATE_WS_FILES=$(impl_git diff --name-only "${CUST_BASE}...${WS_BRANCH}" 2>>"$WS_GIT_LOG" || true)
        GATE_JSON=$(python3 scripts/pre_merge_gate.py \
          --project-dir "$IMPL_WORKDIR" --base "$CUST_BASE" --head "$BRANCH" \
          --diff-files "$GATE_WS_FILES" \
          --policy "$WS_POLICY" \
          --json 2>>"$CLAUDE_LOG") || GATE_RC=$?
      else
        GATE_JSON=$(python3 scripts/pre_merge_gate.py --base main --head "$BRANCH" --json 2>>"$CLAUDE_LOG") || GATE_RC=$?
      fi
    fi

    GATE_DECISION=$(printf '%s' "$GATE_JSON" | python3 -c "import sys,json;print(json.load(sys.stdin).get('merge_decision','block'))" 2>/dev/null || echo "block")
    GATE_TIER=$(printf '%s' "$GATE_JSON" | python3 -c "import sys,json;print(json.load(sys.stdin).get('tier','LOW'))" 2>/dev/null || echo "LOW")
    GATE_FAILS=$(printf '%s' "$GATE_JSON" | python3 -c "import sys,json;print(' / '.join(json.load(sys.stdin).get('failures',[])) or '검증 실패')" 2>/dev/null || echo "게이트 파싱 실패")
    log "거버넌스 게이트: rc=$GATE_RC tier=$GATE_TIER decision=$GATE_DECISION"
    # 트리아지(항목 G) 관측 로깅만 — merge_decision 도메인/판정에는 영향 없음(extra 키 무시).
    GATE_TRIAGE=$(printf '%s' "$GATE_JSON" | python3 -c "import sys,json;print(json.load(sys.stdin).get('triage',''))" 2>/dev/null || echo "")
    [ -n "$GATE_TRIAGE" ] && log "거버넌스 트리아지: band=$GATE_TRIAGE"

    # ── [Tier 3a 메트릭] gate_done — 게이트 판정·위험강등 관측(거버넌스 활성 경로에서만) ──
    M_GATE_DEMOTED=false; [ "$GATE_DECISION" = "pr" ] && M_GATE_DEMOTED=true
    record_metric "$METRIC_RUN_ID" "gate_done" \
      "{\"verdict\": \"$GATE_DECISION\", \"demoted\": $M_GATE_DEMOTED}"

    if [ "$GATE_RC" -eq 2 ] || [ "$GATE_DECISION" = "block" ]; then
      log "ERROR: 거버넌스 검증 실패 → 머지 차단 ($GATE_FAILS)"
      safe_git checkout main 2>/dev/null || true
      if ! handle_task_failure "$ISSUE_KEY" "$ISSUE_ID" "$TASK_MODE" "거버넌스 차단: ${GATE_FAILS}"; then
        python3 scripts/linear_tracker.py update --issue-id "$ISSUE_ID" --status "Backlog" 2>/dev/null || true
      fi
      if is_enabled "FLOWOPS_TELEGRAM" 2>/dev/null; then
        python3 scripts/telegram_notify.py --message "🚫 거버넌스 차단 ${ISSUE_KEY}: ${GATE_FAILS}" 2>/dev/null || true
      fi
      FAILED=$((FAILED + 1))
      # [Tier 3a 메트릭] run_done — 게이트 차단 처분(이 분기는 continue/break 로 종료)
      RUN_OUTCOME="failed"
      record_metric "$METRIC_RUN_ID" "run_done" "{\"outcome\": \"$RUN_OUTCOME\"}"
      rm -rf ".ralph/tasks"
      rm -f "$TASK_MAPPING" .ralph/PLAN.md .ralph/TASK.md .ralph/REVIEW.md ".ralph/refined/${ISSUE_KEY}.md"
      if [ "$ONCE_MODE" = true ]; then
        log "--once 모드: 게이트 차단 후 종료."
        break
      fi
      continue
    fi
  fi

  # PR 생성 또는 직접 머지 (거버넌스 위험강등 우선)
  # [R9~R11/R14] 워크스페이스 딜리버리는 이 체인의 **첫 분기**로 갈라진다: 머지 없음,
  # 태스크 브랜치만 고객 origin 으로 push, ClickEye GitHub 을 겨냥하는 auto_pr_creator 미호출.
  # 고객 기본 브랜치로의 머지는 고객 소유이며 v1 범위 밖이다.
  # 토글 off/자기레포면 WS_DELIVERY=false → 아래 elif 가 원래의 첫 조건 그대로 평가된다.
  if [ "$WS_DELIVERY" = true ]; then
    # [R8] 딜리버리 로그·추적성 승격 입력을 고객 clone 기준으로 채운다.
    # [G10] diff 는 three-dot(merge-base 기준) — 커널의 get_changed_files 와 일치시키고, base 가
    # 전진한 경우 그 전진분이 "이 브랜치의 변경"으로 오기록되는 것을 막는다. 반면 `log` 는
    # three-dot 이 대칭차집합이 되어 base 전용 커밋까지 끌어오므로 two-dot 이 정답이다.
    MERGE_DIFF_STAT=$(impl_git diff --stat "${CUST_BASE}...${WS_BRANCH}" 2>>"$WS_GIT_LOG" || echo "(diff 없음)")
    MERGE_DIFF_FILES=$(impl_git diff --name-only "${CUST_BASE}...${WS_BRANCH}" 2>>"$WS_GIT_LOG" || echo "")
    MERGE_COMMITS=$(impl_git log --oneline "${CUST_BASE}..${WS_BRANCH}" 2>>"$WS_GIT_LOG" || echo "(커밋 없음)")
    MERGE_DIFF_DETAIL=$(impl_git diff "${CUST_BASE}...${WS_BRANCH}" 2>>"$WS_GIT_LOG" || echo "")

    log "워크스페이스 딜리버리: 인테이크 브랜치 push → ${WS_ORIGIN} (${WS_BRANCH})"
    if impl_git push origin "$WS_BRANCH" 2>>"$WS_GIT_LOG"; then
      log "고객 레포 push 성공: ${WS_BRANCH} (기본 브랜치 ${CUST_BASE} 무변경)"
      RUN_OUTCOME="pushed"

      # [G3] 이 시점이 WS 경로의 **유일한 성공 확정 지점** — linear_reporter 를 건너뛴 대신
      # 여기서 명시적으로 Done 으로 옮기고 딜리버리 사실을 코멘트한다(고객 머지는 고객 소유).
      python3 scripts/linear_tracker.py update --issue-id "$ISSUE_ID" --status "Done" 2>>"$WS_GIT_LOG" \
        && log "Linear 상태: Done (고객 레포 push 성공)" \
        || log "WARN: Linear Done 전이 실패 — 수동 확인 필요 (${ISSUE_KEY}, 상세: $WS_GIT_LOG)"
      python3 - "$ISSUE_ID" "$ISSUE_KEY" "$WS_BRANCH" "$CUST_BASE" "$WS_ORIGIN" "$MERGE_DIFF_STAT" <<'PY' 2>/dev/null || true
import sys
sys.path.insert(0, "scripts")
from linear_client import get_env, linear_request
issue_id, key, branch, base, origin, stat = sys.argv[1:7]
api_key, _ = get_env()
body = (
    "🚚 **고객 레포 딜리버리 완료 — 태스크 브랜치 push**\n\n"
    f"- 이슈: {key}\n"
    f"- 고객 원격: `{origin}`\n"
    f"- 브랜치: `{branch}` (base `{base}`)\n"
    "- 머지: **고객 측에서 수행합니다** — 파이프라인은 기본 브랜치를 변경하지 않습니다.\n\n"
    "변경 요약:\n```\n" + stat[:3000] + "\n```"
)
linear_request(
    api_key,
    "mutation($issueId:String!,$body:String!){commentCreate(input:{issueId:$issueId,body:$body}){comment{id}}}",
    {"issueId": issue_id, "body": body},
)
PY
      log "Linear 코멘트 게시(딜리버리 결과)"

      MERGE_LOG_FILE="$PROJECT_DIR/logs/delivery_${ISSUE_KEY}_$(date '+%Y%m%d_%H%M%S').log"
      mkdir -p "$PROJECT_DIR/logs"
      {
        echo "════════════════════════════════════════════════════════════"
        echo "  DELIVERY LOG (고객 레포 태스크 브랜치 push)"
        echo "════════════════════════════════════════════════════════════"
        echo ""
        echo "일시:     $(date '+%Y-%m-%d %H:%M:%S')"
        echo "이슈:     ${ISSUE_KEY}"
        echo "워크스페이스: ${WORKSPACE_KEY:-} ($IMPL_WORKDIR)"
        echo "고객 origin:  ${WS_ORIGIN}"
        echo "브랜치:   ${BRANCH} (base ${CUST_BASE} — 머지하지 않음)"
        echo "제목:     ${TITLE}"
        echo ""
        echo "────────────────────────────────────────────────────────────"
        echo "  커밋 목록"
        echo "────────────────────────────────────────────────────────────"
        echo "$MERGE_COMMITS"
        echo ""
        echo "────────────────────────────────────────────────────────────"
        echo "  변경 파일"
        echo "────────────────────────────────────────────────────────────"
        echo "$MERGE_DIFF_STAT"
        echo ""
        echo "────────────────────────────────────────────────────────────"
        echo "  상세 변경 내용 (diff)"
        echo "────────────────────────────────────────────────────────────"
        echo "$MERGE_DIFF_DETAIL"
        echo ""
        echo "════════════════════════════════════════════════════════════"
      } > "$MERGE_LOG_FILE"
      log "딜리버리 로그: $MERGE_LOG_FILE"
    else
      # [R11] push 거부(권한·보호 브랜치·비패스트포워드) → 로컬 브랜치를 **보존**한 채 실패.
      # branch -d / push --delete 를 절대 실행하지 않는다(구현 결과 유실 0). linear_reporter
      # 가 앞서 올린 Done 은 handle_task_failure 의 상태 복귀로 사후 정정된다.
      log "WARN: 고객 레포 push 거부 — 로컬 브랜치 보존: ${BRANCH} ($IMPL_WORKDIR)"
      ws_delivery_fail "고객 레포 push 거부: ${BRANCH}"
      continue
    fi
  elif [ "$GATE_DECISION" = "pr" ]; then
    log "위험분류 ${GATE_TIER} → 직접머지 금지, 기존 PR 경로로 강등(사람 머지 게이트)"
    RUN_OUTCOME="demoted"
    python3 scripts/auto_pr_creator.py --branch "$BRANCH" 2>&1 || {
      log "WARN: PR 생성 실패"
    }
    safe_git checkout main 2>/dev/null || true
  elif is_enabled "FLOWOPS_AUTO_MERGE" 2>/dev/null; then
    log "AUTO_MERGE 활성화: 직접 머지 수행"

    # 머지 전 diff 정보 수집
    MERGE_DIFF_STAT=$(safe_git diff --stat "main..${BRANCH}" 2>/dev/null || echo "(diff 없음)")
    MERGE_DIFF_FILES=$(safe_git diff --name-only "main..${BRANCH}" 2>/dev/null || echo "")
    MERGE_COMMITS=$(safe_git log --oneline "main..${BRANCH}" 2>/dev/null || echo "(커밋 없음)")
    MERGE_DIFF_DETAIL=$(safe_git diff "main..${BRANCH}" 2>/dev/null || echo "")

    # 메인으로 전환 후 머지
    safe_git checkout main 2>/dev/null || true
    if safe_git merge "$BRANCH" --no-ff -m "Merge branch '${BRANCH}': ${TITLE}" 2>/dev/null; then
      log "머지 성공: ${BRANCH} → main"
      MERGED_DIRECT=true
      RUN_OUTCOME="merged"

      # 머지 로그 생성
      MERGE_LOG_FILE="$PROJECT_DIR/logs/merge_$(date '+%Y%m%d_%H%M%S').log"
      mkdir -p "$PROJECT_DIR/logs"
      {
        echo "════════════════════════════════════════════════════════════"
        echo "  MERGE LOG"
        echo "════════════════════════════════════════════════════════════"
        echo ""
        echo "일시:     $(date '+%Y-%m-%d %H:%M:%S')"
        echo "이슈:     ${ISSUE_KEY}"
        echo "브랜치:   ${BRANCH} → main"
        echo "제목:     ${TITLE}"
        echo ""
        echo "────────────────────────────────────────────────────────────"
        echo "  커밋 목록"
        echo "────────────────────────────────────────────────────────────"
        echo "$MERGE_COMMITS"
        echo ""
        echo "────────────────────────────────────────────────────────────"
        echo "  변경 파일"
        echo "────────────────────────────────────────────────────────────"
        echo "$MERGE_DIFF_STAT"
        echo ""
        echo "────────────────────────────────────────────────────────────"
        echo "  상세 변경 내용 (diff)"
        echo "────────────────────────────────────────────────────────────"
        echo "$MERGE_DIFF_DETAIL"
        echo ""
        echo "════════════════════════════════════════════════════════════"
      } > "$MERGE_LOG_FILE"
      log "머지 로그: $MERGE_LOG_FILE"

      # push
      safe_git push origin main 2>/dev/null || log "WARN: push 실패"

      # 머지된 브랜치 정리
      safe_git branch -d "$BRANCH" 2>/dev/null || true
      safe_git push origin --delete "$BRANCH" 2>/dev/null || true

      # ── [P1.6] LLM 머신 인제스트: 머지 결과를 clickeye-llm KB 로 전송(비차단) ──
      # 명시적 opt-in(FLOWOPS_TEMPORAL 패턴): 미설정=off. 서버가 team→project 역매핑.
      # 실패해도 파이프라인 절대 안 죽음(|| true) — 202/skip/오류 모두 무시.
      if is_enabled "FLOWOPS_LLM_INGEST" 2>/dev/null && [ -n "${FLOWOPS_LLM_INGEST:-}" ] \
        && [ -n "${FLOWOPS_GOVERNANCE_SERVICE_URL:-}" ]; then
        INGEST_URL="${FLOWOPS_GOVERNANCE_SERVICE_URL%/}/api/v1/llm/ingest/pipeline"
        INGEST_PAYLOAD=$(INGEST_TEAM="${LINEAR_TEAM_ID:-}" INGEST_KEY="$ISSUE_KEY" INGEST_TITLE="$TITLE" INGEST_TIER="${GATE_TIER:-LOW}" INGEST_STAT="$MERGE_DIFF_STAT" python3 -c 'import os,json;print(json.dumps({"team_id":os.environ.get("INGEST_TEAM") or None,"source_id":"pipeline:"+os.environ["INGEST_KEY"],"text":"[파이프라인] "+os.environ["INGEST_KEY"]+" "+os.environ["INGEST_TITLE"]+" — 머지 성공(main 직접 머지, tier="+os.environ.get("INGEST_TIER","LOW")+")\n"+os.environ.get("INGEST_STAT",""),"metadata":{"kind":"pipeline","issue_key":os.environ["INGEST_KEY"]}}))' 2>>"$CLAUDE_LOG" || echo '')
        if [ -n "$INGEST_PAYLOAD" ]; then
          curl -sS -m "${FLOWOPS_GOVERNANCE_SERVICE_TIMEOUT:-10}" -X POST "$INGEST_URL" \
            -H "Content-Type: application/json" \
            -H "X-Governance-Token: ${GOVERNANCE_SERVICE_TOKEN:-}" \
            -d "$INGEST_PAYLOAD" >/dev/null 2>>"$CLAUDE_LOG" || true
          log "LLM 머신 인제스트 전송(비차단): pipeline:${ISSUE_KEY}"
        fi
      fi
    else
      log "ERROR: 머지 실패. PR 생성으로 대체합니다."
      RUN_OUTCOME="pr"
      safe_git merge --abort 2>/dev/null || true
      python3 scripts/auto_pr_creator.py --branch "$BRANCH" 2>&1 || {
        log "WARN: PR 생성 실패"
      }
      safe_git checkout main 2>/dev/null || true
    fi
  else
    # AUTO_MERGE 비활성: PR만 생성
    RUN_OUTCOME="pr"
    python3 scripts/auto_pr_creator.py --branch "$BRANCH" --auto-merge 2>&1 || {
      log "WARN: PR 생성 실패"
    }
    safe_git checkout main 2>/dev/null || true
  fi

  # ── [추적성 승격] cleanup(rm) 직전, 이미 생성된 산출물을 per-ticket 영속 위치로 아카이브 ──
  # direct-merge(LOW) 경로에서만 의미 — HIGH는 PR로 강등되어 REVIEW.md가 PR 본문에 보존됨.
  # 재생성 없음(promote only). refined 원본은 Linear 코멘트, diff는 logs/merge_*.log 에 이미 존재.
  # 고복잡도 대용 프록시(변경파일 수/diff 라인)로 한정. FLOWOPS_GOVERNANCE_PROMOTE 토글.
  # [R8] 워크스페이스 딜리버리(push 성공)도 direct-merge 와 같은 추적성 대상이다 — 고객
  # 레포에는 PR 본문이 없으므로 REVIEW/refined 를 여기서만 영속화할 수 있다.
  if is_enabled "FLOWOPS_GOVERNANCE_PROMOTE" 2>/dev/null \
    && { [ "${MERGED_DIRECT:-false}" = true ] || [ "${RUN_OUTCOME:-}" = "pushed" ]; }; then
    PROMOTE_FILES=$(printf '%s\n' "$MERGE_DIFF_FILES" | grep -c . 2>/dev/null || echo 0)
    PROMOTE_LINES=$(printf '%s\n' "$MERGE_DIFF_DETAIL" | wc -l | tr -d ' ')
    if [ "$PROMOTE_FILES" -ge "${FLOWOPS_PROMOTE_MIN_FILES:-10}" ] || [ "$PROMOTE_LINES" -ge "${FLOWOPS_PROMOTE_MIN_LINES:-400}" ]; then
      ARCH_DIR="logs/governance/${ISSUE_KEY}"
      mkdir -p "$ARCH_DIR"
      [ -f .ralph/REVIEW.md ] && cp .ralph/REVIEW.md "$ARCH_DIR/REVIEW.md"
      [ -f ".ralph/refined/${ISSUE_KEY}.md" ] && cp ".ralph/refined/${ISSUE_KEY}.md" "$ARCH_DIR/refined.md"
      {
        echo "issue=${ISSUE_KEY}"
        echo "title=${TITLE}"
        echo "tier=${GATE_TIER}"
        echo "merge_log=${MERGE_LOG_FILE:-}"
        echo "changed_files=${PROMOTE_FILES}"
        echo "diff_lines=${PROMOTE_LINES}"
        echo "archived_at=$(date '+%Y-%m-%d %H:%M:%S')"
      } > "$ARCH_DIR/manifest.txt"
      log "추적성 승격: $ARCH_DIR (files=$PROMOTE_FILES lines=$PROMOTE_LINES)"
    fi
  fi

  # 임시 파일 정리
  rm -rf ".ralph/tasks"
  rm -f "$TASK_MAPPING"
  rm -f .ralph/PLAN.md .ralph/TASK.md .ralph/REVIEW.md
  rm -f ".ralph/refined/${ISSUE_KEY}.md"

  # [P1 완주] 성공 시 실패 이력 정리 — 다음 실패는 1회차부터(누적 이월 금지)
  if is_completion_enabled; then
    python3 scripts/retry_ledger.py clear --issue "$ISSUE_KEY" 2>/dev/null || true
  fi

  log "태스크 완료: $TITLE"

  # ── [Tier 3a 메트릭] run_done — 최종 처분(merged/pr/demoted; 미판별=unknown) ──
  # 게이트 차단(failed) 분기는 상단에서 이미 기록 후 continue 했다(여기 도달 안 함).
  record_metric "$METRIC_RUN_ID" "run_done" "{\"outcome\": \"$RUN_OUTCOME\"}"

  # 완료 이슈 기록
  if [ -n "$COMPLETED_ISSUES" ]; then
    COMPLETED_ISSUES="${COMPLETED_ISSUES}, ${ISSUE_KEY}"
  else
    COMPLETED_ISSUES="${ISSUE_KEY}"
  fi

  # DayQueued 모드: 태스크별 즉시 PR 알림
  if [ "$TASK_MODE" = "day" ] && is_enabled "FLOWOPS_TELEGRAM" 2>/dev/null; then
    # [G13] WS 딜리버리에는 PR 이 없다 — "PR을 머지해주세요" 는 오안내이므로 문구를 분기한다.
    if [ "$WS_DELIVERY" = true ]; then
      python3 scripts/telegram_notify.py --message \
        "✅ 작업완료 ${ISSUE_KEY} — ${TITLE}
고객 레포에 브랜치 push 완료 — 고객 측 머지 필요: ${BRANCH}" 2>/dev/null || true
    else
      python3 scripts/telegram_notify.py --message \
        "✅ 작업완료 ${ISSUE_KEY} — ${TITLE}
PR을 머지해주세요.
🔗 브랜치: ${BRANCH}" 2>/dev/null || true
    fi
  fi

  # --once 모드면 1개만 처리 후 종료
  if [ "$ONCE_MODE" = true ]; then
    log "--once 모드: 1개 태스크 완료 후 종료."
    break
  fi

  log "다음 DayQueued/NightQueued 이슈로 진행..."
done

# ── 실패 이슈 Backlog 이동 ──
# [P1 완주] 토글 on 이면 개별 실패 처리(재시도 복귀/터미널)가 이미 상태를 정했으므로
# 일괄 Backlog 이동을 건너뛴다 — 여기서 옮기면 Queued 복귀가 무효화된다.
if ! is_completion_enabled && [ "$FAILED" -gt 0 ] && [ -f "$TASK_MAPPING" ]; then
  log "실패 ${FAILED}건 → Linear Backlog 이동"
  python3 -c "
import json, subprocess, sys
sys.path.insert(0, 'scripts')
with open('$TASK_MAPPING') as f:
    m = json.load(f)
for title, meta in m.items():
    issue_id = meta.get('issue_id', '')
    identifier = meta.get('identifier', '')
    if issue_id:
        subprocess.run(['python3', 'scripts/linear_tracker.py', 'update', '--issue-id', issue_id, '--status', 'Backlog'], capture_output=True)
        print(f'  {identifier} → Backlog')
" 2>/dev/null || log "WARN: Backlog 이동 실패"
fi

# ── Telegram 완료 보고 ──
log ""
log "══════════════════════════════════════"
log "  파이프라인 결과: 완료 ${COMPLETED}건, 실패 ${FAILED}건"
log "══════════════════════════════════════"

# ── [P1 완주] 정지(HALT) 판정 — 터미널 실패가 있으면 "완료"가 아니라 정지로 보고 ──
if is_completion_enabled; then
  HALT_JSON=$(python3 scripts/retry_ledger.py status --json 2>/dev/null || echo '{}')
  HALT_COUNT=$(printf '%s' "$HALT_JSON" | python3 -c "import sys,json;print(len(json.load(sys.stdin).get('terminal',{})))" 2>/dev/null || echo 0)
  if [ "${HALT_COUNT:-0}" -gt 0 ]; then
    HALT_LINES=$(printf '%s' "$HALT_JSON" | python3 -c "
import sys, json
t = json.load(sys.stdin).get('terminal', {})
for k, v in t.items():
    print(f\"- {k}: {v.get('attempts','?')}회 실패, 사유: {v.get('last_reason','?')}\")
" 2>/dev/null || echo "(요약 실패)")
    log "🛑 정지(HALT): 재시도 한도 소진 ${HALT_COUNT}건 — 사람 개입 필요"
    log "$HALT_LINES"
    if is_enabled "FLOWOPS_TELEGRAM" 2>/dev/null; then
      # Telegram 마크다운 엔티티 파싱 400 방지 — 평문(백틱·별표 금지)으로 보낸다
      python3 scripts/telegram_notify.py --message "🛑 파이프라인 정지(HALT) — 재시도 한도 소진 ${HALT_COUNT}건, 사람 개입 필요
${HALT_LINES}" 2>/dev/null || true
    fi
  fi
fi

# 처리된 작업이 있을 때만 Telegram 알림 발송
if [ $((COMPLETED + FAILED)) -gt 0 ] && is_enabled "FLOWOPS_TELEGRAM" 2>/dev/null; then
  ITER_COUNT=$(cat .ralph/.iteration_count 2>/dev/null || echo "N/A")
  python3 scripts/telegram_notify.py \
    --pipeline-report --iterations "$ITER_COUNT" 2>/dev/null || true

  # NightQueued 모드: 모든 태스크 완료 후 일괄 PR 알림
  if [ "$TASK_MODE" = "night" ] && [ -n "$COMPLETED_ISSUES" ] && [ "$COMPLETED" -gt 0 ]; then
    python3 scripts/telegram_notify.py --message \
      "🌙 야간 자동화 완료
${COMPLETED_ISSUES} — 모든 작업이 완료되었습니다.
순차적으로 PR을 머지해주세요." 2>/dev/null || true
  fi
fi
