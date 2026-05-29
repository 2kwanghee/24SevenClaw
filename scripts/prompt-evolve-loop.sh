#!/usr/bin/env bash
# prompt-evolve-loop.sh — APE/OPRO 오프라인 배치 프롬프트 진화 루프 (야간/수동).
#
# 기본 OFF: FLOWOPS_PROMPT_EVOLVE=false. 하드캡: MAX_GEN·N·B (폭주/rate-limit 방지).
# 승격 = 파일 스왑: 우승 후보 → .ralph/prompts/PROMPT.champion.md + .ralph/PROMPT.md(프로덕션) + git commit.
#   → 프로덕션 주입점(auto_dev_pipeline.sh / ralph-loop.sh)은 변경 없이 .ralph/PROMPT.md 만 갈아끼움.
#
# MVP(이번): 수동 변형 PROMPT.v*.md 를 챔피언과 단일 세대 비교·평가·승격·ledger·git. "배관 검증"이 목표.
#   live 다세대 진화(prompt-evolver 에이전트가 candidates/ 생성)는 deferred(별도 세션).
#
# 사용법:
#   scripts/prompt-evolve-loop.sh [--dry-run]
#     --dry-run : worktree/agent/커밋 없이 합성 점수로 배관만 검증(권장 시작점).

set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=/dev/null
source "$PROJECT_DIR/scripts/pipeline_config.sh" 2>/dev/null || true

DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

PROMPTS_DIR="$PROJECT_DIR/.ralph/prompts"
BENCH_DIR="$PROJECT_DIR/.ralph/benchmark"
LEDGER="$PROMPTS_DIR/ledger.json"
CHAMPION="$PROMPTS_DIR/PROMPT.champion.md"
PROD_PROMPT="$PROJECT_DIR/.ralph/PROMPT.md"
EVAL="$PROJECT_DIR/scripts/prompt-evolve-eval.sh"

# 하드캡 (조기수렴/폭주 방지)
MAX_GEN="${MAX_GEN:-3}"
N="${N:-3}"           # 세대당 후보 수 상한
B="${B:-3}"           # 사용할 벤치마크 케이스 수 상한

log() { echo "[$(date '+%H:%M:%S')] $*"; }

# 안전 게이트: live 는 명시 활성 필요
if ! $DRY_RUN; then
  is_enabled "FLOWOPS_PROMPT_EVOLVE" || { echo "[SKIP] prompt-evolve 비활성(FLOWOPS_PROMPT_EVOLVE=false). 배관 검증은 --dry-run 사용."; exit 0; }
fi

[[ -f "$CHAMPION" ]] || { echo "ERROR: 챔피언 없음: $CHAMPION" >&2; exit 2; }
[[ -f "$EVAL" ]] || { echo "ERROR: eval 스크립트 없음: $EVAL" >&2; exit 2; }
[[ -f "$LEDGER" ]] || { echo "ERROR: ledger 없음: $LEDGER" >&2; exit 2; }

