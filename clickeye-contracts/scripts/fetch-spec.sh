#!/bin/bash
set -euo pipefail

API_URL="${API_URL:-http://localhost:8000}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTRACTS_DIR="$(dirname "$SCRIPT_DIR")"

echo "📥 OpenAPI 스펙 다운로드: $API_URL/openapi.json"
curl -sf "$API_URL/openapi.json" -o "$CONTRACTS_DIR/openapi/openapi.json"
echo "✅ 완료: $CONTRACTS_DIR/openapi/openapi.json"
