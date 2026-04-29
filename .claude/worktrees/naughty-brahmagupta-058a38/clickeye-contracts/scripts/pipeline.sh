#!/bin/bash
# OpenAPI Contract 파이프라인: API 스펙 내보내기 → TS 클라이언트 생성 → 검증
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTRACTS_DIR="$(dirname "$SCRIPT_DIR")"
API_DIR="$CONTRACTS_DIR/../24SevenClaw-api"

echo "=== OpenAPI Contract 파이프라인 ==="
echo ""

# Step 1: API 서버에서 OpenAPI 스펙 내보내기
echo "📤 Step 1: OpenAPI 스펙 내보내기"
if [ -f "$API_DIR/scripts/export_openapi.py" ]; then
  cd "$API_DIR"
  python -m scripts.export_openapi "$CONTRACTS_DIR/openapi/openapi.json"
else
  echo "⚠️ export_openapi.py 없음. fetch-spec.sh로 대체합니다."
  bash "$SCRIPT_DIR/fetch-spec.sh"
fi
echo ""

# Step 2: TypeScript 클라이언트 생성
echo "🔧 Step 2: TypeScript 클라이언트 생성"
cd "$CONTRACTS_DIR"
npx @hey-api/openapi-ts \
  -i openapi/openapi.json \
  -o generated/typescript \
  -c @hey-api/client-fetch
echo ""

# Step 3: 타입 검증
echo "🔍 Step 3: 타입 검증"
npx tsc --noEmit
echo ""

echo "✅ 파이프라인 완료!"
