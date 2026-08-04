#!/usr/bin/env bash
# 인테이크 단위 고객 브랜치 테스트 (CE-369).
#
# 실측 결함: 티켓마다 `ralph/<KEY>` 를 고객 **기본 브랜치**에서 새로 분기했다. 머지는 고객
# 몫(CE-347)이라 앞선 티켓 산출물이 기본 브랜치에 없으므로 의존 티켓 체인이 구조적으로
# 깨졌다(CE-368: CE-366 이 만든 docs/INSTALL.md 를 후속 티켓이 보지 못해 BLOCKED).
#
# 실제 git 저장소를 만들어 **base 선택 분기**를 검증한다(네트워크·claude 불요).
# 핵심 단정: 원격에 인테이크 브랜치가 있으면 그 위에 얹히고(체인 성립), 없으면 기본 브랜치에서
# 분기한다. 그리고 어떤 경우에도 **기본 브랜치는 변하지 않는다.**
#
# Usage: bash scripts/tests/test_intake_branch.sh

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PIPELINE="$REPO_ROOT/scripts/auto_dev_pipeline.sh"

PASS=0; FAIL=0
ok()  { printf "  ✓ %s\n" "$1"; PASS=$((PASS+1)); }
bad() { printf "  ✗ %s\n      %s\n" "$1" "$2"; FAIL=$((FAIL+1)); }
eq()  { [[ "$2" == "$3" ]] && ok "$1" || bad "$1" "기대 '$2' / 실제 '$3'"; }

echo "[1/4] 배선 — 이름 규칙과 분기 로직"
grep -q 'WS_BRANCH="clickeye/intake-\${WORKSPACE_KEY}"' "$PIPELINE" \
  && ok "인테이크 브랜치 이름 규칙" || bad "이름 규칙 없음" "-"
grep -q 'refs/remotes/origin/\${WS_BRANCH}' "$PIPELINE" \
  && ok "원격 존재 확인으로 base 결정" || bad "존재 확인 없음" "-"
grep -q 'impl_git fetch origin --prune' "$PIPELINE" \
  && ok "판정 전 fetch(원격 최신화)" || bad "fetch 없음" "-"
grep -q 'impl_git push origin "\$WS_BRANCH"' "$PIPELINE" \
  && ok "push 대상이 인테이크 브랜치" || bad "push 대상 미교체" "-"
# 게이트는 ticket-ref 때문에 head=BRANCH 를 유지하고 파일은 명시 전달해야 한다.
grep -q -- '--head "\$BRANCH" \\' "$PIPELINE" && ok "게이트 head 는 티켓 브랜치 유지" || bad "게이트 head 변경됨" "-"
grep -q -- '--diff-files "\$GATE_WS_FILES"' "$PIPELINE" \
  && ok "게이트에 고객 델타를 명시 전달" || bad "diff-files 없음" "-"
bash -n "$PIPELINE" && ok "bash -n 통과" || bad "구문 오류" "-"

echo "[2/4] base 선택 — 원격 인테이크 브랜치가 없을 때"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
git init -q --bare "$TMP/origin.git"
git clone -q "$TMP/origin.git" "$TMP/seed" 2>/dev/null
( cd "$TMP/seed" && git config user.email t@t && git config user.name t \
  && echo base > README.md && git add -A && git commit -qm "init" \
  && git branch -M main && git push -q origin main ) 2>/dev/null
git clone -q "$TMP/origin.git" "$TMP/ws" 2>/dev/null
( cd "$TMP/ws" && git config user.email t@t && git config user.name t ) 2>/dev/null

WS_BRANCH="clickeye/intake-abc12345"
run_base_select() {   # 파이프라인의 판정 로직을 동일 순서로 재현
  local d="$1"
  git -C "$d" fetch origin --prune -q 2>/dev/null || true
  if git -C "$d" rev-parse --verify --quiet "refs/remotes/origin/${WS_BRANCH}" >/dev/null 2>&1; then
    git -C "$d" checkout -q -B "$WS_BRANCH" "origin/${WS_BRANCH}" && echo "reuse"
  else
    git -C "$d" checkout -q main && git -C "$d" pull -q origin main 2>/dev/null
    git -C "$d" checkout -q -B "$WS_BRANCH" && echo "fresh"
  fi
}
eq "첫 티켓 → 기본 브랜치에서 신규 분기" "fresh" "$(run_base_select "$TMP/ws")"
eq "현재 브랜치가 인테이크 브랜치" "$WS_BRANCH" "$(git -C "$TMP/ws" branch --show-current)"

# 첫 티켓의 산출물을 커밋·push
( cd "$TMP/ws" && echo "first" > INSTALL.md && git add -A && git commit -qm "T1" \
  && git push -q origin "$WS_BRANCH" ) 2>/dev/null
ok "첫 티켓 산출물 push"

echo "[3/4] base 선택 — 원격 인테이크 브랜치가 있을 때 (체인 성립)"
# 후속 티켓은 새 clone 에서 시작한다고 가정(러너 재생성·다른 틱)
git clone -q "$TMP/origin.git" "$TMP/ws2" 2>/dev/null
( cd "$TMP/ws2" && git config user.email t@t && git config user.name t ) 2>/dev/null
eq "후속 티켓 → 기존 인테이크 브랜치 재사용" "reuse" "$(run_base_select "$TMP/ws2")"
[[ -f "$TMP/ws2/INSTALL.md" ]] \
  && ok "앞선 티켓 산출물이 보인다 ← 이 티켓의 목적" \
  || bad "앞선 산출물이 없다(체인 깨짐)" "INSTALL.md 부재"
eq "산출물 내용도 이어진다" "first" "$(cat "$TMP/ws2/INSTALL.md" 2>/dev/null)"

echo "[4/4] 기본 브랜치 불변 (가장 중요한 안전 단정)"
eq "origin/main 이 첫 커밋 그대로" "init" \
   "$(git -C "$TMP/origin.git" log --format=%s -1 main 2>/dev/null)"
eq "origin/main 에 산출물 없음" "" \
   "$(git -C "$TMP/origin.git" ls-tree --name-only main INSTALL.md 2>/dev/null)"

echo
if (( FAIL == 0 )); then echo "전체 통과: $PASS건"; exit 0
else echo "실패 $FAIL건 / 통과 $PASS건"; exit 1; fi
