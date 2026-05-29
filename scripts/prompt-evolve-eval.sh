#!/usr/bin/env bash
# prompt-evolve-eval.sh — 후보 프롬프트 1개를 벤치마크 케이스 1개로 평가한다.
#
# git worktree 격리 + ralph-stop-hook fitness 게이트(테스트+린트+fix_plan 완료) 재사용.
# fitness = lexicographic: (1) PASS/FAIL, (2) iteration 횟수(낮을수록 우수).
#
# 사용법:
#   scripts/prompt-evolve-eval.sh <candidate_prompt.md> <benchmark_case.json> [--dry-run]
# 출력(stdout, JSON 한 줄):
#   {"candidate":"...","case":"...","pass":true|false,"iterations":N,"mode":"dry-run|live"}
#
# 안전:
#   - live 모드는 FLOWOPS_PROMPT_EVOLVE=true 필요(기본 OFF).
#   - live 평가 1회 = full agent run(구독 세션, 분 단위·rate-limit). 하드캡은 loop 가 관리.
#   - --dry-run 은 worktree/agent 없이 결정적 합성 점수만 — 배관(배선) 검증 전용.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=/dev/null
source "$PROJECT_DIR/scripts/pipeline_config.sh" 2>/dev/null || true

CAND="${1:-}"
CASE="${2:-}"
DRY_RUN=false
[[ "${3:-}" == "--dry-run" ]] && DRY_RUN=true

err() { echo "ERROR: $*" >&2; exit 2; }
[[ -n "$CAND" && -f "$CAND" ]] || err "후보 프롬프트 파일 없음: '$CAND'"
[[ -n "$CASE" && -f "$CASE" ]] || err "벤치마크 케이스 없음: '$CASE'"

CAND_NAME="$(basename "$CAND")"
CASE_ID="$(python3 -c "import json;print(json.load(open('$CASE')).get('id','?'))")"

emit_score() {  # <pass:true|false> <iterations> <mode>
  python3 - "$CAND_NAME" "$CASE_ID" "$1" "$2" "$3" <<'PYEOF'
import json, sys
cand, case_id, passed, iters, mode = sys.argv[1:6]
print(json.dumps({
    "candidate": cand, "case": case_id,
    "pass": passed == "true", "iterations": int(iters), "mode": mode,
}, ensure_ascii=False))
PYEOF
}

# ── DRY-RUN: worktree/agent 없이 결정적 합성 점수 ──
# 후보 파일 cksum 으로 의사 반복 횟수 산출(챔피언과 변형이 구분되도록). 배관 검증 전용.
if $DRY_RUN; then
  CK="$(cksum "$CAND" | awk '{print $1}')"
  SYN_ITER=$(( (CK % 5) + 1 ))   # 1..5
  echo "[dry-run] $CAND_NAME × $CASE_ID → synthetic pass=true iterations=$SYN_ITER (no worktree/agent)" >&2
  emit_score "true" "$SYN_ITER" "dry-run"
  exit 0
fi

# ── LIVE: 실제 평가 (구독 세션, 비쌈 — 기본 OFF) ──
is_enabled "FLOWOPS_PROMPT_EVOLVE" || err "live 평가는 FLOWOPS_PROMPT_EVOLVE=true 필요(기본 OFF). 배관 검증은 --dry-run 사용."
command -v claude >/dev/null 2>&1 || err "claude CLI 없음"

WT_BASE="$PROJECT_DIR/.worktrees"   # .gitignore 처리됨
mkdir -p "$WT_BASE"
WT="$WT_BASE/evolve-${CASE_ID}-$(cksum "$CAND" | awk '{print $1}')"

cleanup() { git -C "$PROJECT_DIR" worktree remove --force "$WT" >/dev/null 2>&1 || rm -rf "$WT"; }
trap cleanup EXIT

# 현재 HEAD 기준 격리 워크트리 생성 (.ralph 전역 상태 오염 방지)
git -C "$PROJECT_DIR" worktree remove --force "$WT" >/dev/null 2>&1 || true
git -C "$PROJECT_DIR" worktree add --detach "$WT" HEAD >/dev/null 2>&1 || err "worktree 생성 실패: $WT"

# 벤치마크 케이스 → 워크트리 .ralph/fix_plan.md
mkdir -p "$WT/.ralph"
python3 -c "import json;open('$WT/.ralph/fix_plan.md','w').write(json.load(open('$CASE'))['fix_plan'])"

# 후보 프롬프트 → 워크트리 .ralph/PROMPT.md (스왑)
cp "$CAND" "$WT/.ralph/PROMPT.md"
rm -f "$WT/.ralph/.iteration_count"

# fitness 게이트 활성 보장
export FLOWOPS_RALPH_STOP_HOOK=true
export RALPH_MAX_ITERATIONS="${RALPH_MAX_ITERATIONS:-15}"

# 에이전트 루프 실행 (구독 세션). stop-hook 와이어링/정밀 점수는 deferred live-run 세션에서 확정.
cd "$WT"
unset ANTHROPIC_API_KEY
set +e
timeout "${EVAL_TIMEOUT:-3600}" claude -p "$(cat .ralph/PROMPT.md)" \
  --model sonnet --dangerously-skip-permissions </dev/null >/dev/null 2>&1
set -e

# fitness 판정: ralph-stop-hook 으로 PASS/FAIL + iteration_count
GATE="$(printf '{}' | bash "$PROJECT_DIR/scripts/ralph-stop-hook.sh" 2>/dev/null || printf '{"decision":"block"}')"
DECISION="$(printf '%s' "$GATE" | python3 -c "import json,sys;print(json.load(sys.stdin).get('decision','block'))" 2>/dev/null || echo block)"
ITERS="$(cat "$WT/.ralph/.iteration_count" 2>/dev/null || echo "$RALPH_MAX_ITERATIONS")"

if [[ "$DECISION" == "allow" ]]; then
  emit_score "true" "$ITERS" "live"
else
  emit_score "false" "$ITERS" "live"
fi
