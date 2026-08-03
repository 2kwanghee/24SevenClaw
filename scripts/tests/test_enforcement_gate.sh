#!/usr/bin/env bash
# P8 집행면 게이트 스모크 테스트 (CE-329) — 프레임워크 없이 순수 bash.
#
# 워크스페이스에 실제 배포되는 산출물(templates/harness-core/hooks/gitguard-gate.cjs)에
# skip-permissions 실행을 모사한 PreToolUse stdin 을 먹여 종료코드를 확인한다.
# 원본 infraeye-harness/install.sh 의 설치 직후 스모크 패턴을 따랐다.
#
# 세부 판정은 templates/harness-core/enforce 의 node:test 스위트(승계 80 + 어댑터)가
# 덮는다. 여기서 보는 것은 "배포되는 1파일이 node_modules 없이도 차단하는가" 뿐이다.
#
# 검증 축:
#   ① 번들 자족성 — node_modules 없는 격리 디렉터리에서 동작
#   ② `git commit --no-verify` → exit 2 (훅 우회 차단)
#   ③ `git status` → exit 0, 무출력 (정상 조작 무간섭)
#   ④ `git add -A` → exit 2 / `git add <파일>` → exit 0 (에이전트 정상 조작 통과)
#   ⑤ Write 내용의 자격증명 → exit 2
#   ⑥ 깨진 stdin·cwd 부재 → exit 2 (fail-closed)
#   ⑦ 번들 최상단 fail-closed 배너 존재
#
# 실행: bash scripts/tests/test_enforcement_gate.sh   (통과 0 / 실패 1)
set -uo pipefail

REPO="$(cd "$(dirname "$(readlink -f "$0")")/../.." && pwd)"
BUNDLE="$REPO/templates/harness-core/hooks/gitguard-gate.cjs"

PASS=0
FAIL=0
ok() { PASS=$((PASS + 1)); echo "  ✅ $1"; }
ng() { FAIL=$((FAIL + 1)); echo "  ❌ $1"; }

TMP="$(mktemp -d)"
cleanup() { chmod -R u+w "$TMP" 2>/dev/null; rm -rf "$TMP"; }
trap cleanup EXIT

echo "== P8 집행면 게이트 스모크 (CE-329) =="

if [ ! -f "$BUNDLE" ]; then
  ng "번들 없음: $BUNDLE (templates/harness-core/enforce 에서 npm run build 필요)"
  echo "결과: 통과 $PASS / 실패 $FAIL"
  exit 1
fi

# ① 자족성 — 번들만 격리 디렉터리로 옮겨 node_modules 없이 실행한다
GATE="$TMP/isolated/gitguard-gate.cjs"
mkdir -p "$TMP/isolated" "$TMP/ws"
cp "$BUNDLE" "$GATE"
WS="$TMP/ws"

# skip-permissions 실행을 모사한 PreToolUse payload
payload() {
  node -e '
const [tool, json, cwd] = process.argv.slice(1);
process.stdout.write(JSON.stringify({
  session_id: "ce329-smoke",
  cwd,
  permission_mode: "bypassPermissions",
  hook_event_name: "PreToolUse",
  tool_name: tool,
  tool_input: JSON.parse(json),
}));
' "$1" "$2" "$WS"
}

# run <기대코드> <라벨> <stdin>
run() {
  local want="$1" label="$2" input="$3" code
  local err="$TMP/err.txt"
  printf '%s' "$input" | node "$GATE" >"$TMP/out.txt" 2>"$err"
  code=$?
  if [ "$code" != "$want" ]; then
    ng "$label — exit $code (기대 $want)"
    sed 's/^/      /' "$err" | head -4
    return 1
  fi
  ok "$label — exit $code"
  return 0
}

# ② 훅 우회 차단
if run 2 "git commit --no-verify 차단" "$(payload Bash '{"command":"git commit --no-verify -m x"}')"; then
  grep -q 'G-02' "$TMP/err.txt" \
    && ok "차단 사유가 G-02 (배선 정상 — 어댑터 자체 오류가 아니다)" \
    || ng "exit 2 이지만 G-02 사유가 아니다: $(head -c 200 "$TMP/err.txt")"
fi

# ③ 정상 조작 무간섭
if run 0 "git status 통과" "$(payload Bash '{"command":"git status"}')"; then
  [ ! -s "$TMP/err.txt" ] && ok "통과는 무출력" || ng "통과인데 stderr 출력이 있다: $(head -c 200 "$TMP/err.txt")"
fi

# ④ 에이전트 정상 조작 vs 일괄 스테이징
run 2 "git add -A 차단" "$(payload Bash '{"command":"git add -A"}')"
run 0 "git add <파일> 통과" "$(payload Bash '{"command":"git add src/x.ts"}')"
run 0 "git commit 통과 (integrateRoots 주입)" "$(payload Bash '{"command":"git commit -m msg"}')"
run 2 "clone 밖 git -C 차단" "$(payload Bash '{"command":"git -C /tmp status"}')"

