#!/bin/bash
# pipeline-trigger.sh
# UserPromptSubmit hook — 프롬프트 키워드 기반 파이프라인 라우팅
# Linear webhook 파이프라인과 완전히 독립적으로 동작함

INPUT=$(cat)
PROMPT=$(echo "$INPUT" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    print(d.get('prompt', ''))
except Exception:
    print('')
" 2>/dev/null || echo "")

# 구현/작업 액션 동사 (명확한 실행 요청)
IMPL_PATTERN="구현해|개발해|작업해|코딩해|짜줘|추가해|수정해|리팩터링|리팩토링|만들어줘|파이프라인.*써|파이프라인.*이용|하네스.*써|implement|refactor|fix the bug|write the code"

# 설명/질문 전용 패턴 (파이프라인 제외)
EXPLAIN_ONLY_PATTERN="^(설명해|설명해줘|설명해주세요|알려줘|알려주세요|뭐야|뭔가요|어떻게 생각|어떤 방식|왜 이렇게|what is|explain|how does|tell me)"

# 구현 액션 감지 + 설명 전용 아니면 트리거
if echo "$PROMPT" | grep -qiE "$IMPL_PATTERN"; then
    if echo "$PROMPT" | grep -qiE "$EXPLAIN_ONLY_PATTERN"; then
        # 설명 요청이 우선 — 파이프라인 불필요
        exit 0
    fi

    cat >&2 << 'EOF'
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[파이프라인 트리거] 구현/작업 요청 감지됨
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
하네스 엔지니어링 파이프라인을 실행하세요:

  1. Router  — 의도 분석 (모호하면 되물어보기, 명확하면 진행)
  2. Context — 관련 agent.md + 필요한 파일만 선별 로딩
  3. Loop    — 코드작성 → lint → typecheck → test (MAX 5회)
  4. Worker  — WRITE_CODE / CODE_REVIEW 역할 분리 실행

질문/설명/상담 요청이면 파이프라인 없이 바로 응답.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF
fi
