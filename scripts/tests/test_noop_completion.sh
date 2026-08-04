#!/usr/bin/env bash
# 무변경 완료(no-op) 처분 판정 테스트 (CE-362 A).
#
# 배경(실측 CE-359): 정제 스펙이 "실제 파일 작성은 제외 범위" 라고 못박은 티켓에서 에이전트가
# 사실조사만 하고 `<promise>DONE</promise>` 로 정상 종료했는데, 파이프라인이 "커밋 0" 만 보고
# 실패·Backlog 처분했다. 에이전트는 스펙을 지켰고 판정이 틀렸다.
#
# 완화의 **안전핀은 워킹트리 클린**이다: "파일을 만들었는데 커밋만 못 한" 진짜 실패는 워킹트리가
# 더러우므로 완화에 걸리지 않아야 한다. 이 테스트가 고정하는 것이 바로 그 경계다.
#
# claude·Linear 를 호출하지 않는다. 판정식과 파이프라인 배선만 검증한다.
#
# Usage: bash scripts/tests/test_noop_completion.sh

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PIPELINE="$REPO_ROOT/scripts/auto_dev_pipeline.sh"

PASS=0; FAIL=0
ok()  { printf "  ✓ %s\n" "$1"; PASS=$((PASS+1)); }
bad() { printf "  ✗ %s\n      %s\n" "$1" "$2"; FAIL=$((FAIL+1)); }

# 파이프라인의 판정식을 그대로 재현(4조건 AND).
noop_ok() {  # noop_ok <impl_rc> <claude_log> <dirty>
    local rc="$1" log="$2" dirty="$3"
    [ "$rc" = "0" ] && grep -q "promise>DONE<" "$log" 2>/dev/null && [ -z "$dirty" ]
}

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
DONE_LOG="$TMP/done.log";    printf '{"type":"result","result":"...<promise>DONE</promise>"}\n' > "$DONE_LOG"
BLOCK_LOG="$TMP/blocked.log"; printf '{"type":"result","result":"...<promise>BLOCKED</promise> 사유"}\n' > "$BLOCK_LOG"
EMPTY_LOG="$TMP/empty.log";   : > "$EMPTY_LOG"

echo "[1/3] 파이프라인 배선"
grep -q "CE-362 A" "$PIPELINE" && ok "무변경 완료 분기 존재" || bad "분기 없음" "-"
grep -q "promise>DONE<" "$PIPELINE" && ok "DONE 선언 검사 존재" || bad "DONE 검사 없음" "-"
grep -q "impl_git status --porcelain" "$PIPELINE" && ok "워킹트리 클린 검사 존재" || bad "클린 검사 없음" "-"
grep -q "무변경 완료" "$PIPELINE" && ok "Linear 코멘트 근거 남김" || bad "코멘트 없음" "-"
bash -n "$PIPELINE" && ok "bash -n 통과" || bad "구문 오류" "-"

echo "[2/3] 완화가 적용되어야 하는 경우"
noop_ok 0 "$DONE_LOG" "" && ok "rc0 + DONE + 클린 → 무변경 완료" || bad "완화 미적용" "-"

echo "[3/3] 완화가 적용되면 안 되는 경우 (실패로 남아야 함)"
! noop_ok 0 "$DONE_LOG" " M docs/INSTALL.md" \
  && ok "파일 있는데 커밋 0(워킹트리 더러움) → 실패 유지 ← 안전핀" \
  || bad "커밋 누락이 완화로 빠져나감 — 위험" "-"
! noop_ok 1 "$DONE_LOG" ""        && ok "에이전트 비정상 종료(rc≠0) → 실패 유지" || bad "rc 무시됨" "-"
! noop_ok 0 "$BLOCK_LOG" ""       && ok "BLOCKED 선언 → 실패 유지" || bad "BLOCKED 가 완화됨" "-"
! noop_ok 0 "$EMPTY_LOG" ""       && ok "완료 선언 없음(빈 로그) → 실패 유지" || bad "무선언이 완화됨" "-"
! noop_ok 0 "$TMP/missing.log" "" && ok "로그 파일 부재 → 실패 유지" || bad "로그 부재가 완화됨" "-"
# git status --porcelain 실패 시 파이프라인은 "unknown" 을 넣는다 → 비어있지 않으므로 완화 차단.
! noop_ok 0 "$DONE_LOG" "unknown" && ok "git status 판독 실패(unknown) → 실패 유지" || bad "판독 실패가 완화됨" "-"

echo
if (( FAIL == 0 )); then echo "전체 통과: $PASS건"; exit 0
else echo "실패 $FAIL건 / 통과 $PASS건"; exit 1; fi
