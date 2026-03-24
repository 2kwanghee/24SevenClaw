#!/usr/bin/env bash
# 24SevenClaw 일일 문서 자동 생성 스크립트
# 자동 실행 시 일일 보고서만 생성. 기타 문서는 수동 요청 시에만 생성.
#
# 사용법:
#   bash scripts/daily_docs.sh              # 일일 보고서만 생성 (기본, cron용)
#   bash scripts/daily_docs.sh --all        # 전체 문서 갱신 (수동 요청 시)
#   bash scripts/daily_docs.sh --prd        # 기획서만 생성
#   bash scripts/daily_docs.sh --api        # API 정의서만 생성
#   bash scripts/daily_docs.sh --tech       # 기술설계서만 생성
#   bash scripts/daily_docs.sh --arch       # 시스템 아키텍처만 생성
#
# cron 등록 예시 (매일 오전 9시 — 일일 보고서만):
#   0 9 * * * cd /mnt/c/workspace/24SevenClaw && bash scripts/daily_docs.sh >> logs/daily_docs.log 2>&1

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "=== 24SevenClaw 문서 생성 시작: $(date '+%Y-%m-%d %H:%M:%S') ==="

# 인자 없으면 일일 보고서만 생성 (기존: --all)
if [ $# -eq 0 ]; then
  python3 scripts/generate_spec_docs.py --daily
else
  python3 scripts/generate_spec_docs.py "$@"
fi

echo "=== 문서 생성 완료: $(date '+%Y-%m-%d %H:%M:%S') ==="
echo ""
echo "생성된 파일 목록:"
ls -la docs/spec/*.docx 2>/dev/null || echo "  (없음)"
