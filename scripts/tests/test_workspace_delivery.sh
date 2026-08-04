#!/usr/bin/env bash
# 고객 레포 딜리버리 리다이렉트 통합 테스트 (CE-347) — 프레임워크 없이 순수 bash.
#
# 임시 디렉터리에 "가짜 PRIMARY 레포"(스텁 스크립트 + git init)와 "고객 bare 레포 + clone"을
# 세우고, 실제 auto_dev_pipeline.sh 를 --once 로 구동해 리다이렉트 결과를 git 상태로 검증한다.
# Linear·Telegram·PR·claude·docker 는 전부 스텁이라 네트워크가 필요 없다. 거버넌스는
# **실제** pre_merge_gate.py + governance 커널을 심볼릭으로 붙여 그대로 돌린다.
#
# 검증 축:
#   ① 토글 off + 워크스페이스 모드 → 원본 경로(허상 재현: 고객 bare 에 아무 것도 안 감)
#   ② 토글 on + 자기레포(IMPL_WORKDIR==PROJECT_DIR) → 원본 경로(리다이렉트 미발동)
#   ③ 고객 기본 브랜치 감지 3단: origin/HEAD → .clickeye_default_branch → 둘 다 없으면 실패
#   ④ 정상: 고객 clone 에 태스크 브랜치 + 커밋 → bare 에 브랜치 존재, 기본 브랜치 불변
#   ⑤ 구현 커밋 없음 → 실패 판정(rev-list 0), push 없음
#   ⑥ push 거부(bare pre-receive exit 1) → 실패 + 로컬 브랜치·커밋 보존
#   ⑦ 중립 정책: 고객 레포의 *auth* 변경이 block/HIGH 로 오분류되지 않음 + ticket-ref 시맨틱 유지
#   ⑧ 기본 브랜치 develop 픽스처 → base·push 가 develop 기준
#
# 실행: bash scripts/tests/test_workspace_delivery.sh   (통과 0 / 실패 1)
set -uo pipefail

REPO="$(cd "$(dirname "$(readlink -f "$0")")/../.." && pwd)"
PIPELINE="$REPO/scripts/auto_dev_pipeline.sh"
POLICY="$REPO/templates/harness-core/governance-workspace.policy.json"

PASS=0
FAIL=0
ISSUE_KEY="CE-999"
BRANCH="ralph/$ISSUE_KEY"

TMP="$(mktemp -d)"
cleanup() { chmod -R u+w "$TMP" 2>/dev/null; rm -rf "$TMP"; }
# CE_KEEP_FIXTURES=1 로 실행하면 픽스처를 남긴다 — 실패 시 run.log·고객 bare 를 들여다보려면
# 정리를 막아야 하는데, 이전에는 그 방법이 없어 진단이 어려웠다.
if [ -n "${CE_KEEP_FIXTURES:-}" ]; then
  printf '[keep] 픽스처 보존: %s\n' "$TMP"
else
  trap cleanup EXIT
fi

export GIT_AUTHOR_NAME="ce347-test" GIT_AUTHOR_EMAIL="ce347@example.com"
export GIT_COMMITTER_NAME="ce347-test" GIT_COMMITTER_EMAIL="ce347@example.com"

# ── 판정 헬퍼 ───────────────────────────────────────────────────────────────
ok()   { PASS=$((PASS + 1)); echo "  ✅ $1"; }
ng()   { FAIL=$((FAIL + 1)); echo "  ❌ $1"; }
want_log() {   # want_log <로그파일> <패턴> <설명>
  grep -q -- "$2" "$1" 2>/dev/null && ok "$3" || ng "$3 (로그에 '$2' 없음: $1)"
}
deny_log() {
  grep -q -- "$2" "$1" 2>/dev/null && ng "$3 (로그에 '$2' 존재: $1)" || ok "$3"
}
want_ref() {   # want_ref <repo> <ref> <설명>
  git -C "$1" rev-parse --verify --quiet "$2" >/dev/null 2>&1 \
    && ok "$3" || ng "$3 (ref 없음: $2 @ $1)"
}
deny_ref() {
  git -C "$1" rev-parse --verify --quiet "$2" >/dev/null 2>&1 \
    && ng "$3 (ref 존재: $2 @ $1)" || ok "$3"
}
want_eq() {    # want_eq <실제> <기대> <설명>
  [ "$1" = "$2" ] && ok "$3" || ng "$3 (실제='$1' 기대='$2')"
}

