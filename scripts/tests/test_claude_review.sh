#!/usr/bin/env bash
# 구현↔리뷰 분리 QA 게이트 테스트 (CE-390).
#
# 배경: STEP C 는 Codex CLI 호출 + 실패 시 위조 REVIEW.md 폴백이었다(SIP-1 — 리뷰 실행 불능이
# 성공으로 위장). 이 테스트는 claude 를 실행하지 않는다(모델 응답은 CLI 소관). 검증 대상은
#   ① run_codex_review.sh 가 삭제되고 참조가 남지 않았다
#   ② run_claude_review() 가 구현 세션과 별도 프로세스로 claude 를 호출한다(모델 변수·읽기전용 플래그)
#   ③ 구현/리뷰 session_id 비교 배선이 있다(자기검증 감지)
#   ④ 리뷰 실행 불능 시 위조 REVIEW.md 를 만들지 않는다(정상 실패 반환)
#   ⑤ PROMPT.review.md 에 무인 실행 절 + 3값 판정 포맷이 있다
#
# Usage: bash scripts/tests/test_claude_review.sh

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PIPELINE="$REPO_ROOT/scripts/auto_dev_pipeline.sh"
PROMPT_REVIEW="$REPO_ROOT/templates/harness-core/PROMPT.review.md"

PASS=0; FAIL=0
ok()  { printf "  ✓ %s\n" "$1"; PASS=$((PASS+1)); }
bad() { printf "  ✗ %s\n      %s\n" "$1" "$2"; FAIL=$((FAIL+1)); }

echo "[1/5] run_codex_review.sh 제거"
[ ! -f "$REPO_ROOT/scripts/run_codex_review.sh" ] && ok "스크립트 삭제됨" || bad "스크립트가 남아있음" "-"
REFS="$(grep -rln "run_codex_review\.sh" "$REPO_ROOT/scripts" 2>/dev/null | grep -v "test_claude_review\.sh" || true)"
[ -z "$REFS" ] && ok "scripts/ 내 참조 0건" || bad "scripts/ 내 참조 잔존" "$REFS"

echo "[2/5] 리뷰 함수 — 별도 프로세스·읽기전용·정식 모델명"
grep -q "^run_claude_review() {" "$PIPELINE" && ok "run_claude_review 정의 존재" || bad "함수 없음" "-"
grep -q 'PIPELINE_MODEL_REVIEW="\${PIPELINE_MODEL_REVIEW:-claude-sonnet-5}"' "$PIPELINE" \
  && ok "리뷰 티어 변수 + 기본 정식명" || bad "리뷰 티어 변수 없음/별칭" "-"
grep -q -- '--model "\$PIPELINE_MODEL_REVIEW"' "$PIPELINE" && ok "리뷰 호출이 변수 사용" || bad "리뷰 호출 하드코딩" "-"
grep -q -- '--disallowedTools "Edit,Write,NotebookEdit"' "$PIPELINE" \
  && ok "Edit/Write/NotebookEdit 비활성화" || bad "쓰기 툴 차단 배선 없음" "-"
REVIEW_FN_BODY="$(sed -n '/^run_claude_review() {/,/^}/p' "$PIPELINE")"
if printf '%s' "$REVIEW_FN_BODY" | grep -q -- '--dangerously-skip-permissions'; then
  bad "리뷰 함수에 --dangerously-skip-permissions 존재" "-"
else
  ok "리뷰 함수는 --dangerously-skip-permissions 미사용"
fi

echo "[3/5] 구현↔리뷰 세션 분리 검증 배선"
grep -q "IMPL_SESSION_ID=" "$PIPELINE" && ok "구현 세션 session_id 파싱" || bad "구현 세션 파싱 없음" "-"
printf '%s' "$REVIEW_FN_BODY" | grep -q 'session_id' && ok "리뷰 세션 session_id 파싱" || bad "리뷰 세션 파싱 없음" "-"
printf '%s' "$REVIEW_FN_BODY" | grep -q '"\$impl_sid" = "\$review_sid"' \
  && ok "동일 session_id 비교 배선" || bad "자기검증 비교 배선 없음" "-"

echo "[4/5] 실행 불능 시 위조 REVIEW.md 미생성"
printf '%s' "$REVIEW_FN_BODY" | grep -q "재시도 소진 — REVIEW.md 생성하지 않음" \
  && ok "재시도 소진 시 REVIEW.md 미생성 로그/분기" || bad "위조 REVIEW.md 방지 배선 없음" "-"
printf '%s' "$REVIEW_FN_BODY" | grep -qE 'for attempt in 1 2;' && ok "비정상 종료 1회 재시도" || bad "재시도 배선 없음" "-"
grep -q '"QA 리뷰 실행 불능 또는 구현/리뷰 세션 분리 위반"' "$PIPELINE" \
  && ok "STEP C 실패가 handle_task_failure 경로로 이어짐" || bad "실패 경로 배선 없음" "-"

echo "[5/5] PROMPT.review.md — 무인 절 + 3값 판정 포맷"
[ -f "$PROMPT_REVIEW" ] && ok "파일 존재" || bad "파일 없음" "-"
grep -q "되묻기는 그 자체가 실패다" "$PROMPT_REVIEW" && ok "무인 실행 절 포함" || bad "무인 실행 절 없음" "-"
grep -q "통과 | 실패 | 판정불가" "$PROMPT_REVIEW" && ok "3값 판정 포맷 고정" || bad "판정 포맷 없음" "-"
grep -q "파일을 고치거나 새로 만들지" "$PROMPT_REVIEW" && ok "읽기전용 역할 명시" || bad "읽기전용 명시 없음" "-"

echo
echo "구문 검사"
bash -n "$PIPELINE" && ok "auto_dev_pipeline.sh" || bad "구문 오류" "-"

echo
if (( FAIL == 0 )); then echo "전체 통과: $PASS건"; exit 0
else echo "실패 $FAIL건 / 통과 $PASS건"; exit 1; fi
