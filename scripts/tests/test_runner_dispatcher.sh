#!/usr/bin/env bash
# runner_dispatcher.sh / runner_clone.sh 통합 테스트 (러너 디스패처 v1 / CE-346).
#
# 프레임워크 없이 순수 bash. 임시 디렉터리에 "가짜 PRIMARY 레포"(git init + 원장 픽스처)를
# 세우고, 디스패처를 그 안에서 실행해 산정·멱등·캡·회수·실스폰을 검증한다. Linear 호출은
# WATCHER_BIN 오버라이드로, 파이프라인 본체는 스텁으로 대체하므로 네트워크가 필요 없다.
#
# 검증 축:
#   ① 토글 off      → exit 0, 스폰 0, .ralph/dispatch 미생성(회귀 0)
#   ② DRYRUN 산정   → 스폰 대상 목록만 출력, 실제 스폰·PID 마커 0
#   ③ 스킵 3종      → 시트 미배정 / 시트 비active / Queued 없음
#   ④ 캡            → active 시트 1 + 후보 2 → 스폰 대상 1
#   ⑤ 라이브니스    → 생존 마커 스킵 / 죽은 마커 회수 / PID 재사용(cmdline 불일치) 회수
#   ⑥ 시트 배타     → 같은 시트에 2키 배정 → 스폰 1만 허용(clone 간 .seat_lock 무력 보완)
#   ⑦ 원장 진단     → #DUPKEY(키 중복) · #BADPREFIX(접두사에 탭)
#   ⑧ 실스폰        → env 조립 + 마커 3필드 + fd9 미상속(스폰 중에도 다음 틱 flock 획득)
#   ⑨ .env 권위     → 공유 .env 의 FLOWOPS 값이 스폰 env 를 덮지 못한다(KEEP_EXISTING)
#   ⑩ runner_clone  → 심볼릭 6종 + origin 재지정/제거 + 2회 실행 멱등
#
# 실행: bash scripts/tests/test_runner_dispatcher.sh   (통과 0 / 실패 1)
set -uo pipefail

REPO="$(cd "$(dirname "$(readlink -f "$0")")/../.." && pwd)"

PASS=0
FAIL=0

TMP="$(mktemp -d)"
SLEEPER=""
cleanup() {
  [ -n "$SLEEPER" ] && kill "$SLEEPER" 2>/dev/null
  pkill -f "$TMP" 2>/dev/null
  chmod -R u+w "$TMP" 2>/dev/null
  rm -rf "$TMP"
}
trap cleanup EXIT

# ── 가짜 PRIMARY 레포 구성 ──────────────────────────────────────────────────
# pipeline_config.sh 를 복사해 _FLOWOPS_CONFIG_DIR 가 이 임시 레포를 가리키게 한다
# (실 레포 .env 의 FLOWOPS_* 가 시나리오 env 를 덮어쓰지 않도록 = 테스트 격리).
FAKE="$TMP/primary"
CLONES="$TMP/clones"
mkdir -p "$FAKE/scripts" "$FAKE/.ralph"
cp "$REPO/scripts/pipeline_config.sh" "$FAKE/scripts/"
cp "$REPO/scripts/runner_dispatcher.sh" "$FAKE/scripts/"
cp "$REPO/scripts/runner_clone.sh" "$FAKE/scripts/"

# 공유 .env — 스폰 env 와 **충돌하는** 값을 일부러 심는다(⑨ 권위 검증용).
cat > "$FAKE/.env" <<'ENVEOF'
# 테스트용 설정 — 디스패처가 넘기는 값과 충돌시켜 권위를 검증한다
FLOWOPS_SEAT_POOL=false
FLOWOPS_WORKSPACE=false
ENVEOF

