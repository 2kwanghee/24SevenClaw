#!/usr/bin/env bash
# Gemini CLI로 PLAN.md 생성 (기획 단계)
#
# 사용법:
#   bash scripts/generate_plan_with_gemini.sh "이슈 제목" "이슈 설명"
#   bash scripts/generate_plan_with_gemini.sh "이슈 제목" "이슈 설명" --fix-plan /path/to/fix_plan.md
#
# 출력: .ralph/PLAN.md
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

source "$PROJECT_DIR/scripts/pipeline_config.sh" 2>/dev/null || true

TITLE="${1:-}"
DESCRIPTION="${2:-}"
FIX_PLAN_PATH=""

shift 2 2>/dev/null || true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --fix-plan)
      FIX_PLAN_PATH="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done

if [ -z "$TITLE" ]; then
  echo "ERROR: 이슈 제목이 필요합니다." >&2
  exit 1
fi

# fix_plan 내용 로드
FIX_PLAN_CONTENT=""
if [ -n "$FIX_PLAN_PATH" ] && [ -f "$FIX_PLAN_PATH" ]; then
  FIX_PLAN_CONTENT=$(cat "$FIX_PLAN_PATH")
fi

mkdir -p .ralph

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Gemini PLAN 생성 시작: $TITLE"

# Gemini CLI 실행
PROMPT="당신은 시니어 PM이자 소프트웨어 아키텍트다.

프로젝트: 24SevenClaw — AI 개발 자동화 솔루션 빌더 플랫폼
아키텍처: Next.js 15 (web) + FastAPI (api) + Python Agent + CLI (TypeScript)

요구사항:
제목: ${TITLE}
설명: ${DESCRIPTION}

${FIX_PLAN_CONTENT:+기존 작업 계획:
$FIX_PLAN_CONTENT}

다음 포맷으로 작성하라. 코드는 작성하지 마라.

## 1. 요구사항 요약
핵심 목표 1~3줄

## 2. 범위 / 비범위
### 범위 (In Scope)
- 이번 작업에서 구현할 것
### 비범위 (Out of Scope)
- 이번 작업에서 구현하지 않을 것

## 3. 작업 단계
1. 단계별 구현 순서 (의존성 고려)
2. 각 단계마다 대상 파일/모듈 명시

## 4. 수용 기준 (Acceptance Criteria)
- [ ] 통과해야 하는 조건들

## 5. 리스크
- 예상 위험 요소와 대응 방안

## 6. 변경 파일 후보
- 파일 경로와 변경 유형 (생성/수정/삭제)

## 7. 테스트 전략
- 유닛 테스트, 통합 테스트, 수동 검증 항목"

timeout 60 gemini -p "$PROMPT" > .ralph/PLAN.md 2>/dev/null || {
  echo "ERROR: Gemini CLI 실행 실패" >&2
  # 폴백: fix_plan을 PLAN.md로 사용
  if [ -n "$FIX_PLAN_CONTENT" ]; then
    echo "FALLBACK: fix_plan.md를 PLAN.md로 사용"
    cp "$FIX_PLAN_PATH" .ralph/PLAN.md
  else
    echo "# PLAN (자동 생성 실패)" > .ralph/PLAN.md
    echo "" >> .ralph/PLAN.md
    echo "## 요구사항" >> .ralph/PLAN.md
    echo "제목: ${TITLE}" >> .ralph/PLAN.md
    echo "설명: ${DESCRIPTION}" >> .ralph/PLAN.md
    exit 1
  fi
}

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Gemini PLAN 생성 완료: .ralph/PLAN.md"
