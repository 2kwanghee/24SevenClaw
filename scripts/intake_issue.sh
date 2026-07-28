#!/usr/bin/env bash
# intake_issue.sh — 티켓 전량 자동 발급 로컬 배치 (다프로젝트화 P6, D-12).
#
# 원칙: 분해 LLM 실행은 **로컬 배치(claude -p 구독 세션)만** 한다. 서버(clickeye-api)는
#   대기 목록 제공/기계 수락/발급 원장 기록(상태 조율)만 담당한다 — 실행 플레인 분리.
#   (intake_refine.sh 와 동일 규약 미러: opt-in 게이트 · 하드캡 · --dry-run 배관 검증)
#
# 흐름:
#   1) GET /api/v1/intake/issue/pending?limit=$MAX_ITEMS  (X-Governance-Token)
#   2) 각 건:
#      a. status=pending_review 면 POST /intake/{id}/auto-accept (기계 수락 —
#         서버가 FLOWOPS_INTAKE_AUTO_ACCEPT opt-in 을 강제. 403 이면 건 skip)
#      b. 분해: live   = claude -p (정제 스펙 → 티켓 JSON, linear_issuer 입력 계약 강제)
#               dry-run = 합성 2티켓 JSON(토큰 0)
#      c. 발급: linear_issuer.py — 검증 fail-closed + 3상 발급(부분 실패 = 실행 0건).
#               dry-run 은 --dry-run(네트워크 0)으로 위상 계획만 검증.
#      d. 기록: 전량 성공 시에만 POST /intake/{id}/tickets (원장 확정 + 콜백).
#               dry-run 은 기록하지 않는다(서버 상태 불변).
#   3) 건별 실패는 로그 후 계속(배치 비중단). 말미에 처리/성공/skip 요약.
#
# 발급 이후는 기존 체인이 이어받는다: webhook(_check_and_retrigger) → linear_watcher
# (blockedBy 선행 미완료 차단) → auto_dev_pipeline(P1 완주 오케스트레이터).
#
# 사용법:
#   scripts/intake_issue.sh --dry-run                    # 배관 검증(권장 시작점)
#   FLOWOPS_INTAKE_ISSUE=true scripts/intake_issue.sh    # live (야간 배치)
#
# env 오버라이드: API_URL(기본 http://localhost:8000) · GOVERNANCE_SERVICE_TOKEN ·
#   MAX_ITEMS(기본 3) · CLAUDE_TIMEOUT(기본 600초) · ISSUE_STATE(기본 NightQueued)

set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=/dev/null
source "$PROJECT_DIR/scripts/pipeline_config.sh" 2>/dev/null || true

DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

API_URL="${API_URL:-http://localhost:8000}"
MAX_ITEMS="${MAX_ITEMS:-3}"
CLAUDE_TIMEOUT="${CLAUDE_TIMEOUT:-600}"
ISSUE_STATE="${ISSUE_STATE:-NightQueued}"

log() { echo "[$(date '+%H:%M:%S')] $*"; }
die() { echo "ERROR: $*" >&2; exit 2; }

# 안전 게이트: live 는 명시 활성(FLOWOPS_INTAKE_ISSUE=true) 필수 — opt-in 규약.
if ! $DRY_RUN; then
  [[ "${FLOWOPS_INTAKE_ISSUE:-false}" == "true" ]] \
    || { echo "[SKIP] intake-issue 비활성(FLOWOPS_INTAKE_ISSUE!=true). 배관 검증은 --dry-run 사용."; exit 0; }
fi

command -v python3 >/dev/null || die "python3 필요"
command -v curl >/dev/null || die "curl 필요"
if ! $DRY_RUN; then
  command -v claude >/dev/null || die "claude CLI 필요(live 분해)"
fi

AUTH_ARGS=()
[[ -n "${GOVERNANCE_SERVICE_TOKEN:-}" ]] \
  && AUTH_ARGS=(-H "X-Governance-Token: $GOVERNANCE_SERVICE_TOKEN")

MODE="live"; $DRY_RUN && MODE="dry-run"
log "MODE=$MODE · API_URL=$API_URL · 하드캡 MAX_ITEMS=$MAX_ITEMS · 상태=$ISSUE_STATE"

WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

# ── 1) 발급 대기 목록 조회 ───────────────────────────────────────────────────
log "=== 1) 발급 대기 목록 조회 ==="
curl -fsS --max-time 30 "${AUTH_ARGS[@]}" \
  "$API_URL/api/v1/intake/issue/pending?limit=$MAX_ITEMS" > "$WORK_DIR/pending.json" \
  || die "GET issue/pending 실패: $API_URL (FEATURE_INTAKE/토큰 확인)"

