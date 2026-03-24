#!/usr/bin/env bash
# Hook: Stop
# On session end: 하위 모듈 + 루트 레포 변경사항을 각각 커밋.
# 하위 모듈은 독립 git 레포이므로 각자 커밋/push 처리.
# Falls back to a generic WIP message if claude -p fails.

set -euo pipefail

# Resolve the git repo root (worktree-safe)
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || REPO_ROOT="$CLAUDE_PROJECT_DIR"
cd "$REPO_ROOT" || exit 0

# 모듈 토글 체크
source "$REPO_ROOT/scripts/pipeline_config.sh" 2>/dev/null || true
if ! is_enabled "FLOWOPS_AUTO_COMMIT" 2>/dev/null; then
  exit 0
fi

# ── 커밋 메시지 생성 함수 ──
generate_commit_msg() {
  local diff="$1"
  local module_name="$2"
  local msg=""

  if command -v claude &>/dev/null; then
    msg=$(echo "$diff" | claude -p \
      "You are a commit message generator. Based on the following git diff, write a single commit message.
Rules:
- First line MUST start with 'WIP(${module_name}): short summary' (max 72 chars)
- Always use 'WIP' as the type prefix, never feat/fix/refactor/etc.
- If needed, add a blank line then bullet points for details
- Be concise and specific
- Output ONLY the commit message, nothing else" 2>/dev/null) || true
  fi

  if [ -z "$msg" ]; then
    local file_count
    file_count=$(echo "$diff" | grep -c '^diff --git' || echo "0")
    msg="wip(${module_name}): update ${file_count} files"
  fi

  echo "$msg"
}

# ── 단일 레포 커밋 함수 ──
commit_repo() {
  local repo_dir="$1"
  local module_name="$2"

  cd "$repo_dir" || return

  # Stage all changes
  git add -A 2>/dev/null || true

  # Skip if nothing to commit
  if git diff-index --quiet HEAD 2>/dev/null; then
    return
  fi

  # Generate commit message
  local diff
  diff=$(git diff --cached 2>/dev/null | head -2000)
  local commit_msg
  commit_msg=$(generate_commit_msg "$diff" "$module_name")

  # Commit
  echo "$commit_msg" | git commit -F - --no-verify 2>/dev/null || true
}

# ── Step 1: 하위 모듈 커밋 ──
SUBMODULES=(
  "24SevenClaw-web:web"
  "24SevenClaw-api:api"
  "24SevenClaw-agent:agent"
  "24SevenClaw-infra:infra"
  "24SevenClaw-contracts:contracts"
)

for entry in "${SUBMODULES[@]}"; do
  IFS=':' read -r dir_name module_name <<< "$entry"
  submod_path="$REPO_ROOT/$dir_name"
  if [ -d "$submod_path/.git" ]; then
    commit_repo "$submod_path" "$module_name"
  fi
done

# ── Step 2: 루트 레포 커밋 ──
commit_repo "$REPO_ROOT" "root"

# ── Step 3: CHANGELOG 업데이트 ──
cd "$REPO_ROOT" || exit 0
CHANGELOG="$REPO_ROOT/docs/CHANGELOG.md"
if [ -f "$CHANGELOG" ]; then
  # 루트의 최신 커밋 메시지 가져오기
  FIRST_LINE=$(git log -1 --pretty=%s 2>/dev/null || echo "")
  if [ -n "$FIRST_LINE" ]; then
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M')

    if grep -q '## \[Unreleased\]' "$CHANGELOG"; then
      sed -i '' "/## \[Unreleased\]/a\\
- $TIMESTAMP: $FIRST_LINE" "$CHANGELOG" 2>/dev/null || \
      sed -i "/## \[Unreleased\]/a\\- $TIMESTAMP: $FIRST_LINE" "$CHANGELOG" 2>/dev/null || true
    fi

    git add "$CHANGELOG" 2>/dev/null || true
    if ! git diff-index --quiet HEAD 2>/dev/null; then
      git commit -m "docs: auto-update changelog" --no-verify 2>/dev/null || true
    fi
  fi
fi
