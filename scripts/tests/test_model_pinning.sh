#!/usr/bin/env bash
# 모델 티어 고정 테스트 (CE-367).
#
# 실측 결함(2026-08-04, CLI 2.1.221): `--model sonnet` **별칭**이 `claude-opus-4-8` 로
# 해석됐다. 구현 1건이 의도 대비 캐시 읽기 2.5배·환산액 2.5배로 실행됐고, **로그에 흔적이
# 없었다**(조용한 원가 누출). 정식 모델명은 정확히 해석된다.
#
# 이 테스트는 claude 를 호출하지 않는다(모델 해석은 CLI·서버 소관). 검증 대상은
#   ① 배치 스크립트가 **별칭을 쓰지 않는다**
#   ② 티어가 변수 한 곳에 모여 있고 env 로 덮을 수 있다
#   ③ 실행 후 불일치를 관측하는 배선이 있다
# 이 세 가지가 유지되는지 고정한다.
#
# Usage: bash scripts/tests/test_model_pinning.sh

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PIPELINE="$REPO_ROOT/scripts/auto_dev_pipeline.sh"

PASS=0; FAIL=0
ok()  { printf "  ✓ %s\n" "$1"; PASS=$((PASS+1)); }
bad() { printf "  ✗ %s\n      %s\n" "$1" "$2"; FAIL=$((FAIL+1)); }

echo "[1/4] 별칭 사용 금지 (전 배치 스크립트)"
# 주석은 제외하고 실제 인자만 본다 — 근거 주석에는 별칭 문자열이 남아 있어야 한다.
ALIAS_HITS="$(grep -rn -- "--model \(sonnet\|opus\|haiku\|fable\)\b" "$REPO_ROOT"/scripts/*.sh 2>/dev/null \
  | grep -v "^\s*#" | grep -vE ":[0-9]+:\s*#" || true)"
[[ -z "$ALIAS_HITS" ]] && ok "별칭 인자 0건" || bad "별칭 사용 잔존" "$ALIAS_HITS"

echo "[2/4] 티어 변수 (단일 지점 + env 오버라이드)"
grep -q 'PIPELINE_MODEL_REFINE="\${PIPELINE_MODEL_REFINE:-claude-sonnet-5}"' "$PIPELINE" \
  && ok "정제 티어 변수 + 기본 정식명" || bad "정제 티어 변수 없음/별칭" "-"
grep -q 'PIPELINE_MODEL_IMPL="\${PIPELINE_MODEL_IMPL:-claude-sonnet-5}"' "$PIPELINE" \
  && ok "구현 티어 변수 + 기본 정식명" || bad "구현 티어 변수 없음/별칭" "-"
grep -q -- '--model "\$PIPELINE_MODEL_REFINE"' "$PIPELINE" \
  && ok "정제 호출이 변수 사용" || bad "정제 호출 하드코딩" "-"
grep -q -- '--model "\$PIPELINE_MODEL_IMPL"' "$PIPELINE" \
  && ok "구현 호출이 변수 사용" || bad "구현 호출 하드코딩" "-"
# 기본값이 정식 모델명 형태인지(별칭이 기본값으로 새어 들어오는 것을 막는다)
for v in PIPELINE_MODEL_REFINE PIPELINE_MODEL_IMPL; do
  def="$(grep -oP "${v}=\"\\\$\{${v}:-\K[^}\"]+" "$PIPELINE" | head -1)"
  [[ "$def" == claude-*-* ]] && ok "$v 기본값이 정식명($def)" || bad "$v 기본값이 별칭 형태" "$def"
done

echo "[3/4] 불일치 관측 배선"
grep -q "실행 모델 불일치" "$PIPELINE" && ok "WARN 로그 존재" || bad "WARN 없음" "-"
grep -q "model_mismatch" "$PIPELINE" && ok "메트릭 이벤트 기록" || bad "메트릭 없음" "-"
grep -q '"subtype":"init"' "$PIPELINE" && ok "init 이벤트에서 실제 모델 파싱" || bad "파싱 없음" "-"

echo "[4/4] 구문"
bash -n "$PIPELINE" && ok "auto_dev_pipeline.sh" || bad "구문 오류" "-"
for s in ralph-loop.sh prompt-evolve-eval.sh; do
  bash -n "$REPO_ROOT/scripts/$s" && ok "$s" || bad "$s 구문 오류" "-"
done

echo
if (( FAIL == 0 )); then echo "전체 통과: $PASS건"; exit 0
else echo "실패 $FAIL건 / 통과 $PASS건"; exit 1; fi
