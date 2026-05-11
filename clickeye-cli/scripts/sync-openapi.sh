#!/usr/bin/env bash
# clickeye-contracts의 OpenAPI 스펙을 가져와 TypeScript 클라이언트를 생성합니다.
# 사용법: bash scripts/sync-openapi.sh [api-url]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONTRACTS_DIR="${CONTRACTS_DIR:-$(dirname "$PROJECT_DIR")/clickeye-contracts}"
SPEC_SRC="${CONTRACTS_DIR}/openapi/openapi.json"
SPEC_DEST="${PROJECT_DIR}/src/api/openapi.json"
OUT_DIR="${PROJECT_DIR}/src/api/generated"

# API URL이 인자로 전달되면 서버에서 실시간 스펙을 가져옴
if [[ "${1:-}" != "" ]]; then
  echo "📡 API에서 OpenAPI 스펙을 가져오는 중..."
  curl -sf "${1}/openapi.json" -o "$SPEC_DEST"
else
  echo "📋 contracts 레포에서 OpenAPI 스펙을 복사하는 중..."
  if [[ ! -f "$SPEC_SRC" ]]; then
    echo "❌ 스펙 파일을 찾을 수 없습니다: $SPEC_SRC"
    echo "   CONTRACTS_DIR 환경변수를 설정하거나 contracts 레포를 확인해 주세요."
    exit 1
  fi
  cp "$SPEC_SRC" "$SPEC_DEST"
fi

echo "⚙️  TypeScript 클라이언트 생성 중..."
npx --yes @hey-api/openapi-ts \
  --input "$SPEC_DEST" \
  --output "$OUT_DIR" \
  --client @hey-api/client-fetch \
  --types true

echo "✅ 클라이언트 생성 완료: $OUT_DIR"
