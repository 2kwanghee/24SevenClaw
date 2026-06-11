#!/usr/bin/env bash
# collect_week.sh — 주간보고용 데이터 수집기
#
# 이번 주(월요일~오늘) 범위를 결정론적으로 계산하고, 그 범위의 git 커밋을
# 구조화된 형태로 출력한다. 날짜/제목/출력경로 계산은 모두 여기서 끝내고,
# 불릿 요약·큐레이션 같은 "판단"은 호출하는 쪽(모델)이 맡는다.
#
# 사용법:
#   collect_week.sh [--week-offset N]
#     --week-offset N : N주 전 주간을 대상으로 (기본 0 = 이번 주)
#
# 출력(파싱하기 쉬운 KEY=VALUE + 구분자 블록):
#   TITLE=<N월 N째주 주간보고>
#   OUTPUT_PATH=<docs/WeeklyWorkReport/<주월요일>/weekly-report.md>
#   RANGE=<월요일> ~ <끝일>
#   COMMIT_COUNT=<n>
#   === COMMITS ===
#   여러 커밋 레코드 (각 레코드는 \x1e 로 시작, 필드는 아래 라벨로 구분)

set -euo pipefail

WEEK_OFFSET=0
while [ $# -gt 0 ]; do
  case "$1" in
    --week-offset) WEEK_OFFSET="${2:-0}"; shift 2 ;;
    --week-offset=*) WEEK_OFFSET="${1#*=}"; shift ;;
    *) echo "알 수 없는 인자: $1" >&2; exit 2 ;;
  esac
done

# --- 주 경계 계산 (월요일 시작) ---
# %u: 1=월 .. 7=일
dow=$(date +%u)
days_since_monday=$((dow - 1))
back=$((days_since_monday + WEEK_OFFSET * 7))

monday=$(date -d "-${back} days" +%Y-%m-%d)
sunday=$(date -d "${monday} +6 days" +%Y-%m-%d)
today=$(date +%Y-%m-%d)

# 끝일: 이번 주면 오늘까지, 지난 주면 그 주 일요일까지
if [ "$WEEK_OFFSET" -eq 0 ]; then
  range_end="$today"
else
  range_end="$sunday"
fi

# --- 제목: "<월>월 <N>째주 주간보고" (주 월요일 기준) ---
m_month=$(date -d "$monday" +%-m)
m_day=$(date -d "$monday" +%-d)
week_of_month=$(( (m_day - 1) / 7 + 1 ))
case "$week_of_month" in
  1) ord="첫째" ;;
  2) ord="둘째" ;;
  3) ord="셋째" ;;
  4) ord="넷째" ;;
  5) ord="다섯째" ;;
  6) ord="여섯째" ;;
  *) ord="${week_of_month}" ;;
esac
TITLE="${m_month}월 ${ord}주 주간보고"

OUTPUT_PATH="docs/WeeklyWorkReport/${monday}/weekly-report.md"

# --- 커밋 수집 ---
# --no-merges: 머지 커밋 제외 / --since,--until: 주 경계 / author 제한 없음(단독 레포)
mapfile -t hashes < <(git log --no-merges \
  --since="${monday} 00:00:00" \
  --until="${range_end} 23:59:59" \
  --pretty=format:'%H' 2>/dev/null || true)

COMMIT_COUNT=${#hashes[@]}

echo "TITLE=${TITLE}"
echo "OUTPUT_PATH=${OUTPUT_PATH}"
echo "RANGE=${monday} ~ ${range_end}"
echo "COMMIT_COUNT=${COMMIT_COUNT}"
echo "=== COMMITS ==="

if [ "$COMMIT_COUNT" -eq 0 ]; then
  exit 0
fi

strip_prefix() {
  # 커밋 타입/모듈 prefix 정리: "WIP(root):", "feat:", "feat: [frontend]", "[api]" 등
  printf '%s' "$1" \
    | sed -E 's/^(WIP|wip|feat|fix|chore|refactor|docs|test|style|perf|build|ci)(\([^)]*\))?:[[:space:]]*//' \
    | sed -E 's/^\[[^]]*\][[:space:]]*//'
}

for h in "${hashes[@]}"; do
  subject=$(git show -s --format='%s' "$h")
  cdate=$(git show -s --format='%ad' --date=short "$h")
  clean=$(strip_prefix "$subject")
  printf '\x1e'
  echo "DATE: ${cdate}"
  echo "SUBJECT_RAW: ${subject}"
  echo "SUBJECT_CLEAN: ${clean}"
  echo "BODY:"
  git show -s --format='%b' "$h"
  echo "FILES:"
  git show --name-only --format='' "$h" | sed '/^$/d'
done
