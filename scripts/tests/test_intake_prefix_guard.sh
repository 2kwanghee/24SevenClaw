#!/usr/bin/env bash
# 수주 접두사 fail-closed 가드 테스트 (CE-358).
#
# 실측 위험: `intake_issue.sh` 가 붙이는 `[수주:<인테이크id 앞8자>] ` 접두사는 "이 티켓은 고객
# 프로젝트 것" 이라는 선언인데, 그 워크스페이스가 조달돼 있지 않으면 resolve_impl_workdir 이
# 조용히 PROJECT_DIR 로 폴백해 **고객 요구사항이 ClickEye 레포에 구현·머지**된다. 인테이크
# 파일럿의 정상 순서(수주→수락→발급)가 새 접두사를 만들므로 정상 절차가 곧 사고 경로였다.
#
# 이 테스트는 파이프라인을 구동하지 않는다. 가드의 두 판정(① 접두사 인식 ② 조달 여부)과
# resolve_impl_workdir 의 폴백 성질을 고정한다.
#
# Usage: bash scripts/tests/test_intake_prefix_guard.sh

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PIPELINE="$REPO_ROOT/scripts/auto_dev_pipeline.sh"

PASS=0; FAIL=0
ok()  { printf "  ✓ %s\n" "$1"; PASS=$((PASS+1)); }
bad() { printf "  ✗ %s\n      %s\n" "$1" "$2"; FAIL=$((FAIL+1)); }

# 가드가 쓰는 판정을 그대로 재현(로직이 갈라지면 테스트가 무의미해지므로 배선 존재도 확인).
is_intake_title() { printf '%s' "$1" | grep -qE '^\[수주:[0-9a-zA-Z]{6,}\][[:space:]]'; }
prefix_key()      { printf '%s' "$1" | sed -E 's/^\[수주:([0-9a-zA-Z]{6,})\].*/\1/'; }

echo "[1/4] 파이프라인 배선"
grep -q "CE-358" "$PIPELINE" && ok "가드 블록 존재(CE-358 마커)" || bad "가드 없음" "-"
grep -q "self-repo 폴백을 차단한다" "$PIPELINE" && ok "차단 로그 문구 존재" || bad "차단 로그 없음" "-"
grep -q "workspace_provision.sh --key" "$PIPELINE" && ok "복구 명령 안내 존재" || bad "복구 안내 없음" "-"
bash -n "$PIPELINE" && ok "bash -n 통과" || bad "구문 오류" "-"

echo "[2/4] 접두사 인식"
is_intake_title "[수주:3be49b62] 리허설 티켓" && ok "8자 키 인식" || bad "8자 키 미인식" "-"
is_intake_title "[수주:a1b2c3d4e5] 긴 키"      && ok "긴 키 인식"  || bad "긴 키 미인식" "-"
! is_intake_title "일반 티켓 제목"             && ok "일반 티켓은 비수주" || bad "일반 티켓 오인" "-"
! is_intake_title "[수주:3be49b62]붙어있음"    && ok "접두사 뒤 공백 없으면 비수주" || bad "공백 규약 미적용" "-"
! is_intake_title "앞에 글자 [수주:3be49b62] " && ok "제목 중간 등장은 비수주(^ 고정)" || bad "^ 고정 안 됨" "-"

echo "[3/4] 키 추출"
[[ "$(prefix_key '[수주:3be49b62] 제목')" == "3be49b62" ]] && ok "키 추출 정확" \
  || bad "키 추출 실패" "$(prefix_key '[수주:3be49b62] 제목')"

echo "[4/4] resolve_impl_workdir 폴백 성질(가드가 필요한 이유)"
eval "$(sed -n '/^resolve_impl_workdir() {/,/^}/p' "$PIPELINE")"
is_enabled() { [ "${!1:-}" = "true" ]; }   # 파이프라인 헬퍼 대역
SANDBOX="$(mktemp -d)"; trap 'rm -rf "$SANDBOX"' EXIT
PROJECT_DIR="$SANDBOX"; mkdir -p "$SANDBOX/workspaces/mapped01"

FLOWOPS_WORKSPACE=true WORKSPACE_KEY=mapped01 out="$(resolve_impl_workdir)"
[[ "$out" == "$SANDBOX/workspaces/mapped01" ]] && ok "조달된 키 → 워크스페이스" || bad "워크스페이스 해석 실패" "$out"

FLOWOPS_WORKSPACE=true WORKSPACE_KEY=missing99 out="$(resolve_impl_workdir)"
[[ "$out" == "$SANDBOX" ]] && ok "미조달 키 → PROJECT_DIR 폴백(가드가 막아야 하는 그 동작)" \
  || bad "폴백 성질이 바뀜 — 가드 전제 재확인 필요" "$out"

echo
if (( FAIL == 0 )); then echo "전체 통과: $PASS건"; exit 0
else echo "실패 $FAIL건 / 통과 $PASS건"; exit 1; fi
