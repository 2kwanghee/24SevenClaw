#!/usr/bin/env bash
# Codex CLI로 REVIEW.md 생성 (QA 단계)
#
# 사용법:
#   bash scripts/run_codex_review.sh
#
# 입력: .ralph/PLAN.md + .ralph/TASK.md + git diff
# 출력: .ralph/REVIEW.md
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

source "$PROJECT_DIR/scripts/pipeline_config.sh" 2>/dev/null || true

mkdir -p .ralph

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Codex QA 리뷰 시작"

# PLAN.md 내용
PLAN_CONTENT=""
if [ -f .ralph/PLAN.md ]; then
  PLAN_CONTENT=$(cat .ralph/PLAN.md)
fi

# TASK.md 내용
TASK_CONTENT=""
if [ -f .ralph/TASK.md ]; then
  TASK_CONTENT=$(cat .ralph/TASK.md)
fi

# 변경된 파일 목록 + diff 요약
DIFF_STAT=$(git diff --stat main 2>/dev/null || echo "(diff 없음)")
DIFF_FILES=$(git diff --name-only main 2>/dev/null || echo "")

PROMPT="당신은 시니어 QA 엔지니어이자 코드 리뷰어다.

프로젝트: 24SevenClaw — AI 개발 자동화 솔루션 빌더 플랫폼

## 기획서 (PLAN)
${PLAN_CONTENT:-기획서 없음}

## 구현 결과 (TASK)
${TASK_CONTENT:-구현 결과 없음}

## 변경 파일
${DIFF_STAT}

## 변경된 파일 목록
${DIFF_FILES}

위 기획서와 구현 결과를 비교하여 리뷰하라.
코드를 직접 수정하지 마라. 분석 결과만 작성하라.

다음 포맷으로 출력:

## 1. 주요 발견
- 구현에서 발견된 주요 사항 (긍정적/부정적)

## 2. 요구사항 충족 여부
- [ ] 수용 기준 1: 충족/미충족 (사유)
- [ ] 수용 기준 2: 충족/미충족 (사유)

## 3. 리스크
- 회귀 위험, 성능 문제, 보안 이슈 등

## 4. 테스트 부족
- 누락된 테스트 케이스

## 5. PR 코멘트 제안
- PR에 남길 리뷰 코멘트 초안"

timeout 120 codex exec "$PROMPT" 2>/dev/null > .ralph/REVIEW.md || {
  echo "WARN: Codex CLI 실행 실패. 기본 REVIEW.md 생성" >&2
  {
    echo "# QA Review (자동 생성 실패)"
    echo ""
    echo "Codex CLI 실행에 실패하여 수동 리뷰가 필요합니다."
    echo ""
    echo "## 변경 파일"
    echo '```'
    echo "$DIFF_STAT"
    echo '```'
  } > .ralph/REVIEW.md
}

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Codex QA 리뷰 완료: .ralph/REVIEW.md"
