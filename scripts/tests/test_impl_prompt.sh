#!/usr/bin/env bash
# build_impl_prompt() 회귀 테스트 (CE-356) — self-repo / 워크스페이스 분기.
#
# 실측 결함: 구현 콜이 고객 clone 으로 cwd 를 옮기는데도 `.ralph/PROMPT.md` 를 그대로 넘겨,
# 그 프롬프트가 지시하는 `.ralph/PLAN.md`·`fix_plan.md` 를 에이전트가 찾지 못해 BLOCKED 로
# 끝났다(커밋 0 → 딜리버리 실패, CE-355). 이 테스트가 고정하는 것:
#   ① self-repo 모드 출력은 이전과 동일하다(회귀 0 — 이게 깨지면 자기레포 개발이 망가진다)
#   ② 워크스페이스 모드는 워크스페이스 전용 프롬프트를 쓴다
#   ③ 워크스페이스 모드는 스펙을 **인라인**한다(파일 경로 의존 제거)
#   ④ 스펙이 비면 "구현하지 말고 BLOCKED" 지시가 들어간다
#
# claude 를 호출하지 않는다 — 검증 대상은 조립 문자열뿐이다.
#
# Usage: bash scripts/tests/test_impl_prompt.sh

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PIPELINE="$REPO_ROOT/scripts/auto_dev_pipeline.sh"

PASS=0; FAIL=0
ok()   { printf "  ✓ %s\n" "$1"; PASS=$((PASS+1)); }
bad()  { printf "  ✗ %s\n      %s\n" "$1" "$2"; FAIL=$((FAIL+1)); }
has()  { grep -qF -- "$2" <<< "$1"; }

# 함수만 떼어 로드(파이프라인 본체 실행 금지).
eval "$(sed -n '/^build_impl_prompt()/,/^}/p' "$PIPELINE")"
declare -f build_impl_prompt >/dev/null || { echo "build_impl_prompt 추출 실패"; exit 1; }

# 샌드박스: PROJECT_DIR 을 임시 디렉터리로 바꿔 실제 레포 파일을 건드리지 않는다.
SANDBOX="$(mktemp -d)"
trap 'rm -rf "$SANDBOX"' EXIT
PROJECT_DIR="$SANDBOX"
mkdir -p "$SANDBOX/.ralph" "$SANDBOX/templates/harness-core" "$SANDBOX/ws"
printf '# Ralph Loop — self repo 프롬프트\n.ralph/PLAN.md 를 읽어라\n' > "$SANDBOX/.ralph/PROMPT.md"
printf '# 워크스페이스 프롬프트\n파일을 찾지 마라\n' > "$SANDBOX/templates/harness-core/PROMPT.workspace.md"

echo "[1/5] self-repo 모드 — 정제 스펙 없음"
out="$(build_impl_prompt "$SANDBOX" "$SANDBOX/.ralph/refined/none.md" "CE-1" "제목")"
expected="$(cat "$SANDBOX/.ralph/PROMPT.md")"
[[ "$out" == "$expected" ]] && ok "PROMPT.md 를 그대로 넘긴다(바이트 동일)" \
                            || bad "PROMPT.md 원문과 다르다" "$(head -2 <<< "$out")"

echo "[2/5] self-repo 모드 — 정제 스펙 있음"
mkdir -p "$SANDBOX/.ralph/refined"
printf '정제된 스펙 본문 XYZ\n' > "$SANDBOX/.ralph/refined/CE-1.md"
out="$(build_impl_prompt "$SANDBOX" "$SANDBOX/.ralph/refined/CE-1.md" "CE-1" "제목")"
has "$out" "## 정제된 구현 스펙" && ok "정제 스펙 헤더가 앞에 붙는다" || bad "정제 스펙 헤더 없음" "-"
has "$out" "정제된 스펙 본문 XYZ" && ok "정제 스펙 본문 포함" || bad "정제 본문 없음" "-"
has "$out" "# Ralph Loop" && ok "self 프롬프트가 뒤에 이어진다" || bad "self 프롬프트 없음" "-"

echo "[3/5] 워크스페이스 모드 — 스펙 인라인"
printf '## 수용 기준\n- README 에 개요 섹션\n' > "$SANDBOX/.ralph/PLAN.md"
out="$(build_impl_prompt "$SANDBOX/ws" "$SANDBOX/.ralph/refined/absent.md" "CE-355" "리허설 티켓")"
has "$out" "# 워크스페이스 프롬프트" && ok "워크스페이스 전용 프롬프트를 쓴다" || bad "전용 프롬프트 미사용" "-"
! has "$out" "# Ralph Loop" && ok "self 프롬프트가 섞이지 않는다" || bad "self 프롬프트 혼입" "-"
has "$out" "README 에 개요 섹션" && ok "PLAN.md 스펙이 인라인된다" || bad "스펙 인라인 안 됨" "-"
has "$out" "티켓: CE-355" && ok "티켓 키가 들어간다" || bad "티켓 키 없음" "-"
has "$out" "제목: 리허설 티켓" && ok "제목이 들어간다" || bad "제목 없음" "-"
has "$out" "파일을 찾지 말고" && ok "파일 탐색 금지 지시가 있다" || bad "파일 탐색 금지 지시 없음" "-"

echo "[4/5] 워크스페이스 모드 — 정제 스펙 우선"
out="$(build_impl_prompt "$SANDBOX/ws" "$SANDBOX/.ralph/refined/CE-1.md" "CE-1" "제목")"
has "$out" "정제된 스펙 본문 XYZ" && ok "정제 스펙이 PLAN.md 보다 우선" || bad "정제 우선 아님" "-"
! has "$out" "README 에 개요 섹션" && ok "PLAN.md 는 쓰이지 않는다" || bad "PLAN.md 가 섞였다" "-"

echo "[5/5] 경계"
rm -f "$SANDBOX/.ralph/PLAN.md"
out="$(build_impl_prompt "$SANDBOX/ws" "$SANDBOX/.ralph/refined/absent.md" "CE-9" "제목")"
has "$out" "BLOCKED 로 보고하라" && ok "스펙 없으면 BLOCKED 지시" || bad "빈 스펙 안내 없음" "-"

# 워크스페이스 프롬프트 파일이 없으면(구버전 조달) self 경로로 안전 폴백해야 한다.
rm -f "$SANDBOX/templates/harness-core/PROMPT.workspace.md"
printf '## 수용 기준\n' > "$SANDBOX/.ralph/PLAN.md"
out="$(build_impl_prompt "$SANDBOX/ws" "$SANDBOX/.ralph/refined/absent.md" "CE-9" "제목")"
[[ "$out" == "$(cat "$SANDBOX/.ralph/PROMPT.md")" ]] \
  && ok "전용 프롬프트 부재 시 self 프롬프트로 폴백" || bad "폴백 실패" "$(head -1 <<< "$out")"

echo
if (( FAIL == 0 )); then echo "전체 통과: $PASS건"; exit 0
else echo "실패 $FAIL건 / 통과 $PASS건"; exit 1; fi
