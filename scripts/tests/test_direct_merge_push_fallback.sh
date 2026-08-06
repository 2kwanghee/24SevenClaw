#!/usr/bin/env bash
# direct-merge push 실패 fail-closed 테스트 (CE-409).
#
# 실측 결함: AUTO_MERGE 직접 머지에서 `git push origin main`(±push --delete) 이
# `|| log "WARN"` 으로 삼켜져 비-FF 거부에도 RUN_OUTCOME=merged 로 성공 처리됐다
# (CE-405 런: #128·#129 원격 선착으로 push 거부, 산출물이 로컬에만 남음).
#
# 실제 git 저장소로 "원격이 로컬보다 먼저 전진한" 비-FF 상황을 재현하고, 파이프라인의
# push 확인 로직(원격 반영 실증 + 1회 재시도 + reconcile 브랜치 PR 폴백)을 동일 순서로
# 재현해 단정한다(네트워크·claude 불요).
#
# Usage: bash scripts/tests/test_direct_merge_push_fallback.sh

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PIPELINE="$REPO_ROOT/scripts/auto_dev_pipeline.sh"

PASS=0; FAIL=0
ok()  { printf "  ✓ %s\n" "$1"; PASS=$((PASS+1)); }
bad() { printf "  ✗ %s\n      %s\n" "$1" "$2"; FAIL=$((FAIL+1)); }
eq()  { [[ "$2" == "$3" ]] && ok "$1" || bad "$1" "기대 '$2' / 실제 '$3'"; }

echo "[1/3] 배선 — push 확인 로직이 실제로 있는가"
grep -q 'ls-remote origin main' "$PIPELINE" \
  && ok "원격 반영 실증(ls-remote) 로직 존재" || bad "ls-remote 실증 없음" "-"
grep -q 'pull --no-rebase origin main' "$PIPELINE" \
  && ok "push 실패 시 pull --no-rebase 재시도" || bad "재시도 로직 없음" "-"
grep -q 'RECONCILE_BRANCH="fix/\${ISSUE_KEY}-reconcile"' "$PIPELINE" \
  && ok "reconcile 브랜치명 규칙" || bad "reconcile 브랜치명 없음" "-"
bash -n "$PIPELINE" && ok "bash -n 통과" || bad "구문 오류" "-"

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
git init -q --bare "$TMP/origin.git"

git clone -q "$TMP/origin.git" "$TMP/seed" 2>/dev/null
( cd "$TMP/seed" && git config user.email t@t && git config user.name t \
  && echo base > README.md && git add -A && git commit -qm "init" \
  && git branch -M main && git push -q origin main ) 2>/dev/null

# 파이프라인의 push 확인 로직(원격 반영 실증 + 1회 재시도 + reconcile 폴백)을 동일 순서로 재현
run_push_confirm() {   # $1=워크스페이스 디렉토리, $2=ISSUE_KEY
  local d="$1" issue_key="$2"
  local local_sha remote_sha push_ok="false"
  local_sha="$(git -C "$d" rev-parse main 2>/dev/null)"
  if git -C "$d" push origin main >/dev/null 2>&1; then
    remote_sha="$(git -C "$d" ls-remote origin main 2>/dev/null | awk '{print $1}')"
    [ -n "$remote_sha" ] && [ "$remote_sha" = "$local_sha" ] && push_ok="true"
  fi
  if [ "$push_ok" != "true" ]; then
    if git -C "$d" pull --no-rebase origin main >/dev/null 2>&1 && git -C "$d" push origin main >/dev/null 2>&1; then
      local_sha="$(git -C "$d" rev-parse main 2>/dev/null)"
      remote_sha="$(git -C "$d" ls-remote origin main 2>/dev/null | awk '{print $1}')"
      [ -n "$remote_sha" ] && [ "$remote_sha" = "$local_sha" ] && push_ok="true"
    else
      git -C "$d" merge --abort 2>/dev/null || true
    fi
  fi
  if [ "$push_ok" = "true" ]; then
    echo "merged"
  else
    local reconcile="fix/${issue_key}-reconcile"
    if git -C "$d" push origin "main:refs/heads/${reconcile}" >/dev/null 2>&1; then
      echo "pr"
    else
      echo "pr-no-reconcile"
    fi
    git -C "$d" fetch origin >/dev/null 2>&1 || true
    git -C "$d" reset --hard origin/main >/dev/null 2>&1 || true
  fi
}

