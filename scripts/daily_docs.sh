#!/usr/bin/env bash
# 24SevenClaw 일일 문서 자동 생성 스크립트
# 매일 실행하여 docs/spec/에 최신 사양 문서(.docx)를 갱신한다.
#
# 사용법:
#   bash scripts/daily_docs.sh          # 전체 문서 갱신
#   bash scripts/daily_docs.sh --daily  # 일일 보고서만 생성
#
# cron 등록 예시 (매일 오전 9시):
#   0 9 * * * cd /mnt/c/workspace/24SevenClaw && bash scripts/daily_docs.sh >> logs/daily_docs.log 2>&1

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "=== 24SevenClaw 문서 생성 시작: $(date '+%Y-%m-%d %H:%M:%S') ==="

python3 scripts/generate_spec_docs.py "$@"

echo "=== 문서 생성 완료: $(date '+%Y-%m-%d %H:%M:%S') ==="
echo ""
echo "생성된 파일 목록:"
ls -la docs/spec/*.docx 2>/dev/null || echo "  (없음)"