# 스텁 watcher — --title-prefix 값이 STUB_QUEUED_MATCH 를 포함하면 0(Queued 있음),
# 아니면 2(없음). STUB_QUEUED_MATCH=__all__ 이면 항상 0. 파일은 쓰지 않는다.
cat > "$FAKE/scripts/stub_watcher.sh" <<'STUB'
#!/usr/bin/env bash
prefix=""
while [ $# -gt 0 ]; do
  case "$1" in
    --title-prefix) prefix="${2:-}"; shift 2 ;;
    *) shift ;;
  esac
done
[ "${STUB_QUEUED_MATCH:-}" = "__all__" ] && exit 0
[ -n "${STUB_QUEUED_MATCH:-}" ] && [[ "$prefix" == *"$STUB_QUEUED_MATCH"* ]] && exit 0
exit 2
STUB
chmod +x "$FAKE/scripts/stub_watcher.sh"

# 스텁 파이프라인 — 실 레포의 auto_dev_pipeline.sh 자리를 대신한다. 실제 파이프라인처럼
# pipeline_config.sh 를 소싱한 **뒤** 토글을 기록하므로, 공유 .env 가 스폰 env 를 덮는지까지
# 그대로 드러난다. STUB_PIPELINE_SLEEP 로 생존 창을 열어 fd9·라이브니스를 검증한다.
cat > "$FAKE/scripts/auto_dev_pipeline.sh" <<'STUB'
#!/usr/bin/env bash
source "$(dirname "$0")/pipeline_config.sh" 2>/dev/null || true
mkdir -p logs
{
  echo "ARGS=$*"
  echo "WORKSPACE_KEY=${WORKSPACE_KEY:-}"
  echo "WATCHER_TITLE_PREFIX=${WATCHER_TITLE_PREFIX:-}"
  echo "FLOWOPS_WORKSPACE=${FLOWOPS_WORKSPACE:-}"
  echo "FLOWOPS_SEAT_POOL=${FLOWOPS_SEAT_POOL:-}"
  echo "FLOWOPS_SEAT_POOL_STRICT=${FLOWOPS_SEAT_POOL_STRICT:-}"
  echo "FLOWOPS_ENV_KEEP_EXISTING=${FLOWOPS_ENV_KEEP_EXISTING:-}"
  echo "CWD=$PWD"
} >> logs/spawn_record.txt
sleep "${STUB_PIPELINE_SLEEP:-0}"
exit 0
STUB
chmod +x "$FAKE/scripts/auto_dev_pipeline.sh"

# 마커 신원 확인(cmdline)이 통과해야 하는 장수 프로세스 — 이름에 auto_dev_pipeline 을 포함한다.
cat > "$FAKE/scripts/auto_dev_pipeline_sleeper.sh" <<'STUB'
#!/usr/bin/env bash
sleep 120
STUB
chmod +x "$FAKE/scripts/auto_dev_pipeline_sleeper.sh"

( cd "$FAKE" \
  && git init -q -b main . \
  && git config user.email "test@example.com" \
  && git config user.name "테스트" \
  `# .env·.ralph 는 추적하지 않는다(실 레포 .gitignore 와 동일) — clone 에 실체가 딸려가면` \
  `# 심볼릭 배선이 "실체 보존" 규칙에 걸려 건너뛰어진다.` \
  && git add scripts \
  && git commit -q -m "테스트 픽스처" ) >/dev/null 2>&1