echo "[2/3] 재시도(pull --no-rebase)도 실패하는 충돌 시나리오 → reconcile 브랜치 PR 폴백"
ISSUE_KEY="CE-409"
git clone -q "$TMP/origin.git" "$TMP/ws2" 2>/dev/null
( cd "$TMP/ws2" && git config user.email t@t && git config user.name t ) 2>/dev/null
( cd "$TMP/ws2" && git checkout -q -b ralph/CE-409-test2 \
  && echo "feature v2" > feature.md && git add -A && git commit -qm "T1" ) 2>/dev/null
( cd "$TMP/ws2" && git checkout -q main \
  && git merge --no-ff -q -m "Merge branch 'ralph/CE-409-test2': test2" ralph/CE-409-test2 ) 2>/dev/null

# 원격에 같은 파일을 다르게 고치는 충돌 커밋을 추가 push (다른 러너의 선착 머지 시뮬레이션)
git clone -q "$TMP/origin.git" "$TMP/other2" 2>/dev/null
( cd "$TMP/other2" && git config user.email t@t && git config user.name t \
  && git fetch -q origin && git checkout -q main \
  && echo other2 > feature.md && git add -A && git commit -qm "conflicting other run" \
  && git push -q origin main ) 2>/dev/null

RESULT2="$(run_push_confirm "$TMP/ws2" "$ISSUE_KEY")"
eq "충돌 재시도 실패 → PR 폴백(RUN_OUTCOME=pr)" "pr" "$RESULT2"

REMOTE_RECONCILE="$(git -C "$TMP/origin.git" branch --list "fix/${ISSUE_KEY}-reconcile")"
[[ -n "$REMOTE_RECONCILE" ]] \
  && ok "원격에 fix/${ISSUE_KEY}-reconcile 브랜치 존재(산출물 보존)" \
  || bad "reconcile 브랜치가 원격에 없음(산출물 유실)" "-"

echo "[3/3] 정상 push 경로 무회귀 — 원격 반영 실증"
git clone -q "$TMP/origin.git" "$TMP/ws3" 2>/dev/null
( cd "$TMP/ws3" && git config user.email t@t && git config user.name t ) 2>/dev/null
( cd "$TMP/ws3" && git checkout -q -b ralph/CE-409-test3 \
  && echo "feature v3" > feature3.md && git add -A && git commit -qm "T1" ) 2>/dev/null
( cd "$TMP/ws3" && git checkout -q main \
  && git merge --no-ff -q -m "Merge branch 'ralph/CE-409-test3': test3" ralph/CE-409-test3 ) 2>/dev/null

RESULT3="$(run_push_confirm "$TMP/ws3" "$ISSUE_KEY")"
eq "충돌 없는 정상 경로 → 머지 성공(RUN_OUTCOME=merged)" "merged" "$RESULT3"

LOCAL_SHA3="$(git -C "$TMP/ws3" rev-parse main 2>/dev/null)"
REMOTE_SHA3="$(git -C "$TMP/origin.git" rev-parse main 2>/dev/null)"
eq "원격 HEAD == 로컬 머지 커밋(ls-remote 실증)" "$LOCAL_SHA3" "$REMOTE_SHA3"

echo
if (( FAIL == 0 )); then echo "전체 통과: $PASS건"; exit 0
else echo "실패 $FAIL건 / 통과 $PASS건"; exit 1; fi
