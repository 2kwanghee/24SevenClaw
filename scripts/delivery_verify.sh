#!/usr/bin/env bash
# delivery_verify.sh — 딜리버리 정합성 게이트 로컬 배치 (다프로젝트화 P7).
#
# 체인 ⑤·⑥: 발급 티켓 전량 완주 → 프로젝트 통합 게이트 → 최종 상태(verified) 확정
# → 서비스 #2 콜백. refine/issue 배치와 동일 규약(opt-in · 하드캡 · --dry-run).
#
# 흐름:
#   1) GET /api/v1/intake/verify/pending?limit=$MAX_ITEMS  (X-Governance-Token)
#      — 응답에 발급 원장(tickets) 포함
#   2) 각 건: delivery_verifier.py 실행 → exit 코드로 분기
#        0 (verified)    → POST /intake/{id}/verified {passed:true, report}
#        4 (gate_failed) → POST /intake/{id}/verified {passed:false, report}
#        3 (미완주)       → skip — 다음 주기 재확인 (상태 불변)
#        5 (게이트 부재)  → 관측 로그만 — verified 전이 금지(통과 위장 방지)
#        2 (입력 오류)    → skip + WARN
#   3) 건별 실패는 로그 후 계속. 말미 요약.
#
# dry-run: verifier --check-only(Linear 읽기 전용 완주 관측)만 수행, 게이트 미실행 ·
#          서버 상태 불변(POST 없음).
#
# 게이트 명령 소스(v1): VERIFY_GATES_FILE(줄당 1명령) — 미설정 시
#   $PROJECT_DIR/.clickeye-gates.txt 가 있으면 사용. 둘 다 없으면 verifier 가
#   exit 5(검증 불가)로 알린다. 제어면 YAML gates 의 프로젝트별 자동 해석은
#   다프로젝트 워크스페이스(P5/P8)와 함께 배선한다 — 그 전까지 워크스페이스는
#   VERIFY_WORKDIR(기본: 이 저장소) 하나다.
#
# 사용법:
#   scripts/delivery_verify.sh --dry-run                      # 완주 관측(권장 시작점)
#   FLOWOPS_DELIVERY_VERIFY=true scripts/delivery_verify.sh   # live (야간 배치)
#
# env: API_URL(기본 http://localhost:8000) · GOVERNANCE_SERVICE_TOKEN · MAX_ITEMS(기본 5)
#      VERIFY_WORKDIR(기본 저장소 루트) · VERIFY_GATES_FILE · GATE_TIMEOUT(기본 1800초)

set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=/dev/null
source "$PROJECT_DIR/scripts/pipeline_config.sh" 2>/dev/null || true

DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

API_URL="${API_URL:-http://localhost:8000}"
MAX_ITEMS="${MAX_ITEMS:-5}"
GATE_TIMEOUT="${GATE_TIMEOUT:-1800}"

# ── [파생형 하네스] 워크스페이스 연동 (CE-339) ──
# 명시 env(VERIFY_WORKDIR·VERIFY_GATES_FILE)는 **항상 우선**한다. 명시가 없을 때만
# 워크스페이스 해석(WORKSPACE_KEY 전용 러너 또는 automap 제목 접두사 → 원장)으로
# 건별 workdir·gates 기본값을 채운다. 미해석(워크스페이스 모드 off/미매핑) 시 현행
# (self-repo · .clickeye-gates.txt) 그대로 = 무회귀.
VERIFY_WORKDIR_EXPLICIT="${VERIFY_WORKDIR:-}"
VERIFY_GATES_EXPLICIT="${VERIFY_GATES_FILE:-}"
WORKSPACE_KEY_INITIAL="${WORKSPACE_KEY:-}"
# 설정 로그·기본값(명시 없으면 self-repo). 실제 건별 값은 루프에서 해석한다.
VERIFY_WORKDIR="${VERIFY_WORKDIR_EXPLICIT:-$PROJECT_DIR}"

resolve_ws_dir() {
  # 워크스페이스 키의 물리 경로를 echo(워크스페이스 모드 활성 + 디렉터리 존재 시에만).
  # 아니면 빈 값 — resolve_impl_workdir(auto_dev_pipeline.sh)과 동일한 게이트.
  local key="$1"
  if is_enabled "FLOWOPS_WORKSPACE" 2>/dev/null && [ -n "${FLOWOPS_WORKSPACE:-}" ] \
    && [ -n "$key" ] && [ -d "$PROJECT_DIR/workspaces/$key" ]; then
    printf '%s\n' "$PROJECT_DIR/workspaces/$key"
  fi
}

