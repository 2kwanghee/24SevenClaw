#!/usr/bin/env bash
# 자동 기능 개발 파이프라인 (v6 — 멀티 Agent 순차 실행)
#
# 워크플로우:
#   1. Linear Queued 이슈 1개 감지 → fix_plan 생성
#   2. [Claude] 메타프롬프트 정제(관측형 사전 정제, 기획+정제 일체) → PLAN.md 생성
#      (FLOWOPS_METAPROMPT=false 시 레거시 Gemini 기획으로 폴백)
#   3. 브랜치 생성 → [Claude] 구현(정제 스펙 prepend) → TASK.md 생성
#   4. [Codex] QA 리뷰 → REVIEW.md 생성
#   5. Linear 결과 보고 + PR 생성
#   6. 다음 Queued 이슈로 반복
#
# 사용법:
#   bash scripts/auto_dev_pipeline.sh
#   bash scripts/auto_dev_pipeline.sh --max-turns 5        # 시연용 (짧은 루프)
#   bash scripts/auto_dev_pipeline.sh --max-iterations 50
#   bash scripts/auto_dev_pipeline.sh --once                # 1개만 처리 후 종료
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# 모듈 토글 로드
source "$PROJECT_DIR/scripts/pipeline_config.sh" 2>/dev/null || true

# LINEAR_TEAM_ID 로드 — pipeline_config 는 FLOWOPS_* 만 export 하므로 여기서 보강.
# 거버넌스 evaluate 페이로드·LLM 머신 인제스트(P1.6)의 team→project 역매핑에 사용. 없으면 빈 값.
if [ -z "${LINEAR_TEAM_ID:-}" ] && [ -f "$PROJECT_DIR/.env" ]; then
  LINEAR_TEAM_ID="$(grep -E '^LINEAR_TEAM_ID=' "$PROJECT_DIR/.env" 2>/dev/null | head -n1 | cut -d= -f2- | tr -d '[:space:]')" || LINEAR_TEAM_ID=""
fi

LOCK_FILE=".ralph/.pipeline_lock"
TASK_MAPPING=".ralph/.task_mapping.json"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

# ── Git lock guard ──
# index.lock 대기 후 실행. 최대 15초 대기, 초과 시 stale lock 제거.
wait_for_git_lock() {
  local lock_file
  lock_file="$(git rev-parse --git-dir 2>/dev/null)/index.lock"
  local max_wait=15
  local waited=0

  while [ -f "$lock_file" ] && [ "$waited" -lt "$max_wait" ]; do
    sleep 1
    waited=$((waited + 1))
  done

  if [ -f "$lock_file" ]; then
    log "WARN: git index.lock이 ${max_wait}초 후에도 존재. stale lock 제거."
    rm -f "$lock_file"
  fi
}

safe_git() {
  wait_for_git_lock
  git "$@"
}

# ── 파라미터 ──
MAX_ITERATIONS=30
MAX_TURNS=""
ONCE_MODE=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --max-iterations)
      MAX_ITERATIONS="$2"
      shift 2
      ;;
    --max-turns)
      MAX_TURNS="$2"
      shift 2
      ;;
    --once)
      ONCE_MODE=true
      shift
      ;;
    *)
      log "알 수 없는 옵션: $1"
      exit 1
      ;;
  esac
done

# ── 중복 실행 방지 ──
if [ -f "$LOCK_FILE" ]; then
  LOCK_PID=$(cat "$LOCK_FILE" 2>/dev/null || echo "")
  if [ -n "$LOCK_PID" ] && kill -0 "$LOCK_PID" 2>/dev/null; then
    log "SKIP: 이전 파이프라인 실행 중 (PID: $LOCK_PID)"
    exit 0
  else
    log "WARN: 잔류 lock 파일 제거 (PID: $LOCK_PID 종료됨)"
    rm -f "$LOCK_FILE"
  fi
fi

echo $$ > "$LOCK_FILE"

cleanup() {
  rm -f "$LOCK_FILE"
  safe_git checkout main 2>/dev/null || true
}
trap cleanup EXIT

log "======================================="
log "  자동 개발 파이프라인 v6 (멀티 Agent)"
log "  Gemini(기획) → Claude(구현) → Codex(QA)"
log "======================================="

# ── Linear Watcher 활성화 확인 ──
if ! is_enabled "FLOWOPS_LINEAR_WATCHER" 2>/dev/null; then
  log "SKIP: Linear Watcher 비활성화됨 (FLOWOPS_LINEAR_WATCHER=false)"
  exit 0
fi