# ── 스텁 실행 파일 (docker / claude) ───────────────────────────────────────
BIN="$TMP/bin"
mkdir -p "$BIN"
cat > "$BIN/docker" <<'EOF'
#!/usr/bin/env bash
# DB 기동 확인 단계를 통과시키는 스텁 — docker compose 는 호출되지 않는다.
[ "${1:-}" = "ps" ] && echo "sevenclaw-db  Up" && exit 0
exit 0
EOF
cat > "$BIN/claude" <<'EOF'
#!/usr/bin/env bash
# 구현 에이전트 스텁 — cwd(= STEP B 의 IMPL_WORKDIR)에 산출물을 만들고 커밋한다.
#   STUB_CLAUDE_COMMIT=0   커밋 없이 종료(구현 커밋 없음)
#   STUB_CLAUDE_DETACH=1   detached HEAD 로 옮긴 뒤 커밋(태스크 브랜치에 안 얹히는 사고)
#   STUB_CLAUDE_POLLUTE=1  하네스 운영 파일(fix_plan.md)까지 커밋(고객 레포 오염 사고)
if [ "${STUB_CLAUDE_COMMIT:-1}" != "1" ]; then
  echo '{"type":"result","subtype":"stub_no_commit"}'
  exit 0
fi
if [ "${STUB_CLAUDE_DETACH:-0}" = "1" ]; then
  git checkout -q --detach HEAD >/dev/null 2>&1
fi
f="${STUB_CLAUDE_FILE:-impl_feature.txt}"
# 티켓별로 내용을 다르게 쓴다. 고정 문자열이면 **같은 브랜치를 이어 쓰는 2회차**(CE-369 의
# 인테이크 단위 브랜치)에서 이미 같은 내용이 있어 변경이 0 → 커밋 없음으로 오판된다.
# 실제 티켓은 서로 다른 일을 하므로 스텁도 그것을 반영해야 한다.
printf '구현 산출물(스텁) %s\n' "${STUB_ISSUE_KEY:-CE-999}" > "$f"
git add -- "$f" >/dev/null 2>&1
if [ "${STUB_CLAUDE_POLLUTE:-0}" = "1" ]; then
  printf '# fix_plan (하네스 운영 파일)\n' > fix_plan.md
  git add -- fix_plan.md >/dev/null 2>&1
fi
git commit -q -m "[stub] 구현 커밋" >/dev/null 2>&1
echo '{"type":"result","subtype":"stub_committed"}'
EOF
chmod +x "$BIN"/docker "$BIN"/claude
export PATH="$BIN:$PATH"