N_TOTAL="$(python3 -c "import json,sys;print(len(json.load(open(sys.argv[1]))))" "$WORK_DIR/pending.json")"
log "발급 대기: ${N_TOTAL}건 (cap MAX_ITEMS=$MAX_ITEMS)"
if [[ "$N_TOTAL" -eq 0 ]]; then
  log "대기 0건 — 발급 불필요. 정상 종료."
  exit 0
fi

python3 - "$WORK_DIR/pending.json" "$WORK_DIR" <<'PYEOF'
import json, sys
items, work = json.load(open(sys.argv[1])), sys.argv[2]
for i, it in enumerate(items, 1):
    json.dump(it, open(f"{work}/item_{i}.json", "w"), ensure_ascii=False)
PYEOF

# ── 2) 건별: (수락) → 분해 → 발급 → 기록 ────────────────────────────────────
log "=== 2) 건별 발급 ($MODE) ==="
N_OK=0; N_SKIP=0
for i in $(seq 1 "$N_TOTAL"); do
  ITEM="$WORK_DIR/item_$i.json"
  INTAKE_ID="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['id'])" "$ITEM")"
  TITLE="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['title'])" "$ITEM")"
  STATUS="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['status'])" "$ITEM")"
  log "--- [$i/$N_TOTAL] $INTAKE_ID · $TITLE (status=$STATUS) ---"

  # a. 기계 수락 — pending_review 는 서버 opt-in 이 켜져 있어야 목록에 온다.
  #    dry-run 은 서버 상태를 바꾸지 않으므로 수락도 건너뛴다(배관 로그만).
  if [[ "$STATUS" == "pending_review" ]]; then
    if $DRY_RUN; then
      log "[DRY-RUN] auto-accept 생략(서버 상태 불변)"
    elif curl -fsS --max-time 30 "${AUTH_ARGS[@]}" -X POST \
           "$API_URL/api/v1/intake/$INTAKE_ID/auto-accept" > "$WORK_DIR/accept_$i.json"; then
      log "기계 수락 완료(project 생성)"
    else
      log "WARN: auto-accept 실패(403=토글 off/409=조건 미충족) — 건 skip: $INTAKE_ID"
      N_SKIP=$((N_SKIP + 1)); continue
    fi
  fi

  # b. 분해 — 정제 스펙 → linear_issuer 입력 계약 JSON.
  DECOMP="$WORK_DIR/decomp_$i.json"
  if $DRY_RUN; then
    python3 - "$ITEM" > "$DECOMP" <<'PYEOF'
import json, sys
it = json.load(open(sys.argv[1]))
print(json.dumps({"tickets": [
    {"key": "T1", "title": f"[DRY-RUN 설계] {it['title']}"},
    {"key": "T2", "title": f"[DRY-RUN 구현] {it['title']}", "depends_on": ["T1"]},
]}, ensure_ascii=False))
PYEOF
  else
    GEN_PROMPT="$WORK_DIR/prompt_$i.md"
    {
      echo "너는 SI 딜리버리 PM 이다. 아래 '구현 스펙'을 Linear 설계·구현 티켓으로 전량 분해하라."
      echo
      echo "## 출력 계약 (엄격 — 이 JSON 외에 아무것도 출력하지 마라. 코드펜스 금지)"
      echo '{"tickets":[{"key":"T1","title":"...","description":"...","labels":["api"],"priority":2,"depends_on":[]}]}'
      echo
      echo "## 분해 규칙"
      echo "- key 는 T1,T2… 유일. depends_on 은 선행 티켓 key 배열 — 이 관계가 실행 순서가 된다."
      echo "- 설계 티켓(스키마/계약/구조)을 먼저, 구현 티켓이 이를 depends_on 으로 참조."
      echo "- 각 티켓은 독립 구현·테스트 가능 단위(PR 1개 크기). description 에 수용 기준 포함."
      echo "- labels 는 [api, web, agent, contracts, infra] 중에서. priority 는 1(긴급)~4(낮음)."
      echo "- 순환 의존 금지. 자기 참조 금지. 총 3~30개 권장(최대 100 — 초과는 거부된다)."
      echo
      echo "## 구현 스펙 (분해 대상)"
      python3 - "$ITEM" <<'PYEOF'
import json, sys
it = json.load(open(sys.argv[1]))
print(f"[제목] {it['title']}")
if it.get("target"):
    print(f"[타깃] {json.dumps(it['target'], ensure_ascii=False)}")
print()
print(it.get("refined_text") or "(정제 스펙 없음)")
PYEOF
    } > "$GEN_PROMPT"

    RAW_OUT="$WORK_DIR/raw_$i.txt"
    if ! timeout "$CLAUDE_TIMEOUT" claude -p < "$GEN_PROMPT" > "$RAW_OUT"; then
      log "WARN: claude -p 실패/타임아웃 — 건 skip(다음 주기 재시도): $INTAKE_ID"
      N_SKIP=$((N_SKIP + 1)); continue
    fi
    # 모델이 코드펜스로 감쌌을 경우 방어적으로 벗긴다(계약 위반이지만 회복 가능).
    python3 - "$RAW_OUT" > "$DECOMP" <<'PYEOF' || { echo "PARSE_FAIL"; } > "$DECOMP"
