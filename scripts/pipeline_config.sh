#!/usr/bin/env bash
# Flow-Ops 파이프라인 모듈 토글 설정 로더 (Shell용)
#
# 사용법:
#   source scripts/pipeline_config.sh
#   if is_enabled "FLOWOPS_AUTO_COMMIT"; then
#     echo "자동 커밋 활성화됨"
#   fi

_FLOWOPS_CONFIG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# .env 파일에서 설정 로드
#
# 기본 동작은 "무조건 덮어쓰기" 다(기존 그대로). 다만 러너 디스패처처럼 **호출자가 env 로
# 넘긴 값이 권위** 여야 하는 경우가 있다 — 러너 clone 은 PRIMARY 의 .env 를 심볼릭으로
# 공유하므로, 운영자가 .env 에 `FLOWOPS_SEAT_POOL=false` 를 써두면 디스패처가 넘긴
# `FLOWOPS_SEAT_POOL=true` 가 덮여 전 러너가 개인 계정으로 폴백한다(CE-345 가 막은 오귀속의
# 재발). `FLOWOPS_ENV_KEEP_EXISTING` 마커가 **명시 설정된 경우에만** 이미 set 된 변수를
# 보존한다 — 미설정 시 이 함수의 동작은 이전과 바이트 단위로 동일하다(회귀 0).
_load_flowops_env() {
  local env_file="$_FLOWOPS_CONFIG_DIR/.env"
  local keep=0 key
  if is_enabled "FLOWOPS_ENV_KEEP_EXISTING" 2>/dev/null && [ -n "${FLOWOPS_ENV_KEEP_EXISTING:-}" ]; then
    keep=1
  fi
  if [ -f "$env_file" ]; then
    while IFS= read -r line || [ -n "$line" ]; do
      line="${line%%#*}"   # 주석 제거
      line="${line// /}"   # 공백 제거
      if [[ "$line" == FLOWOPS_*=* ]]; then
        if [ "$keep" = "1" ]; then
          key="${line%%=*}"
          # 이미 프로세스 env 에 있는 값(빈 문자열 포함)은 호출자의 의사로 보고 보존한다.
          [ -n "${!key+x}" ] && continue
        fi
        export "$line"
      fi
    done < "$env_file"
  fi
}

# ── 옵트인(기본 off) 토글 목록 (참고) ──
# is_enabled 는 미설정 시 true 를 반환하므로, 아래 토글들은 호출부에서
# `is_enabled X && [ -n "${X:-}" ]` 이중 체크로 명시적 opt-in 을 강제한다(미설정=off).
#   FLOWOPS_TEMPORAL       — Temporal 섀도우 트리거
#   FLOWOPS_USAGE_INGEST   — 사용량 원장 인제스트
#   FLOWOPS_LLM_INGEST     — LLM KB 머신 인제스트
#   FLOWOPS_WORKSPACE      — 파생형 하네스: WORKSPACE_KEY 워크스페이스에서 구현 실행
#                            (workspaces/<key> 존재 시에만 STEP B cwd 전환, 미설정=off)
#   FLOWOPS_WORKSPACE_DELIVERY — 고객 레포 딜리버리 리다이렉트(CE-347): 워크스페이스 모드에서
#                            브랜치 생성·구현 커밋 확인·거버넌스·push 대상을 ClickEye 레포
#                            대신 고객 clone(IMPL_WORKDIR)으로 돌린다. 태스크 브랜치만 고객
#                            origin 에 push 하고 기본 브랜치 머지·PR 은 하지 않는다.
#                            FLOWOPS_WORKSPACE + WORKSPACE_KEY 가 함께 성립할 때만 유효
#                            (미설정=off → 기존 자기레포 머지 경로 그대로)
#   FLOWOPS_DOMAIN_PROFILE — 파생형 하네스 Tier 2: STEP A 정제 산출물의 도메인 제약을
#                            대상 워크디렉터리 .claude/CLAUDE.domain.md 로 누적(미설정=off)
#   FLOWOPS_METRICS        — 파생형 하네스 Tier 3a: 단계 경계 이벤트를
#                            logs/metrics/pipeline_runs.jsonl 원장에 수집(미설정=off, 비차단)
#   FLOWOPS_SEAT_POOL      — 시트 풀: WORKSPACE_KEY 에 배정된 시트(.ralph/seats.json)를
#                            claude CLI 인증에 주입(미설정=off → 현행 로그인 세션)
#   FLOWOPS_RUNNER_DISPATCH — 러너 수평 확장 디스패처: 매핑·시트 원장을 읽어 워크스페이스별
#                            전용 러너를 clone 안에서 스폰/감시/회수(미설정=off, cron 무해)
#   FLOWOPS_RUNNER_DISPATCH_DRYRUN — 위 디스패처의 산정 결과(스폰 대상)만 출력하고
#                            clone·스폰은 하지 않는다(미설정=off)
#   FLOWOPS_ENV_KEEP_EXISTING — .env 로더가 **이미 set 된 FLOWOPS_* 변수를 덮지 않는다**.
#                            디스패처가 스폰 러너에 넘기는 값(WORKSPACE/SEAT_POOL 등)이
#                            공유 .env 에 눌리는 것을 막는다(미설정=off → 기존 덮어쓰기)
#   FLOWOPS_ENFORCEMENT   — P8 집행면 게이트(CE-329): 조달 시 워크스페이스
#                            .claude/settings.json 에 PreToolUse 훅(gitguard-gate.cjs)을
#                            가산 배선. 미설정=off → 조달 산출물 현행과 바이트 동일
#   FLOWOPS_SEAT_POOL_STRICT — 위 토글의 fail-closed 모드(=true 일 때만).
#                            시트 미배정/타 러너 점유 시 경고 후 진행하지 않고 해당 단계를
#                            스킵한다(기본 미설정 = 경고만 하고 기본 세션으로 진행)

# 모듈 활성화 여부 확인
# 기본값: true (설정이 없으면 활성화)
is_enabled() {
  local key="$1"
  local value="${!key:-}"

  # 값이 없으면 기본값 true
  if [ -z "$value" ]; then
    return 0
  fi

  # "false", "0", "off", "no" → 비활성
  case "${value,,}" in
    false|0|off|no)
      return 1
      ;;
    *)
      return 0
      ;;
  esac
}

# 모듈이 비활성화되어 있으면 메시지 출력 후 종료
# 사용법: check_enabled "FLOWOPS_AUTO_COMMIT" "자동 커밋" || exit 0
check_enabled() {
  local key="$1"
  local label="$2"

  if ! is_enabled "$key"; then
    echo "[SKIP] $label 비활성화됨 ($key=false)"
    return 1
  fi
  return 0
}

# 초기화: .env 로드
_load_flowops_env