# 벤치마크 케이스 수집 (최대 B개)
mapfile -t CASES < <(ls "$BENCH_DIR"/case-*.json 2>/dev/null | head -n "$B")
[[ ${#CASES[@]} -gt 0 ]] || { echo "ERROR: 벤치마크 케이스 없음($BENCH_DIR)" >&2; exit 2; }
$DRY_RUN && log "MODE=dry-run (worktree/agent/커밋 없음)" || log "MODE=live (FLOWOPS_PROMPT_EVOLVE=true)"
log "벤치마크 ${#CASES[@]}개 (cap B=$B) · 하드캡 MAX_GEN=$MAX_GEN N=$N"

DRY_FLAG=""; $DRY_RUN && DRY_FLAG="--dry-run"

# 후보 1개를 모든 케이스로 평가 → "all_pass(0/1) avg_iter" 출력
eval_candidate() {  # <prompt_file>
  local pf="$1" total=0 cnt=0 all_pass=1 out p i
  for c in "${CASES[@]}"; do
    out="$(bash "$EVAL" "$pf" "$c" $DRY_FLAG)" || { all_pass=0; continue; }
    p="$(printf '%s' "$out" | python3 -c "import json,sys;print('1' if json.load(sys.stdin)['pass'] else '0')")"
    i="$(printf '%s' "$out" | python3 -c "import json,sys;print(json.load(sys.stdin)['iterations'])")"
    [[ "$p" == "1" ]] || all_pass=0
    total=$((total + i)); cnt=$((cnt + 1))
  done
  local avg=999
  [[ "$cnt" -gt 0 ]] && avg=$(( (total + cnt/2) / cnt ))
  echo "$all_pass $avg"
}

# lexicographic 우열: pass 우선, 동률이면 iterations 적은 쪽. → 1(우수)/0
is_better() {  # <cP> <cA> <hP> <hA>
  if [[ "$1" -gt "$3" ]]; then echo 1; return; fi
  if [[ "$1" -lt "$3" ]]; then echo 0; return; fi
  [[ "$2" -lt "$4" ]] && echo 1 || echo 0
}

log "=== 챔피언 평가 ==="
read -r CH_PASS CH_AVG < <(eval_candidate "$CHAMPION")
log "champion: pass=$CH_PASS avg_iter=$CH_AVG"

# 후보 수집 — MVP: 수동 변형 PROMPT.v*.md (최대 N). live 진화는 candidates/ 도 포함(deferred).
mapfile -t CANDS < <(ls "$PROMPTS_DIR"/PROMPT.v*.md 2>/dev/null | head -n "$N")
[[ ${#CANDS[@]} -gt 0 ]] || { log "후보 없음(PROMPT.v*.md). 진화 종료."; exit 0; }
log "후보 ${#CANDS[@]}개 (cap N=$N)"

BEST_PF="$CHAMPION"; BEST_PASS="$CH_PASS"; BEST_AVG="$CH_AVG"
for cand in "${CANDS[@]}"; do
  log "--- 평가: $(basename "$cand") ---"
  read -r C_PASS C_AVG < <(eval_candidate "$cand")
  log "$(basename "$cand"): pass=$C_PASS avg_iter=$C_AVG"
  if [[ "$(is_better "$C_PASS" "$C_AVG" "$BEST_PASS" "$BEST_AVG")" == "1" ]]; then
    BEST_PF="$cand"; BEST_PASS="$C_PASS"; BEST_AVG="$C_AVG"
  fi
done

PROMOTED=0
if [[ "$BEST_PF" != "$CHAMPION" ]]; then
  PROMOTED=1
  log "🏆 승격 후보: $(basename "$BEST_PF") (pass=$BEST_PASS avg_iter=$BEST_AVG > champion pass=$CH_PASS avg_iter=$CH_AVG)"
else
  log "승격 없음 — 챔피언 유지(조기수렴)."
fi

# ledger 기록 + (live·승격 시) 파일 스왑 & git 커밋
python3 - "$LEDGER" "$(basename "$BEST_PF")" "$BEST_PASS" "$BEST_AVG" "$PROMOTED" "$DRY_RUN" <<'PYEOF'
import json, sys
ledger, best, bp, ba, promoted, dry = sys.argv[1:7]
d = json.load(open(ledger))
gen = len(d.get("history", []))
entry = {
    "generation": gen,
    "candidate": best,
    "score": {"pass": bp == "1", "avg_iterations": int(ba)},
    "promoted": promoted == "1",
    "dry_run": dry == "true",
    "ts": None,
}
if promoted == "1" and dry != "true":
    d["champion_version"] = d.get("champion_version", 0) + 1
d.setdefault("history", []).append(entry)
if dry == "true":
    print("[dry-run] ledger entry (미저장):", json.dumps(entry, ensure_ascii=False))
else:
    json.dump(d, open(ledger, "w"), ensure_ascii=False, indent=2)
    open(ledger, "a").write("\n")
    print("ledger updated:", json.dumps(entry, ensure_ascii=False))
PYEOF

if [[ "$PROMOTED" == "1" ]]; then
  if $DRY_RUN; then
    log "[dry-run] 승격 시뮬레이션 — PROMPT.champion.md/PROMPT.md 스왑 및 git 커밋 생략."
  else
    NEW_VER="$(python3 -c "import json;print(json.load(open('$LEDGER')).get('champion_version',0))")"
    cp "$BEST_PF" "$CHAMPION"
    cp "$BEST_PF" "$PROD_PROMPT"   # 프로덕션 프롬프트 스왑(주입점 불변)
    git -C "$PROJECT_DIR" add "$CHAMPION" "$PROD_PROMPT" "$LEDGER"
    git -C "$PROJECT_DIR" commit -m "[prompt-evolve] champion → v${NEW_VER} ($(basename "$BEST_PF"))" || log "WARN: git commit 실패(수동 확인)"
    log "✅ 승격 완료: champion v${NEW_VER} = $(basename "$BEST_PF")"
  fi
fi

log "완료. (MVP 단일 세대 비교 — 다세대 live 진화는 deferred)"