# ── 가짜 PRIMARY 레포 구성 ──────────────────────────────────────────────────
# pipeline_config.sh 를 복사해 _FLOWOPS_CONFIG_DIR 가 이 임시 레포를 가리키게 한다
# (실 레포 .env 의 FLOWOPS_* 가 시나리오 env 를 덮어쓰지 않도록 = 테스트 격리).
build_primary() {   # build_primary <경로>
  local P="$1"
  mkdir -p "$P/scripts" "$P/.ralph/tasks" "$P/templates/harness-core" "$P/logs" "$P/workspaces"
  cp "$REPO/scripts/pipeline_config.sh" "$P/scripts/"
  cp "$PIPELINE" "$P/scripts/"
  cp "$REPO/scripts/pre_merge_gate.py" "$P/scripts/"
  cp "$POLICY" "$P/templates/harness-core/"
  ln -s "$REPO/governance" "$P/governance"

  # Linear·알림·PR 스텁 — 전부 무동작 exit 0 (네트워크 0)
  local s
  for s in telegram_notify.py auto_pr_creator.py retry_ledger.py pipeline_metrics.py; do
    printf '#!/usr/bin/env python3\nimport sys\nsys.exit(0)\n' > "$P/scripts/$s"
  done
  # 상태 전이 관측용 스텁 — 호출 인자를 .ralph/stub_calls.log 에 남긴다(시나리오 ⑪).
  for s in linear_tracker.py linear_reporter.py; do
    cat > "$P/scripts/$s" <<'PY'
#!/usr/bin/env python3
"""상태 전이 스텁 — 호출 사실과 인자만 기록한다(네트워크 0)."""
import os
import sys

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
log = os.path.join(root, ".ralph", "stub_calls.log")
os.makedirs(os.path.dirname(log), exist_ok=True)
with open(log, "a", encoding="utf-8") as fh:
    fh.write(os.path.basename(__file__) + " " + " ".join(sys.argv[1:]) + "\n")
sys.exit(0)
PY
  done

  # 스텁 watcher — 태스크를 **1회만** 내주고(exit 0) 이후 exit 2(잔여 없음).
  # 실패 경로의 continue 가 무한루프가 되지 않도록 종료를 보장한다.
  cat > "$P/scripts/linear_watcher.py" <<'PY'
#!/usr/bin/env python3
"""스텁 Linear watcher — 태스크 1건을 1회만 수거하고 이후 '잔여 없음'(exit 2)."""
import json
import os
import sys

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ralph = os.path.join(root, ".ralph")
counter = os.path.join(ralph, ".stub_watch_count")
try:
    with open(counter, encoding="utf-8") as fh:
        n = int(fh.read().strip() or "0")
except (OSError, ValueError):
    n = 0
n += 1
os.makedirs(ralph, exist_ok=True)
with open(counter, "w", encoding="utf-8") as fh:
    fh.write(str(n))

if n > 1:
    print("IDLE: 잔여 이슈 없음(스텁)")
    sys.exit(2)

key = os.environ.get("STUB_ISSUE_KEY", "CE-999")
branch = os.environ.get("STUB_BRANCH", "ralph/" + key)
os.makedirs(os.path.join(ralph, "tasks"), exist_ok=True)
with open(os.path.join(ralph, "tasks", key + ".md"), "w", encoding="utf-8") as fh:
    fh.write("# fix_plan\n- [ ] 스텁 태스크 구현\n")
mapping = {
    "스텁 태스크 " + key: {
        "identifier": key,
        "issue_id": "issue-uuid-stub",
        "branch": branch,
        "mode": "day",
        "description": "스텁 태스크 설명",
    }
}
with open(os.path.join(ralph, ".task_mapping.json"), "w", encoding="utf-8") as fh:
    json.dump(mapping, fh, ensure_ascii=False)
print("스텁 watcher: %s 수거" % key)
PY

  printf '자동 구현 프롬프트(스텁)\n' > "$P/.ralph/PROMPT.md"
  git -C "$P" init -q
  git -C "$P" symbolic-ref HEAD refs/heads/main
  git -C "$P" add -A >/dev/null 2>&1
  git -C "$P" commit -q -m "픽스처 초기 커밋"
}

# ── 고객 레포(bare + clone) 구성 ────────────────────────────────────────────
build_customer() {  # build_customer <bare경로> <clone경로> <기본브랜치>
  local BARE="$1" CLONE="$2" DEF="$3" seed="$TMP/seed.$$.$RANDOM"
  mkdir -p "$seed"
  git -C "$seed" init -q
  git -C "$seed" symbolic-ref HEAD "refs/heads/$DEF"
  mkdir -p "$seed/auth"
  printf 'def login():\n    return True\n' > "$seed/auth/login.py"
  printf '# 고객 프로젝트\n' > "$seed/README.md"
  git -C "$seed" add -A >/dev/null 2>&1
  git -C "$seed" commit -q -m "고객 레포 초기 커밋"
  git init -q --bare "$BARE"
  git -C "$BARE" symbolic-ref HEAD "refs/heads/$DEF"
  git -C "$seed" remote add origin "$BARE"
  git -C "$seed" push -q origin "$DEF"
  rm -rf "$seed"
  git clone -q "$BARE" "$CLONE"
}

