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
_load_flowops_env() {
  local env_file="$_FLOWOPS_CONFIG_DIR/.env"
  if [ -f "$env_file" ]; then
    while IFS= read -r line || [ -n "$line" ]; do
      line="${line%%#*}"   # 주석 제거
      line="${line// /}"   # 공백 제거
      if [[ "$line" == FLOWOPS_*=* ]]; then
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
#   FLOWOPS_DOMAIN_PROFILE — 파생형 하네스 Tier 2: STEP A 정제 산출물의 도메인 제약을
#                            대상 워크디렉터리 .claude/CLAUDE.domain.md 로 누적(미설정=off)

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
