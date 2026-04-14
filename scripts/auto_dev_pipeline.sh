#!/usr/bin/env bash
# 자동 기능 개발 파이프라인 (v6 — 멀티 Agent 순차 실행)
#
# 워크플로우:
#   1. Linear Queued 이슈 1개 감지 → fix_plan 생성
#   2. [Gemini] 기획 → PLAN.md 생성
#   3. 브랜치 생성 → [Claude] 구현 → TASK.md 생성
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

LOCK_FILE=".ralph/.pipeline_lock"
TASK_MAPPING=".ralph/.task_mapping.json"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
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
  git checkout main 2>/dev/null || true
}
trap cleanup EXIT

# ── stale git lock 정리 ──
if [ -f "$PROJECT_DIR/.git/index.lock" ]; then
  LOCK_AGE=$(( $(date +%s) - $(stat -c %Y "$PROJECT_DIR/.git/index.lock" 2>/dev/null || echo "0") ))
  if [ "$LOCK_AGE" -gt 60 ]; then
    rm -f "$PROJECT_DIR/.git/index.lock"
    log "WARN: stale git index.lock 제거 (${LOCK_AGE}초 경과)"
  fi
fi

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
  docker compose -f "$PROJECT_DIR/24SevenClaw-infra/docker/docker-compose.yml" up -d db redis
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

  # 브랜치 생성/전환
  git checkout main 2>/dev/null || true
  git pull origin main 2>/dev/null || true
  # 이미 머지된 동명 브랜치가 있으면 삭제 후 재생성
  if git branch --merged main | grep -q "$BRANCH"; then
    log "WARN: 머지 완료된 브랜치 $BRANCH 삭제 후 재생성"
    git branch -d "$BRANCH" 2>/dev/null || true
  fi
  git checkout -b "$BRANCH" 2>/dev/null || git checkout "$BRANCH" 2>/dev/null || {
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
    git checkout main 2>/dev/null || true
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

  # ── [STEP A] Gemini 기획 → PLAN.md ──
  if is_enabled "FLOWOPS_GEMINI_PLAN" 2>/dev/null; then
    log "── Gemini 기획 시작 ──"
    TASK_DESC=$(python3 -c "
import json
with open('$TASK_MAPPING') as f:
    m = json.load(f)
for title, meta in m.items():
    print(meta.get('description', ''))
    break
" 2>/dev/null || echo "")

    bash scripts/generate_plan_with_gemini.sh "$TITLE" "$TASK_DESC" \
      --fix-plan ".ralph/fix_plan.md" 2>&1 || {
      log "WARN: Gemini PLAN 생성 실패. fix_plan.md로 대체"
      cp .ralph/fix_plan.md .ralph/PLAN.md 2>/dev/null || true
    }
    log "Gemini PLAN 생성 완료"
  else
    log "SKIP: Gemini PLAN 비활성화 (FLOWOPS_GEMINI_PLAN=false)"
    # PLAN.md가 없으면 fix_plan을 복사
    cp .ralph/fix_plan.md .ralph/PLAN.md 2>/dev/null || true
  fi

  # ── [STEP B] Claude 구현 (동기 — 완료까지 대기) ──
  CLAUDE_LOG="$PROJECT_DIR/logs/claude_${ISSUE_KEY}_$(date '+%Y%m%d_%H%M%S').log"
  mkdir -p "$PROJECT_DIR/logs"

  log "── Claude 구현 시작 ──"
  log "로그: $CLAUDE_LOG"

  export RALPH_MAX_ITERATIONS=$MAX_ITERATIONS
  rm -f .ralph/.iteration_count

  claude -p "$(cat .ralph/PROMPT.md)" \
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
      git diff --name-only main 2>/dev/null | while read -r f; do echo "- $f"; done
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

  # PR 생성 또는 직접 머지
  if is_enabled "FLOWOPS_AUTO_MERGE" 2>/dev/null; then
    log "AUTO_MERGE 활성화: 직접 머지 수행"

    # 머지 전 diff 정보 수집
    MERGE_DIFF_STAT=$(git diff --stat "main..${BRANCH}" 2>/dev/null || echo "(diff 없음)")
    MERGE_DIFF_FILES=$(git diff --name-only "main..${BRANCH}" 2>/dev/null || echo "")
    MERGE_COMMITS=$(git log --oneline "main..${BRANCH}" 2>/dev/null || echo "(커밋 없음)")
    MERGE_DIFF_DETAIL=$(git diff "main..${BRANCH}" 2>/dev/null || echo "")

    # 메인으로 전환 후 머지
    git checkout main 2>/dev/null || true
    if git merge "$BRANCH" --no-ff -m "Merge branch '${BRANCH}': ${TITLE}" 2>/dev/null; then
      log "머지 성공: ${BRANCH} → main"

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
      git push origin main 2>/dev/null || log "WARN: push 실패"

      # 머지된 브랜치 정리
      git branch -d "$BRANCH" 2>/dev/null || true
      git push origin --delete "$BRANCH" 2>/dev/null || true
    else
      log "ERROR: 머지 실패. PR 생성으로 대체합니다."
      git merge --abort 2>/dev/null || true
      python3 scripts/auto_pr_creator.py --branch "$BRANCH" 2>&1 || {
        log "WARN: PR 생성 실패"
      }
      git checkout main 2>/dev/null || true
    fi
  else
    # AUTO_MERGE 비활성: PR만 생성
    python3 scripts/auto_pr_creator.py --branch "$BRANCH" --auto-merge 2>&1 || {
      log "WARN: PR 생성 실패"
    }
    git checkout main 2>/dev/null || true
  fi

  # 임시 파일 정리
  rm -rf ".ralph/tasks"
  rm -f "$TASK_MAPPING"
  rm -f .ralph/PLAN.md .ralph/TASK.md .ralph/REVIEW.md

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

if is_enabled "FLOWOPS_TELEGRAM" 2>/dev/null; then
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