# ⑤ 비밀 스캔
if run 2 "Write 자격증명 차단" "$(payload Write '{"file_path":"cfg.ts","content":"const k = \"AKIAIOSFODNN7EXAMPLE\";"}')"; then
  grep -q 'G-03' "$TMP/err.txt" \
    && ok "차단 사유가 G-03" \
    || ng "exit 2 이지만 G-03 사유가 아니다: $(head -c 200 "$TMP/err.txt")"
fi
run 0 "Write 정상 내용 통과" "$(payload Write '{"file_path":"cfg.ts","content":"export const x = 1;\n"}')"

# ⑤-b 작업면 경계 (E-01) — Bash 의 cd·git -C 경계를 쓰기 툴에도 적용
if run 2 "clone 밖 Write 차단" "$(payload Write '{"file_path":"../../etc/evil.txt","content":"x"}')"; then
  grep -q 'E-01' "$TMP/err.txt" \
    && ok "차단 사유가 E-01 (작업면 경계)" \
    || ng "exit 2 이지만 E-01 경계 거부가 아니다: $(head -c 200 "$TMP/err.txt")"
fi
run 0 "clone 안 Write 통과" "$(payload Write '{"file_path":"src/app.ts","content":"export const x = 1;\n"}')"

# ⑤-c Bash 경유 평문 비밀 (방어 깊이 — 원본 범위 밖)
run 2 "echo 로 쓰는 자격증명 차단" "$(payload Bash '{"command":"echo AKIAIOSFODNN7EXAMPLE > cfg.env"}')"
run 0 "일상 명령 오탐 없음(git log)" "$(payload Bash '{"command":"git log --oneline -20"}')"

# ⑤-d 게이트 자기보호 (E-02) — 번들이 지워지면 훅이 rc=1(자문형)이 되어 조용히 열린다
mkdir -p "$WS/.claude/hooks" "$WS/.harness"
: > "$WS/.claude/hooks/gitguard-gate.cjs"; : > "$WS/.claude/settings.json"
if run 2 "훅 번들 삭제 차단" "$(payload Bash '{"command":"rm -f .claude/hooks/gitguard-gate.cjs"}')"; then
  grep -q 'E-02' "$TMP/err.txt" \
    && ok "차단 사유가 E-02 (자기보호)" \
    || ng "exit 2 이지만 E-02 자기보호 거부가 아니다: $(head -c 200 "$TMP/err.txt")"
fi
run 2 "settings.json 변조 차단" "$(payload Write '{"file_path":".claude/settings.json","content":"{}"}')"
run 0 "보호 경로 읽기는 통과" "$(payload Bash '{"command":"cat .claude/settings.json"}')"

# ⑤-e 불투명 실행 표면 (E-03) — 좁은 표적만. 정상 빌드 명령은 반드시 통과해야 한다
run 2 "파이프로 셸 먹이기 차단" "$(payload Bash '{"command":"echo \"git add .\" | bash"}')"
run 2 "git 대시 디스패치 차단" "$(payload Bash '{"command":"git-stash"}')"
run 0 "npm run 통과(무인 체인 필수)" "$(payload Bash '{"command":"npm run build"}')"
run 0 "make 통과(무인 체인 필수)" "$(payload Bash '{"command":"make build"}')"

# ⑤-f 비문자열 command (형태 깨짐 = 거부)
run 2 "command 배열 차단" "{\"cwd\":\"$WS\",\"tool_name\":\"Bash\",\"tool_input\":{\"command\":[\"git\",\"stash\"]}}"

# ⑥ fail-closed
run 2 "깨진 stdin 차단" 'not-json{{'
run 2 "빈 stdin 차단" ''
run 2 "cwd 부재 차단" '{"tool_name":"Bash","tool_input":{"command":"git status"}}'
run 2 "tool_name 부재 차단" "{\"cwd\":\"$WS\",\"tool_input\":{\"command\":\"git add -A\"}}"

# ⑦ 배너 — 모듈 로딩 예외가 exit 1(자문형)로 새는 것을 막는 최후 방어선
head -n 1 "$GATE" | grep -qx 'process.exitCode = 2;' \
  && ok "번들 최상단 fail-closed 배너 존재" \
  || ng "번들 첫 줄이 process.exitCode = 2 가 아니다: $(head -n 1 "$GATE")"

# 감사 로그 — 차단 판정만 남는다
if [ -f "$WS/.harness/enforce-audit.jsonl" ]; then
  ok "감사 로그 기록됨 ($(grep -c '' "$WS/.harness/enforce-audit.jsonl")줄)"
else
  ng "차단이 있었는데 감사 로그가 없다: $WS/.harness/enforce-audit.jsonl"
fi

echo
echo "결과: 통과 $PASS / 실패 $FAIL"
[ "$FAIL" -eq 0 ] || exit 1
