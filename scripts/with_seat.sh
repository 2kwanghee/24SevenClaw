#!/usr/bin/env bash
# with_seat.sh — 구독 시트 토큰 주입 래퍼 (다프로젝트화 P4 T3).
#
# 프로젝트에 배정된 시트의 OAuth 토큰을 서버에서 수령해 CLAUDE_CODE_OAUTH_TOKEN 으로
# 주입한 뒤 임의 명령을 실행한다. **합성(composition) 방식** — 기존 배치
# (auto_dev_pipeline.sh / intake_refine.sh / intake_issue.sh / delivery_verify.sh)를
# 한 줄도 수정하지 않는다. 래퍼 없이 실행하면 현행 로그인 세션 그대로(회귀 0).
#
#   scripts/with_seat.sh <project_id> -- <command...>
#   예) scripts/with_seat.sh 3be49b62-... -- env FLOWOPS_INTAKE_ISSUE=true scripts/intake_issue.sh
#
# 동시성: 주입은 **프로세스 env** 이므로 서로 다른 프로젝트를 서로 다른 시트로 감싼
# 프로세스들이 한 서버에서 동시에 실행된다 — 계정 스위칭 없음(claude setup-token →
# CLAUDE_CODE_OAUTH_TOKEN, 공식 지원 경로. 인증 우선순위상 ANTHROPIC_API_KEY 가
# 있으면 그것이 이기므로 여기서 unset 한다 — P3 구독형 전용과 정합).
#
# v1 한계(문서화): 배치 1회 실행 = 시트 1개. 여러 프로젝트의 인테이크를 한 배치가
# 섞어 처리하는 현행 구조에서는 런 단위 시트가 된다 — 프로젝트별 배치 분리는 P5
# (다프로젝트 동시 실행)의 락 세분화와 함께 온다.
#
# 실패는 fail-closed: 시트 수령 불가(404=시트 없음/409=비active/네트워크)면 명령을
# **실행하지 않는다** — 로그인 세션으로 조용히 폴백하면 "어느 계정이 썼는지"가
# 원장에서 거짓이 된다(D-8 위반).
#
# env: API_URL(기본 http://localhost:8000) · GOVERNANCE_SERVICE_TOKEN

set -euo pipefail

usage() { echo "사용법: $0 <project_id> -- <command...>" >&2; exit 2; }

[[ $# -ge 3 ]] || usage
PROJECT_ID="$1"; shift
[[ "${1:-}" == "--" ]] || usage
shift

API_URL="${API_URL:-http://localhost:8000}"
AUTH_ARGS=()
[[ -n "${GOVERNANCE_SERVICE_TOKEN:-}" ]] \
  && AUTH_ARGS=(-H "X-Governance-Token: $GOVERNANCE_SERVICE_TOKEN")

# ── 시트 토큰 수령 (fail-closed — 실패 시 명령 미실행) ─────────────────────
RESP="$(mktemp)"; trap 'rm -f "$RESP"' EXIT
HTTP_CODE=$(curl -sS -m 15 -o "$RESP" -w "%{http_code}" \
  -X POST "$API_URL/api/v1/governance/seat-token" \
  "${AUTH_ARGS[@]}" -H "Content-Type: application/json" \
  -d "{\"project_id\":\"$PROJECT_ID\"}") || {
    echo "[with-seat] ERROR: 시트 수령 요청 실패(네트워크) — 명령 미실행(fail-closed)" >&2
    exit 3
  }
if [[ "$HTTP_CODE" != "200" ]]; then
  echo "[with-seat] ERROR: 시트 수령 거부(HTTP $HTTP_CODE) — 명령 미실행. $(cat "$RESP")" >&2
  exit 3
fi

SEAT_TOKEN=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['token'])" "$RESP")
SEAT_ID=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['seat_id'])" "$RESP")
rm -f "$RESP"; trap - EXIT
[[ -n "$SEAT_TOKEN" ]] || { echo "[with-seat] ERROR: 빈 토큰 — 명령 미실행" >&2; exit 3; }

echo "[with-seat] 시트 주입: seat=$SEAT_ID project=$PROJECT_ID → $1 ..." >&2

# ── 주입 실행 — 토큰은 자식 프로세스 env 로만 전달(로그·파일에 절대 미기록) ──
# ANTHROPIC_API_KEY 는 인증 우선순위상 OAuth 토큰을 이기므로 제거(구독형 전용, P3).
# CLICKEYE_SEAT_ID: 자식(파이프라인→게이트웨이 원장 경유)이 seat 축 기록에 쓸 상관관계 키.
exec env -u ANTHROPIC_API_KEY \
  CLAUDE_CODE_OAUTH_TOKEN="$SEAT_TOKEN" \
  CLICKEYE_SEAT_ID="$SEAT_ID" \
  CLICKEYE_PROJECT_ID="$PROJECT_ID" \
  "$@"