import json, re, sys
raw = open(sys.argv[1], encoding="utf-8").read().strip()
m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", raw, re.DOTALL)
if m:
    raw = m.group(1)
json.loads(raw)  # 유효성 1차 확인(상세 검증은 issuer 가 fail-closed 로)
print(raw)
PYEOF
    if grep -q "PARSE_FAIL" "$DECOMP"; then
      log "WARN: 분해 출력이 JSON 아님 — 건 skip(발급 0건): $INTAKE_ID"
      N_SKIP=$((N_SKIP + 1)); continue
    fi
  fi

  # c. 발급 — issuer 가 검증 fail-closed + 3상(부분 실패 = 실행 0건)을 보장한다.
  LEDGER="$WORK_DIR/ledger_$i.json"
  ISSUER_ARGS=(--input "$DECOMP" --state "$ISSUE_STATE" --title-prefix "[수주:${INTAKE_ID:0:8}] ")
  $DRY_RUN && ISSUER_ARGS+=(--dry-run)
  if ! python3 "$PROJECT_DIR/scripts/linear_issuer.py" "${ISSUER_ARGS[@]}" > "$LEDGER"; then
    log "WARN: 발급 실패(불량 분해 또는 Linear 오류 — stderr 참조) — 건 skip: $INTAKE_ID"
    N_SKIP=$((N_SKIP + 1)); continue
  fi

  # d. 기록 — 전량 성공 시에만. dry-run 은 서버 상태 불변.
  if $DRY_RUN; then
    log "[DRY-RUN] 위상 계획: $(cat "$LEDGER")"
    N_OK=$((N_OK + 1)); continue
  fi
  if curl -fsS --max-time 30 "${AUTH_ARGS[@]}" -H "Content-Type: application/json" \
       -X POST --data-binary "@$LEDGER" \
       "$API_URL/api/v1/intake/$INTAKE_ID/tickets" > "$WORK_DIR/rec_$i.json"; then
    N_TICKETS="$(python3 -c "import json,sys;print(len(json.load(open(sys.argv[1]))['tickets']))" "$LEDGER")"
    log "발급 확정: ${N_TICKETS}티켓 → $ISSUE_STATE (원장 기록 + 콜백)"
    N_OK=$((N_OK + 1))
  else
    # 발급은 됐는데 기록 실패 — 티켓은 Queued 로 실행되지만 원장은 다음 재시도에서
    # 멱등 기록된다... 는 보장이 없다(재실행 시 pending 목록에 다시 떠 중복 발급 위험).
    # 따라서 즉시 사람 개입을 요구한다(로그 + 종료 코드에 반영).
    log "ERROR: 발급 성공 후 원장 기록 실패 — 중복 발급 위험. 수동 확인 필요: $INTAKE_ID (원장: $LEDGER 내용 확인)"
    cat "$LEDGER" >&2
    N_SKIP=$((N_SKIP + 1))
  fi
done

# ── 3) 요약 ──────────────────────────────────────────────────────────────────
log "완료. (MODE=$MODE) 처리=$N_TOTAL · 성공=$N_OK · skip=$N_SKIP"

# ── crontab 예시 (정제 배치 30분 뒤 — 정제 완료분을 이어받는다) ───────────────
#   0 4 * * * cd /mnt/c/workspace/ClickEye && \
#     FLOWOPS_INTAKE_ISSUE=true FLOWOPS_INTAKE_AUTO_ACCEPT=on GOVERNANCE_SERVICE_TOKEN=... \
#     scripts/intake_issue.sh >> logs/intake_issue.log 2>&1
# 토글: FLOWOPS_INTAKE_ISSUE(배치 live) · FLOWOPS_INTAKE_AUTO_ACCEPT(서버 기계수락, 서버 env)