# ── 원장 픽스처 ─────────────────────────────────────────────────────────────
# 기본 매핑: mapped 4개(aaa/bbb/ddd/eee) + pending_source 1개(ccc, 후보 제외).
write_ws_ledger() {
  cat > "$FAKE/.ralph/workspaces.json" <<'JSON'
{
  "version": 1,
  "updated_at": "2026-08-03T00:00:00Z",
  "workspaces": {
    "[수주:aaa11111] ": {"workspace_key": "aaa11111", "intake_id": "aaa11111-x", "project_id": null, "repo_source": "/tmp/a", "status": "mapped"},
    "[수주:bbb22222] ": {"workspace_key": "bbb22222", "intake_id": "bbb22222-x", "project_id": null, "repo_source": "/tmp/b", "status": "mapped"},
    "[수주:ccc33333] ": {"workspace_key": "ccc33333", "intake_id": "ccc33333-x", "project_id": null, "repo_source": null, "status": "pending_source"},
    "[수주:ddd44444] ": {"workspace_key": "ddd44444", "intake_id": "ddd44444-x", "project_id": null, "repo_source": "/tmp/d", "status": "mapped"},
    "[수주:eee55555] ": {"workspace_key": "eee55555", "intake_id": "eee55555-x", "project_id": null, "repo_source": "/tmp/e", "status": "mapped"}
  }
}
JSON
}

# 기본 시트: seat-a/seat-b active(=캡 2), seat-c disabled. ddd 는 배정 없음.
write_seat_ledger() {
  cat > "$FAKE/.ralph/seats.json" <<'JSON'
{
  "version": 1,
  "updated_at": "2026-08-03T00:00:00Z",
  "seats": {
    "seat-a": {"seat_id": "seat-a", "status": "active", "auth": {}},
    "seat-b": {"seat_id": "seat-b", "status": "active", "auth": {}},
    "seat-c": {"seat_id": "seat-c", "status": "disabled", "auth": {}}
  },
  "assignments": {"aaa11111": "seat-a", "bbb22222": "seat-b", "eee55555": "seat-c"}
}
JSON
}

# 캡 시나리오: active 시트 2개(aaa→seat-a, bbb→seat-b) — 서로 다른 시트라 시트 배타에는
# 걸리지 않는다. 캡은 **다른 키의 라이브 러너가 자리를 이미 먹고 있을 때** 비로소 binding 한다.
write_seat_ledger_cap() {
  cat > "$FAKE/.ralph/seats.json" <<'JSON'
{
  "version": 1,
  "updated_at": "2026-08-03T00:00:00Z",
  "seats": {
    "seat-a": {"seat_id": "seat-a", "status": "active", "auth": {}},
    "seat-b": {"seat_id": "seat-b", "status": "active", "auth": {}}
  },
  "assignments": {"aaa11111": "seat-a", "bbb22222": "seat-b"}
}
JSON
}

# 시트 배타 시나리오: active 시트 2개인데 두 키가 **같은 시트**를 쓴다(캡은 남아 있다).
write_seat_ledger_shared() {
  cat > "$FAKE/.ralph/seats.json" <<'JSON'
{
  "version": 1,
  "updated_at": "2026-08-03T00:00:00Z",
  "seats": {
    "seat-a": {"seat_id": "seat-a", "status": "active", "auth": {}},
    "seat-b": {"seat_id": "seat-b", "status": "active", "auth": {}}
  },
  "assignments": {"aaa11111": "seat-a", "bbb22222": "seat-a"}
}
JSON
}

write_ws_ledger
write_seat_ledger

# ── 실행기 ──────────────────────────────────────────────────────────────────
OUT=""; RC=0
run_dispatch() {  # run_dispatch [env 할당...]
  OUT="$(env -u FLOWOPS_RUNNER_DISPATCH -u FLOWOPS_RUNNER_DISPATCH_DRYRUN \
         -u WORKSPACE_KEY -u STUB_QUEUED_MATCH -u FLOWOPS_SEAT_POOL -u FLOWOPS_WORKSPACE \
         RUNNER_CLONE_ROOT="$CLONES" \
         WATCHER_BIN="$FAKE/scripts/stub_watcher.sh" \
         "$@" bash "$FAKE/scripts/runner_dispatcher.sh" 2>&1)"
  RC=$?
}

ok()   { PASS=$((PASS + 1)); echo "PASS  $1"; }
bad()  { FAIL=$((FAIL + 1)); echo "FAIL  $1 — $2"; sed 's/^/        /' <<<"$OUT"; }

