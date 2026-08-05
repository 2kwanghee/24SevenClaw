#!/usr/bin/env bash
# fullstack_run.sh 단위 테스트 — 실제 기동 없이 인자 파싱·헬퍼 정규화만 검증한다.
#
# 왜 헬퍼만 보는가: 실제 기동은 docker·npm·ngrok 에 의존하므로 CI 재현이 불가능하다. 대신
# **개발 중 실측으로 잡힌 결함 4건**을 회귀로 고정한다(모두 조용한 오판정이라 재발 감지가 어렵다):
#   ① http_code 가 접속 실패 시 "000000" 을 돌려줘 "000 이 아니면 준비됨" 판정을 오통과
#   ② docker inspect 실패 출력(빈 줄)이 상태 문자열에 섞여 "\nabsent/\nabsent" 로 깨짐
#   ③ printf %-Ns 가 바이트 기준이라 한글 라벨에서 요약 표 컬럼이 깨짐
#   ④ pgrep -c 미매칭 시 "0" 출력 + exit 1 → `|| echo 0` 이 "0\n0" 을 만들어 출력에 빈 줄
#
# Usage:
#   bash scripts/tests/test_fullstack_run.sh

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TARGET="$PROJECT_ROOT/scripts/fullstack_run.sh"

PASS=0
FAIL=0
check() {   # check <설명> <기대> <실제>
    if [[ "$2" == "$3" ]]; then
        printf "  ✓ %s\n" "$1"; PASS=$((PASS+1))
    else
        printf "  ✗ %s\n      기대: %q\n      실제: %q\n" "$1" "$2" "$3"; FAIL=$((FAIL+1))
    fi
}

echo "[1/4] 스크립트 자체"
bash -n "$TARGET" && check "bash -n 구문 통과" "0" "0" || check "bash -n 구문 통과" "0" "1"
[[ -x "$TARGET" ]] && check "실행 권한" "yes" "yes" || check "실행 권한" "yes" "no"

echo "[2/4] 인자 파싱"
out="$(bash "$TARGET" --help 2>&1)"; rc=$?
check "--help exit 0" "0" "$rc"
[[ "$out" == *"풀스택 런처"* ]] && check "--help 본문 출력" "yes" "yes" || check "--help 본문 출력" "yes" "no"

out="$(bash "$TARGET" --bogus-flag 2>&1)"; rc=$?
check "알 수 없는 옵션 → exit 2" "2" "$rc"
[[ "$out" == *"알 수 없는 옵션"* ]] && check "알 수 없는 옵션 메시지" "yes" "yes" \
                                    || check "알 수 없는 옵션 메시지" "yes" "no"

# --restart-web (CE-374) — 모순 조합은 **조용히 무시하지 않는다**. 재기동을 기대한 사용자가
# 낡은 서버를 계속 보게 되는 것이 이 플래그가 없애려는 바로 그 증상이므로, 무시 대신 exit 2.
[[ "$(bash "$TARGET" --help 2>&1)" == *"--restart-web"* ]] \
    && check "--help 에 --restart-web 문서화" "yes" "yes" \
    || check "--help 에 --restart-web 문서화" "yes" "no"

out="$(bash "$TARGET" --restart-web --check 2>&1)"; rc=$?
check "--restart-web --check → exit 2" "2" "$rc"
[[ "$out" == *"함께 쓸 수 없습니다"* ]] && check "--check 조합 거부 메시지" "yes" "yes" \
                                        || check "--check 조합 거부 메시지" "yes" "no"

out="$(bash "$TARGET" --restart-web --stop 2>&1)"; rc=$?
check "--restart-web --stop → exit 2" "2" "$rc"

out="$(bash "$TARGET" --restart-web --no-web 2>&1)"; rc=$?
check "--restart-web --no-web → exit 2" "2" "$rc"
[[ "$out" == *"모순"* ]] && check "--no-web 조합 거부 메시지" "yes" "yes" \
                          || check "--no-web 조합 거부 메시지" "yes" "no"

# 재기동은 프로세스가 **사라질 때까지** 기다려야 한다. 포트 해제만 보면 SIGTERM 직후 자식이
# 잠깐 생존해 멱등 생략이 낡은 서버를 "이미 실행 중"으로 잡는다(실측: HTTP 000).
restart_block="$(sed -n '/if \$RESTART_WEB; then/,/^    fi$/p' "$TARGET")"
[[ "$restart_block" == *"filter_ours"* ]] && check "재기동이 filter_ours 로 남의 것 보호" "yes" "yes" \
                                          || check "재기동이 filter_ours 로 남의 것 보호" "yes" "no"
[[ "$restart_block" == *"web_pids | filter_ours | head -1"* ]] \
    && check "재기동 대기가 프로세스 소멸을 확인" "yes" "yes" \
    || check "재기동 대기가 프로세스 소멸을 확인" "yes" "no"
[[ "$restart_block" == *"kill -9"* ]] && check "생존 프로세스 SIGKILL 에스컬레이션" "yes" "yes" \
                                      || check "생존 프로세스 SIGKILL 에스컬레이션" "yes" "no"

# 헬퍼만 떼어 로드(본체 실행 금지 — source 하면 기동이 시작된다).
extract() { sed -n "/^$1()/,/^}/p" "$TARGET"; }
eval "$(extract http_code)"
eval "$(extract trim1)"
eval "$(extract pad)"

echo "[3/4] http_code 정규화 (결함 ①)"
dead_code="$(http_code http://127.0.0.1:59999/)"
check "죽은 포트 → 000 (000000 아님)" "000" "$dead_code"
check "출력이 정확히 3자리" "3" "${#dead_code}"

echo "[4/4] trim1 · pad (결함 ②③④)"
check "trim1: 빈 줄+토큰 → 첫 토큰" "absent" "$(printf '\nabsent\n' | trim1)"
check "trim1: 정상 단일 토큰" "running" "$(printf 'running\n' | trim1)"
check "trim1: pgrep -c 형태(0 두 줄)" "0" "$(printf '0\n0\n' | trim1)"
# pad 는 ASCII 1칸·비ASCII 2칸으로 세어 목표 폭까지 공백을 채운다.
check "pad: ASCII 라벨 폭" "14" "$(printf '%s' "$(pad db 14)" | wc -c | tr -d ' ')"
# '워커'(2자·4칸) → 공백 10개 = 6바이트+10 = 16바이트
check "pad: 한글 라벨은 표시폭 기준" "16" "$(printf '%s' "$(pad 워커 14)" | wc -c | tr -d ' ')"

echo
if (( FAIL == 0 )); then
    echo "전체 통과: $PASS건"
    exit 0
else
    echo "실패 $FAIL건 / 통과 $PASS건"
    exit 1
fi