log() { echo "[$(date '+%H:%M:%S')] $*"; }
die() { echo "ERROR: $*" >&2; exit 2; }

if ! $DRY_RUN; then
  [[ "${FLOWOPS_DELIVERY_VERIFY:-false}" == "true" ]] \
    || { echo "[SKIP] delivery-verify 비활성(FLOWOPS_DELIVERY_VERIFY!=true). 관측은 --dry-run 사용."; exit 0; }
fi

command -v python3 >/dev/null || die "python3 필요"
command -v curl >/dev/null || die "curl 필요"

# 게이트 파일 해석 — 없으면 빈 값(verifier 가 exit 5 로 "검증 불가"를 알린다).
GATES_FILE="${VERIFY_GATES_FILE:-}"
if [[ -z "$GATES_FILE" && -f "$PROJECT_DIR/.clickeye-gates.txt" ]]; then
  GATES_FILE="$PROJECT_DIR/.clickeye-gates.txt"
fi

AUTH_ARGS=()
[[ -n "${GOVERNANCE_SERVICE_TOKEN:-}" ]] \
  && AUTH_ARGS=(-H "X-Governance-Token: $GOVERNANCE_SERVICE_TOKEN")

MODE="live"; $DRY_RUN && MODE="dry-run"
log "MODE=$MODE · API_URL=$API_URL · workdir=$VERIFY_WORKDIR · gates=${GATES_FILE:-'(없음 — 검증 불가로 관측됨)'}"

WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

# ── 1) 검증 대기 목록 ────────────────────────────────────────────────────────
log "=== 1) 검증 대기 목록 조회 ==="
curl -fsS --max-time 30 "${AUTH_ARGS[@]}" \
  "$API_URL/api/v1/intake/verify/pending?limit=$MAX_ITEMS" > "$WORK_DIR/pending.json" \
  || die "GET verify/pending 실패: $API_URL (FEATURE_INTAKE/토큰 확인)"

N_TOTAL="$(python3 -c "import json,sys;print(len(json.load(open(sys.argv[1]))))" "$WORK_DIR/pending.json")"
log "검증 대기: ${N_TOTAL}건"
[[ "$N_TOTAL" -eq 0 ]] && { log "대기 0건 — 정상 종료."; exit 0; }

python3 - "$WORK_DIR/pending.json" "$WORK_DIR" <<'PYEOF'
import json, sys
items, work = json.load(open(sys.argv[1])), sys.argv[2]
for i, it in enumerate(items, 1):
    json.dump(it, open(f"{work}/item_{i}.json", "w"), ensure_ascii=False)
    json.dump({"tickets": it.get("tickets") or []}, open(f"{work}/ledger_{i}.json", "w"), ensure_ascii=False)
PYEOF

