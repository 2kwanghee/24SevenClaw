#!/usr/bin/env bash
# workspace_provision.sh — 파생형 하네스 워크스페이스 조달 (Tier 0 복사 + Tier 1 프로파일).
#
# 무인 딜리버리가 "남의 프로젝트"를 구현할 수 있도록 워크스페이스를 마련한다:
#   ① workspaces/<key>/ 없으면 clone(로컬 경로면 git clone <path>), 있으면 스킵(멱등)
#   ② templates/harness-core/ 를 워크스페이스 .claude/ 로 복사(Tier 0 불변 코어)
#   ③ stack_profiler.py 실행 → harness-profile.json + CLAUDE.stack.md + gates(Tier 1)
#   ④ 워크스페이스 루트에 CLAUDE.md 없으면 core+stack 프래그먼트를 이어붙여 생성,
#      이미 있으면 덮어쓰지 않고 .claude/ 프래그먼트만 유지
#
# 사용법:
#   scripts/workspace_provision.sh --key <PROJECT_KEY> --source <git-url-또는-로컬경로> [--dest <루트>]
#
# 기본 대상 루트: <repo>/workspaces (.gitignore 대상)

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}
die() {
  echo "ERROR: $*" >&2
  exit 1
}

# ── 인자 파싱 ──
KEY=""
SOURCE=""
DEST="$PROJECT_DIR/workspaces"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --key) KEY="$2"; shift 2 ;;
    --source) SOURCE="$2"; shift 2 ;;
    --dest) DEST="$2"; shift 2 ;;
    *) die "알 수 없는 옵션: $1" ;;
  esac
done

[ -n "$KEY" ] || die "--key 필요 (프로젝트 키)"
[ -n "$SOURCE" ] || die "--source 필요 (git URL 또는 로컬 경로)"

CORE_DIR="$PROJECT_DIR/templates/harness-core"
[ -d "$CORE_DIR" ] || die "harness-core 템플릿 없음: $CORE_DIR"

WS="$DEST/$KEY"
mkdir -p "$DEST"

# ── ① clone/checkout (멱등) ──
if [ -d "$WS/.git" ] || [ -d "$WS" ]; then
  log "워크스페이스 이미 존재 — clone 스킵(멱등): $WS"
else
  log "워크스페이스 조달 clone: $SOURCE → $WS"
  git clone "$SOURCE" "$WS" || die "git clone 실패: $SOURCE"
  # [CE-347] 고객 기본 브랜치를 clone 직후에 기록한다 — 딜리버리 리다이렉트가 base 를 정할 때
  # origin/HEAD 가 지워졌거나 참조 불가한 clone 에서 쓰는 폴백(2단). 이후 태스크 브랜치로
  # 옮겨간 뒤에는 HEAD 가 기본 브랜치가 아니므로 여기서만 기록한다.
  WS_DEFAULT_BRANCH="$(git -C "$WS" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
  if [ -n "$WS_DEFAULT_BRANCH" ] && [ "$WS_DEFAULT_BRANCH" != "HEAD" ]; then
    printf '%s\n' "$WS_DEFAULT_BRANCH" > "$WS/.clickeye_default_branch"
  else
    # unborn HEAD(커밋 0개) 또는 detached — 리터럴 'HEAD' 를 기본 브랜치로 기록하면 이후
    # checkout/push 가 엉뚱한 ref 를 겨냥한다. 기록을 생략하고 origin/HEAD 경로에 맡긴다.
    log "WARN: clone 의 HEAD 가 기본 브랜치를 가리키지 않음(빈 레포/detached) — 기본 브랜치 메모 생략: $WS"
  fi
fi

