#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
CONTRACTS_DIR="$ROOT_DIR/clickeye-contracts"
API_URL="${API_URL:-http://localhost:8000}"

echo "🔄 OpenAPI 클라이언트 생성"
echo ""

# 1. API 서버에서 스펙 가져오기
echo "📥 OpenAPI 스펙 다운로드 중..."
curl -sf "$API_URL/openapi.json" -o "$CONTRACTS_DIR/openapi/openapi.json"
echo "✅ openapi.json 다운로드 완료"

# 2. TypeScript 클라이언트 생성
echo "🔧 TypeScript 클라이언트 생성 중..."
cd "$CONTRACTS_DIR"
npx @hey-api/openapi-ts -i openapi/openapi.json -o generated/typescript -c @hey-api/client-fetch
echo "✅ TypeScript 클라이언트 생성 완료"

# 3. 타입 검증
echo "🔍 타입 검증 중..."
npx tsc --noEmit
echo "✅ 타입 검증 통과"

echo ""
echo "✅ API 클라이언트가 $CONTRACTS_DIR/generated/typescript/ 에 생성되었습니다."
