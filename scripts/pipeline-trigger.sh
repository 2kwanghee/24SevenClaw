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
        exit 0
    fi

    cat >&2 << 'EOF'
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[파이프라인 트리거] 구현/작업 요청 감지됨
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
반드시 아래 순서로 진행하세요:

  [1] 플랜 작성
      .claude/current-plan.md 에 아래 형식으로 작성:
      ## 목표 / ## 변경 파일 목록 / ## 구현 단계 / ## 예상 영향 범위

  [2] 사용자 확인 대기
      플랜을 사용자에게 보여주고 승인을 기다리세요.
      코드 수정은 이 단계 전까지 물리적으로 차단됩니다.

  [3] 승인 처리
      사용자가 '승인'/'진행해'/OK 시 → 플랜 파일 끝에 추가:
      ## STATUS: APPROVED

  [4] 구현 실행 (하네스 Loop)
      Router → Context → Loop(코드→lint→test MAX 5회) → Worker

  [5] 완료 후 정리
      .claude/current-plan.md 삭제

질문/설명/상담 요청이면 파이프라인 없이 바로 응답.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF
fi
