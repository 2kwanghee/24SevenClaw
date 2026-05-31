#!/usr/bin/env bash
# prompt-evolve-eval.sh — 후보 프롬프트 1개를 벤치마크 케이스 1개로 평가한다.
#
# git worktree 격리 + ralph-stop-hook fitness 게이트(테스트+린트+fix_plan 완료) 재사용.
# fitness = lexicographic: (1) PASS/FAIL, (2) iteration 횟수(낮을수록 우수).
#
# 사용법:
#   scripts/prompt-evolve-eval.sh <candidate_prompt.md> <benchmark_case.json> [--dry-run|--no-agent]
# 출력(stdout, JSON 한 줄):
#   {"candidate":"...","case":"...","pass":true|false,"iterations":N,"mode":"dry-run|no-agent|live"}
#
# 모드:
#   (기본 live) worktree+settings+swap+agent+gate. FLOWOPS_PROMPT_EVOLVE=true 필요(기본 OFF).
#   --no-agent  worktree+settings+swap+정리까지 실제 수행, agent/gate 만 스킵 → /mnt/c 워크트리 배관을 토큰 0 으로 검증.
#   --dry-run   worktree 없이 결정적 합성 점수만 → 루프 로직 검증 전용.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=/dev/null
source "$PROJECT_DIR/scripts/pipeline_config.sh" 2>/dev/null || true

CAND="${1:-}"
CASE="${2:-}"
MODE="live"
for a in "${@:3}"; do
  case "$a" in
    --dry-run) MODE="dry-run" ;;
    --no-agent) MODE="no-agent" ;;
  esac
done

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
# 후보 파일 cksum 으로 의사 반복 횟수 산출(챔피언과 변형이 구분되도록). 루프 로직 검증 전용.
if [[ "$MODE" == "dry-run" ]]; then
  CK="$(cksum "$CAND" | awk '{print $1}')"
  SYN_ITER=$(( (CK % 5) + 1 ))   # 1..5
  echo "[dry-run] $CAND_NAME × $CASE_ID → synthetic pass=true iterations=$SYN_ITER (no worktree/agent)" >&2
  emit_score "true" "$SYN_ITER" "dry-run"
  exit 0
fi

# ── live 안전 게이트 (no-agent 는 토큰 미소비라 허용) ──
if [[ "$MODE" == "live" ]]; then
  is_enabled "FLOWOPS_PROMPT_EVOLVE" || err "live 평가는 FLOWOPS_PROMPT_EVOLVE=true 필요(기본 OFF). 배관 검증은 --no-agent/--dry-run 사용."
  command -v claude >/dev/null 2>&1 || err "claude CLI 없음"
fi

# ── 워크트리 격리 셋업 (live + no-agent 공통) ──
WT_BASE="$PROJECT_DIR/.worktrees"   # .gitignore 처리됨
mkdir -p "$WT_BASE"
WT="$WT_BASE/evolve-${CASE_ID}-$(cksum "$CAND" | awk '{print $1}')"

cleanup() { git -C "$PROJECT_DIR" worktree remove --force "$WT" >/dev/null 2>&1 || rm -rf "$WT"; }
trap cleanup EXIT

git -C "$PROJECT_DIR" worktree remove --force "$WT" >/dev/null 2>&1 || true
git -C "$PROJECT_DIR" worktree add --detach "$WT" HEAD >/dev/null 2>&1 || err "worktree 생성 실패: $WT"
echo "[$MODE] worktree 생성: $WT" >&2

# 워크트리에 purpose-built .claude/settings.json 작성:
#   Stop hook = ralph-stop-hook(루프/fitness 게이트)만. plan-gate/commit-session 제외 → eval 에이전트가 막히지 않음.
#   (HEAD 의 settings.json 에는 plan-gate PreToolUse 가 있어 --dangerously-skip-permissions 로도 편집이 차단됨)
mkdir -p "$WT/.claude"
cat > "$WT/.claude/settings.json" <<'JSON'
{
  "hooks": {
    "Stop": [
      { "hooks": [ { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/scripts/ralph-stop-hook.sh\"" } ] }
    ]
  }
}
JSON

# 벤치마크 케이스 → 워크트리 .ralph/fix_plan.md, 후보 프롬프트 → .ralph/PROMPT.md (스왑)
mkdir -p "$WT/.ralph"
python3 -c "import json;open('$WT/.ralph/fix_plan.md','w').write(json.load(open('$CASE'))['fix_plan'])"
cp "$CAND" "$WT/.ralph/PROMPT.md"
rm -f "$WT/.ralph/.iteration_count"
echo "[$MODE] settings/fix_plan/PROMPT 스왑 완료" >&2

# ── NO-AGENT: 배관(워크트리/스왑/정리)만 검증, agent/gate 스킵 ──
if [[ "$MODE" == "no-agent" ]]; then
  # 스왑 무결성 확인
  [[ -f "$WT/.claude/settings.json" && -s "$WT/.ralph/PROMPT.md" && -s "$WT/.ralph/fix_plan.md" ]] \
    || err "워크트리 스왑 무결성 실패"
  grep -q "ralph-stop-hook" "$WT/.claude/settings.json" || err "Stop hook 미배선"
  grep -q "harness-plan-gate" "$WT/.claude/settings.json" && err "plan-gate 가 남아있음(eval 차단됨)" || true
  echo "[no-agent] 배관 OK — worktree add/settings/swap/정리 검증 (agent/gate 미실행, 토큰 0)" >&2
  emit_score "true" "0" "no-agent"
  exit 0
fi

# ── LIVE: 실제 에이전트 루프 + fitness 게이트 (구독 세션, 비쌈) ──
export FLOWOPS_RALPH_STOP_HOOK=true
export RALPH_MAX_ITERATIONS="${RALPH_MAX_ITERATIONS:-15}"

cd "$WT"
unset ANTHROPIC_API_KEY
set +e
timeout "${EVAL_TIMEOUT:-3600}" claude -p "$(cat .ralph/PROMPT.md)" \
  --model sonnet --dangerously-skip-permissions </dev/null >/dev/null 2>&1
set -e

# fitness: ralph-stop-hook 으로 PASS/FAIL + iteration_count
GATE="$(printf '{}' | bash "$PROJECT_DIR/scripts/ralph-stop-hook.sh" 2>/dev/null || printf '{"decision":"block"}')"
DECISION="$(printf '%s' "$GATE" | python3 -c "import json,sys;print(json.load(sys.stdin).get('decision','block'))" 2>/dev/null || echo block)"
ITERS="$(cat "$WT/.ralph/.iteration_count" 2>/dev/null || echo "$RALPH_MAX_ITERATIONS")"

if [[ "$DECISION" == "allow" ]]; then
  emit_score "true" "$ITERS" "live"
else
  emit_score "false" "$ITERS" "live"
fi