# ── 2) 건별: 완주 판정 → 게이트 → 결과 확정 ─────────────────────────────────
log "=== 2) 건별 검증 ($MODE) ==="
N_VERIFIED=0; N_FAILED=0; N_SKIP=0
for i in $(seq 1 "$N_TOTAL"); do
  ITEM="$WORK_DIR/item_$i.json"
  INTAKE_ID="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['id'])" "$ITEM")"
  TITLE="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['title'])" "$ITEM")"
  log "--- [$i/$N_TOTAL] $INTAKE_ID · $TITLE ---"

  # ── 워크스페이스 건별 해석 (명시 env 우선 → WORKSPACE_KEY/automap → self-repo) ──
  ITEM_KEY="$WORKSPACE_KEY_INITIAL"
  if [ -z "$ITEM_KEY" ] && is_enabled "FLOWOPS_WORKSPACE_AUTOMAP" 2>/dev/null \
    && [ -n "${FLOWOPS_WORKSPACE_AUTOMAP:-}" ]; then
    ITEM_KEY="$(python3 "$PROJECT_DIR/scripts/workspace_map.py" \
      --resolve-title "$TITLE" --output "$PROJECT_DIR/.ralph/workspaces.json" 2>/dev/null || true)"
  fi
  ITEM_WS_DIR="$(resolve_ws_dir "$ITEM_KEY")"
  # workdir: 명시 우선 → 워크스페이스 → self-repo.
  ITEM_WORKDIR="${VERIFY_WORKDIR_EXPLICIT:-${ITEM_WS_DIR:-$PROJECT_DIR}}"
  # gates: 명시 우선 → 워크스페이스 harness-gates.txt → 전역(.clickeye-gates.txt).
  ITEM_GATES="$GATES_FILE"
  if [ -z "$VERIFY_GATES_EXPLICIT" ] && [ -n "$ITEM_WS_DIR" ] \
    && [ -f "$ITEM_WS_DIR/.claude/harness-gates.txt" ]; then
    ITEM_GATES="$ITEM_WS_DIR/.claude/harness-gates.txt"
  fi
  [ -n "$ITEM_WS_DIR" ] && log "  워크스페이스: ${ITEM_KEY} (workdir=$ITEM_WORKDIR gates=${ITEM_GATES:-없음})"

  VERIFIER_ARGS=(--ledger "$WORK_DIR/ledger_$i.json" --workdir "$ITEM_WORKDIR" --gate-timeout "$GATE_TIMEOUT")
  if $DRY_RUN; then
    VERIFIER_ARGS+=(--check-only)   # Linear 읽기 전용 — 게이트·POST 없음
  elif [[ -n "$ITEM_GATES" ]]; then
    VERIFIER_ARGS+=(--gates-file "$ITEM_GATES")
  fi

  RESULT="$WORK_DIR/result_$i.json"
  RC=0
  python3 "$PROJECT_DIR/scripts/delivery_verifier.py" "${VERIFIER_ARGS[@]}" > "$RESULT" || RC=$?

  case "$RC" in
    0|4)
      if $DRY_RUN; then
        log "[DRY-RUN] 완주 관측: $(cat "$RESULT")"
        N_SKIP=$((N_SKIP + 1)); continue
      fi
      PASSED="true"; [[ "$RC" -eq 4 ]] && PASSED="false"
      BODY="$WORK_DIR/body_$i.json"
      python3 - "$RESULT" "$PASSED" > "$BODY" <<'PYEOF'
import json, sys
res = json.load(open(sys.argv[1]))
print(json.dumps({"passed": sys.argv[2] == "true", "report": res["report"] or "(리포트 없음)"},
                 ensure_ascii=False))
PYEOF
      if curl -fsS --max-time 30 "${AUTH_ARGS[@]}" -H "Content-Type: application/json" \
           -X POST --data-binary "@$BODY" \
           "$API_URL/api/v1/intake/$INTAKE_ID/verified" > "$WORK_DIR/rec_$i.json"; then
        if [[ "$PASSED" == "true" ]]; then
          log "✅ verified 확정 — 최종 콜백 발송(체인 ⑥)"; N_VERIFIED=$((N_VERIFIED + 1))
        else
          log "🛑 gate_failed 확정 — 결함 수정 후 재검증 필요"; N_FAILED=$((N_FAILED + 1))
        fi
      else
        log "WARN: 결과 확정 POST 실패 — 건 skip(다음 주기 재시도, 멱등): $INTAKE_ID"
        N_SKIP=$((N_SKIP + 1))
      fi
      ;;
    3)
      log "미완주 — 잔존 티켓 있음. 다음 주기 재확인: $(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['report'].splitlines()[-1])" "$RESULT" 2>/dev/null || true)"
      N_SKIP=$((N_SKIP + 1))
      ;;
    5)
      log "⚠️ 게이트 명령 부재 — 검증 불가(verified 전이 금지). VERIFY_GATES_FILE 설정 필요: $INTAKE_ID"
      N_SKIP=$((N_SKIP + 1))
      ;;
    *)
      log "WARN: verifier 오류(rc=$RC) — 건 skip: $INTAKE_ID"
      N_SKIP=$((N_SKIP + 1))
      ;;
  esac
done

# ── 3) 요약 ──────────────────────────────────────────────────────────────────
log "완료. (MODE=$MODE) 처리=$N_TOTAL · verified=$N_VERIFIED · gate_failed=$N_FAILED · skip=$N_SKIP"

# ── crontab 예시 (발급 배치 이후 — 완주는 며칠 걸릴 수 있어 매일 재확인) ──────
#   0 5 * * * cd /mnt/c/workspace/ClickEye && \
#     FLOWOPS_DELIVERY_VERIFY=true GOVERNANCE_SERVICE_TOKEN=... \
#     VERIFY_GATES_FILE=.clickeye-gates.txt \
#     scripts/delivery_verify.sh >> logs/delivery_verify.log 2>&1
