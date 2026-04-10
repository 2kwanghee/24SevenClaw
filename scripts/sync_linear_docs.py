#!/usr/bin/env python3
"""Linear DOCS 팀 이슈를 docs/reference/ 에 마크다운으로 동기화.

실행: python3 scripts/sync_linear_docs.py
Hook: .claude/settings.json → SessionStart 이벤트에서 자동 실행

워크플로우:
  1. Linear DOCS 팀의 모든 이슈를 가져온다
  2. 각 이슈를 docs/reference/{sanitized_title}.md 로 저장한다
  3. 기존 파일이 있으면 본문을 비교하여 변경 이력을 기록한다
  4. 메타데이터(동기화 시각, Linear URL 등)를 파일 상단에 유지한다
"""

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta

# ── 경로 설정 ──
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.join(SCRIPT_DIR, "..")
REFERENCE_DIR = os.path.join(PROJECT_DIR, "docs", "reference")
CHANGELOG_PATH = os.path.join(REFERENCE_DIR, "_changelog.md")

sys.path.insert(0, SCRIPT_DIR)
from linear_client import get_env, linear_request

KST = timezone(timedelta(hours=9))


def now_kst() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")


def sanitize_filename(title: str) -> str:
    """이슈 제목을 파일명으로 변환."""
    name = title.strip()
    # 특수문자 → 하이픈
    name = re.sub(r"[^\w가-힣\s-]", "", name)
    name = re.sub(r"\s+", "-", name)
    name = re.sub(r"-+", "-", name).strip("-")
    return name[:120]  # 파일명 길이 제한


def content_hash(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:12]


def format_comments(issue: dict) -> str:
    """이슈의 댓글을 마크다운으로 포맷."""
    comments_data = issue.get("comments", {}).get("nodes", [])
    if not comments_data:
        return ""

    # 생성일 기준 오름차순 정렬
    comments_data = sorted(comments_data, key=lambda c: c.get("createdAt", ""))

    lines = ["## 댓글", ""]
    for c in comments_data:
        user = c.get("user") or {}
        author = user.get("displayName") or user.get("name") or "Unknown"
        created = c.get("createdAt", "")[:10]  # YYYY-MM-DD
        body = c.get("body", "").strip()

        lines.append(f"### {author} ({created})")
        lines.append("")
        lines.append(body)
        lines.append("")

    return "\n".join(lines)


def comments_hash(issue: dict) -> str:
    """댓글 내용의 해시를 생성."""
    comments_data = issue.get("comments", {}).get("nodes", [])
    if not comments_data:
        return ""
    raw = "|".join(
        f"{c.get('id', '')}:{c.get('updatedAt', '')}"
        for c in sorted(comments_data, key=lambda c: c.get("createdAt", ""))
    )
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def build_md(issue: dict, prev_changelog: str = "") -> str:
    """이슈 데이터로 마크다운 파일 내용을 생성."""
    identifier = issue["identifier"]
    title = issue["title"]
    url = issue["url"]
    state = issue.get("state", {}).get("name", "Unknown")
    priority_map = {0: "None", 1: "Urgent", 2: "High", 3: "Medium", 4: "Low"}
    priority = priority_map.get(issue.get("priority", 0), "None")
    description = issue.get("description") or "(내용 없음)"
    updated_at = issue.get("updatedAt", "")
    c_hash = comments_hash(issue)

    lines = [
        f"# {title}",
        "",
        "<!-- sync-metadata",
        f"linear_id: {identifier}",
        f"linear_url: {url}",
        f"linear_state: {state}",
        f"linear_priority: {priority}",
        f"linear_updated: {updated_at}",
        f"last_synced: {now_kst()}",
        f"content_hash: {content_hash(description)}",
        f"comments_hash: {c_hash}",
        "-->",
        "",
        f"> **Linear**: [{identifier}]({url}) | **상태**: {state} | **우선순위**: {priority}",
        f"> **최종 동기화**: {now_kst()}",
        "",
        "---",
        "",
        description,
    ]

    # 댓글 섹션
    comments_md = format_comments(issue)
    if comments_md:
        lines += ["", "---", "", comments_md]

    if prev_changelog:
        lines += ["", "---", "", "## 변경 이력", "", prev_changelog]

    return "\n".join(lines) + "\n"