# ── 파이프라인 실행기 ───────────────────────────────────────────────────────
# 시나리오 env 만 명시하고 그 외 FLOWOPS_* 는 unset 으로 격리한다. 기획(STEP A)·Codex·
# Telegram 은 끄고, 관측/인제스트 계열은 미설정(=opt-in off) 상태로 둔다.
run_pipeline() {   # run_pipeline <primary> [KEY=VAL ...]
  local P="$1"; shift
  env -u FLOWOPS_WORKSPACE -u FLOWOPS_WORKSPACE_DELIVERY -u FLOWOPS_WORKSPACE_AUTOMAP \
      -u WORKSPACE_KEY -u FLOWOPS_SEAT_POOL -u FLOWOPS_SEAT_POOL_STRICT \
      -u FLOWOPS_COMPLETION -u FLOWOPS_METRICS -u FLOWOPS_TEMPORAL \
      -u FLOWOPS_DOMAIN_PROFILE -u FLOWOPS_USAGE_INGEST -u FLOWOPS_LLM_INGEST \
      -u FLOWOPS_GOVERNANCE_SERVICE_URL -u ANTHROPIC_API_KEY -u WATCHER_TITLE_PREFIX \
      FLOWOPS_METAPROMPT=false FLOWOPS_GEMINI_PLAN=false FLOWOPS_CODEX_REVIEW=false \
      FLOWOPS_TELEGRAM=false FLOWOPS_GOVERNANCE_PROMOTE=false \
      "$@" \
      bash "$P/scripts/auto_dev_pipeline.sh" --once >"$P/run.log" 2>&1
  return 0
}

echo "── ① 토글 off + 워크스페이스 모드 → 원본 경로(허상 재현) ──"
P1="$TMP/p1"; build_primary "$P1"
build_customer "$TMP/c1.git" "$P1/workspaces/proj1" main
run_pipeline "$P1" FLOWOPS_WORKSPACE=true WORKSPACE_KEY=proj1
deny_log "$P1/run.log" "워크스페이스 딜리버리" "리다이렉트 미발동(로그 무출현)"
want_log "$P1/run.log" "AUTO_MERGE 활성화" "원본 자기레포 머지 경로 진입"
deny_ref "$TMP/c1.git" "refs/heads/clickeye/intake-proj1" "고객 bare 에 태스크 브랜치 없음(허상 = 현행 버그 재현)"
want_eq "$(git -C "$P1/workspaces/proj1" rev-parse --abbrev-ref HEAD)" "main" \
  "고객 clone 이 기본 브랜치에 머묾(태스크 브랜치 미생성)"

echo "── ② 토글 on + 자기레포 → 리다이렉트 미발동 ──"
P2="$TMP/p2"; build_primary "$P2"
run_pipeline "$P2" FLOWOPS_WORKSPACE_DELIVERY=true
deny_log "$P2/run.log" "워크스페이스 딜리버리" "IMPL_WORKDIR==PROJECT_DIR → WS_DELIVERY=false"
want_log "$P2/run.log" "머지 성공" "자기레포 머지 경로 정상 수행"
want_ref "$P2" "main" "PRIMARY main 유지"

echo "── ③ 고객 기본 브랜치 감지 3단 ──"
# ③-a origin/HEAD 경유
P3A="$TMP/p3a"; build_primary "$P3A"
build_customer "$TMP/c3a.git" "$P3A/workspaces/proj3" main
run_pipeline "$P3A" FLOWOPS_WORKSPACE=true WORKSPACE_KEY=proj3 FLOWOPS_WORKSPACE_DELIVERY=true
want_log "$P3A/run.log" "기본브랜치=main" "①단 origin/HEAD 로 기본 브랜치 감지"

# ③-b origin/HEAD 제거 + .clickeye_default_branch 폴백
P3B="$TMP/p3b"; build_primary "$P3B"
build_customer "$TMP/c3b.git" "$P3B/workspaces/proj3" main
git -C "$P3B/workspaces/proj3" symbolic-ref -d refs/remotes/origin/HEAD 2>/dev/null || true
printf 'main\n' > "$P3B/workspaces/proj3/.clickeye_default_branch"
run_pipeline "$P3B" FLOWOPS_WORKSPACE=true WORKSPACE_KEY=proj3 FLOWOPS_WORKSPACE_DELIVERY=true
want_log "$P3B/run.log" "기본브랜치=main" "②단 .clickeye_default_branch 폴백"
want_ref "$TMP/c3b.git" "refs/heads/clickeye/intake-proj3" "폴백 경로에서도 push 성공"

