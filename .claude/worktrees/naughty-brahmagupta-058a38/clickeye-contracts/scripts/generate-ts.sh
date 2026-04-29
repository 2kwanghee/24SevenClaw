#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTRACTS_DIR="$(dirname "$SCRIPT_DIR")"

cd "$CONTRACTS_DIR"

echo "🔧 TypeScript 클라이언트 생성 중..."
npx @hey-api/openapi-ts \
  -i openapi/openapi.json \
  -o generated/typescript \
  -c @hey-api/client-fetch

echo "🔍 타입 검증 중..."
npx tsc --noEmit

echo "✅ 생성 완료: generated/typescript/"
