#!/usr/bin/env bash
# modernize_pipeline.sh — ClickEye Modernize 오케스트레이터 엔트리 스크립트
#
# 실행 전 환경을 점검(.env, git, agent CLI)하고 orchestrator.py 를 기동한다.
# 모든 인자는 orchestrator.py 로 그대로 전달된다 (--dry-run/--resume/--only/--wave 등).
#
# Usage:
#   bash scripts/modernize_pipeline.sh [orchestrator.py 옵션...]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
AGENT_CLI="${AGENT_CLI:-claude}"

cd "$PROJECT_ROOT"

echo "== ClickEye Modernize 오케스트레이터 =="

# 1) .env 존재 확인
if [ ! -f ".env" ]; then
  echo "❌ .env 파일이 없습니다."
  echo "   cp .env.example .env 후 필요한 값을 채워주세요."
  exit 1
fi

# 2) git 저장소 확인
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "❌ git 저장소가 아닙니다. 이 스크립트는 git 으로 관리되는 프로젝트 루트에서 실행해야 합니다."
  exit 1
fi

# 3) agent CLI 확인
if ! command -v "$AGENT_CLI" >/dev/null 2>&1; then
  echo "❌ '$AGENT_CLI' 명령을 찾을 수 없습니다."
  echo "   AGENT_CLI 환경변수로 사용할 CLI를 지정하거나 (예: AGENT_CLI=gemini), '$AGENT_CLI' 를 설치해주세요."
  exit 1
fi

# 4) preflight-review.md 재확인 (있는 경우에만) — plan.json 실행 전 사용자 검수 확인
PREFLIGHT_FILE="docs/preflight-review.md"
if [ -f "$PREFLIGHT_FILE" ]; then
  echo "ℹ️  $PREFLIGHT_FILE 이 존재합니다 — 실행 계획을 검토했는지 확인하세요."
fi

echo "▶ orchestrator.py 기동 (cli=$AGENT_CLI)"
exec python3 "$SCRIPT_DIR/orchestrator.py" --cli "$AGENT_CLI" "$@"
