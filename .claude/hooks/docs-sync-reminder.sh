#!/usr/bin/env bash
# docs-sync-reminder.sh — 문서 지속 현행화 강제 훅 (PostToolUse: Edit|Write)
#
# 토큰 안전 설계: 이 훅은 LLM을 호출하지 않는 순수 스크립트다(per-edit 0 토큰).
#   ① 편집 파일을 docs/ 프론트매터 related: 와 매칭
#   ② 영향 문서를 status: current → needs-revision 로 결정적 플립(idempotent)
#   ③ stderr 로 "커밋 전 /docs-sync 실행" 리마인더만 출력
# 실제 본문 현행화(LLM)는 /docs-sync 가 커밋 전 1회·범위 한정으로 수행한다.
#
# 항상 exit 0 (PostToolUse 는 비차단·advisory). 어떤 오류도 도구 흐름을 막지 않는다.

set +e

# 토글: FLOWOPS_DOCS_SYNC=off 이면 비활성 (기본 on)
if [ "${FLOWOPS_DOCS_SYNC:-on}" = "off" ]; then
  exit 0
fi

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || REPO_ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"

# 도구 입력(JSON)은 stdin 으로 들어온다. 파이썬엔 env 로 넘겨 stdin 충돌을 피한다.
DOCS_HOOK_INPUT="$(cat)" DOCS_HOOK_REPO="$REPO_ROOT" python3 - <<'PY' 2>/dev/null || true
import os, json, re, glob

repo = os.environ.get("DOCS_HOOK_REPO", "")
raw = os.environ.get("DOCS_HOOK_INPUT", "")

# --- 편집 파일 경로 추출 ---
try:
    d = json.loads(raw)
    inp = d.get("tool_input", {}) or {}
    fp = inp.get("file_path", "") or inp.get("path", "")
except Exception:
    fp = ""
if not fp or not repo:
    raise SystemExit(0)

ap = os.path.abspath(fp)
try:
    rel = os.path.relpath(ap, repo).replace(os.sep, "/")
except Exception:
    raise SystemExit(0)
if rel.startswith(".."):   # repo 밖
    raise SystemExit(0)

# --- skip 필터: 문서 영향 무관/자기 자신 ---
low = rel.lower()
if low.startswith(("docs/", ".claude/", ".git/", "node_modules/")):
    raise SystemExit(0)
if any(s in "/" + low for s in ("/node_modules/", "/__pycache__/", "/.git/", "/__tests__/", "/tests/", "/test/")):
    raise SystemExit(0)
if low.endswith((".lock", "-lock.json", ".pyc", ".snap")):
    raise SystemExit(0)
if os.path.basename(low) in ("package-lock.json", "pnpm-lock.yaml", "yarn.lock", "uv.lock", "poetry.lock"):
    raise SystemExit(0)

# --- 프론트매터 파서 ---
def frontmatter(text):
    m = re.match(r"---\n(.*?)\n---", text, re.S)
    return m.group(1) if m else None

def list_block(fm, key):
    out = []
    m = re.search(rf"^{key}:[ \t]*(.*)$", fm, re.M)
    if not m:
        return out
    inline = m.group(1).strip()
    if inline.startswith("[") and inline.endswith("]"):
        return [x.strip().strip("'\"") for x in inline[1:-1].split(",") if x.strip()]
    for line in fm[m.end():].splitlines():
        if re.match(r"^\s*-\s+", line):
            out.append(re.sub(r"^\s*-\s+", "", line).strip().strip("'\""))
        elif line.strip() == "":
            continue
        elif re.match(r"^[a-zA-Z_]+:", line):
            break
    return out

# --- code→doc 매칭 + needs-revision 플립 ---
stale = []
for doc in glob.glob(os.path.join(repo, "docs", "**", "*.md"), recursive=True):
    try:
        text = open(doc, encoding="utf-8").read()
    except Exception:
        continue
    fm = frontmatter(text)
    if not fm:
        continue
    tracked = [t.strip() for t in (list_block(fm, "related") + list_block(fm, "pages") + list_block(fm, "components")) if t.strip()]
    matched = any(rel == t or rel.startswith(t.rstrip("/") + "/") for t in tracked)
    if not matched:
        continue
    doc_rel = os.path.relpath(doc, repo).replace(os.sep, "/")
    new = re.sub(r"(?m)^(status:\s*)current\s*$", r"\1needs-revision", text)
    if new != text:
        try:
            open(doc, "w", encoding="utf-8").write(new)
        except Exception:
            pass
        stale.append(doc_rel)
    elif re.search(r"(?m)^status:\s*needs-revision\s*$", text):
        stale.append(doc_rel)  # 이미 stale — 여전히 미반영이므로 리마인더 유지

if stale:
    uniq = sorted(set(stale))
    import sys
    sys.stderr.write(
        "[docs-sync] 코드 변경(%s)으로 stale 표시된 문서 %d개: %s\n"
        "  → 커밋 전 /docs-sync 를 1회 호출해 본문을 현행화하세요(영향 문서만, 배치).\n"
        % (rel, len(uniq), ", ".join(uniq))
    )
PY

exit 0
