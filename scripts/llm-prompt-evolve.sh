#!/usr/bin/env bash
# llm-prompt-evolve.sh — clickeye-llm RAG 챔피언 프롬프트 진화 배치 (P2-full, 야간/수동).
#
# prompt-evolve-loop.sh 규약 미러:
#   게이트(FLOWOPS_PROMPT_EVOLVE, live 만) · 하드캡(MAX_CAND/MAX_EVAL_CASES) ·
#   ledger(prompts/ledger.json) · 챔피언 파일 스왑 승격 · --dry-run 배관 검증.
#
# 흐름:
#   1) GET $LLM_URL/feedback?limit=200 → down(실패)/up(회귀) 케이스 분리·상한 적용.
#      down 0건이면 "진화 불필요" 정상 종료.
#   2) 후보 생성:
#      live    = claude -p 헤드리스(prompt-evolver 페르소나 + 챔피언 + 실패 피드백)
#                → clickeye-llm/prompts/candidates/cand_N.md (마커 파싱).
#      dry-run = 챔피언 복제 + 주석 합성 후보 1개 (claude 미호출, 토큰 0).
#   3) 평가: 각 후보·챔피언 × 케이스 → /chat(prompt_override=후보, delivery_id=원 케이스)
#      재실행 → ollama /api/generate judge(YES/NO 루브릭) → pass 수 비교(동률 = 챔피언 유지).
#   4) 승격(live 만): 우승 후보 → prompts/rag_system.champion.md 스왑 + ledger
#      (champion_version 증가) + git commit. dry-run 은 시뮬 로그만.
#
# 주의: /chat + judge 는 dry-run 에서도 실호출(로컬 ollama — 구독 토큰 0).
#       claude CLI 토큰을 쓰는 것은 live 후보 생성뿐.
#
# 사용법:
#   scripts/llm-prompt-evolve.sh --dry-run                     # 배관 검증(권장 시작점)
#   FLOWOPS_PROMPT_EVOLVE=true scripts/llm-prompt-evolve.sh    # live (야간 배치)
#
# env 오버라이드: LLM_URL(기본 http://localhost:8100) · OLLAMA_URL(기본 http://localhost:11434)
#   · LLM_MODEL(judge 모델, 기본 phi3:mini) · MAX_CAND(기본 3) · MAX_EVAL_CASES(기본 12)

set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=/dev/null
source "$PROJECT_DIR/scripts/pipeline_config.sh" 2>/dev/null || true

DRY_RUN=false
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=true

LLM_URL="${LLM_URL:-http://localhost:8100}"
OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"
LLM_MODEL="${LLM_MODEL:-phi3:mini}"
# 하드캡 (폭주/토큰 낭비 방지 — prompt-evolve-loop.sh 규약)
MAX_CAND="${MAX_CAND:-3}"
MAX_EVAL_CASES="${MAX_EVAL_CASES:-12}"

PROMPTS_DIR="$PROJECT_DIR/clickeye-llm/prompts"
CHAMPION="$PROMPTS_DIR/rag_system.champion.md"
CAND_DIR="$PROMPTS_DIR/candidates"
LEDGER="$PROMPTS_DIR/ledger.json"
EVOLVER_MD="$PROJECT_DIR/.claude/agents/prompt-evolver.md"

log() { echo "[$(date '+%H:%M:%S')] $*"; }
die() { echo "ERROR: $*" >&2; exit 2; }

# 안전 게이트: live 는 명시 활성(FLOWOPS_PROMPT_EVOLVE=true) 필수.
# (is_enabled 는 미설정=true 라 여기서는 기본 OFF 를 명시적으로 강제한다.)
if ! $DRY_RUN; then
  [[ "${FLOWOPS_PROMPT_EVOLVE:-false}" == "true" ]] \
    || { echo "[SKIP] llm-prompt-evolve 비활성(FLOWOPS_PROMPT_EVOLVE!=true). 배관 검증은 --dry-run 사용."; exit 0; }
fi

[[ -f "$CHAMPION" ]] || die "챔피언 없음: $CHAMPION"
[[ -f "$EVOLVER_MD" ]] || die "prompt-evolver 페르소나 없음: $EVOLVER_MD"
command -v python3 >/dev/null || die "python3 필요"
curl -fsS --max-time 5 "$LLM_URL/health" >/dev/null || die "clickeye-llm 미가용: $LLM_URL (profile llm 기동 필요)"
curl -fsS --max-time 5 "$OLLAMA_URL/api/tags" >/dev/null || die "ollama 미가용: $OLLAMA_URL (judge 백엔드)"