# ③-c origin/HEAD 제거 + 메모 없음 + 원격 접근 가능 → G11 remote set-head 복구
P3C="$TMP/p3c"; build_primary "$P3C"
build_customer "$TMP/c3c.git" "$P3C/workspaces/proj3" main
git -C "$P3C/workspaces/proj3" symbolic-ref -d refs/remotes/origin/HEAD 2>/dev/null || true
run_pipeline "$P3C" FLOWOPS_WORKSPACE=true WORKSPACE_KEY=proj3 FLOWOPS_WORKSPACE_DELIVERY=true
want_log "$P3C/run.log" "기본브랜치=main" "G11 remote set-head 로 origin/HEAD 복구"
want_ref "$TMP/c3c.git" "refs/heads/clickeye/intake-proj3" "복구 경로에서도 push 성공"

# ③-d origin/HEAD 제거 + 메모 없음 + 원격 접근 불가 → 실패(main 추측 금지)
P3D="$TMP/p3d"; build_primary "$P3D"
build_customer "$TMP/c3d.git" "$P3D/workspaces/proj3" main
git -C "$P3D/workspaces/proj3" symbolic-ref -d refs/remotes/origin/HEAD 2>/dev/null || true
git -C "$P3D/workspaces/proj3" remote set-url origin "$TMP/absent-remote.git"
run_pipeline "$P3D" FLOWOPS_WORKSPACE=true WORKSPACE_KEY=proj3 FLOWOPS_WORKSPACE_DELIVERY=true
want_log "$P3D/run.log" "고객 기본 브랜치 감지 실패" "3단 전부 실패 → 실패 처리(추측 금지)"
deny_ref "$TMP/c3d.git" "refs/heads/clickeye/intake-proj3" "감지 실패 시 push 없음"

echo "── ④ 정상 딜리버리: 태스크 브랜치만 고객 origin 으로 push ──"
P4="$TMP/p4"; build_primary "$P4"
build_customer "$TMP/c4.git" "$P4/workspaces/proj4" main
BASE_SHA_BEFORE="$(git -C "$TMP/c4.git" rev-parse refs/heads/main)"
run_pipeline "$P4" FLOWOPS_WORKSPACE=true WORKSPACE_KEY=proj4 FLOWOPS_WORKSPACE_DELIVERY=true
want_log "$P4/run.log" "고객 레포 push 성공" "push 성공 로그"
want_ref "$TMP/c4.git" "refs/heads/clickeye/intake-proj4" "고객 bare 에 태스크 브랜치 도달"
want_eq "$(git -C "$TMP/c4.git" rev-parse refs/heads/main)" "$BASE_SHA_BEFORE" \
  "고객 기본 브랜치 tip 불변(머지 안 함)"
want_eq "$(git -C "$P4/workspaces/proj4" rev-parse --abbrev-ref HEAD)" "clickeye/intake-proj4" \
  "고객 clone 이 태스크 브랜치에 위치"
want_eq "$(git -C "$P4/workspaces/proj4" rev-list --count "main..clickeye/intake-proj4")" "1" \
  "구현 커밋이 태스크 브랜치에 얹힘"
deny_ref "$P4" "refs/heads/$BRANCH" "PRIMARY 레포에는 태스크 브랜치를 만들지 않음"
deny_log "$P4/run.log" "AUTO_MERGE 활성화" "머지 경로 미진입(머지 없음)"
ls "$P4/logs"/delivery_"$ISSUE_KEY"_*.log >/dev/null 2>&1 \
  && ok "딜리버리 로그 생성" || ng "딜리버리 로그 생성 (logs/delivery_${ISSUE_KEY}_*.log 없음)"

echo "── ⑤ 구현 커밋 없음 → 실패 판정 ──"
P5="$TMP/p5"; build_primary "$P5"
build_customer "$TMP/c5.git" "$P5/workspaces/proj5" main
run_pipeline "$P5" FLOWOPS_WORKSPACE=true WORKSPACE_KEY=proj5 FLOWOPS_WORKSPACE_DELIVERY=true \
  STUB_CLAUDE_COMMIT=0
want_log "$P5/run.log" "구현 커밋 없음" "rev-list 0 → 실패 확정(빈 머지 성공 대체)"
deny_log "$P5/run.log" "고객 레포 push 성공" "커밋 없으면 push 미수행"
deny_ref "$TMP/c5.git" "refs/heads/clickeye/intake-proj5" "고객 bare 에 빈 브랜치 미도달"

