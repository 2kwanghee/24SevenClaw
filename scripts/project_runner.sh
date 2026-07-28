#!/usr/bin/env bash
# project_runner.sh — 프로젝트 단위 파이프라인 러너 (다프로젝트화 P5 T2).
#
# 한 서버에서 여러 프로젝트를 **프로젝트별 시트 + 프로젝트별 티켓 범위**로 돌린다.
# 기존 배치를 한 줄도 수정하지 않는 **합성(composition)** 방식 — 시트 주입은
# with_seat.sh, 티켓 범위는 watcher 의 --title-prefix(env WATCHER_TITLE_PREFIX)로
# 얹는다. 러너를 쓰지 않으면 현행 동작 그대로(회귀 0).
#
#   scripts/project_runner.sh <project_id> --prefix "[수주:3be49b62] " [--once]
#
# ── P5 v1 동시성 범위 ────────────────────────────────────────────────────────
# v1 은 **순차-다프로젝트(인터리브)** 다. 파이프라인의 전역 락(.ralph/.pipeline_lock)이
# 동시 기동을 직렬화하므로, 두 프로젝트 러너를 같이 띄우면 후발 러너는 SKIP 된다 —
# 버그가 아니라 의도된 동작이다(단일 체크아웃에서 두 파이프라인이 main 브랜치를
# 동시 점유할 수 없다). 프로젝트 A 종료 후 B 가 도는 인터리브까지가 v1 의 보장 범위.
#
# 진짜 병렬은 락 세분화가 아니라 **러너 수평 확장** — 프로젝트별 클론/컨테이너로
# 워킹트리를 분리하고, 각 러너가 자기 트리에서 독립 실행한다. 이때 남는 요구사항은
# main 머지 직렬화(여러 트리가 같은 원격 main 에 머지 → 머지 게이트/큐 필요)와
# 시트별 레이트 카운터(로컬 claude -p 사용량의 서버 원장 인제스트 배관 선행)다.
#
# ── --prefix 가 필수 인자인 이유 ──────────────────────────────────────────────
# 티켓 접두사는 `[수주:<intake_id 앞 8자>] `(intake_issue.sh 규약)이며, 이는
# **프로젝트 id 가 아니라 인테이크 id** 에서 나온다. 머신(러너)이 project_id 만으로
# 이를 유도할 방법이 현재 없다 — 인테이크 조회 엔드포인트(GET /api/v1/intake)는
# 사용자 JWT 를 요구해 머신 토큰으로 못 부르고, 이 한 값을 위해 새 엔드포인트를
# 추가하는 것은 과잉이다. 운영자는 인테이크 콘솔/발급 로그에서 접두사를 알고 있으므로
# 명시 인자로 받는다. (자동 유도가 필요해지면 그때 머신용 조회면을 설계한다.)
#
# env: API_URL · GOVERNANCE_SERVICE_TOKEN (with_seat.sh 로 그대로 전달)

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  cat >&2 <<'EOF'
사용법: scripts/project_runner.sh <project_id> --prefix "<티켓 제목 접두사>" [--once]

  <project_id>  시트가 배정된 프로젝트 UUID (with_seat.sh 로 전달)
  --prefix      필수. 이 프로젝트로 발급된 티켓의 제목 접두사.
                형식: "[수주:<intake_id 앞 8자>] " (intake_issue.sh 규약)
                필수인 이유: 접두사는 프로젝트 id 가 아니라 **인테이크 id** 에서
                유도되고, 인테이크 조회 API 는 사용자 JWT 를 요구해 머신이 부를 수
                없다. 운영자는 인테이크 콘솔/발급 로그에서 이 값을 알고 있다.
  --once        태스크 1개 처리 후 종료 (파이프라인에 전달)

예) scripts/project_runner.sh 3be49b62-1e0c-4b7d-9a11-000000000000 \
      --prefix "[수주:3be49b62] " --once
EOF
  exit 2
}

[[ $# -ge 1 ]] || usage
PROJECT_ID="$1"; shift
[[ "$PROJECT_ID" != --* ]] || usage

PREFIX=""
PIPELINE_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --prefix)
      [[ $# -ge 2 ]] || usage
      PREFIX="$2"; shift 2
      ;;
    --prefix=*)
      PREFIX="${1#--prefix=}"; shift
      ;;
    --once)
      PIPELINE_ARGS+=("--once"); shift
      ;;
    *)
      echo "[runner] ERROR: 알 수 없는 인자: $1" >&2
      usage
      ;;
  esac
done
[[ -n "$PREFIX" ]] || { echo "[runner] ERROR: --prefix 는 필수입니다." >&2; usage; }

# ── 프로젝트별 로그 ──────────────────────────────────────────────────────────
mkdir -p "$PROJECT_DIR/logs"
LOG_FILE="$PROJECT_DIR/logs/runner_${PROJECT_ID:0:8}_$(date '+%Y%m%d_%H%M%S').log"

# 자기 stdout/stderr 를 tee 로 갈아끼운 뒤 exec 한다 — exec 된 자식이 이 fd 를
# 물려받으므로 로그는 남고, **종료 코드는 가공 없이 그대로 전파**된다
# (with_seat 의 fail-closed exit 3 을 러너가 삼키면 안 된다).
exec > >(tee -a "$LOG_FILE") 2>&1

echo "[runner] project=$PROJECT_ID prefix='$PREFIX'" \
     "pipeline_args=[${PIPELINE_ARGS[*]+${PIPELINE_ARGS[*]}}] log=$LOG_FILE"

# ── 시트 주입 → 프로젝트 티켓 범위 → 파이프라인 ───────────────────────────────
# 시트 수령 실패(exit 3)면 with_seat 이 파이프라인을 실행하지 않는다 — 러너는
# 로그인 세션으로 조용히 대체하지 않는다(어느 계정이 썼는지가 원장에서 거짓이 되면
# 안 된다. D-8).
exec "$PROJECT_DIR/scripts/with_seat.sh" "$PROJECT_ID" -- \
  env WATCHER_TITLE_PREFIX="$PREFIX" FLOWOPS_LINEAR_WATCHER=true \
  bash "$PROJECT_DIR/scripts/auto_dev_pipeline.sh" "${PIPELINE_ARGS[@]+"${PIPELINE_ARGS[@]}"}"