# ── DB 확인 ──
if ! docker ps 2>/dev/null | grep -q sevenclaw-db; then
  log "DB 미실행. 시작합니다..."
  docker compose -f "$PROJECT_DIR/clickeye-infra/docker/docker-compose.yml" up -d db redis
  sleep 10
fi

# ── 이전 실행 결과 정리 ──
rm -f ".ralph/.pipeline_result.json"

# ── 순차 실행 루프 ──
COMPLETED=0
FAILED=0
COMPLETED_ISSUES=""  # NightQueued 일괄 알림용

while true; do
  log ""
  log "── DayQueued/NightQueued 이슈 감지 중... ──"

  # 1개만 가져오기
  WATCHER_OUTPUT=$(python3 scripts/linear_watcher.py --per-task --limit 1 2>&1) || WATCHER_EXIT=$?
  WATCHER_EXIT=${WATCHER_EXIT:-0}

  echo "$WATCHER_OUTPUT"

  if [ "$WATCHER_EXIT" -eq 2 ]; then
    log "DONE: DayQueued/NightQueued 이슈 없음. 순차 실행 종료."
    break
  elif [ "$WATCHER_EXIT" -ne 0 ]; then
    log "ERROR: linear_watcher.py 실행 실패 (exit: $WATCHER_EXIT)"
    python3 scripts/telegram_notify.py --message "파이프라인 에러: linear_watcher 실행 실패" 2>/dev/null || true
    break
  fi

  # task_mapping에서 태스크 정보 추출
  if [ ! -f "$TASK_MAPPING" ]; then
    log "ERROR: $TASK_MAPPING 파일이 존재하지 않습니다."
    break
  fi

  TASK_INFO=$(python3 -c "
import json
with open('$TASK_MAPPING') as f:
    m = json.load(f)
for title, meta in m.items():
    mode = meta.get('mode', 'day')
    print(f\"{meta['identifier']}|{meta['issue_id']}|{meta['branch']}|{mode}|{title}\")
    break
")

  IFS='|' read -r ISSUE_KEY ISSUE_ID BRANCH TASK_MODE TITLE <<< "$TASK_INFO"

  COMPLETED=$((COMPLETED + 1))
  log ""
  log "══════════════════════════════════════"
  log "  태스크 #$COMPLETED: $TITLE"
  log "  이슈: $ISSUE_KEY | 브랜치: $BRANCH"
  log "══════════════════════════════════════"

  # ── Temporal 섀도우 트리거(CE-297, P1) ──
  # FLOWOPS_TEMPORAL 활성 시에만 거버넌스 결정을 미러링하는 ShadowDeliveryWorkflow 를
  # fire-and-forget 로 트리거한다. 부작용 0(머지/커밋/PR 없음), 비블로킹, 실패 무시 →
  # 기존 파이프라인 실제 경로를 막지 않고 병렬 대조 로깅만 한다. 미설정 시 아무 것도 안 함(회귀 0).
  if is_enabled "FLOWOPS_TEMPORAL" 2>/dev/null && [ -n "${FLOWOPS_TEMPORAL:-}" ]; then
    python3 "$PROJECT_DIR/scripts/temporal_shadow_trigger.py" \
      --issue-key "$ISSUE_KEY" --head "$BRANCH" >>"$CLAUDE_LOG" 2>&1 || true
  fi

  # 브랜치 생성/전환
  safe_git checkout main 2>/dev/null || true
  safe_git pull origin main 2>/dev/null || true
  # 이미 머지된 동명 브랜치가 있으면 삭제 후 재생성
  if safe_git branch --merged main | grep -q "$BRANCH"; then
    log "WARN: 머지 완료된 브랜치 $BRANCH 삭제 후 재생성"
    safe_git branch -d "$BRANCH" 2>/dev/null || true
  fi
  safe_git checkout -b "$BRANCH" 2>/dev/null || safe_git checkout "$BRANCH" 2>/dev/null || {
    log "ERROR: 브랜치 생성 실패: $BRANCH"
    python3 scripts/linear_tracker.py update --issue-id "$ISSUE_ID" --status "Backlog" 2>/dev/null || true
    log "Linear 상태: Backlog (브랜치 생성 실패)"
    FAILED=$((FAILED + 1))
    continue
  }

  # fix_plan 준비
  mkdir -p ".ralph"
  cp ".ralph/tasks/${ISSUE_KEY}.md" ".ralph/fix_plan.md" 2>/dev/null || {
    log "ERROR: fix_plan 없음: .ralph/tasks/${ISSUE_KEY}.md"
    safe_git checkout main 2>/dev/null || true
    python3 scripts/linear_tracker.py update --issue-id "$ISSUE_ID" --status "Backlog" 2>/dev/null || true
    log "Linear 상태: Backlog (fix_plan 없음)"
    FAILED=$((FAILED + 1))
    continue
  }

  # 프론트엔드 UI/UX 작업 감지 → PROMPT에 에이전트 지침 주입
  UIUX_KEYWORDS="페이지|UI|컴포넌트|폼|대시보드|레이아웃|디자인|반응형|스타일|frontend|component|page"
  if grep -qiE "$UIUX_KEYWORDS" ".ralph/fix_plan.md" 2>/dev/null; then
    log "UI/UX 작업 감지: uiux-agent 지침 활성화"
    export RALPH_UIUX_MODE=true
  else
    export RALPH_UIUX_MODE=false
  fi

  # Linear 상태 → In Progress (1개만)
  python3 scripts/linear_tracker.py update --issue-id "$ISSUE_ID" --status "In Progress" 2>/dev/null || true
  log "Linear 상태: In Progress"

  # ── [STEP A] 메타프롬프트 정제 (관측형 사전 정제 — 기획+정제 일체) → PLAN.md ──
  # 거친 태스크 → 고품질 구현 스펙으로 정제 → .ralph/refined/{ISSUE}.md + PLAN.md + Linear 코멘트.
  # Claude 구독 세션(ANTHROPIC_API_KEY unset)으로 실행. FLOWOPS_METAPROMPT=false면 Gemini 레거시 폴백.
  mkdir -p "$PROJECT_DIR/logs"
  TASK_DESC=$(python3 -c "
import json
with open('$TASK_MAPPING') as f:
    m = json.load(f)
for title, meta in m.items():
    print(meta.get('description', ''))
    break
" 2>/dev/null || echo "")

  METAPROMPT_SKILL=".claude/skills/metaprompt/SKILL.md"
  REFINED_DIR=".ralph/refined"
  REFINED_FILE="$REFINED_DIR/${ISSUE_KEY}.md"
  mkdir -p "$REFINED_DIR"

  if is_enabled "FLOWOPS_METAPROMPT" 2>/dev/null && [ -f "$METAPROMPT_SKILL" ]; then
    log "── 메타프롬프트 정제 시작 ──"
    # 멱등성: 이미 정제된 스펙이 있으면 정제 콜 생략 (중복 토큰 방지)
    if [ ! -s "$REFINED_FILE" ]; then
      REFINE_PROMPT="$(cat "$METAPROMPT_SKILL")

---

# 정제 대상 태스크
- 이슈: $ISSUE_KEY
- 제목: $TITLE
- 설명:
$TASK_DESC

# fix_plan (참고)
$(cat .ralph/fix_plan.md 2>/dev/null || echo '(없음)')

위 metaprompt 지침에 따라 이 태스크를 '구현 스펙'으로 정제하라.
정제된 구현 스펙(마크다운)만 출력하라. 코드는 작성하지 마라."
      REFINE_LOG="$PROJECT_DIR/logs/refine_${ISSUE_KEY}_$(date '+%Y%m%d_%H%M%S').log"
      # Claude 구독 세션 사용 (API 크레딧 차감 방지)
      ( unset ANTHROPIC_API_KEY
        timeout "${REFINE_TIMEOUT:-600}" claude -p "$REFINE_PROMPT" \
          --model sonnet \
          --dangerously-skip-permissions \
          </dev/null ) > "$REFINED_FILE" 2>>"$REFINE_LOG" || true
    else
      log "기존 정제 스펙 재사용: $REFINED_FILE"
    fi

    if [ -s "$REFINED_FILE" ]; then
      cp "$REFINED_FILE" .ralph/PLAN.md
      log "메타프롬프트 정제 완료 → $REFINED_FILE (PLAN.md 동기화)"
      # 정제 스펙을 Linear 코멘트로 기록 (실패 무시)
      python3 - "$ISSUE_ID" "$REFINED_FILE" <<'PY' 2>/dev/null || true
import sys
sys.path.insert(0, "scripts")
from linear_client import get_env, linear_request
issue_id, refined_file = sys.argv[1], sys.argv[2]
api_key, _ = get_env()
body = "🤖 **ClickEye 메타프롬프팅 — 정제된 구현 스펙**\n\n" + open(refined_file, encoding="utf-8").read()
linear_request(
    api_key,
    "mutation($issueId:String!,$body:String!){commentCreate(input:{issueId:$issueId,body:$body}){comment{id}}}",
    {"issueId": issue_id, "body": body},
)
PY
      log "Linear 코멘트 게시(정제 스펙)"
    else
      log "WARN: 메타프롬프트 정제 실패/빈 출력 — fix_plan→PLAN 폴백"
      rm -f "$REFINED_FILE"
      cp .ralph/fix_plan.md .ralph/PLAN.md 2>/dev/null || true
    fi
  elif is_enabled "FLOWOPS_GEMINI_PLAN" 2>/dev/null; then
    log "── Gemini 기획 시작 (레거시 폴백) ──"
    bash scripts/generate_plan_with_gemini.sh "$TITLE" "$TASK_DESC" \
      --fix-plan ".ralph/fix_plan.md" 2>&1 || {
      log "WARN: Gemini PLAN 생성 실패. fix_plan.md로 대체"
      cp .ralph/fix_plan.md .ralph/PLAN.md 2>/dev/null || true
    }
    log "Gemini PLAN 생성 완료"
  else
    log "SKIP: 기획 단계 비활성화 — fix_plan을 PLAN.md로 복사"
    cp .ralph/fix_plan.md .ralph/PLAN.md 2>/dev/null || true
  fi

  # ── [STEP B] Claude 구현 (동기 — 완료까지 대기) ──
  CLAUDE_LOG="$PROJECT_DIR/logs/claude_${ISSUE_KEY}_$(date '+%Y%m%d_%H%M%S').log"
  mkdir -p "$PROJECT_DIR/logs"

  log "── Claude 구현 시작 ──"
  log "로그: $CLAUDE_LOG"

  export RALPH_MAX_ITERATIONS=$MAX_ITERATIONS
  rm -f .ralph/.iteration_count

  # ANTHROPIC_API_KEY를 unset — claude.ai 구독 세션 사용 (API 크레딧 차감 방지)
  unset ANTHROPIC_API_KEY

  # 정제 스펙이 있으면 구현 프롬프트 맨 앞에 prepend (메타프롬프팅 결과 우선 참고)
  if [ -s "$REFINED_FILE" ]; then
    IMPL_PROMPT="## 정제된 구현 스펙 (메타프롬프팅 결과 — 우선 참고)
$(cat "$REFINED_FILE")

---

$(cat .ralph/PROMPT.md)"
  else
    IMPL_PROMPT="$(cat .ralph/PROMPT.md)"
  fi

  claude -p "$IMPL_PROMPT" \
    --model sonnet \
    --dangerously-skip-permissions \
    --verbose \
    --output-format stream-json \
    ${MAX_TURNS:+--max-turns $MAX_TURNS} \
    2>&1 | tee "$CLAUDE_LOG" || {
    log "WARN: Claude 실행 비정상 종료"
  }

  log "Claude 구현 완료: $TITLE"

  # Claude 실행 후 TASK.md 자동 생성 (없으면)
  if [ ! -f .ralph/TASK.md ]; then
    log "TASK.md 자동 생성 (Claude 실행 결과 기반)"
    {
      echo "# TASK — ${TITLE}"
      echo ""
      echo "## 변경 파일"
      safe_git diff --name-only main 2>/dev/null | while read -r f; do echo "- $f"; done
      echo ""
      echo "## 구현 내용"
      echo "fix_plan.md 기반 자율 구현 완료"
      echo ""
      echo "## 테스트 결과"
      echo "(파이프라인 검증 참조)"
      echo ""
      echo "## 남은 이슈"
      grep -E "^\- \[[ !]\]" .ralph/fix_plan.md 2>/dev/null || echo "없음"
    } > .ralph/TASK.md
  fi

  # ── [STEP C] Codex QA 리뷰 → REVIEW.md ──
  if is_enabled "FLOWOPS_CODEX_REVIEW" 2>/dev/null; then
    log "── Codex QA 리뷰 시작 ──"
    bash scripts/run_codex_review.sh 2>&1 || {
      log "WARN: Codex QA 리뷰 실패"
    }
    log "Codex QA 리뷰 완료"
  else
    log "SKIP: Codex QA 리뷰 비활성화 (FLOWOPS_CODEX_REVIEW=false)"
  fi

  # Linear 결과 보고
  python3 scripts/linear_reporter.py --task-id "$ISSUE_KEY" 2>&1 || {
    log "WARN: Linear 결과 보고 실패"
  }

  # ── [거버넌스 게이트] 머지 직전 권위 검증+위험분류 (SSOT: scripts/pre_merge_gate.py) ──
  # direct-merge + push origin main 이 유일한 비보호 경로 → 여기가 권위 게이트. CI(ci.yml)는 미러.
  GATE_DECISION="direct"
  GATE_TIER="LOW"
  MERGED_DIRECT=false
  if is_enabled "FLOWOPS_GOVERNANCE" 2>/dev/null; then
    GATE_RC=0
    GATE_JSON=""

    # ── 거버넌스 판정 획득: HTTP 컨트롤 플레인 경유(선택) → 실패 시 로컬 shim 폴백 ──
    # FLOWOPS_GOVERNANCE_SERVICE_URL 이 설정된 경우에만 HTTP 서비스를 경유한다.
    # 미설정(빈 값)이면 이 블록 전체를 건너뛰어 기존 로컬 shim 경로 그대로 → 회귀 0.
    if [ -n "${FLOWOPS_GOVERNANCE_SERVICE_URL:-}" ]; then
      # 변경 파일 목록 계산(원격 호출자는 git 접근 불가 → 명시 전달). 커널과 동일 three-dot(merge-base) 사용.
      GATE_FILES=$(safe_git diff --name-only "main...${BRANCH}" 2>>"$CLAUDE_LOG" || true)
      # JSON 페이로드 구성(jq 우선, 없으면 python3 로 안전 직렬화)
      # linear_team_id(P1.6): 서버가 team→project 역매핑해 KB 인제스트에만 사용(하위호환 — 빈 값이면 null).
      if command -v jq >/dev/null 2>&1; then
        GATE_PAYLOAD=$(printf '%s\n' "$GATE_FILES" | jq -R . | jq -s --arg h "$BRANCH" --arg t "${LINEAR_TEAM_ID:-}" '{base:"main", head:$h, files:[.[]|select(.!="")], plan_text:null, linear_team_id:(if $t=="" then null else $t end)}' 2>>"$CLAUDE_LOG" || echo '')
      else
        GATE_PAYLOAD=$(GATE_BRANCH="$BRANCH" GATE_FILES="$GATE_FILES" GATE_TEAM="${LINEAR_TEAM_ID:-}" python3 -c 'import os,json;fs=[f for f in os.environ.get("GATE_FILES","").splitlines() if f];print(json.dumps({"base":"main","head":os.environ["GATE_BRANCH"],"files":fs,"plan_text":None,"linear_team_id":os.environ.get("GATE_TEAM") or None}))' 2>>"$CLAUDE_LOG" || echo '')
      fi
      GATE_URL="${FLOWOPS_GOVERNANCE_SERVICE_URL%/}/api/v1/governance/evaluate"
      # curl 실패(연결/타임아웃)가 set -e 로 스크립트를 죽이지 않게 rc 캡처. 응답 마지막 줄=HTTP 코드.
      GATE_HTTP_RESP=$(curl -sS -m "${FLOWOPS_GOVERNANCE_SERVICE_TIMEOUT:-10}" -w $'\n%{http_code}' \
        -X POST "$GATE_URL" \
        -H "Content-Type: application/json" \
        -H "X-Governance-Token: ${GOVERNANCE_SERVICE_TOKEN:-}" \
        -d "$GATE_PAYLOAD" 2>>"$CLAUDE_LOG") || GATE_HTTP_RESP=""
      GATE_HTTP_CODE=$(printf '%s' "$GATE_HTTP_RESP" | tail -n1)
      GATE_HTTP_BODY=$(printf '%s' "$GATE_HTTP_RESP" | sed '$d')
      if [ "$GATE_HTTP_CODE" = "200" ] && [ -n "$GATE_HTTP_BODY" ]; then
        GATE_JSON="$GATE_HTTP_BODY"
        log "거버넌스 게이트: HTTP 서비스 경유 성공 (url=$GATE_URL code=200)"
      else
        # 권위 게이트는 조용히 skip 금지 → WARN 후 로컬 shim 으로 판정 계속.
        log "WARN: 거버넌스 HTTP 서비스 호출 실패 (url=$GATE_URL code=${GATE_HTTP_CODE:-none}) → 로컬 shim 폴백"
      fi
    fi

    # HTTP 미사용(URL 미설정) 또는 HTTP 실패 → 로컬 shim(SSOT) 으로 판정(권위 게이트 유지).
    if [ -z "$GATE_JSON" ]; then
      GATE_JSON=$(python3 scripts/pre_merge_gate.py --base main --head "$BRANCH" --json 2>>"$CLAUDE_LOG") || GATE_RC=$?
    fi

    GATE_DECISION=$(printf '%s' "$GATE_JSON" | python3 -c "import sys,json;print(json.load(sys.stdin).get('merge_decision','block'))" 2>/dev/null || echo "block")
    GATE_TIER=$(printf '%s' "$GATE_JSON" | python3 -c "import sys,json;print(json.load(sys.stdin).get('tier','LOW'))" 2>/dev/null || echo "LOW")
    GATE_FAILS=$(printf '%s' "$GATE_JSON" | python3 -c "import sys,json;print(' / '.join(json.load(sys.stdin).get('failures',[])) or '검증 실패')" 2>/dev/null || echo "게이트 파싱 실패")
    log "거버넌스 게이트: rc=$GATE_RC tier=$GATE_TIER decision=$GATE_DECISION"
    # 트리아지(항목 G) 관측 로깅만 — merge_decision 도메인/판정에는 영향 없음(extra 키 무시).
    GATE_TRIAGE=$(printf '%s' "$GATE_JSON" | python3 -c "import sys,json;print(json.load(sys.stdin).get('triage',''))" 2>/dev/null || echo "")
    [ -n "$GATE_TRIAGE" ] && log "거버넌스 트리아지: band=$GATE_TRIAGE"

    if [ "$GATE_RC" -eq 2 ] || [ "$GATE_DECISION" = "block" ]; then
      log "ERROR: 거버넌스 검증 실패 → 머지 차단 ($GATE_FAILS)"
      safe_git checkout main 2>/dev/null || true
      python3 scripts/linear_tracker.py update --issue-id "$ISSUE_ID" --status "Backlog" 2>/dev/null || true
      if is_enabled "FLOWOPS_TELEGRAM" 2>/dev/null; then
        python3 scripts/telegram_notify.py --message "🚫 거버넌스 차단 ${ISSUE_KEY}: ${GATE_FAILS}" 2>/dev/null || true
      fi
      FAILED=$((FAILED + 1))
      rm -rf ".ralph/tasks"
      rm -f "$TASK_MAPPING" .ralph/PLAN.md .ralph/TASK.md .ralph/REVIEW.md ".ralph/refined/${ISSUE_KEY}.md"
      if [ "$ONCE_MODE" = true ]; then
        log "--once 모드: 게이트 차단 후 종료."
        break
      fi
      continue
    fi
  fi

  # PR 생성 또는 직접 머지 (거버넌스 위험강등 우선)
  if [ "$GATE_DECISION" = "pr" ]; then
    log "위험분류 ${GATE_TIER} → 직접머지 금지, 기존 PR 경로로 강등(사람 머지 게이트)"
    python3 scripts/auto_pr_creator.py --branch "$BRANCH" 2>&1 || {
      log "WARN: PR 생성 실패"
    }
    safe_git checkout main 2>/dev/null || true
  elif is_enabled "FLOWOPS_AUTO_MERGE" 2>/dev/null; then
    log "AUTO_MERGE 활성화: 직접 머지 수행"

    # 머지 전 diff 정보 수집
    MERGE_DIFF_STAT=$(safe_git diff --stat "main..${BRANCH}" 2>/dev/null || echo "(diff 없음)")
    MERGE_DIFF_FILES=$(safe_git diff --name-only "main..${BRANCH}" 2>/dev/null || echo "")
    MERGE_COMMITS=$(safe_git log --oneline "main..${BRANCH}" 2>/dev/null || echo "(커밋 없음)")
    MERGE_DIFF_DETAIL=$(safe_git diff "main..${BRANCH}" 2>/dev/null || echo "")

    # 메인으로 전환 후 머지
    safe_git checkout main 2>/dev/null || true
    if safe_git merge "$BRANCH" --no-ff -m "Merge branch '${BRANCH}': ${TITLE}" 2>/dev/null; then
      log "머지 성공: ${BRANCH} → main"
      MERGED_DIRECT=true

      # 머지 로그 생성
      MERGE_LOG_FILE="$PROJECT_DIR/logs/merge_$(date '+%Y%m%d_%H%M%S').log"
      mkdir -p "$PROJECT_DIR/logs"
      {
        echo "════════════════════════════════════════════════════════════"
        echo "  MERGE LOG"
        echo "════════════════════════════════════════════════════════════"
        echo ""
        echo "일시:     $(date '+%Y-%m-%d %H:%M:%S')"
        echo "이슈:     ${ISSUE_KEY}"
        echo "브랜치:   ${BRANCH} → main"
        echo "제목:     ${TITLE}"
        echo ""
        echo "────────────────────────────────────────────────────────────"
        echo "  커밋 목록"
        echo "────────────────────────────────────────────────────────────"
        echo "$MERGE_COMMITS"
        echo ""
        echo "────────────────────────────────────────────────────────────"
        echo "  변경 파일"
        echo "────────────────────────────────────────────────────────────"
        echo "$MERGE_DIFF_STAT"
        echo ""
        echo "────────────────────────────────────────────────────────────"
        echo "  상세 변경 내용 (diff)"
        echo "────────────────────────────────────────────────────────────"
        echo "$MERGE_DIFF_DETAIL"
        echo ""
        echo "════════════════════════════════════════════════════════════"
      } > "$MERGE_LOG_FILE"
      log "머지 로그: $MERGE_LOG_FILE"

      # push
      safe_git push origin main 2>/dev/null || log "WARN: push 실패"

      # 머지된 브랜치 정리
      safe_git branch -d "$BRANCH" 2>/dev/null || true
      safe_git push origin --delete "$BRANCH" 2>/dev/null || true

      # ── [P1.6] LLM 머신 인제스트: 머지 결과를 clickeye-llm KB 로 전송(비차단) ──
      # 명시적 opt-in(FLOWOPS_TEMPORAL 패턴): 미설정=off. 서버가 team→project 역매핑.
      # 실패해도 파이프라인 절대 안 죽음(|| true) — 202/skip/오류 모두 무시.
      if is_enabled "FLOWOPS_LLM_INGEST" 2>/dev/null && [ -n "${FLOWOPS_LLM_INGEST:-}" ] \
        && [ -n "${FLOWOPS_GOVERNANCE_SERVICE_URL:-}" ]; then
        INGEST_URL="${FLOWOPS_GOVERNANCE_SERVICE_URL%/}/api/v1/llm/ingest/pipeline"
        INGEST_PAYLOAD=$(INGEST_TEAM="${LINEAR_TEAM_ID:-}" INGEST_KEY="$ISSUE_KEY" INGEST_TITLE="$TITLE" INGEST_TIER="${GATE_TIER:-LOW}" INGEST_STAT="$MERGE_DIFF_STAT" python3 -c 'import os,json;print(json.dumps({"team_id":os.environ.get("INGEST_TEAM") or None,"source_id":"pipeline:"+os.environ["INGEST_KEY"],"text":"[파이프라인] "+os.environ["INGEST_KEY"]+" "+os.environ["INGEST_TITLE"]+" — 머지 성공(main 직접 머지, tier="+os.environ.get("INGEST_TIER","LOW")+")\n"+os.environ.get("INGEST_STAT",""),"metadata":{"kind":"pipeline","issue_key":os.environ["INGEST_KEY"]}}))' 2>>"$CLAUDE_LOG" || echo '')
        if [ -n "$INGEST_PAYLOAD" ]; then
          curl -sS -m "${FLOWOPS_GOVERNANCE_SERVICE_TIMEOUT:-10}" -X POST "$INGEST_URL" \
            -H "Content-Type: application/json" \
            -H "X-Governance-Token: ${GOVERNANCE_SERVICE_TOKEN:-}" \
            -d "$INGEST_PAYLOAD" >/dev/null 2>>"$CLAUDE_LOG" || true
          log "LLM 머신 인제스트 전송(비차단): pipeline:${ISSUE_KEY}"
        fi
      fi
    else
      log "ERROR: 머지 실패. PR 생성으로 대체합니다."
      safe_git merge --abort 2>/dev/null || true
      python3 scripts/auto_pr_creator.py --branch "$BRANCH" 2>&1 || {
        log "WARN: PR 생성 실패"
      }
      safe_git checkout main 2>/dev/null || true
    fi
  else
    # AUTO_MERGE 비활성: PR만 생성
    python3 scripts/auto_pr_creator.py --branch "$BRANCH" --auto-merge 2>&1 || {
      log "WARN: PR 생성 실패"
    }
    safe_git checkout main 2>/dev/null || true
  fi

  # ── [추적성 승격] cleanup(rm) 직전, 이미 생성된 산출물을 per-ticket 영속 위치로 아카이브 ──
  # direct-merge(LOW) 경로에서만 의미 — HIGH는 PR로 강등되어 REVIEW.md가 PR 본문에 보존됨.
  # 재생성 없음(promote only). refined 원본은 Linear 코멘트, diff는 logs/merge_*.log 에 이미 존재.
  # 고복잡도 대용 프록시(변경파일 수/diff 라인)로 한정. FLOWOPS_GOVERNANCE_PROMOTE 토글.
  if is_enabled "FLOWOPS_GOVERNANCE_PROMOTE" 2>/dev/null && [ "${MERGED_DIRECT:-false}" = true ]; then
    PROMOTE_FILES=$(printf '%s\n' "$MERGE_DIFF_FILES" | grep -c . 2>/dev/null || echo 0)
    PROMOTE_LINES=$(printf '%s\n' "$MERGE_DIFF_DETAIL" | wc -l | tr -d ' ')
    if [ "$PROMOTE_FILES" -ge "${FLOWOPS_PROMOTE_MIN_FILES:-10}" ] || [ "$PROMOTE_LINES" -ge "${FLOWOPS_PROMOTE_MIN_LINES:-400}" ]; then
      ARCH_DIR="logs/governance/${ISSUE_KEY}"
      mkdir -p "$ARCH_DIR"
      [ -f .ralph/REVIEW.md ] && cp .ralph/REVIEW.md "$ARCH_DIR/REVIEW.md"
      [ -f ".ralph/refined/${ISSUE_KEY}.md" ] && cp ".ralph/refined/${ISSUE_KEY}.md" "$ARCH_DIR/refined.md"
      {
        echo "issue=${ISSUE_KEY}"
        echo "title=${TITLE}"
        echo "tier=${GATE_TIER}"
        echo "merge_log=${MERGE_LOG_FILE:-}"
        echo "changed_files=${PROMOTE_FILES}"
        echo "diff_lines=${PROMOTE_LINES}"
        echo "archived_at=$(date '+%Y-%m-%d %H:%M:%S')"
      } > "$ARCH_DIR/manifest.txt"
      log "추적성 승격: $ARCH_DIR (files=$PROMOTE_FILES lines=$PROMOTE_LINES)"
    fi
  fi

  # 임시 파일 정리
  rm -rf ".ralph/tasks"
  rm -f "$TASK_MAPPING"
  rm -f .ralph/PLAN.md .ralph/TASK.md .ralph/REVIEW.md
  rm -f ".ralph/refined/${ISSUE_KEY}.md"

  log "태스크 완료: $TITLE"

  # 완료 이슈 기록
  if [ -n "$COMPLETED_ISSUES" ]; then
    COMPLETED_ISSUES="${COMPLETED_ISSUES}, ${ISSUE_KEY}"
  else
    COMPLETED_ISSUES="${ISSUE_KEY}"
  fi

  # DayQueued 모드: 태스크별 즉시 PR 알림
  if [ "$TASK_MODE" = "day" ] && is_enabled "FLOWOPS_TELEGRAM" 2>/dev/null; then
    python3 scripts/telegram_notify.py --message \
      "✅ 작업완료 ${ISSUE_KEY} — ${TITLE}
PR을 머지해주세요.
🔗 브랜치: ${BRANCH}" 2>/dev/null || true
  fi

  # --once 모드면 1개만 처리 후 종료
  if [ "$ONCE_MODE" = true ]; then
    log "--once 모드: 1개 태스크 완료 후 종료."
    break
  fi

  log "다음 DayQueued/NightQueued 이슈로 진행..."
done

# ── 실패 이슈 Backlog 이동 ──
if [ "$FAILED" -gt 0 ] && [ -f "$TASK_MAPPING" ]; then
  log "실패 ${FAILED}건 → Linear Backlog 이동"
  python3 -c "
import json, subprocess, sys
sys.path.insert(0, 'scripts')
with open('$TASK_MAPPING') as f:
    m = json.load(f)
for title, meta in m.items():
    issue_id = meta.get('issue_id', '')
    identifier = meta.get('identifier', '')
    if issue_id:
        subprocess.run(['python3', 'scripts/linear_tracker.py', 'update', '--issue-id', issue_id, '--status', 'Backlog'], capture_output=True)
        print(f'  {identifier} → Backlog')
" 2>/dev/null || log "WARN: Backlog 이동 실패"
fi

# ── Telegram 완료 보고 ──
log ""
log "══════════════════════════════════════"
log "  파이프라인 결과: 완료 ${COMPLETED}건, 실패 ${FAILED}건"
log "══════════════════════════════════════"

# 처리된 작업이 있을 때만 Telegram 알림 발송
if [ $((COMPLETED + FAILED)) -gt 0 ] && is_enabled "FLOWOPS_TELEGRAM" 2>/dev/null; then
  ITER_COUNT=$(cat .ralph/.iteration_count 2>/dev/null || echo "N/A")
  python3 scripts/telegram_notify.py \
    --pipeline-report --iterations "$ITER_COUNT" 2>/dev/null || true

  # NightQueued 모드: 모든 태스크 완료 후 일괄 PR 알림
  if [ "$TASK_MODE" = "night" ] && [ -n "$COMPLETED_ISSUES" ] && [ "$COMPLETED" -gt 0 ]; then
    python3 scripts/telegram_notify.py --message \
      "🌙 야간 자동화 완료
${COMPLETED_ISSUES} — 모든 작업이 완료되었습니다.
순차적으로 PR을 머지해주세요." 2>/dev/null || true
  fi
fi
