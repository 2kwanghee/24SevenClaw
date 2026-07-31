#!/usr/bin/env bash
# harness-plan-gate.sh — 플랜 존재 + 사용자 승인 확인 게이트
# PreToolUse hook: Edit/Write 도구 실행 전 플랜 파일과 승인 마커를 검사한다.

PLAN_FILE="${CLAUDE_PROJECT_DIR}/.claude/current-plan.md"

INPUT=$(cat)

# 툴 입력에서 대상 파일 경로 추출
FILE_PATH=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    inp = d.get('tool_input', {})
    print(inp.get('file_path', '') or inp.get('path', ''))
except Exception:
    print('')
" 2>/dev/null || echo "")

# current-plan.md 자체 수정은 항상 허용 (플랜 작성/승인 마커 추가용)
if echo "$FILE_PATH" | grep -q "current-plan.md"; then
    exit 0
fi

# 플랜 파일이 없으면 차단
if [ ! -f "$PLAN_FILE" ]; then
    cat >&2 << 'EOF'
🚫 [플랜 게이트] 코드 수정이 차단되었습니다.

구현 전에 반드시 플랜을 먼저 작성하세요:

  1. .claude/current-plan.md 파일을 아래 형식으로 작성
  2. 사용자에게 플랜을 보여주고 확인 대기
  3. 사용자가 '승인' 또는 '진행해' → 플랜 파일에 아래 줄 추가:
     ## STATUS: APPROVED
  4. 이후 코드 구현 시작

─────────────────────────────────────
플랜 파일 형식 (.claude/current-plan.md):

## 목표
(무엇을 구현하는지 1-2문장)

## 변경 파일 목록
- 파일경로: 변경 내용

## 구현 단계
1. 단계 1
2. 단계 2

## 예상 영향 범위
(다른 기능/모듈에 미치는 영향)
─────────────────────────────────────
EOF
    exit 1
fi

# 플랜은 있지만 승인 마커 없으면 차단
if ! grep -q "STATUS: APPROVED" "$PLAN_FILE"; then
    cat >&2 << 'EOF'
⏳ [플랜 게이트] 사용자 승인 대기 중

플랜이 작성되었습니다. 사용자 확인이 필요합니다.

사용자가 '승인', '진행해', 'OK' 등 확인 시:
  → .claude/current-plan.md 파일 끝에 아래 줄을 추가하세요:
     ## STATUS: APPROVED

이후 코드 구현을 시작할 수 있습니다.
EOF
    exit 1
fi

# 승인 완료 — 통과
exit 0