MODE="live"; $DRY_RUN && MODE="dry-run"
log "MODE=$MODE · LLM_URL=$LLM_URL · judge=$LLM_MODEL · 하드캡 MAX_CAND=$MAX_CAND MAX_EVAL_CASES=$MAX_EVAL_CASES"

WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT
CASES_FILE="$WORK_DIR/cases.json"

# ── 1) 피드백 수집 → down(실패)/up(회귀) 분리·상한 ─────────────────────────────
log "=== 1) 피드백 수집 ==="
curl -fsS --max-time 30 "$LLM_URL/feedback?limit=200" > "$WORK_DIR/feedback.json" \
  || die "GET /feedback 실패: $LLM_URL"

# 케이스 상한: down(실패) 우선 채움, 남는 슬롯을 up(회귀)으로 — 합계 MAX_EVAL_CASES.
read -r N_DOWN N_UP < <(python3 - "$WORK_DIR/feedback.json" "$CASES_FILE" "$MAX_EVAL_CASES" <<'PYEOF'
import json, sys
fb_path, out_path, cap = sys.argv[1], sys.argv[2], int(sys.argv[3])
data = json.load(open(fb_path))
items = data.get("items", [])
def pick(it):
    return {
        "delivery_id": it["delivery_id"],
        "query": it["query"],
        "answer": it.get("answer", ""),
        "comment": it.get("comment"),
        "rating": it["rating"],
    }
down = [pick(i) for i in items if i.get("rating") == "down"][:cap]
up = [pick(i) for i in items if i.get("rating") == "up"][: max(cap - len(down), 0)]
json.dump({"down": down, "up": up}, open(out_path, "w"), ensure_ascii=False)
print(len(down), len(up))
PYEOF
)
log "피드백: down(실패)=$N_DOWN · up(회귀)=$N_UP (cap 합계 $MAX_EVAL_CASES)"
if [[ "$N_DOWN" -eq 0 ]]; then
  log "실패 피드백(down) 0건 — 진화 불필요. 정상 종료."
  exit 0
fi

# ── 2) 후보 생성 ──────────────────────────────────────────────────────────────
log "=== 2) 후보 생성 ==="
mkdir -p "$CAND_DIR"
rm -f "$CAND_DIR"/cand_*.md

# 챔피언 본문(HTML 주석 제거 — 서비스 로더와 동일 규칙).
CHAMPION_TEXT="$(python3 - "$CHAMPION" <<'PYEOF'
import re, sys
raw = open(sys.argv[1], encoding="utf-8").read()
print(re.sub(r"<!--.*?-->", "", raw, flags=re.DOTALL).strip())
PYEOF
)"

if $DRY_RUN; then
  # 합성 후보 1개: 챔피언 복제 + 주석 (claude 미호출 — 토큰 0, 배관 검증용).
  {
    echo "<!-- dry-run 합성 후보: 챔피언 복제. paraphrase : 배관 검증용(토큰 0) -->"
    echo "$CHAMPION_TEXT"
  } > "$CAND_DIR/cand_1.md"
  log "[dry-run] 합성 후보 1개 생성: candidates/cand_1.md (챔피언 복제)"
else
  command -v claude >/dev/null || die "claude CLI 필요(live 후보 생성)"
  GEN_PROMPT="$WORK_DIR/gen_prompt.md"
  {
    cat "$EVOLVER_MD"
    echo
    echo "--- 이번 배치 입력 (clickeye-llm RAG 챗 시스템 프롬프트 진화) ---"
    echo
    echo "★출력 계약 대체★: 이번 진화 대상은 .ralph 파이프라인 프롬프트가 아니라"
    echo "clickeye-llm RAG 챗 '시스템 프롬프트'다. 파일을 직접 쓰지 말고, 서로 의미적으로"
    echo "구별되는 후보 ${MAX_CAND}개를 아래 마커 형식으로만 stdout 에 출력하라."
    echo "각 후보는 단독 완결된 시스템 프롬프트(한국어)여야 하며, '축적된 지식(컨텍스트)만"
    echo "근거로 답하고 없으면 모른다고 답한다'는 안전 원칙을 반드시 보존하라."
    echo
    echo "<<<CANDIDATE 1>>>"
    echo "(후보 1 전문)"
    echo "<<<END 1>>>"
    echo "... (${MAX_CAND}개까지 반복)"
    echo
    echo "[현 챔피언 시스템 프롬프트]"
    echo "$CHAMPION_TEXT"
    echo
    echo "[실패 피드백 (rating=down — 질문/오답/코멘트)]"
    python3 - "$CASES_FILE" <<'PYEOF'
import json, sys
cases = json.load(open(sys.argv[1]))
for i, c in enumerate(cases["down"], 1):
    print(f"{i}. 질문: {c['query']}")
    print(f"   오답: {c['answer']}")
    if c.get("comment"):
        print(f"   코멘트: {c['comment']}")
PYEOF
  } > "$GEN_PROMPT"

  log "claude -p 헤드리스 후보 생성 (N=$MAX_CAND)..."
  claude -p < "$GEN_PROMPT" > "$WORK_DIR/gen_out.txt" || die "claude -p 후보 생성 실패"
  N_CAND="$(python3 - "$WORK_DIR/gen_out.txt" "$CAND_DIR" "$MAX_CAND" <<'PYEOF'