echo "── ⑥ push 거부 → 실패 + 로컬 브랜치 보존 ──"
P6="$TMP/p6"; build_primary "$P6"
build_customer "$TMP/c6.git" "$P6/workspaces/proj6" main
printf '#!/bin/sh\necho "거부(테스트 훅)" >&2\nexit 1\n' > "$TMP/c6.git/hooks/pre-receive"
chmod +x "$TMP/c6.git/hooks/pre-receive"
run_pipeline "$P6" FLOWOPS_WORKSPACE=true WORKSPACE_KEY=proj6 FLOWOPS_WORKSPACE_DELIVERY=true
want_log "$P6/run.log" "push 거부" "push 거부 감지 → 실패 처리"
want_log "$P6/run.log" "브랜치 보존" "브랜치 보존 로그"
deny_ref "$TMP/c6.git" "refs/heads/clickeye/intake-proj6" "거부되어 원격에는 미반영"
want_ref "$P6/workspaces/proj6" "refs/heads/clickeye/intake-proj6" "로컬 태스크 브랜치 보존(유실 0)"
want_eq "$(git -C "$P6/workspaces/proj6" rev-list --count "main..clickeye/intake-proj6")" "1" \
  "보존된 브랜치에 구현 커밋 유지"

echo "── ⑦ 중립 정책(governance-workspace.policy.json) ──"
GATE_REPO="$TMP/gate"
build_customer "$TMP/cgate.git" "$GATE_REPO" main
git -C "$GATE_REPO" checkout -q -b "$BRANCH"
printf 'def login():\n    return False  # 변경\n' > "$GATE_REPO/auth/login.py"
mkdir -p "$GATE_REPO/clickeye-api/app/api"
printf '# 계약면처럼 보이는 경로\n' > "$GATE_REPO/clickeye-api/app/api/x.py"
git -C "$GATE_REPO" add -A >/dev/null 2>&1
git -C "$GATE_REPO" commit -q -m "auth·계약면 유사 경로 변경"
GATE_OUT="$(python3 "$REPO/scripts/pre_merge_gate.py" --project-dir "$GATE_REPO" \
  --base main --head "$BRANCH" --policy "$POLICY" --json 2>/dev/null)"
GATE_RC=$?
want_eq "$GATE_RC" "0" "중립 정책 판정 exit 0(차단 아님)"
want_eq "$(printf '%s' "$GATE_OUT" | python3 -c 'import sys,json;print(json.load(sys.stdin)["merge_decision"])' 2>/dev/null)" \
  "direct" "*auth*·계약면 유사 경로가 pr 강등되지 않음"
want_eq "$(printf '%s' "$GATE_OUT" | python3 -c 'import sys,json;print(json.load(sys.stdin)["tier"])' 2>/dev/null)" \
  "LOW" "위험분류 LOW(HIGH_PREFIXES·PATTERNS 비움)"
want_eq "$(printf '%s' "$GATE_OUT" | python3 -c 'import sys,json;print(json.load(sys.stdin)["checks"]["ticket_ref"]["status"])' 2>/dev/null)" \
  "pass" "ticket-ref 는 그대로 유효(브랜치 키 검증)"
# ticket-ref 시맨틱 보존: 형태 불량 키는 여전히 차단, 슬래시 없는 브랜치는 skip→pass
git -C "$GATE_REPO" branch -q "ralph/badkey" "$BRANCH"
python3 "$REPO/scripts/pre_merge_gate.py" --project-dir "$GATE_REPO" \
  --base main --head "ralph/badkey" --policy "$POLICY" --json >/dev/null 2>&1
want_eq "$?" "2" "이슈 키 형태 불량 → 차단(기존 게이트 시맨틱 유지)"
git -C "$GATE_REPO" branch -q "nokey" "$BRANCH"
python3 "$REPO/scripts/pre_merge_gate.py" --project-dir "$GATE_REPO" \
  --base main --head "nokey" --policy "$POLICY" --json >/dev/null 2>&1
want_eq "$?" "0" "슬래시 없는 브랜치 → ticket-ref skip(pass)"

