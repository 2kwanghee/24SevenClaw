#!/usr/bin/env bash
# apply_seat_env 통합 테스트 (시트 풀 v1 / CE-345) — 프레임워크 없이 순수 bash.
#
# auto_dev_pipeline.sh 에서 apply_seat_env 함수 본문만 추출해 격리 소싱하고, 시나리오별
# 반환코드와 **주입 결과**를 검증한다. pytest(seat_map 단위)와 별개로 셸 계층을 덮는다.
#
# 검증 축:
#   1. 토글 off  → 무동작(회귀 0)
#   2. 정상 주입 → 토큰 env + CLICKEYE_SEAT_ID + 성공 로그 (CRLF 제거 포함)
#   3. 판독 불가 토큰 → 시트 참칭 없음(CLICKEYE_SEAT_ID 미설정) + 폴백
#   4. 빈 토큰      → 위와 동일
#   5. STRICT + 미배정  → rc 3 (호출부 exit 97 → 티켓 실패 경로)
#   6. disabled 시트    → STRICT 무관 rc 3 (기본 계정 폴백 금지 = 오귀속 방지)
#   7. 상위 주입(with_seat.sh) 존재 → 존중, 무동작
#   8. 어떤 경로에서도 토큰 **값**이 출력에 나오지 않는다
#
# 실행: bash scripts/tests/test_seat_env.sh   (통과 0 / 실패 1)
set -uo pipefail

REPO="$(cd "$(dirname "$(readlink -f "$0")")/../.." && pwd)"
PIPELINE="$REPO/scripts/auto_dev_pipeline.sh"
TOKEN_VALUE='oat-테스트비밀토큰-노출금지'

PASS=0
FAIL=0

TMP="$(mktemp -d)"
cleanup() { rm -rf "$TMP"; }
trap cleanup EXIT

# ── 격리 레포 구성 ──────────────────────────────────────────────────────────
# pipeline_config.sh 를 **복사**해 _FLOWOPS_CONFIG_DIR 가 이 임시 레포를 가리키게 한다
# (실 레포 .env 의 FLOWOPS_* 가 시나리오 env 를 덮어쓰지 않도록 = 테스트 격리).
FAKE="$TMP/repo"
mkdir -p "$FAKE/scripts" "$FAKE/.ralph/seats"
cp "$REPO/scripts/pipeline_config.sh" "$FAKE/scripts/"
cp "$REPO/scripts/seat_map.py" "$FAKE/scripts/"
LEDGER="$FAKE/.ralph/seats.json"

# 토큰 파일은 CRLF 로 저장 — apply_seat_env 가 \r 을 제거하는지까지 본다.
printf '%s\r\n' "$TOKEN_VALUE" > "$FAKE/.ralph/seats/seat-a.token"
chmod 600 "$FAKE/.ralph/seats/seat-a.token"
: > "$FAKE/.ralph/seats/seat-empty.token"           # 빈 토큰
printf 'x\n' > "$FAKE/.ralph/seats/seat-unreadable.token"
chmod 000 "$FAKE/.ralph/seats/seat-unreadable.token"

seatmap() { python3 "$FAKE/scripts/seat_map.py" "$@" --output "$LEDGER" >/dev/null 2>&1; }
seatmap register-seat --id seat-a --token-file .ralph/seats/seat-a.token --label "계정 A"
seatmap assign --workspace ws-ok --seat seat-a
seatmap register-seat --id seat-empty --token-file .ralph/seats/seat-empty.token
seatmap assign --workspace ws-empty --seat seat-empty
seatmap register-seat --id seat-unreadable --token-file .ralph/seats/seat-unreadable.token
seatmap assign --workspace ws-unreadable --seat seat-unreadable
seatmap register-seat --id seat-off --token-file .ralph/seats/seat-a.token
seatmap assign --workspace ws-disabled --seat seat-off
seatmap set-status --seat seat-off --status disabled

# ── 함수 추출 ───────────────────────────────────────────────────────────────
FN="$TMP/apply_seat_env.sh"
sed -n '/^apply_seat_env() {/,/^}/p' "$PIPELINE" > "$FN"
if [ ! -s "$FN" ]; then
  echo "FAIL: auto_dev_pipeline.sh 에서 apply_seat_env 를 추출하지 못했습니다(함수명·서식 변경?)"
  exit 1
fi