import re, sys
out, cand_dir, cap = open(sys.argv[1], encoding="utf-8").read(), sys.argv[2], int(sys.argv[3])
blocks = re.findall(r"<<<CANDIDATE\s+(\d+)>>>\s*(.*?)\s*<<<END\s+\1>>>", out, flags=re.DOTALL)
n = 0
for _idx, text in blocks[:cap]:
    if not text.strip():
        continue
    n += 1
    open(f"{cand_dir}/cand_{n}.md", "w", encoding="utf-8").write(text.strip() + "\n")
print(n)
PYEOF
)"
  [[ "$N_CAND" -gt 0 ]] || die "후보 파싱 0건 — claude 출력 마커 확인: $WORK_DIR/gen_out.txt"
  log "후보 ${N_CAND}개 생성 (cap MAX_CAND=$MAX_CAND)"
fi

mapfile -t CANDS < <(ls "$CAND_DIR"/cand_*.md 2>/dev/null | head -n "$MAX_CAND")
[[ ${#CANDS[@]} -gt 0 ]] || die "후보 파일 없음: $CAND_DIR"

# ── 3) 평가: /chat(prompt_override) 재실행 + ollama judge ────────────────────
log "=== 3) 평가 (케이스 $((N_DOWN + N_UP))개 × 후보 $((${#CANDS[@]} + 1))종) ==="
EVAL_PY="$WORK_DIR/eval.py"
cat > "$EVAL_PY" <<'PYEOF'
"""후보 프롬프트 1개 평가 — 케이스 재실행(/chat prompt_override) + ollama judge.

stdout: "<pass> <total>". HTTP 실패는 명확 에러로 종료(오프라인 배치 규약).
"""
import json, re, sys, urllib.request

prompt_file, cases_file, llm_url, ollama_url, judge_model = sys.argv[1:6]
raw = open(prompt_file, encoding="utf-8").read()
# 서비스 로더와 동일 규칙: HTML 주석 제거 후 시스템 프롬프트로 사용.
prompt_text = re.sub(r"<!--.*?-->", "", raw, flags=re.DOTALL).strip()

def post(url, body, timeout):
    req = urllib.request.Request(
        url, json.dumps(body).encode(), {"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)

cases = json.load(open(cases_file))
passed = total = 0
for case in cases["down"] + cases["up"]:
    total += 1
    chat = post(
        f"{llm_url}/chat",
        {
            "delivery_id": case["delivery_id"],
            "query": case["query"],
            "prompt_override": prompt_text,
        },
        timeout=300,
    )
    answer = chat.get("answer", "")
    ctx = "\n".join(f"- {s.get('text', '')}" for s in chat.get("sources", []))
    judge_prompt = (
        "다음은 SI 딜리버리 지식 어시스턴트 답변의 품질 평가입니다.\n"
        f"[질문]\n{case['query']}\n\n"
        f"[검색된 컨텍스트]\n{ctx or '(없음)'}\n\n"
        f"[답변]\n{answer}\n\n"
        "루브릭: 답변이 질문·컨텍스트에 비춰 적절한가?"
        " (질문에 응답하고, 컨텍스트에 근거하며, 컨텍스트에 없으면 모른다고 인정)\n"
        "적절하면 YES, 부적절하면 NO. 반드시 YES 또는 NO 한 단어로만 답하라."
    )
    judged = post(
        f"{ollama_url}/api/generate",
        {"model": judge_model, "prompt": judge_prompt, "stream": False},
        timeout=300,
    )
    verdict = re.search(r"\b(YES|NO)\b", str(judged.get("response", "")).upper())
    ok = bool(verdict and verdict.group(1) == "YES")
    passed += ok
    print(
        f"  case[{case['rating']}] {case['query'][:40]!r} -> {'PASS' if ok else 'FAIL'}",
        file=sys.stderr,
    )
print(passed, total)
PYEOF

eval_prompt() {  # <prompt_file> → "pass total"
  python3 "$EVAL_PY" "$1" "$CASES_FILE" "$LLM_URL" "$OLLAMA_URL" "$LLM_MODEL" \
    || die "평가 실패: $1 (clickeye-llm/ollama 로그 확인)"
}

log "--- 챔피언 평가 ---"
read -r CH_PASS TOTAL < <(eval_prompt "$CHAMPION")
log "champion: pass=$CH_PASS/$TOTAL"

BEST_PF="$CHAMPION"; BEST_PASS="$CH_PASS"
for cand in "${CANDS[@]}"; do
  log "--- 평가: $(basename "$cand") ---"
  read -r C_PASS _ < <(eval_prompt "$cand")
  log "$(basename "$cand"): pass=$C_PASS/$TOTAL"
  # 동률 = 챔피언 유지(strict >). 후보 간 동률은 선순위 유지.
  if [[ "$C_PASS" -gt "$BEST_PASS" ]]; then
    BEST_PF="$cand"; BEST_PASS="$C_PASS"
  fi
done

PROMOTED=0
if [[ "$BEST_PF" != "$CHAMPION" ]]; then
  PROMOTED=1
  log "🏆 승격 후보: $(basename "$BEST_PF") (pass=$BEST_PASS/$TOTAL > champion $CH_PASS/$TOTAL)"
else
  log "승격 없음 — 챔피언 유지(동률 포함)."
fi

# ── 4) ledger 기록 + (live·승격 시) 챔피언 스왑 & git 커밋 ────────────────────
python3 - "$LEDGER" "$(basename "$BEST_PF")" "$BEST_PASS" "$CH_PASS" "$TOTAL" "$PROMOTED" "$DRY_RUN" <<'PYEOF'
import datetime, json, os, sys
ledger, best, bp, cp, total, promoted, dry = sys.argv[1:8]
if os.path.exists(ledger):
    d = json.load(open(ledger))
else:
    # 최초 실행 시 시드(멱등) — prompt-evolve-loop.sh ledger 스키마 미러.
    d = {
        "schema_version": 1,
        "champion": "rag_system.champion.md",
        "champion_version": 0,
        "fitness": "judge pass count: 실패(down)+회귀(up) 케이스 재실행 → ollama YES/NO judge. 동률 시 챔피언 유지.",
        "history": [],
    }
entry = {
    "generation": len(d["history"]),
    "candidate": best,
    "score": {"pass": int(bp), "champion_pass": int(cp), "total": int(total)},
    "promoted": promoted == "1",
    "dry_run": dry == "true",
    "ts": datetime.datetime.now(datetime.UTC).isoformat(),
}
if promoted == "1" and dry != "true":
    d["champion_version"] = d.get("champion_version", 0) + 1
d["history"].append(entry)
if dry == "true":
    print("[검증모드] ledger entry (미저장):", json.dumps(entry, ensure_ascii=False))
else:
    json.dump(d, open(ledger, "w"), ensure_ascii=False, indent=2)
    open(ledger, "a").write("\n")
    print("ledger updated:", json.dumps(entry, ensure_ascii=False))
PYEOF

if [[ "$PROMOTED" == "1" ]]; then
  if $DRY_RUN; then
    log "[검증모드] 승격 시뮬레이션 — rag_system.champion.md 스왑 및 git 커밋 생략."
  else
    NEW_VER="$(python3 -c "import json;print(json.load(open('$LEDGER')).get('champion_version',0))")"
    # 스왑: 후보 본문 + 챔피언 헤더 주석 재부착(로더가 주석은 제거하므로 안전).
    {
      echo "<!--"
      echo "  RAG 챗 시스템 프롬프트 — 진화 대상 챔피언 (v${NEW_VER}, $(basename "$BEST_PF") 승격)."
      echo "  스왑 = scripts/llm-prompt-evolve.sh 배치 승격. 롤백 = git revert."
      echo "-->"
      python3 - "$BEST_PF" <<'PYEOF'
import re, sys
raw = open(sys.argv[1], encoding="utf-8").read()
print(re.sub(r"<!--.*?-->", "", raw, flags=re.DOTALL).strip())
PYEOF
    } > "$CHAMPION"
    git -C "$PROJECT_DIR" add "$CHAMPION" "$LEDGER"
    git -C "$PROJECT_DIR" commit -m "[llm] RAG 챔피언 프롬프트 v${NEW_VER} 승격 — $(basename "$BEST_PF") (pass ${BEST_PASS}/${TOTAL} > 챔피언 ${CH_PASS}/${TOTAL})" \
      || log "WARN: git commit 실패(수동 확인)"
    log "✅ 승격 완료: champion v${NEW_VER} = $(basename "$BEST_PF") (컨테이너는 mtime 캐시로 즉시 반영)"
  fi
fi

log "완료. (MODE=$MODE)"