assert_rc()      { [ "$RC" = "$2" ] && ok "$1" || bad "$1" "rc=$RC(기대 $2)"; }
assert_out()     { grep -qF "$2" <<<"$OUT" && ok "$1" || bad "$1" "출력에 '$2' 없음"; }
assert_not_out() { grep -qF "$2" <<<"$OUT" && bad "$1" "출력에 '$2' 가 있음" || ok "$1"; }
assert_file()    { [ -e "$2" ] && ok "$1" || bad "$1" "파일 없음: $2"; }
assert_no_file() { [ -e "$2" ] && bad "$1" "파일이 존재: $2" || ok "$1"; }
assert_eq()      { [ "$2" = "$3" ] && ok "$1" || bad "$1" "'$2' != 기대 '$3'"; }
assert_link()    {  # assert_link <이름> <링크경로> <기대 타깃>
  if [ -L "$2" ] && [ "$(readlink "$2")" = "$3" ]; then ok "$1"
  else bad "$1" "링크 불일치: $2 → $(readlink "$2" 2>/dev/null || echo 없음) (기대 $3)"; fi
}

echo "── runner_dispatcher 통합 테스트 ──"

# ① 토글 off → 무동작
rm -rf "$FAKE/.ralph/dispatch"
run_dispatch STUB_QUEUED_MATCH=__all__
assert_rc      "① off exit 0" 0
assert_out     "①-1 SKIP 로그" "SKIP: FLOWOPS_RUNNER_DISPATCH"
assert_no_file "①-2 dispatch 디렉터리 미생성" "$FAKE/.ralph/dispatch"
assert_not_out "①-3 스폰 없음" "스폰:"

# ② DRYRUN 산정 + ③ 스킵 2종(미배정/비active)
run_dispatch FLOWOPS_RUNNER_DISPATCH=true FLOWOPS_RUNNER_DISPATCH_DRYRUN=true \
             STUB_QUEUED_MATCH=__all__
assert_rc  "② DRYRUN exit 0" 0
assert_out "②-1 aaa 스폰 대상" "[DRYRUN] 스폰 대상: aaa11111"
assert_out "②-2 bbb 스폰 대상" "[DRYRUN] 스폰 대상: bbb22222"
assert_out "②-3 요약(후보4·스폰2)" "후보=4 스폰=2 스킵=2"
assert_not_out "②-4 pending_source 는 후보 아님" "ccc33333"
assert_not_out "②-5 실제 스폰 없음" "스폰: "
assert_no_file "②-6 PID 마커 미생성" "$FAKE/.ralph/dispatch/aaa11111.pid"
assert_out "③-1 시트 미배정 스킵" "스킵: ddd44444 — 시트 미배정"
assert_out "③-2 비active 시트 스킵" "스킵: eee55555 — 배정 시트가 active 아님"

# ③-3 Queued 없음 스킵 (stub 이 aaa 접두사에만 0 반환)
run_dispatch FLOWOPS_RUNNER_DISPATCH=true FLOWOPS_RUNNER_DISPATCH_DRYRUN=true \
             STUB_QUEUED_MATCH=aaa11111
assert_out "③-3 Queued 없음 스킵" "스킵: bbb22222 — Queued 이슈 없음"
assert_out "③-4 aaa 만 스폰 대상" "[DRYRUN] 스폰 대상: aaa11111"

# ④ 캡 — active 시트 2, 후보 2(서로 다른 시트)인데 **무관한 키의 라이브 러너가 1자리를
#    먹고 있다** → 남은 자리는 1이므로 둘째 후보는 캡에 걸린다. 캡은 Queued 사전확인보다
#    앞이므로 캡에 걸린 후보는 watcher 를 호출하지 않는다(=API 비용 미지출).
write_seat_ledger_cap
mkdir -p "$FAKE/.ralph/dispatch"
bash "$FAKE/scripts/auto_dev_pipeline_sleeper.sh" &
SLEEPER=$!
printf '%s %s %s\n' "$SLEEPER" "$(date +%s)" "seat-z" > "$FAKE/.ralph/dispatch/zzz99999.pid"
run_dispatch FLOWOPS_RUNNER_DISPATCH=true FLOWOPS_RUNNER_DISPATCH_DRYRUN=true \
             STUB_QUEUED_MATCH=__all__
