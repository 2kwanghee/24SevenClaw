#!/bin/bash
# deploy.sh — ClickEye 로컬 전체 스택 순차 자동 기동 메뉴 (단계6)
#
# 사용자가 로컬에서 전체 스택을 의존성 순서로 순차 기동해 테스트하기 위한 메뉴형 스크립트.
# 각 서비스가 healthy 될 때까지 대기한 뒤 다음 단계로 진행한다(순차 헬스 게이트).
#
# 사용법:
#   bash deploy.sh            # 인자 없으면 번호 선택형 메뉴
#   bash deploy.sh up         # 이미지 재빌드(캐시) 후 전체 스택 순차 기동(기본)
#   bash deploy.sh up --no-build  # 재빌드 스킵(=DEPLOY_NO_BUILD=true). 코드 무변경 시 빠른 기동
#   bash deploy.sh down       # 전체 내리기(볼륨 유지)
#   bash deploy.sh status     # 상태 요약
#   bash deploy.sh logs [svc] # 로그 tailing
#   bash deploy.sh reset      # 볼륨까지 삭제(확인 프롬프트)
#
# 회귀 0: 이 스크립트는 자체 프로세스에서만 COMPOSE_PROFILES 를 설정한다.
#   기존 `docker compose up`(프로파일 없음)은 여전히 db/redis 만 기동한다.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$INFRA_DIR/docker"

# deploy 대상 = full(api) + temporal(temporal/ui/worker) 프로파일.
#   이 export 는 이 스크립트 프로세스 내부의 docker compose 호출에만 적용된다.
export COMPOSE_PROFILES="full,temporal"

# web 은 선택 기동(Next 빌드가 무거워 기본 제외). DEPLOY_WITH_WEB=true 시 포함.
DEPLOY_WITH_WEB="${DEPLOY_WITH_WEB:-false}"

cd "$DOCKER_DIR"

# ─────────────────────────────────────────────────────────────
# 헬퍼
# ─────────────────────────────────────────────────────────────

# 컨테이너 healthcheck 가 healthy 될 때까지 대기(순차 게이트).
#   $1 = 컨테이너 이름, $2 = 타임아웃(초, 기본 180)
wait_healthy() {
  local name="$1"
  local timeout="${2:-180}"
  local waited=0
  echo "⏳ ${name} 헬스 대기 중..."
  while true; do
    local status
    status="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$name" 2>/dev/null || echo "missing")"
    case "$status" in
      healthy)
        echo "✅ ${name} healthy"
        return 0
        ;;
      missing)
        echo "❌ ${name} 컨테이너를 찾을 수 없습니다."
        return 1
        ;;
      none)
        # healthcheck 미정의 서비스 → running 여부만 확인
        if [ "$(docker inspect -f '{{.State.Running}}' "$name" 2>/dev/null)" = "true" ]; then
          echo "✅ ${name} running (헬스체크 없음)"
          return 0
        fi
        ;;
    esac
    sleep 2
    waited=$((waited + 2))
    if [ "$waited" -ge "$timeout" ]; then
      echo "❌ ${name} 헬스 타임아웃(${timeout}s). 최근 로그:"
      docker logs --tail 40 "$name" 2>&1 || true
      return 1
    fi
  done
}

print_urls() {
  echo ""
  echo "========================================="
  echo "  ✅ 스택 기동 완료 — 접속 URL"
  echo "========================================="
  echo "  API 서버:      http://localhost:8000"
  echo "  API 문서:      http://localhost:8000/docs"
  echo "  API 헬스:      http://localhost:8000/api/v1/health"
  echo "  Temporal UI:   http://localhost:8080"
  echo "  Temporal gRPC: localhost:7233"
  echo "  PostgreSQL:    localhost:5432 (clickeye/devpassword)"
  echo "  Redis:         localhost:6379"
  if [ "$DEPLOY_WITH_WEB" = "true" ]; then
    echo "  Web:           http://localhost:3000"
  fi
  echo ""
  echo "  상태 확인: bash deploy.sh status"
  echo "  로그 보기: bash deploy.sh logs [서비스]"
  echo "  내리기:    bash deploy.sh down"
  echo ""
}

# ─────────────────────────────────────────────────────────────
# 명령
# ─────────────────────────────────────────────────────────────

