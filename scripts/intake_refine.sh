#!/usr/bin/env bash
# intake_refine.sh — 인테이크 metaprompt 정제 로컬 배치 (CE-310 A3-full, 야간/수동).
#
# 원칙: 정제 LLM 실행은 **로컬 배치(claude -p)만** 한다. 서버(clickeye-api)는
#   대기 목록 제공/결과 저장(상태 조율)만 담당한다 — 실행 플레인 분리.
#
# llm-prompt-evolve.sh 규약 미러:
#   게이트(FLOWOPS_INTAKE_REFINE, live 만) · 하드캡(MAX_ITEMS) · --dry-run 배관 검증.
#
# 흐름:
#   1) GET $API_URL/api/v1/intake/refine/pending?limit=$MAX_ITEMS
#      (X-Governance-Token — GOVERNANCE_SERVICE_TOKEN 설정 시)
#   2) 각 건:
#      live    = claude -p 헤드리스(.claude/skills/metaprompt/SKILL.md 방법론 +
#                인테이크 제목/원문/target) → "구현 스펙" 마크다운 캡처(타임아웃)
#                → POST /intake/{id}/refined. 출력이 비면 해당 건 skip.
#      dry-run = claude 미호출(토큰 0). "[DRY-RUN 정제] <제목>" + 원문 앞 500자
#                합성문 제출로 배관만 검증.
#   3) 건별 실패는 로그 후 계속(배치 비중단). 말미에 처리/성공/skip 요약.
#
# 사용법:
#   scripts/intake_refine.sh --dry-run                    # 배관 검증(권장 시작점)
#   FLOWOPS_INTAKE_REFINE=true scripts/intake_refine.sh   # live (야간 배치)
#
# env 오버라이드: API_URL(기본 http://localhost:8000) · GOVERNANCE_SERVICE_TOKEN
#   (있으면 X-Governance-Token 헤더) · MAX_ITEMS(기본 5) · CLAUDE_TIMEOUT(기본 300초)

set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=/dev/null
source "$PROJECT_DIR/scripts/pipeline_config.sh" 2>/dev/null || true

DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

API_URL="${API_URL:-http://localhost:8000}"
MAX_ITEMS="${MAX_ITEMS:-5}"
CLAUDE_TIMEOUT="${CLAUDE_TIMEOUT:-300}"
SKILL_MD="$PROJECT_DIR/.claude/skills/metaprompt/SKILL.md"

log() { echo "[$(date '+%H:%M:%S')] $*"; }
die() { echo "ERROR: $*" >&2; exit 2; }

# 안전 게이트: live 는 명시 활성(FLOWOPS_INTAKE_REFINE=true) 필수.
# (미설정=off — llm-prompt-evolve.sh 와 동일한 명시적 opt-in 규약.)
if ! $DRY_RUN; then
  [[ "${FLOWOPS_INTAKE_REFINE:-false}" == "true" ]] \
    || { echo "[SKIP] intake-refine 비활성(FLOWOPS_INTAKE_REFINE!=true). 배관 검증은 --dry-run 사용."; exit 0; }
fi

command -v python3 >/dev/null || die "python3 필요"
command -v curl >/dev/null || die "curl 필요"
[[ -f "$SKILL_MD" ]] || die "metaprompt 스킬 없음: $SKILL_MD"
if ! $DRY_RUN; then
  command -v claude >/dev/null || die "claude CLI 필요(live 정제)"
fi

# 머신 토큰 헤더 (governance verify_governance_token — 미설정 dev 는 개방).
AUTH_ARGS=()
[[ -n "${GOVERNANCE_SERVICE_TOKEN:-}" ]] \
  && AUTH_ARGS=(-H "X-Governance-Token: $GOVERNANCE_SERVICE_TOKEN")

MODE="live"; $DRY_RUN && MODE="dry-run"
log "MODE=$MODE · API_URL=$API_URL · 하드캡 MAX_ITEMS=$MAX_ITEMS · CLAUDE_TIMEOUT=${CLAUDE_TIMEOUT}s"

WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

# ── 1) 정제 대기 목록 조회 ───────────────────────────────────────────────────
log "=== 1) 정제 대기 목록 조회 ==="
curl -fsS --max-time 30 "${AUTH_ARGS[@]}" \
  "$API_URL/api/v1/intake/refine/pending?limit=$MAX_ITEMS" > "$WORK_DIR/pending.json" \
  || die "GET refine/pending 실패: $API_URL (FEATURE_INTAKE/토큰 확인)"

N_TOTAL="$(python3 -c "import json,sys;print(len(json.load(open(sys.argv[1]))))" "$WORK_DIR/pending.json")"
log "정제 대기: ${N_TOTAL}건 (cap MAX_ITEMS=$MAX_ITEMS)"
if [[ "$N_TOTAL" -eq 0 ]]; then
  log "대기 0건 — 정제 불필요. 정상 종료."
  exit 0
fi

# 건별 입력 파일 분해: $WORK_DIR/item_N.json + 메타(id/title) 목록.
python3 - "$WORK_DIR/pending.json" "$WORK_DIR" <<'PYEOF'
import json, sys
items, work = json.load(open(sys.argv[1])), sys.argv[2]
for i, it in enumerate(items, 1):
    json.dump(it, open(f"{work}/item_{i}.json", "w"), ensure_ascii=False)
