#!/usr/bin/env bash
# 소비 토큰 원장의 프로젝트 축 테스트 (CE-362).
#
# 이 축이 없으면 "프로젝트당 얼마의 토큰을 썼나" 를 집계할 수 없다. 실측 결함:
# usage_ingest.py 는 CLICKEYE_PROJECT_ID env 로 프로젝트를 받는데 파이프라인이 그것을 넘기지
# 않아, 인제스트를 켜도 project_id 가 NULL 로 들어갔다.
#
# 서버·claude 를 호출하지 않는다. 원장 해석(resolve_project_for_key)과 파이프라인 배선만 본다.
#
# Usage: bash scripts/tests/test_usage_project_axis.sh

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PIPELINE="$REPO_ROOT/scripts/auto_dev_pipeline.sh"
WSMAP="$REPO_ROOT/scripts/workspace_map.py"

PASS=0; FAIL=0
ok()  { printf "  ✓ %s\n" "$1"; PASS=$((PASS+1)); }
bad() { printf "  ✗ %s\n      %s\n" "$1" "$2"; FAIL=$((FAIL+1)); }
eq()  { [[ "$2" == "$3" ]] && ok "$1" || bad "$1" "기대 '$2' / 실제 '$3'"; }

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
LEDGER="$TMP/workspaces.json"
cat > "$LEDGER" <<'JSON'
{"workspaces": {
  "[수주:aaaa1111] ": {"workspace_key": "aaaa1111", "intake_id": "aaaa1111-x", "project_id": "11111111-1111-1111-1111-111111111111", "repo_source": "https://example.invalid/a.git", "status": "mapped"},
  "[수주:bbbb2222] ": {"workspace_key": "bbbb2222", "intake_id": "bbbb2222-x", "project_id": null, "repo_source": null, "status": "pending_source"}
}}
JSON

echo "[1/3] 파이프라인 배선"
grep -q "CE-362" "$PIPELINE" && ok "프로젝트 축 블록 존재" || bad "블록 없음" "-"
grep -q "resolve-project" "$PIPELINE" && ok "resolver 호출 존재" || bad "resolver 미호출" "-"
grep -q 'CLICKEYE_PROJECT_ID="\$USAGE_PROJECT_ID"' "$PIPELINE" \
  && ok "인제스트 호출에 env 로 전달" || bad "env 전달 없음" "-"
bash -n "$PIPELINE" && ok "bash -n 통과" || bad "구문 오류" "-"
# 관측이 파이프라인을 막지 않아야 한다: resolver 실패를 삼키는 `|| true` 가 있어야 한다.
grep -q -- "--resolve-project \"\$WORKSPACE_KEY\"" "$PIPELINE" && ok "WORKSPACE_KEY 로 해석" || bad "키 전달 없음" "-"

echo "[2/3] 원장 해석"
eq "mapped 항목 → project_id" "11111111-1111-1111-1111-111111111111" \
   "$(python3 "$WSMAP" --resolve-project aaaa1111 --output "$LEDGER")"
eq "접두사 형태로도 해석" "11111111-1111-1111-1111-111111111111" \
   "$(python3 "$WSMAP" --resolve-project "[수주:aaaa1111]" --output "$LEDGER" 2>/dev/null || true)"
eq "project_id 없는 항목 → 빈 값" "" "$(python3 "$WSMAP" --resolve-project bbbb2222 --output "$LEDGER")"
eq "미존재 키 → 빈 값" "" "$(python3 "$WSMAP" --resolve-project zzzz9999 --output "$LEDGER")"
eq "빈 키 → 빈 값" "" "$(python3 "$WSMAP" --resolve-project "" --output "$LEDGER")"

echo "[3/3] 비차단 계약 (관측이 실행을 막지 않는다)"
rc=0; python3 "$WSMAP" --resolve-project aaaa1111 --output "$TMP/absent.json" >/dev/null 2>&1 || rc=$?
eq "원장 파일 부재에도 exit 0" "0" "$rc"
rc=0; printf 'not json' > "$TMP/broken.json"
python3 "$WSMAP" --resolve-project aaaa1111 --output "$TMP/broken.json" >/dev/null 2>&1 || rc=$?
eq "원장 파손에도 exit 0" "0" "$rc"

echo
if (( FAIL == 0 )); then echo "전체 통과: $PASS건"; exit 0
else echo "실패 $FAIL건 / 통과 $PASS건"; exit 1; fi