echo "── ⑧ 기본 브랜치 develop 픽스처 ──"
P8="$TMP/p8"; build_primary "$P8"
build_customer "$TMP/c8.git" "$P8/workspaces/proj8" develop
DEV_SHA_BEFORE="$(git -C "$TMP/c8.git" rev-parse refs/heads/develop)"
run_pipeline "$P8" FLOWOPS_WORKSPACE=true WORKSPACE_KEY=proj8 FLOWOPS_WORKSPACE_DELIVERY=true
want_log "$P8/run.log" "기본브랜치=develop" "develop 을 base 로 감지"
want_ref "$TMP/c8.git" "refs/heads/clickeye/intake-proj8" "develop 기준 태스크 브랜치 push"
want_eq "$(git -C "$TMP/c8.git" rev-parse refs/heads/develop)" "$DEV_SHA_BEFORE" \
  "develop tip 불변"
deny_ref "$TMP/c8.git" "refs/heads/main" "main 을 만들지 않음(추측 금지 확인)"
want_eq "$(git -C "$P8/workspaces/proj8" rev-list --count "develop..clickeye/intake-proj8")" "1" \
  "develop..태스크 브랜치 커밋 1건"

echo "── ⑨ 재시도 잔여 브랜치: 이번 런 델타로 판정 (G1) ──"
P9="$TMP/p9"; build_primary "$P9"
build_customer "$TMP/c9.git" "$P9/workspaces/proj9" main
run_pipeline "$P9" FLOWOPS_WORKSPACE=true WORKSPACE_KEY=proj9 FLOWOPS_WORKSPACE_DELIVERY=true
want_log "$P9/run.log" "고객 레포 push 성공" "1회차 push 성공"
RUN1_SHA="$(git -C "$TMP/c9.git" rev-parse "refs/heads/clickeye/intake-proj9")"
rm -f "$P9/.ralph/.stub_watch_count"   # 같은 티켓 재수거(재시도) 재현
run_pipeline "$P9" FLOWOPS_WORKSPACE=true WORKSPACE_KEY=proj9 FLOWOPS_WORKSPACE_DELIVERY=true \
  STUB_CLAUDE_COMMIT=0
want_log "$P9/run.log" "이번 런 구현 커밋 없음" "2회차 빈손 → 잔여 커밋이 있어도 실패 판정"
deny_log "$P9/run.log" "고객 레포 push 성공" "2회차 push 미수행"
want_eq "$(git -C "$TMP/c9.git" rev-parse "refs/heads/clickeye/intake-proj9")" "$RUN1_SHA" \
  "고객 원격 브랜치 tip 불변(빈손 런이 성공으로 소진되지 않음)"

echo "── ⑩ 더러운 clone: stash 보존 후 진행 (G2) ──"
P10="$TMP/p10"; build_primary "$P10"
build_customer "$TMP/c10.git" "$P10/workspaces/proj10" main
run_pipeline "$P10" FLOWOPS_WORKSPACE=true WORKSPACE_KEY=proj10 FLOWOPS_WORKSPACE_DELIVERY=true \
  STUB_ISSUE_KEY=CE-901 STUB_BRANCH=ralph/CE-901
want_ref "$TMP/c10.git" "refs/heads/clickeye/intake-proj10" "1회차 CE-901 push"
# 에이전트가 미커밋 변경(추적 파일 수정 + 미추적 파일)을 남기고 죽은 상태 재현
printf '미커밋 잔여\n' >> "$P10/workspaces/proj10/impl_feature.txt"
printf '미추적 잔여\n' > "$P10/workspaces/proj10/leftover_untracked.txt"
rm -f "$P10/.ralph/.stub_watch_count"
run_pipeline "$P10" FLOWOPS_WORKSPACE=true WORKSPACE_KEY=proj10 FLOWOPS_WORKSPACE_DELIVERY=true \
  STUB_ISSUE_KEY=CE-902 STUB_BRANCH=ralph/CE-902
want_log "$P10/run.log" "stash 보존 후 진행" "미커밋 변경을 stash 로 보존"
want_log "$P10/run.log" "고객 레포 push 성공" "wedge 없이 2회차 완주"
want_ref "$TMP/c10.git" "refs/heads/clickeye/intake-proj10" "2회차 CE-902 push"
git -C "$P10/workspaces/proj10" stash list 2>/dev/null | grep -q "clickeye-auto-preserve" \
  && ok "stash 항목이 복구 가능하게 남음(유실 0)" || ng "stash 항목이 복구 가능하게 남음"

