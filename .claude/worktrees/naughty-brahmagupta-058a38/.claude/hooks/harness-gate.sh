#!/usr/bin/env bash
# harness-gate.sh — 하네스 엔지니어링 Gate 강제 실행
# 커밋 전 lint/typecheck/test를 돌려서 실패 시 커밋을 차단한다.
#
# 사용: PreToolUse hook으로 git commit 전에 자동 실행
# 반환: 0 = 통과 (커밋 허용), 1 = 실패 (커밋 차단)

set -euo pipefail

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
ERRORS=""
GATE_PASSED=true

# 변경된 모듈 감지
detect_changed_modules() {
    local modules=""

    # staged 파일 기준으로 변경 모듈 감지
    if git -C "$PROJECT_DIR" diff --cached --name-only 2>/dev/null | grep -q "^24SevenClaw-api/"; then
        modules="$modules api"
    fi
    if git -C "$PROJECT_DIR" diff --cached --name-only 2>/dev/null | grep -q "^24SevenClaw-web/"; then
        modules="$modules web"
    fi
    if git -C "$PROJECT_DIR" diff --cached --name-only 2>/dev/null | grep -q "^24SevenClaw-agent/"; then
        modules="$modules agent"
    fi
    if git -C "$PROJECT_DIR" diff --cached --name-only 2>/dev/null | grep -q "^24SevenClaw-contracts/"; then
        modules="$modules contracts"
    fi

    # staged 파일이 없으면 unstaged 변경 확인
    if [ -z "$modules" ]; then
        if git -C "$PROJECT_DIR" diff --name-only 2>/dev/null | grep -q "^24SevenClaw-api/"; then
            modules="$modules api"
        fi
        if git -C "$PROJECT_DIR" diff --name-only 2>/dev/null | grep -q "^24SevenClaw-web/"; then
            modules="$modules web"
        fi
        if git -C "$PROJECT_DIR" diff --name-only 2>/dev/null | grep -q "^24SevenClaw-agent/"; then
            modules="$modules agent"
        fi
        if git -C "$PROJECT_DIR" diff --name-only 2>/dev/null | grep -q "^24SevenClaw-contracts/"; then
            modules="$modules contracts"
        fi
    fi

    echo "$modules"
}

# Gate 실행 함수
run_gate() {
    local gate_name="$1"
    local module="$2"
    local command="$3"
    local dir="$4"

    if [ ! -d "$dir" ]; then
        return 0
    fi

    if ! (cd "$dir" && eval "$command") >/dev/null 2>&1; then
        ERRORS="${ERRORS}\n  ❌ [$module] $gate_name 실패: $command"
        GATE_PASSED=false
    fi
}

# 메인 실행
MODULES=$(detect_changed_modules)

# 변경된 모듈이 없으면 (docs, scripts 등만 변경) 통과
if [ -z "$MODULES" ]; then
    exit 0
fi

# 각 모듈별 Gate 실행
for module in $MODULES; do
    case "$module" in
        api)
            dir="$PROJECT_DIR/24SevenClaw-api"
            run_gate "Gate1:Lint" "api" "uv run ruff check ." "$dir"
            run_gate "Gate2:Type" "api" "uv run mypy app/" "$dir"
            run_gate "Gate3:Test" "api" "uv run pytest --tb=short -q" "$dir"
            ;;
        web)
            dir="$PROJECT_DIR/24SevenClaw-web"
            run_gate "Gate1:Lint" "web" "npm run lint" "$dir"
            run_gate "Gate2:Type" "web" "npx tsc --noEmit" "$dir"
            ;;
        agent)
            dir="$PROJECT_DIR/24SevenClaw-agent"
            run_gate "Gate1:Lint" "agent" "uv run ruff check ." "$dir"
            run_gate "Gate2:Type" "agent" "uv run mypy agent/" "$dir"
            run_gate "Gate3:Test" "agent" "uv run pytest --tb=short -q" "$dir"
            ;;
        contracts)
            dir="$PROJECT_DIR/24SevenClaw-contracts"
            run_gate "Gate2:Type" "contracts" "npx tsc --noEmit" "$dir"
            ;;
    esac
done

# 결과 판정
if [ "$GATE_PASSED" = false ]; then
    echo "🚨 [하네스 Gate] 커밋 차단 — 아래 Gate를 통과하지 못했습니다:" >&2
    echo -e "$ERRORS" >&2
    echo "" >&2
    echo "Gate를 통과한 후 다시 커밋하세요." >&2
    exit 1
fi

exit 0