def extract_metadata(filepath: str) -> dict:
    """기존 md 파일에서 sync-metadata 블록을 파싱."""
    meta = {}
    if not os.path.exists(filepath):
        return meta
    with open(filepath, encoding="utf-8") as f:
        in_meta = False
        for line in f:
            if "<!-- sync-metadata" in line:
                in_meta = True
                continue
            if in_meta and "-->" in line:
                break
            if in_meta and ":" in line:
                k, v = line.strip().split(":", 1)
                meta[k.strip()] = v.strip()
    return meta


def extract_changelog(filepath: str) -> str:
    """기존 md 파일에서 변경 이력 섹션을 추출."""
    if not os.path.exists(filepath):
        return ""
    with open(filepath, encoding="utf-8") as f:
        content = f.read()
    marker = "## 변경 이력"
    idx = content.find(marker)
    if idx == -1:
        return ""
    return content[idx + len(marker):].strip()


def fetch_docs_issues(api_key: str, team_id: str) -> list[dict]:
    """DOCS 팀의 모든 이슈를 가져온다."""
    query = """
    query($teamId: String!, $cursor: String) {
        team(id: $teamId) {
            issues(first: 50, after: $cursor, orderBy: updatedAt) {
                nodes {
                    id
                    identifier
                    title
                    description
                    url
                    priority
                    updatedAt
                    state { name type }
                    comments {
                        nodes {
                            id
                            body
                            createdAt
                            updatedAt
                            user { name displayName }
                        }
                    }
                }
                pageInfo { hasNextPage endCursor }
            }
        }
    }
    """
    all_issues = []
    cursor = None

    while True:
        variables = {"teamId": team_id}
        if cursor:
            variables["cursor"] = cursor

        data = linear_request(api_key, query, variables)
        if not data or not data.get("team"):
            break

        issues_data = data["team"]["issues"]
        all_issues.extend(issues_data["nodes"])

        page_info = issues_data["pageInfo"]
        if page_info["hasNextPage"]:
            cursor = page_info["endCursor"]
        else:
            break

    return all_issues


def sync_issue(issue: dict) -> dict:
    """단일 이슈를 docs/reference/에 동기화. 결과 dict 반환."""
    title = issue["title"]
    identifier = issue["identifier"]
    filename = f"{sanitize_filename(title)}.md"
    filepath = os.path.join(REFERENCE_DIR, filename)

    new_description = issue.get("description") or "(내용 없음)"
    new_hash = content_hash(new_description)

    result = {
        "identifier": identifier,
        "title": title,
        "filename": filename,
        "action": "unchanged",
    }

    new_c_hash = comments_hash(issue)

    if os.path.exists(filepath):
        # 기존 파일 비교
        old_meta = extract_metadata(filepath)
        old_hash = old_meta.get("content_hash", "")
        old_c_hash = old_meta.get("comments_hash", "")

        if old_hash == new_hash and old_c_hash == new_c_hash:
            result["action"] = "unchanged"
            return result

        # 변경 감지 → 변경 이력 추가
        old_changelog = extract_changelog(filepath)
        change_parts = []
        if old_hash != new_hash:
            change_parts.append(f"내용 변경 (hash: {old_hash} → {new_hash})")
        if old_c_hash != new_c_hash:
            change_parts.append(f"댓글 변경 (hash: {old_c_hash} → {new_c_hash})")
        change_entry = f"- **{now_kst()}** — [{identifier}] {', '.join(change_parts)}\n"
        new_changelog = change_entry + old_changelog

        md_content = build_md(issue, new_changelog)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(md_content)

        result["action"] = "updated"
    else:
        # 새 파일 생성
        init_changelog = f"- **{now_kst()}** — [{identifier}] 최초 동기화\n"
        md_content = build_md(issue, init_changelog)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(md_content)

        result["action"] = "created"

    return result