assert_out "④-1 첫 후보만 스폰 대상" "[DRYRUN] 스폰 대상: aaa11111"
assert_out "④-2 둘째 후보 캡 스킵" "스킵: bbb22222 — 시트 캡 도달"
assert_out "④-3 요약(라이브1·스폰1)" "스폰=1"
assert_out "④-4 라이브 반영" "라이브=1"
kill "$SLEEPER" 2>/dev/null; SLEEPER=""
rm -f "$FAKE"/.ralph/dispatch/*.pid
write_seat_ledger

# ⑤ 라이브니스 — 살아있는 마커는 스킵, 죽은 마커는 회수
mkdir -p "$FAKE/.ralph/dispatch"
bash "$FAKE/scripts/auto_dev_pipeline_sleeper.sh" &
SLEEPER=$!
printf '%s %s %s\n' "$SLEEPER" "$(date +%s)" "seat-a" > "$FAKE/.ralph/dispatch/aaa11111.pid"
# 죽은 PID: 자식을 띄우고 즉시 회수(wait)해 확실히 존재하지 않는 PID 를 만든다.
( exit 0 ) &
DEAD=$!
wait "$DEAD" 2>/dev/null
printf '%s %s %s\n' "$DEAD" "$(date +%s)" "seat-b" > "$FAKE/.ralph/dispatch/bbb22222.pid"

run_dispatch FLOWOPS_RUNNER_DISPATCH=true FLOWOPS_RUNNER_DISPATCH_DRYRUN=true \
             STUB_QUEUED_MATCH=__all__
assert_out     "⑤-1 살아있는 러너 스킵" "스킵: aaa11111 — 러너 실행 중"
assert_file    "⑤-2 살아있는 마커 보존" "$FAKE/.ralph/dispatch/aaa11111.pid"
assert_out     "⑤-3 죽은 마커 회수 로그" "회수: 종료된 러너 마커 정리 — key=bbb22222"
assert_no_file "⑤-4 죽은 마커 삭제" "$FAKE/.ralph/dispatch/bbb22222.pid"
assert_out     "⑤-5 라이브 반영 요약" "라이브=1"
kill "$SLEEPER" 2>/dev/null; SLEEPER=""
rm -f "$FAKE"/.ralph/dispatch/*.pid

# ⑤-b PID 재사용 — 살아있지만 cmdline 이 러너가 아니면 마커를 회수한다.
sleep 120 &
SLEEPER=$!
printf '%s %s %s\n' "$SLEEPER" "$(date +%s)" "seat-a" > "$FAKE/.ralph/dispatch/aaa11111.pid"
run_dispatch FLOWOPS_RUNNER_DISPATCH=true FLOWOPS_RUNNER_DISPATCH_DRYRUN=true \
             STUB_QUEUED_MATCH=__all__
assert_out     "⑤-6 PID 재사용 회수 로그" "회수: PID 재사용 감지(러너 아님) — key=aaa11111"
assert_no_file "⑤-7 재사용 마커 삭제" "$FAKE/.ralph/dispatch/aaa11111.pid"
assert_out     "⑤-8 회수 후 정상 후보 취급" "[DRYRUN] 스폰 대상: aaa11111"
kill "$SLEEPER" 2>/dev/null; SLEEPER=""
rm -f "$FAKE"/.ralph/dispatch/*.pid

# ⑥ 시트 배타 — 같은 시트에 2키. 캡(active 2)은 남아 있지만 시트가 겹쳐 1개만 스폰된다.
write_seat_ledger_shared
run_dispatch FLOWOPS_RUNNER_DISPATCH=true FLOWOPS_RUNNER_DISPATCH_DRYRUN=true \
             STUB_QUEUED_MATCH=__all__
assert_out     "⑥-1 첫 키만 스폰 대상" "[DRYRUN] 스폰 대상: aaa11111"
assert_out     "⑥-2 같은 시트 두번째 키 스킵" "스킵: bbb22222 — 시트 seat-a 를 쓰는 러너가 이미 실행 중"
assert_not_out "⑥-3 캡 사유가 아님(시트 배타로 걸림)" "스킵: bbb22222 — 시트 캡 도달"
assert_out     "⑥-4 요약 스폰=1" "스폰=1"
write_seat_ledger

# ⑦ 원장 진단 행 — 키 중복 / 접두사에 탭
printf '%s\n' '{' \
  '  "version": 1,' \
  '  "workspaces": {' \
  '    "[수주:aaa11111] ": {"workspace_key": "aaa11111", "repo_source": "/tmp/a", "status": "mapped"},' \
  '    "[중복:aaa11111] ": {"workspace_key": "aaa11111", "repo_source": "/tmp/a2", "status": "mapped"},' \
  '    "[탭\t포함] ": {"workspace_key": "bbb22222", "repo_source": "/tmp/b", "status": "mapped"}' \
  '  }' \
  '}' > "$FAKE/.ralph/workspaces.json"
run_dispatch FLOWOPS_RUNNER_DISPATCH=true FLOWOPS_RUNNER_DISPATCH_DRYRUN=true \
             STUB_QUEUED_MATCH=__all__
assert_out "⑦-1 키 중복 경고" "WARN: workspace_key 중복"
assert_out "⑦-2 탭 포함 접두사 경고" "WARN: ticket_prefix 에 탭/개행이 있어"
assert_out "⑦-3 정상 후보 1개만" "후보=1"
write_ws_ledger

echo "── 실스폰 · env 권위 테스트 ──"

# ⑧⑨ 실스폰 — DRYRUN 아님. 스텁 파이프라인이 3초 생존하는 창에서 fd9·라이브니스를 본다.
rm -f "$FAKE/logs/spawn_record.txt"
run_dispatch FLOWOPS_RUNNER_DISPATCH=true STUB_QUEUED_MATCH=aaa11111 STUB_PIPELINE_SLEEP=3
assert_rc   "⑧ 실스폰 exit 0" 0
assert_out  "⑧-1 스폰 로그(seat 포함)" "스폰: aaa11111 pid="
assert_file "⑧-2 PID 마커 생성" "$FAKE/.ralph/dispatch/aaa11111.pid"

MARKER="$(cat "$FAKE/.ralph/dispatch/aaa11111.pid" 2>/dev/null || echo "")"
assert_eq "⑧-3 마커 3필드" "$(awk '{print NF}' <<<"$MARKER")" "3"
assert_eq "⑧-4 마커 seat_id" "$(awk '{print $3}' <<<"$MARKER")" "seat-a"
SPAWN_PID="$(awk '{print $1}' <<<"$MARKER")"

# fd9 미상속 — 러너가 살아있는 동안 다음 틱이 락을 획득해야 한다(못 하면 디스패치 영구 정지).
run_dispatch FLOWOPS_RUNNER_DISPATCH=true FLOWOPS_RUNNER_DISPATCH_DRYRUN=true \
             STUB_QUEUED_MATCH=__all__
assert_not_out "⑧-5 fd9 미상속(다음 틱 락 획득)" "이전 틱이 아직 실행 중"
assert_out     "⑧-6 스폰된 러너를 라이브로 인식" "스킵: aaa11111 — 러너 실행 중"

# 스텁 파이프라인 종료 대기 후 회수 확인
for _ in 1 2 3 4 5 6 7 8 9 10; do
  kill -0 "$SPAWN_PID" 2>/dev/null || break
  sleep 1
done
run_dispatch FLOWOPS_RUNNER_DISPATCH=true FLOWOPS_RUNNER_DISPATCH_DRYRUN=true \
             STUB_QUEUED_MATCH=aaa11111
assert_out     "⑧-7 종료 후 마커 회수" "회수: 종료된 러너 마커 정리 — key=aaa11111"
assert_no_file "⑧-8 마커 삭제" "$FAKE/.ralph/dispatch/aaa11111.pid"

# 스폰 env 조립 — 기록은 공유 logs/ 심볼릭을 타고 PRIMARY 로 들어온다.
REC="$FAKE/logs/spawn_record.txt"
assert_file "⑨-1 스폰 기록(공유 logs 경유)" "$REC"
if [ -f "$REC" ]; then
  OUT="$(cat "$REC")"
  assert_out "⑨-2 --once 인자"            "ARGS=--once"
  assert_out "⑨-3 WORKSPACE_KEY 주입"     "WORKSPACE_KEY=aaa11111"
  assert_out "⑨-4 접두사 주입"            "WATCHER_TITLE_PREFIX=[수주:aaa11111] "
  assert_out "⑨-5 STRICT 주입"            "FLOWOPS_SEAT_POOL_STRICT=true"
  assert_out "⑨-6 KEEP_EXISTING 주입"     "FLOWOPS_ENV_KEEP_EXISTING=true"
  # 핵심: .env 에 FLOWOPS_SEAT_POOL=false / FLOWOPS_WORKSPACE=false 가 있는데도
  # 스폰 env(true)가 이긴다. 지면 전 러너가 개인 계정으로 폴백한다(오귀속 재발).
  assert_out "⑨-7 .env 가 SEAT_POOL 을 덮지 못함" "FLOWOPS_SEAT_POOL=true"
  assert_out "⑨-8 .env 가 WORKSPACE 를 덮지 못함" "FLOWOPS_WORKSPACE=true"
  assert_out "⑨-9 clone cwd 에서 실행"    "CWD=$CLONES/aaa11111"
fi

# ⑨-10/11 마커 미설정 시 pipeline_config 동작 불변(=.env 가 이긴다)
OUT="$(env -u FLOWOPS_ENV_KEEP_EXISTING FLOWOPS_SEAT_POOL=true bash -c '
  source "'"$FAKE"'/scripts/pipeline_config.sh"
  echo "SEAT=${FLOWOPS_SEAT_POOL:-}"' 2>&1)"
assert_out "⑨-10 마커 미설정 → .env 가 덮는다(회귀 0)" "SEAT=false"
OUT="$(env FLOWOPS_ENV_KEEP_EXISTING=true FLOWOPS_SEAT_POOL=true bash -c '
  source "'"$FAKE"'/scripts/pipeline_config.sh"
  echo "SEAT=${FLOWOPS_SEAT_POOL:-}"' 2>&1)"
assert_out "⑨-11 마커 설정 → 기존 env 보존" "SEAT=true"

echo "── runner_clone 프로비저닝 테스트 ──"

# ⑩ clone + 심볼릭 6종 + origin + 멱등
rm -rf "$CLONES/testkey"
OUT="$(RUNNER_CLONE_ROOT="$CLONES" bash "$FAKE/scripts/runner_clone.sh" testkey 2>&1)"
RC=$?
CLONE="$CLONES/testkey"
assert_rc   "⑩ clone exit 0" 0
assert_file "⑩-1 clone 생성" "$CLONE/.git"
assert_out  "⑩-2 신규 clone 로그" "신규 clone"
assert_link "⑩-3 .env 링크"            "$CLONE/.env"                   "$FAKE/.env"
assert_link "⑩-4 seats.json 링크"      "$CLONE/.ralph/seats.json"      "$FAKE/.ralph/seats.json"
assert_link "⑩-5 seats/ 링크"          "$CLONE/.ralph/seats"           "$FAKE/.ralph/seats"
assert_link "⑩-6 workspaces.json 링크" "$CLONE/.ralph/workspaces.json" "$FAKE/.ralph/workspaces.json"
assert_link "⑩-7 workspaces/ 링크"     "$CLONE/workspaces"             "$FAKE/workspaces"
assert_link "⑩-8 logs/ 링크"           "$CLONE/logs"                   "$FAKE/logs"

# .ralph 자체는 clone-로컬이어야 한다(스크래치·락 격리의 본질).
if [ -L "$CLONE/.ralph" ]; then bad "⑩-9 .ralph 는 clone-로컬" ".ralph 가 심볼릭이다"
else ok "⑩-9 .ralph 는 clone-로컬"; fi

# dangling 링크도 유효한 배선이다(이후 PRIMARY 에 파일이 생기면 즉시 살아난다).
# PRIMARY 에 .ralph/seats 가 없는 상태에서 링크만 존재해야 통과한다.
if [ -e "$FAKE/.ralph/seats" ]; then
  bad "⑩-10 dangling 링크 배선" "픽스처 전제 위반 — PRIMARY 에 .ralph/seats 가 생겼다"
elif [ -L "$CLONE/.ralph/seats" ]; then
  ok "⑩-10 dangling 링크 배선(타깃 부재인데 링크 존재)"
else
  bad "⑩-10 dangling 링크 배선" "링크가 없다"
fi

# origin — PRIMARY 에 origin 이 없으므로 clone 의 origin(=PRIMARY 경로)은 제거돼야 한다.
# 남겨두면 러너의 push/브랜치 삭제가 PRIMARY 체크아웃을 겨냥한다(실측 성사됨).
assert_eq  "⑩-11 PRIMARY origin 부재 → clone origin 제거" \
           "$(git -C "$CLONE" remote get-url origin 2>/dev/null || echo "없음")" "없음"
assert_out "⑩-12 origin 제거 경고" "PRIMARY 에 origin 이 없어"

# PRIMARY 에 origin 을 달면 기존 clone 에도 그것이 상속된다(재사용 경로 교정).
git -C "$FAKE" remote add origin "https://example.invalid/canonical.git" >/dev/null 2>&1
OUT="$(RUNNER_CLONE_ROOT="$CLONES" bash "$FAKE/scripts/runner_clone.sh" testkey 2>&1)"
RC=$?
assert_rc  "⑩-13 재실행 exit 0" 0
assert_out "⑩-14 clone 재사용" "재사용"
assert_out "⑩-15 origin 재지정 보고" "origin=재지정"
assert_eq  "⑩-16 canonical origin 상속" \
           "$(git -C "$CLONE" remote get-url origin 2>/dev/null || echo 없음)" \
           "https://example.invalid/canonical.git"

# 멱등 — 3회째 실행은 아무것도 바꾸지 않는다
LINKS_BEFORE="$(find "$CLONE" -maxdepth 2 -type l -printf '%p→%l\n' 2>/dev/null | sort)"
OUT="$(RUNNER_CLONE_ROOT="$CLONES" bash "$FAKE/scripts/runner_clone.sh" testkey 2>&1)"
RC=$?
assert_rc  "⑩-17 3회째 exit 0" 0
assert_out "⑩-18 origin 유지" "origin=유지"
LINKS_AFTER="$(find "$CLONE" -maxdepth 2 -type l -printf '%p→%l\n' 2>/dev/null | sort)"
if [ "$LINKS_BEFORE" = "$LINKS_AFTER" ]; then ok "⑩-19 링크 멱등"
else bad "⑩-19 링크 멱등" "재실행 후 링크 집합이 달라짐"; fi

echo "──────────────────────────────"
echo "통과 ${PASS} / 실패 ${FAIL}"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
