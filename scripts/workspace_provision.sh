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

# ── [CE-329] P8 집행면 게이트 토글 (이중 opt-in, 미설정=off) ──────────────────
# is_enabled 는 미설정 시 true 를 돌려주므로 `-n` 을 함께 본다. off 일 때 아래
# 배선 블록 전체가 no-op 이고 조달 산출물은 현행과 바이트 단위로 동일하다.
#
# ⚠️ 호출자 env 우선(CE-346 해법 재사용). pipeline_config.sh 의 `_load_flowops_env` 는
# 기본적으로 `.env` 값으로 **이미 set 된 변수를 덮는다**. 그대로 두면
# `FLOWOPS_ENFORCEMENT=true scripts/workspace_provision.sh …` 가 `.env` 의 false 에
# 강등되어 **조용히 미배선**된다(CE-345/346 에서 이미 겪은 오귀속 계열). 이 스크립트가
# 읽는 FLOWOPS_* 는 ENFORCEMENT 하나뿐이라 이 마커가 다른 해석에 영향을 주지 않는다.
FLOWOPS_ENV_KEEP_EXISTING="${FLOWOPS_ENV_KEEP_EXISTING:-true}"
export FLOWOPS_ENV_KEEP_EXISTING
source "$PROJECT_DIR/scripts/pipeline_config.sh" 2>/dev/null || true
ENFORCEMENT_ON=0
if is_enabled "FLOWOPS_ENFORCEMENT" 2>/dev/null && [ -n "${FLOWOPS_ENFORCEMENT:-}" ]; then
  ENFORCEMENT_ON=1
fi

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
  # [CE-329] '.harness/' — 집행면 감사 로그(enforce-audit.jsonl). 토글과 무관하게 등재한다:
  # 없는 디렉터리 exclude 는 no-op 이고, 짝 목록을 조건부로 갈라두면 불변식이 깨진다.
  for _ex in '.clickeye_default_branch' '.claude/' 'CLAUDE.md' '.harness/'; do
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
  for _hook in "$CORE_DIR/hooks/"*; do
    [ -f "$_hook" ] || continue
    # [CE-329] 집행면 번들은 토글 on 일 때만 물질화한다(off = 조달 산출물 현행 동일).
    if [ "$(basename "$_hook")" = "gitguard-gate.cjs" ] && [ "$ENFORCEMENT_ON" != "1" ]; then
      continue
    fi
    cp "$_hook" "$WS_CLAUDE/hooks/" 2>/dev/null || true
  done
  chmod +x "$WS_CLAUDE/hooks/"*.sh 2>/dev/null || true
fi

# ── ②-b [CE-329] settings.json 에 집행면 PreToolUse 훅 가산 병합 ──────────────
# 두 조달 경로(신규 복사 / CE-344 기존 settings 보존)를 한 코드로 덮는다:
#   - 신규 조달: 방금 복사한 코어 settings.json 에 엔트리를 **가산**한다. 정적 템플릿
#     파일 자체는 건드리지 않는다 — 토글 off 조달 결과가 현행과 같아야 하므로.
#   - 보존 경로: 고객 settings.json 에 PreToolUse 엔트리 1개만 가산한다(다른 키 불변).
# 멱등: 같은 훅 명령이 이미 있으면 아무것도 하지 않는다.
# 병합 실패(고객 JSON 손상 등)는 경고만 남기고 조달을 계속한다 — 비차단.
if [ "$ENFORCEMENT_ON" = "1" ]; then
  ENFORCE_BUNDLE="$WS_CLAUDE/hooks/gitguard-gate.cjs"
  if [ ! -f "$ENFORCE_BUNDLE" ]; then
    log "WARN: 집행면 번들이 없어 훅 배선을 건너뜀(빌드 필요: templates/harness-core/enforce → npm run build): $ENFORCE_BUNDLE"
  else
    # [CE-329 F8] `${CLAUDE_PROJECT_DIR:-.}` + `|| exit 2` 두 겹으로 fail-closed 한다.
    #   ① 변수 미설정 시 `node /.claude/...` 를 실행해 **rc=1(자문형) = 게이트 우회**가
    #      되던 것을 cwd 폴백으로 막는다.
    #   ② 번들이 지워지거나 손상돼 node 가 rc=1 로 죽어도 셸이 2 로 바꿔 차단한다.
    #      allow(0)는 `||` 를 타지 않으므로 정상 통과는 그대로다.
    #      exit 1 이 자문형이라는 실측 사실에 대한 배선 층 방어선이다.
    ENFORCE_CMD='node "${CLAUDE_PROJECT_DIR:-.}"/.claude/hooks/gitguard-gate.cjs || exit 2'
    ENFORCE_MATCHER='Bash|Write|Edit|MultiEdit|NotebookEdit'
    MERGE_JS="$(mktemp)"
    # shellcheck disable=SC2064
    trap "rm -f '$MERGE_JS'" EXIT
    cat > "$MERGE_JS" <<'MERGEEOF'