PYEOF

# ── 2) 건별 정제 → 제출 ──────────────────────────────────────────────────────
log "=== 2) 건별 정제 ($MODE) ==="
N_OK=0; N_SKIP=0
for i in $(seq 1 "$N_TOTAL"); do
  ITEM="$WORK_DIR/item_$i.json"
  INTAKE_ID="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['id'])" "$ITEM")"
  TITLE="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['title'])" "$ITEM")"
  log "--- [$i/$N_TOTAL] $INTAKE_ID · $TITLE ---"

  REFINED_FILE="$WORK_DIR/refined_$i.md"
  if $DRY_RUN; then
    # 합성 정제문: claude 미호출(토큰 0) — 배관(조회→제출→상태 전이)만 검증.
    python3 - "$ITEM" > "$REFINED_FILE" <<'PYEOF'
import json, sys
it = json.load(open(sys.argv[1]))
print(f"[DRY-RUN 정제] {it['title']}\n")
print((it.get("normalized_text") or "")[:500])
PYEOF
  else
    # 정제 프롬프트: metaprompt SKILL 방법론 + 인테이크 제목/원문/target.
    GEN_PROMPT="$WORK_DIR/prompt_$i.md"
    {
      cat "$SKILL_MD"
      echo
      echo "--- 이번 입력 (인테이크 수주 요구사항 → 구현 스펙 정제) ---"
      echo
      echo "위 metaprompt 방법론(정제 절차 1~3, 하지 말 것, 자기 점검)을 그대로 적용해"
      echo "아래 인테이크 요구사항을 '구현 스펙' 마크다운으로 정제하라."
      echo "출력 형식은 SKILL 의 '## 목표/## 가정/## 대상 파일/## 구현 단계/## 테스트/"
      echo "## 준수할 컨벤션' 구조를 따르되, 인테이크는 고객 요구사항이므로 '대상 파일'"
      echo "대신 '## 범위(스코프)' 로 대체해도 된다. 마크다운 스펙 **본문만** 출력하고"
      echo "코드/서론/후기는 출력하지 마라."
      echo
      python3 - "$ITEM" <<'PYEOF'
import json, sys
it = json.load(open(sys.argv[1]))
print(f"[제목] {it['title']}")
print(f"[유형] {it['input_type']} · [우선순위] {it.get('priority') or '-'}")
if it.get("target"):
    print(f"[타깃] {json.dumps(it['target'], ensure_ascii=False)}")
print()
print("[원문(normalized_text)]")
print(it.get("normalized_text") or "(없음)")
PYEOF
    } > "$GEN_PROMPT"

    if ! timeout "$CLAUDE_TIMEOUT" claude -p < "$GEN_PROMPT" > "$REFINED_FILE"; then
      log "WARN: claude -p 실패/타임아웃 — 건 skip(다음 주기 재시도): $INTAKE_ID"
      N_SKIP=$((N_SKIP + 1)); continue
    fi
    if ! grep -q '[^[:space:]]' "$REFINED_FILE"; then
      log "WARN: 정제 출력 비어있음 — 건 skip: $INTAKE_ID"
      N_SKIP=$((N_SKIP + 1)); continue
    fi
  fi

  # 제출: POST /intake/{id}/refined {refined_text}. 건별 실패는 로그 후 계속.
  BODY="$WORK_DIR/body_$i.json"
  python3 - "$REFINED_FILE" > "$BODY" <<'PYEOF'
import json, sys
print(json.dumps({"refined_text": open(sys.argv[1], encoding="utf-8").read()}, ensure_ascii=False))
PYEOF
  if curl -fsS --max-time 30 "${AUTH_ARGS[@]}" -H "Content-Type: application/json" \
       -X POST --data-binary "@$BODY" \
       "$API_URL/api/v1/intake/$INTAKE_ID/refined" > "$WORK_DIR/resp_$i.json"; then
    STATUS="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['refine_status'])" "$WORK_DIR/resp_$i.json")"
    log "제출 완료: refine_status=$STATUS"
    N_OK=$((N_OK + 1))
  else
    log "WARN: refined 제출 실패(409=검토 종료됨 가능) — 건 skip: $INTAKE_ID"
    N_SKIP=$((N_SKIP + 1))
  fi
done

# ── 3) 요약 ──────────────────────────────────────────────────────────────────
log "완료. (MODE=$MODE) 처리=$N_TOTAL · 성공=$N_OK · skip=$N_SKIP"

# ── crontab 예시 (야간 1회, 자정 이후 저부하 시간대) ─────────────────────────
#   30 3 * * * cd /mnt/c/workspace/ClickEye && \
#     FLOWOPS_INTAKE_REFINE=true GOVERNANCE_SERVICE_TOKEN=... \
#     scripts/intake_refine.sh >> logs/intake_refine.log 2>&1
# 토글 문서화: .env.example 의 FLOWOPS 블록(FLOWOPS_INTAKE_REFINE=false 기본 off).