echo "── ⑪ WS 성공 시 Linear 처분 (G3) ──"
P11="$TMP/p11"; build_primary "$P11"
build_customer "$TMP/c11.git" "$P11/workspaces/proj11" main
run_pipeline "$P11" FLOWOPS_WORKSPACE=true WORKSPACE_KEY=proj11 FLOWOPS_WORKSPACE_DELIVERY=true
want_log "$P11/run.log" "고객 레포 push 성공" "push 성공"
grep -q "linear_tracker.py.*--status Done" "$P11/.ralph/stub_calls.log" 2>/dev/null \
  && ok "push 성공 직후 tracker Done 전이 호출" || ng "push 성공 직후 tracker Done 전이 호출"
grep -q "^linear_reporter.py" "$P11/.ralph/stub_calls.log" 2>/dev/null \
  && ng "linear_reporter 미호출(PRIMARY 기준 Backlog 방지)" \
  || ok "linear_reporter 미호출(PRIMARY 기준 Backlog 방지)"
want_log "$P11/run.log" "linear_reporter 생략" "생략 사실이 로그에 드러남"
# 자기레포 경로에서는 reporter 가 그대로 호출된다(무회귀)
P11B="$TMP/p11b"; build_primary "$P11B"
run_pipeline "$P11B" FLOWOPS_WORKSPACE_DELIVERY=true
grep -q "^linear_reporter.py" "$P11B/.ralph/stub_calls.log" 2>/dev/null \
  && ok "자기레포는 linear_reporter 호출 유지(무회귀)" || ng "자기레포는 linear_reporter 호출 유지"

echo "── ⑫ 하네스 산출물 오염 차단 (G6) ──"
P12="$TMP/p12"; build_primary "$P12"
build_customer "$TMP/c12.git" "$P12/workspaces/proj12" main
run_pipeline "$P12" FLOWOPS_WORKSPACE=true WORKSPACE_KEY=proj12 FLOWOPS_WORKSPACE_DELIVERY=true \
  STUB_CLAUDE_POLLUTE=1
want_log "$P12/run.log" "오염 차단" "하네스 운영 파일 커밋 → fail-closed"
deny_log "$P12/run.log" "고객 레포 push 성공" "오염 시 push 미수행"
deny_ref "$TMP/c12.git" "refs/heads/clickeye/intake-proj12" "오염 브랜치가 고객 원격에 안 감"

echo "── ⑬ detached HEAD 구현 → 회수 브랜치 + 실패 (G4) ──"
P13="$TMP/p13"; build_primary "$P13"
build_customer "$TMP/c13.git" "$P13/workspaces/proj13" main
run_pipeline "$P13" FLOWOPS_WORKSPACE=true WORKSPACE_KEY=proj13 FLOWOPS_WORKSPACE_DELIVERY=true \
  STUB_CLAUDE_DETACH=1
want_log "$P13/run.log" "detached HEAD" "detached 구현 감지"
want_log "$P13/run.log" "회수 브랜치" "회수 브랜치로 커밋 보존"
deny_log "$P13/run.log" "고객 레포 push 성공" "detached 시 push 미수행(허상 재발 차단)"
git -C "$P13/workspaces/proj13" for-each-ref --format='%(refname:short)' refs/heads \
  | grep -q "^rescue/${ISSUE_KEY}-" \
  && ok "rescue/<KEY>-* 브랜치 존재(유실 0)" || ng "rescue/<KEY>-* 브랜치 존재"

echo "── ⑭ 고객 origin 이 ClickEye 를 가리킴 → 착수 차단 (G8) ──"
P14="$TMP/p14"; build_primary "$P14"
build_customer "$TMP/c14.git" "$P14/workspaces/proj14" main
git -C "$P14/workspaces/proj14" remote set-url origin "$P14"
run_pipeline "$P14" FLOWOPS_WORKSPACE=true WORKSPACE_KEY=proj14 FLOWOPS_WORKSPACE_DELIVERY=true
want_log "$P14/run.log" "ClickEye 레포를 가리킴" "오조달 origin 착수 전 차단"
deny_ref "$P14" "refs/heads/$BRANCH" "PRIMARY 에 브랜치가 생기지 않음"

echo ""
echo "═══════════════════════════════════════"
echo "  통과 ${PASS}건 / 실패 ${FAIL}건"
echo "═══════════════════════════════════════"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
