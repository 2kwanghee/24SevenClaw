#!/usr/bin/env bash
# 메타프롬프트 정제 프롬프트 조립 회귀 테스트.
#
# 실측 결함(2026-08-04): `REFINE_PROMPT="$(cat SKILL.md)…"` 가 SKILL.md 의 `---` YAML
# 프론트매터로 시작하는 문자열을 claude 의 첫 인자로 넘겨, CLI 가 그것을 옵션으로 파싱해
# `error: unknown option '---…'` 로 즉시 죽었다. 파이프라인은 이를 "정제 실패/빈 출력" 으로
# 흡수하고 fix_plan 폴백으로 계속 진행하므로 **전 티켓에서 기획 단계가 조용히 빠져 있었다**
# (logs/pipeline-cron.log 에 4회 기록).
#
# 이 테스트는 claude 를 호출하지 않는다(비용·비결정성 배제). 검증 대상은 조립 결과 문자열의
# **첫 글자가 `-` 가 아니라는 것** 하나다 — 그것이 CLI 옵션 오인의 필요조건이었다.
#
# Usage: bash scripts/tests/test_refine_prompt.sh

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PIPELINE="$PROJECT_ROOT/scripts/auto_dev_pipeline.sh"
SKILL="$PROJECT_ROOT/.claude/skills/metaprompt/SKILL.md"

PASS=0; FAIL=0
check() {
    if [[ "$2" == "$3" ]]; then printf "  ✓ %s\n" "$1"; PASS=$((PASS+1))
    else printf "  ✗ %s\n      기대: %q\n      실제: %q\n" "$1" "$2" "$3"; FAIL=$((FAIL+1)); fi
}

# 파이프라인이 쓰는 프론트매터 제거 awk 를 그대로 재현(로직이 갈라지면 이 테스트가 무의미하므로
# 파이프라인 본문에서 해당 awk 가 살아있는지도 함께 확인한다).
strip_frontmatter() {
    awk '
      NR==1 && /^---[[:space:]]*$/ { fm=1; next }
      fm  && /^---[[:space:]]*$/   { fm=0; next }
      !fm
    ' "$1"
}

echo "[1/4] 파이프라인 배선 확인"
grep -q "METAPROMPT_BODY=" "$PIPELINE" \
  && check "METAPROMPT_BODY 조립 존재" "yes" "yes" || check "METAPROMPT_BODY 조립 존재" "yes" "no"
grep -q '^REFINE_PROMPT="# 정제 지침\|REFINE_PROMPT="# 정제 지침' "$PIPELINE" \
  && check "REFINE_PROMPT 이 '#' 헤더로 시작" "yes" "yes" || check "REFINE_PROMPT 이 '#' 헤더로 시작" "yes" "no"

echo "[2/4] 실제 SKILL.md 프론트매터 제거"
if [[ -f "$SKILL" ]]; then
    first_raw="$(head -c 3 "$SKILL")"
    check "SKILL.md 는 프론트매터로 시작한다(전제)" "---" "$first_raw"
    body="$(strip_frontmatter "$SKILL")"
    first_body="${body:0:1}"
    [[ "$first_body" != "-" ]] && check "제거 후 첫 글자가 '-' 가 아니다" "ok" "ok" \
                               || check "제거 후 첫 글자가 '-' 가 아니다" "ok" "dash:$first_body"
    grep -q "name: metaprompt" <<< "$body" && check "프론트매터 필드가 남지 않았다" "no" "yes" \
                                           || check "프론트매터 필드가 남지 않았다" "no" "no"
else
    echo "  - SKILL.md 없음 — 실파일 검증 skip"
fi

echo "[3/4] 합성 케이스"
tmp="$(mktemp)"
printf -- '---\nname: t\nmodel: sonnet\n---\n\n# 본문 시작\n내용\n' > "$tmp"
out="$(strip_frontmatter "$tmp")"
check "프론트매터만 제거되고 본문 보존" "# 본문 시작" "$(printf '%s' "$out" | sed -n '2p')"
[[ "${out:0:1}" != "-" ]] && check "합성 케이스 첫 글자 안전" "ok" "ok" || check "합성 케이스 첫 글자 안전" "ok" "dash"

printf -- '# 프론트매터 없는 파일\n본문\n' > "$tmp"
out="$(strip_frontmatter "$tmp")"
check "프론트매터 없으면 원본 그대로" "# 프론트매터 없는 파일" "$(printf '%s' "$out" | head -1)"

printf -- '---\nonly: front\n' > "$tmp"   # 닫는 --- 이 없는 깨진 파일
out="$(strip_frontmatter "$tmp")"
check "닫히지 않은 프론트매터는 전부 흡수(빈 본문)" "" "$(printf '%s' "$out")"
rm -f "$tmp"

echo "[4/4] 최종 조립 문자열"
# 파이프라인과 동일한 순서로 조립했을 때 첫 글자가 '-' 가 아닌지(= CLI 가 옵션으로 오인하지 않음)
if [[ -f "$SKILL" ]]; then
    assembled="# 정제 지침 (metaprompt 스킬)

$(strip_frontmatter "$SKILL")

---

# 정제 대상 태스크"
    [[ "${assembled:0:1}" == "#" ]] && check "조립 결과가 '#' 로 시작" "ok" "ok" \
                                    || check "조립 결과가 '#' 로 시작" "ok" "${assembled:0:1}"
fi

echo
if (( FAIL == 0 )); then echo "전체 통과: $PASS건"; exit 0
else echo "실패 $FAIL건 / 통과 $PASS건"; exit 1; fi