// settings.json 멱등 병합 — infraeye-harness/install.sh 의 병합 JS 이식(CE-329).
// PreToolUse 엔트리 1개만 가산하고 다른 키는 건드리지 않는다.
const fs = require('fs');
const path = require('path');
const [, , settingsPath, gateCmd, matcher, timeout] = process.argv;

let obj = {};
if (fs.existsSync(settingsPath)) {
  const raw = fs.readFileSync(settingsPath, 'utf8').trim();
  if (raw !== '') {
    try { obj = JSON.parse(raw); }
    catch (e) { console.error('PARSE_ERROR: ' + e.message); process.exit(3); }
  }
}
if (obj === null || typeof obj !== 'object' || Array.isArray(obj)) {
  console.error('NOT_OBJECT'); process.exit(3);
}

if (!obj.hooks || typeof obj.hooks !== 'object' || Array.isArray(obj.hooks)) obj.hooks = {};
const pre = Array.isArray(obj.hooks.PreToolUse) ? obj.hooks.PreToolUse : [];

// 멱등성: 집행면 훅이 이미 등록돼 있으면 아무것도 하지 않는다.
// [CE-329] 원본은 gateCmd 정확 일치였다. 경로 표기나 따옴표가 바뀌면 같은 훅이 중복
// 누적되므로 번들 파일명 포함 여부로 판정한다(훅 1개 = 파일 1개).
const installed = pre.some(
  (e) =>
    e &&
    Array.isArray(e.hooks) &&
    e.hooks.some((h) => h && typeof h.command === 'string' && h.command.includes('gitguard-gate.cjs')),
);
if (installed) { console.log('ALREADY'); process.exit(0); }

pre.push({
  matcher,
  hooks: [{ type: 'command', command: gateCmd, timeout: Number(timeout) }],
});
obj.hooks.PreToolUse = pre;

fs.mkdirSync(path.dirname(settingsPath), { recursive: true });
fs.writeFileSync(settingsPath, JSON.stringify(obj, null, 2) + '\n');
console.log('ADDED');
MERGEEOF

    if MERGE_OUT="$(node "$MERGE_JS" "$WS_CLAUDE/settings.json" "$ENFORCE_CMD" "$ENFORCE_MATCHER" 15 2>&1)"; then
      case "$MERGE_OUT" in
        ADDED)   log "집행면 훅 배선: settings.json PreToolUse 엔트리 등록 완료" ;;
        ALREADY) log "집행면 훅 배선: 이미 등록됨 — 변경 없음(멱등)" ;;
        *)       log "WARN: 집행면 훅 병합 결과가 예상과 다름 — enforcement 미배선 상태로 조달됨(게이트 없음): $MERGE_OUT" ;;
      esac
    else
      log "WARN: 집행면 훅 병합 실패 — enforcement 미배선 상태로 조달됨(게이트 없음). 조달은 계속: $MERGE_OUT"
      log "      이 워크스페이스의 에이전트 git·파일 조작은 집행면 검사를 받지 않는다."
      log "      고객 .claude/settings.json 의 JSON 문법을 고치고 재조달하라: $WS_CLAUDE/settings.json"
    fi
    rm -f "$MERGE_JS"
    trap - EXIT
  fi
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