# ── 시나리오 실행기 ─────────────────────────────────────────────────────────
# 자식 bash 에서 apply_seat_env 를 호출하고 결과를 마커로 출력한다.
run_case() {  # run_case <이름> <기대rc> <기대 SEAT 값 또는 -> [env 할당...]
  local name="$1" want_rc="$2" want_seat="$3"; shift 3
  local out rc seat token_set
  out="$(env -u CLAUDE_CODE_OAUTH_TOKEN -u CLICKEYE_SEAT_ID -u CLAUDE_CONFIG_DIR \
         -u FLOWOPS_SEAT_POOL -u FLOWOPS_SEAT_POOL_STRICT -u WORKSPACE_KEY "$@" \
    bash -c '
      # 실제 파이프라인과 동일한 셸 옵션 — set -u/-e 지뢰(미설정 변수 참조 등)까지 잡는다.
      set -euo pipefail
      source "'"$FAKE"'/scripts/pipeline_config.sh"
      PROJECT_DIR="'"$FAKE"'"
      log() { echo "[log] $*"; }
      source "'"$FN"'"
      rc=0
      apply_seat_env || rc=$?   # 호출부와 동일한 || 형태(set -e 억제 문맥)
      echo "__RC=$rc"
      echo "__SEAT=${CLICKEYE_SEAT_ID:--}"
      echo "__TOKEN=${CLAUDE_CODE_OAUTH_TOKEN:--}"
    ' 2>&1)"

  rc="$(sed -n 's/^__RC=//p' <<<"$out")"
  seat="$(sed -n 's/^__SEAT=//p' <<<"$out")"
  token_set="$(sed -n 's/^__TOKEN=//p' <<<"$out")"

  local errs=""
  [ "$rc" = "$want_rc" ] || errs="${errs} rc=$rc(기대 $want_rc)"
  [ "$seat" = "$want_seat" ] || errs="${errs} seat=$seat(기대 $want_seat)"
  # 토큰 값은 어떤 로그·출력에도 나오면 안 된다(__TOKEN 마커 줄만 예외적으로 검사 대상).
  if grep -v '^__TOKEN=' <<<"$out" | grep -qF "$TOKEN_VALUE"; then
    errs="${errs} 토큰값노출"
  fi

  if [ -z "$errs" ]; then
    PASS=$((PASS + 1)); echo "PASS  $name"
  else
    FAIL=$((FAIL + 1)); echo "FAIL  $name —${errs}"; sed 's/^/        /' <<<"$out"
  fi
  # 검사용으로 반환(케이스별 추가 단언에 사용)
  LAST_OUT="$out"; LAST_TOKEN="$token_set"
  rm -f "$FAKE"/.ralph/.seat_lock.* 2>/dev/null || true
}

assert_contains() {  # assert_contains <이름> <문자열>
  if grep -qF "$2" <<<"$LAST_OUT"; then
    PASS=$((PASS + 1)); echo "PASS  $1"
  else
    FAIL=$((FAIL + 1)); echo "FAIL  $1 — 출력에 '$2' 없음"; sed 's/^/        /' <<<"$LAST_OUT"
  fi
}

echo "── apply_seat_env 통합 테스트 ──"

# ① 토글 off(미설정) → 무동작
run_case "① 토글 off 무동작" 0 "-" WORKSPACE_KEY=ws-ok

# ② 정상 주입
run_case "② 정상 주입" 0 "seat-a" FLOWOPS_SEAT_POOL=true WORKSPACE_KEY=ws-ok
assert_contains "②-1 성공 로그" "시트 주입: seat=seat-a"
if [ "$LAST_TOKEN" = "$TOKEN_VALUE" ]; then
  PASS=$((PASS + 1)); echo "PASS  ②-2 토큰 env 적재(CRLF 제거)"
else
  FAIL=$((FAIL + 1)); echo "FAIL  ②-2 토큰 env 불일치(CRLF 잔존?)"
fi

# ③ 판독 불가 토큰 → 시트 참칭 없음
if [ -r "$FAKE/.ralph/seats/seat-unreadable.token" ]; then
  echo "SKIP  ③ 판독 불가 토큰 (이 환경은 파일 권한을 강제하지 않음 — root?)"
else
  run_case "③ 판독 불가 토큰 → 참칭 없음" 0 "-" FLOWOPS_SEAT_POOL=true WORKSPACE_KEY=ws-unreadable
  assert_contains "③-1 폴백 경고" "WARN"
fi

# ④ 빈 토큰 → 시트 참칭 없음
run_case "④ 빈 토큰 → 참칭 없음" 0 "-" FLOWOPS_SEAT_POOL=true WORKSPACE_KEY=ws-empty
assert_contains "④-1 적재 실패 경고" "시트 인증 적재 실패"

# ⑤ STRICT + 미배정 → rc 3
run_case "⑤ STRICT 미배정 rc=3" 3 "-" \
  FLOWOPS_SEAT_POOL=true FLOWOPS_SEAT_POOL_STRICT=true WORKSPACE_KEY=ws-없음

# ⑥ disabled 시트 → STRICT 무관 rc 3
run_case "⑥ disabled 차단(STRICT 무관) rc=3" 3 "-" FLOWOPS_SEAT_POOL=true WORKSPACE_KEY=ws-disabled
assert_contains "⑥-1 차단 사유 로그" "disabled 상태"

# ⑦ 상위 주입(with_seat.sh) 존중
run_case "⑦ 상위 주입 존중" 0 "srv-seat-9" \
  FLOWOPS_SEAT_POOL=true WORKSPACE_KEY=ws-ok CLICKEYE_SEAT_ID=srv-seat-9
if grep -qF "시트 주입: seat=" <<<"$LAST_OUT"; then
  FAIL=$((FAIL + 1)); echo "FAIL  ⑦-1 상위 주입을 덮어썼다"
else
  PASS=$((PASS + 1)); echo "PASS  ⑦-1 로컬 주입 미수행"
fi

echo "──────────────────────────────"
echo "통과 ${PASS} / 실패 ${FAIL}"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