cmd_up() {
  echo "========================================="
  echo "  ClickEye 로컬 스택 순차 기동"
  echo "========================================="

  # 0. 이미지 재빌드 (코드 변경 반영 — 캐시로 변경분만, 무변경 시 수 초)
  #    재발 방지: 코드 수정 후 재빌드 누락 → migrate 가 새 마이그레이션을 못 찾는 문제 차단.
  #    스킵: DEPLOY_NO_BUILD=true bash deploy.sh up  (또는 deploy.sh up --no-build)
  if [ "${DEPLOY_NO_BUILD:-false}" != "true" ]; then
    echo ""
    echo "▶ [0/5] 이미지 재빌드 (변경분만, 캐시 활용)..."
    docker compose build
    echo "✅ 이미지 최신화 완료"
  else
    echo ""
    echo "▶ [0/5] 재빌드 스킵 (DEPLOY_NO_BUILD=true)"
  fi

  # 1. PostgreSQL
  echo ""
  echo "▶ [1/5] PostgreSQL 기동..."
  docker compose up -d db
  wait_healthy clickeye-db 120

  # 2. Redis
  echo ""
  echo "▶ [2/5] Redis 기동..."
  docker compose up -d redis
  wait_healthy clickeye-redis 60

  # 3. DB 마이그레이션 (CE-305: migrate one-shot 서비스 게이트로 일원화)
  #    기존 `docker compose run --rm --no-deps api ... alembic upgrade head` 를 제거하고
  #    compose 의 migrate 서비스(restart:no)를 1회 기동해 완료(exit 0)를 확인한다.
  #    api 는 depends_on: migrate(service_completed_successfully) 로 이 완료를 다시
  #    기다리므로 [4/5] 에서 재실행되지 않는다(복제본 있어도 1회).
  echo ""
  echo "▶ [3/5] DB 마이그레이션(migrate 서비스 게이트 · alembic upgrade head)..."
  docker compose up -d migrate
  migrate_code="$(docker wait clickeye-migrate 2>/dev/null || echo 1)"
  if [ "$migrate_code" = "0" ]; then
    echo "✅ 마이그레이션 완료 (migrate exit 0)"
  else
    echo "❌ 마이그레이션 실패 (migrate exit ${migrate_code}). 최근 로그:"
    docker logs --tail 40 clickeye-migrate 2>&1 || true
    exit 1
  fi

  # 4. API
  echo ""
  echo "▶ [4/5] API 서버 기동..."
  docker compose up -d api
  wait_healthy clickeye-api 180
  # 호스트에서 헬스 엔드포인트 확인
  if curl -fsS http://localhost:8000/api/v1/health >/dev/null 2>&1; then
    echo "✅ API /api/v1/health 200"
  else
    echo "⚠️  API 헬스 엔드포인트 응답 없음(컨테이너는 healthy)."
  fi

  # 5. Temporal (서버 → UI → 워커)
  echo ""
  echo "▶ [5/5] Temporal 스택 기동..."
  docker compose up -d temporal
  wait_healthy clickeye-temporal 180
  docker compose up -d temporal-ui worker
  echo "✅ Temporal UI / 워커 기동"

  # (선택) Web
  if [ "$DEPLOY_WITH_WEB" = "true" ]; then
    echo ""
    echo "▶ [+] Web 기동(DEPLOY_WITH_WEB=true)..."
    docker compose up -d web
  fi

  print_urls
}

cmd_down() {
  echo "🔽 전체 스택을 내립니다(볼륨 유지)..."
  docker compose down
  echo "✅ 완료. 데이터 볼륨(pgdata/redisdata)은 보존되었습니다."
}

cmd_status() {
  echo "📦 Docker 서비스:"
  docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "  (없음)"
  echo ""
  # 기존 health-check.sh 재사용(있으면)
  if [ -f "$SCRIPT_DIR/health-check.sh" ]; then
    bash "$SCRIPT_DIR/health-check.sh" || true
  fi
}

cmd_logs() {
  local svc="${1:-}"
  if [ -n "$svc" ]; then
    echo "📜 [$svc] 로그 (Ctrl-C 로 종료)..."
    docker compose logs -f "$svc"
  else
    echo "📜 전체 로그 (Ctrl-C 로 종료)..."
    docker compose logs -f
  fi
}

cmd_reset() {
  echo "⚠️  reset 은 컨테이너와 **데이터 볼륨(pgdata/redisdata)** 을 모두 삭제합니다."
  read -r -p "정말 진행하시겠습니까? (yes 입력 시 진행) " ans
  if [ "$ans" = "yes" ]; then
    docker compose down -v
    echo "✅ 컨테이너 및 볼륨 삭제 완료."
  else
    echo "취소되었습니다."
  fi
}

show_menu() {
  echo "========================================="
  echo "  ClickEye deploy 메뉴"
  echo "========================================="
  echo "  1) up     — 전체 스택 순차 기동"
  echo "  2) down   — 전체 내리기(볼륨 유지)"
  echo "  3) status — 상태 요약"
  echo "  4) logs   — 로그 보기"
  echo "  5) reset  — 볼륨까지 삭제"
  echo "  q) 종료"
  echo ""
  read -r -p "선택> " choice
  case "$choice" in
    1) cmd_up ;;
    2) cmd_down ;;
    3) cmd_status ;;
    4) read -r -p "서비스명(엔터=전체)> " svc; cmd_logs "$svc" ;;
    5) cmd_reset ;;
    q|Q) echo "종료합니다." ;;
    *) echo "알 수 없는 선택: $choice" ;;
  esac
}

# ─────────────────────────────────────────────────────────────
# 엔트리포인트
# ─────────────────────────────────────────────────────────────
main() {
  local action="${1:-menu}"
  case "$action" in
    up)     shift || true; [ "${1:-}" = "--no-build" ] && export DEPLOY_NO_BUILD=true; cmd_up ;;
    down)   cmd_down ;;
    status) cmd_status ;;
    logs)   shift || true; cmd_logs "${1:-}" ;;
    reset)  cmd_reset ;;
    menu)   show_menu ;;
    *)
      echo "알 수 없는 명령: $action"
      echo "사용법: bash deploy.sh [up [--no-build]|down|status|logs [svc]|reset]"
      echo "  up 은 기동 전 이미지를 재빌드한다(캐시). 스킵: up --no-build 또는 DEPLOY_NO_BUILD=true"
      exit 1
      ;;
  esac
}

main "$@"