# ── ①-c ClickEye 주입물 clone-로컬 제외 (멱등) ──────────────────────────────
# 아래 항목은 ClickEye 가 워크스페이스에 심는 것이라 고객 레포의 추적 대상이 아니다. 제외하지
# 않으면 ① 에이전트의 `git add -A` 가 이들을 고객 브랜치에 커밋하고(오염) ② 딜리버리
# 리다이렉트의 "더러운 트리" 판정이 항상 참이 되어 stash 가 하네스 프래그먼트를 걷어간다.
# exclude 는 untracked 만 대상이므로 고객이 실제로 추적하는 CLAUDE.md 등에는 영향이 없다.
# 목록은 auto_dev_pipeline.sh 의 ws_exclude_harness_artifacts 와 짝 — 한쪽만 바꾸지 말 것.
if [ -d "$WS/.git" ]; then
  mkdir -p "$WS/.git/info"
  for _ex in '.clickeye_default_branch' '.claude/' 'CLAUDE.md'; do
    grep -qxF -- "$_ex" "$WS/.git/info/exclude" 2>/dev/null \
      || printf '%s\n' "$_ex" >> "$WS/.git/info/exclude" 2>/dev/null || true
  done
fi
[ -d "$WS" ] || die "워크스페이스 디렉터리 없음: $WS"

# ── ② Tier 0 코어 복사 → .claude/ ──
WS_CLAUDE="$WS/.claude"
mkdir -p "$WS_CLAUDE"
log "Tier 0 코어 복사: $CORE_DIR → $WS_CLAUDE"
# CLAUDE.core.md · settings.json · hooks/ 를 복사(코어 프래그먼트 물질화)
cp "$CORE_DIR/CLAUDE.core.md" "$WS_CLAUDE/CLAUDE.core.md"

# settings.json 은 CLAUDE.md 처리와 대칭(보수적 보존): 대상 레포에 이미 있으면
# 덮어쓰지 않고 코어 버전을 settings.core.json 으로 병치(고객 훅·권한·env 파괴 방지).
SETTINGS_PRESERVED=0
if [ -f "$WS_CLAUDE/settings.json" ]; then
  log "대상 레포에 .claude/settings.json 존재 — 덮어쓰지 않음(settings.core.json 병치, 코어 훅 수동 병합 필요): $WS_CLAUDE/settings.json"
  cp "$CORE_DIR/settings.json" "$WS_CLAUDE/settings.core.json"
  SETTINGS_PRESERVED=1
else
  cp "$CORE_DIR/settings.json" "$WS_CLAUDE/settings.json"
fi

if [ -d "$CORE_DIR/hooks" ]; then
  mkdir -p "$WS_CLAUDE/hooks"
  cp "$CORE_DIR/hooks/"* "$WS_CLAUDE/hooks/" 2>/dev/null || true
  chmod +x "$WS_CLAUDE/hooks/"*.sh 2>/dev/null || true
fi

# ── ③ Tier 1 스택 프로파일 생성 → .claude/ ──
log "Tier 1 스택 프로파일링: stack_profiler.py --repo $WS"
python3 "$PROJECT_DIR/scripts/stack_profiler.py" --repo "$WS" --out "$WS_CLAUDE" \
  || die "stack_profiler 실패"

# ── ④ CLAUDE.md 물질화 (없을 때만 — 대상 레포 원본 보존) ──
WS_CLAUDE_MD="$WS/CLAUDE.md"
if [ -f "$WS_CLAUDE_MD" ]; then
  log "대상 레포에 CLAUDE.md 존재 — 덮어쓰지 않음(.claude/ 프래그먼트만 유지): $WS_CLAUDE_MD"
else
  log "CLAUDE.md 물질화: core + stack 프래그먼트 결합 → $WS_CLAUDE_MD"
  {
    cat "$WS_CLAUDE/CLAUDE.core.md"
    echo ""
    echo "---"
    echo ""
    cat "$WS_CLAUDE/CLAUDE.stack.md"
  } > "$WS_CLAUDE_MD"
fi

log "조달 완료: $WS"
log "  프로파일: $WS_CLAUDE/harness-profile.json"
log "  스택규약: $WS_CLAUDE/CLAUDE.stack.md"
log "  게이트:   $WS_CLAUDE/harness-gates.txt"
if [ "$SETTINGS_PRESERVED" = "1" ]; then
  log "  주의: 기존 settings.json 보존됨 — 코어 훅이 자동 설치되지 않았을 수 있음. $WS_CLAUDE/settings.core.json 과 수동 병합 필요"
fi