def detect_deleted_issues(synced_filenames: set[str]) -> list[dict]:
    """로컬 docs/reference/에 있지만 Linear에는 없는 파일을 찾아 삭제 처리."""
    deleted = []
    if not os.path.exists(REFERENCE_DIR):
        return deleted

    for fname in os.listdir(REFERENCE_DIR):
        # _changelog.md, 이미 삭제 표시된 파일, 비-md 파일은 건너뜀
        if not fname.endswith(".md") or fname.startswith("_") or "(삭제)" in fname:
            continue
        if fname in synced_filenames:
            continue

        # 메타데이터에서 Linear 정보 추출
        filepath = os.path.join(REFERENCE_DIR, fname)
        meta = extract_metadata(filepath)
        if not meta.get("linear_id"):
            continue  # sync-metadata가 없는 수동 파일은 건너뜀

        # 파일명에 (삭제) 표시 추가
        base = fname.rsplit(".md", 1)[0]
        new_fname = f"{base}(삭제).md"
        new_filepath = os.path.join(REFERENCE_DIR, new_fname)
        os.rename(filepath, new_filepath)

        deleted.append({
            "identifier": meta.get("linear_id", "?"),
            "title": base,
            "filename": fname,
            "new_filename": new_fname,
            "action": "deleted",
        })

    return deleted


def update_changelog(results: list[dict]):
    """전체 동기화 결과를 _changelog.md에 기록."""
    created = [r for r in results if r["action"] == "created"]
    updated = [r for r in results if r["action"] == "updated"]
    deleted = [r for r in results if r["action"] == "deleted"]

    if not created and not updated and not deleted:
        return

    entry_lines = [f"### {now_kst()}", ""]

    if created:
        entry_lines.append("**새로 생성:**")
        for r in created:
            entry_lines.append(f"- [{r['identifier']}] {r['title']} → `{r['filename']}`")
        entry_lines.append("")

    if updated:
        entry_lines.append("**변경 감지:**")
        for r in updated:
            entry_lines.append(f"- [{r['identifier']}] {r['title']} → `{r['filename']}`")
        entry_lines.append("")

    if deleted:
        entry_lines.append("**삭제 감지:**")
        for r in deleted:
            entry_lines.append(f"- [{r['identifier']}] {r['title']} → `{r['filename']}` ➜ `{r['new_filename']}`")
        entry_lines.append("")

    entry_lines.append("---")
    entry_lines.append("")
    new_entry = "\n".join(entry_lines)

    # 기존 changelog 읽기
    existing = ""
    if os.path.exists(CHANGELOG_PATH):
        with open(CHANGELOG_PATH, encoding="utf-8") as f:
            existing = f.read()

    header = "# Linear DOCS 동기화 변경 이력\n\n"
    body = existing.replace(header, "") if existing.startswith(header) else existing

    with open(CHANGELOG_PATH, "w", encoding="utf-8") as f:
        f.write(header + new_entry + body)


def main():
    os.makedirs(REFERENCE_DIR, exist_ok=True)

    api_key, team_id = get_env("docs")

    print(f"[sync-docs] Linear DOCS 팀 이슈 동기화 시작 ({now_kst()})")

    issues = fetch_docs_issues(api_key, team_id)
    print(f"[sync-docs] {len(issues)}개 이슈 발견")

    results = []
    synced_filenames = set()
    for issue in issues:
        result = sync_issue(issue)
        results.append(result)
        synced_filenames.add(result["filename"])
        if result["action"] != "unchanged":
            print(f"  {result['action'].upper():>8}: [{result['identifier']}] {result['title']}")

    # 삭제된 이슈 감지: 로컬에 있지만 Linear에 없는 파일
    deleted_results = detect_deleted_issues(synced_filenames)
    for r in deleted_results:
        print(f"   DELETED: [{r['identifier']}] {r['title']} → {r['new_filename']}")
    results.extend(deleted_results)

    update_changelog(results)

    created = sum(1 for r in results if r["action"] == "created")
    updated = sum(1 for r in results if r["action"] == "updated")
    deleted = sum(1 for r in results if r["action"] == "deleted")
    unchanged = sum(1 for r in results if r["action"] == "unchanged")

    print(f"[sync-docs] 완료: 생성 {created} / 변경 {updated} / 삭제 {deleted} / 동일 {unchanged}")


if __name__ == "__main__":
    main()
