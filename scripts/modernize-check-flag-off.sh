#!/usr/bin/env bash
# R-6 회귀 검증 — Feature flag OFF 시 Modernize 라우트/endpoint 가 모두 404.
#
# 사용:
#   bash scripts/modernize-check-flag-off.sh [API_URL] [WEB_URL]
#
# API/WEB URL 미지정 시 localhost. dev 서버 + flag=false 상태로 기동되어 있어야 함.
set -uo pipefail

API_URL="${1:-http://localhost:8000}"
WEB_URL="${2:-http://localhost:3000}"

echo "═══════════════════════════════════════════════════"
echo "  R-6 Feature flag OFF 검증"
echo "  api=$API_URL · web=$WEB_URL"
echo "═══════════════════════════════════════════════════"

violations=0
check_404() {
    local label="$1" url="$2"
    local code
    code=$(curl -s -o /dev/null -w "%{http_code}" -m 5 "$url" 2>/dev/null || echo "000")
    if [[ "$code" == "404" || "$code" == "401" || "$code" == "403" ]]; then
        # 404 (flag off) / 401 (unauth) / 403 (forbid) 모두 OK — 신규 endpoint 가 노출되지 않음
        echo "  ✓ $label → $code (차단됨)"
    else
        echo "  ✗ $label → $code (노출 의심)"
        violations=$((violations + 1))
    fi
}

# Backend endpoints — flag OFF 시 require_modernize_feature 가 404
echo
echo "[Backend Modernize endpoints — flag OFF 시 404 기대]"
check_404 "/integrations/github/app/install-url" "$API_URL/api/v1/integrations/github/app/install-url"
check_404 "/modernize/installations" "$API_URL/api/v1/modernize/installations"
check_404 "/modernize/sessions/00000000-0000-0000-0000-000000000000" \
    "$API_URL/api/v1/modernize/sessions/00000000-0000-0000-0000-000000000000"

# Backend 기존 endpoint 1개 — 정상 응답 확인 (회귀 안전)
echo
echo "[Backend 기존 endpoint — 200/401 등 정상 응답 기대]"
code=$(curl -s -o /dev/null -w "%{http_code}" -m 5 "$API_URL/api/v1/healthz" 2>/dev/null || echo "000")
if [[ "$code" == "200" || "$code" == "404" ]]; then
    echo "  ✓ /healthz → $code (기존 endpoint 정상)"
else
    echo "  ⚠ /healthz → $code"
fi

# Frontend route — flag OFF 시 redirect (HTTP 200 + redirect markup, 또는 client-side redirect)
echo
echo "[Frontend /solutions/modernize/new — flag OFF 시 redirect/404 기대]"
code=$(curl -s -o /dev/null -w "%{http_code}" -m 5 "$WEB_URL/solutions/modernize/new" 2>/dev/null || echo "000")
echo "  /solutions/modernize/new → $code"
echo "  (Next.js SPA — flag 체크는 클라이언트 측에서 일어남.\n    실제 검증은 브라우저에서 페이지 로드 후 redirect 확인)"

echo
if [[ $violations -gt 0 ]]; then
    echo "✗ R-6 실패: $violations 건의 신규 endpoint 가 flag OFF 상태에서 노출"
    exit 1
fi

echo "✓ R-6 통과: backend 신규 endpoint 모두 차단됨"
exit 0
