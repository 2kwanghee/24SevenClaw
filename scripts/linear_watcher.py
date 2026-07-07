#!/usr/bin/env python3
"""Linear 요구사항 감지기 — Queued 상태 이슈를 fix_plan.md로 변환.

Usage:
  python3 scripts/linear_watcher.py --per-task
  python3 scripts/linear_watcher.py --dry-run

Exit codes:
  0 — Queued 이슈 발견, fix_plan 생성 완료
  1 — 에러
  2 — Queued 이슈 없음 (정상 종료)
"""

import json
import os
import subprocess
import sys

# linear_client를 같은 디렉토리에서 import
sys.path.insert(0, os.path.dirname(__file__))
from linear_client import (
    get_env,
    linear_request,
    find_state_id,
    from_linear_priority,
    PROJECT_DIR,
)

FIX_PLAN_PATH = os.path.join(PROJECT_DIR, ".ralph", "fix_plan.md")
TASK_MAPPING_PATH = os.path.join(PROJECT_DIR, ".ralph", ".task_mapping.json")
TASKS_DIR = os.path.join(PROJECT_DIR, ".ralph", "tasks")

# 종결 상태 — 자식 이슈 확장 시 이 상태의 자식은 건너뜀
TERMINAL_STATES = {"Done", "Canceled", "Duplicate"}


def fetch_children(api_key: str, team_id: str, parent_id: str) -> list[dict]:
    """부모 이슈의 직접 자식 이슈들을 조회한다.

    Linear의 parent-child 관계를 GraphQL `parent: { id: { eq } }` 필터로 추출.
    """
    query = """
    query($teamId: ID!, $parentId: ID!) {
        issues(
            filter: {
                team: { id: { eq: $teamId } }
                parent: { id: { eq: $parentId } }
            }
            orderBy: createdAt
        ) {
            nodes {
                id identifier title description priority dueDate url
                labels { nodes { name } }
                state { id name }
            }
        }
    }
    """
    data = linear_request(api_key, query, {"teamId": team_id, "parentId": parent_id})
    if not data:
        return []
    return data.get("issues", {}).get("nodes", [])


def expand_to_leaves(api_key: str, team_id: str, issue: dict) -> list[dict]:
    """부모 이슈를 재귀적으로 리프 태스크까지 확장.

    - 자식이 없으면 자기 자신을 리프로 반환
    - 자식 중 TERMINAL_STATES(Done/Canceled/Duplicate)는 건너뜀
    - 다단계 계층(grandchild 등)도 자동 재귀
    """
    children = fetch_children(api_key, team_id, issue["id"])
    if not children:
        return [issue]
    leaves: list[dict] = []
    for child in children:
        if child.get("state", {}).get("name") in TERMINAL_STATES:
            continue
        leaves.extend(expand_to_leaves(api_key, team_id, child))
    return leaves


def incomplete_blockers(issue: dict) -> list[str]:
    """이 이슈를 막고 있는(blockedBy) 선행 이슈 중 아직 미완료인 것의 identifier 목록.

    Linear 관계에서 "A blocks B" 는 B 의 inverseRelations 에 type="blocks", issue=A 로 나타난다.
    선행 이슈(A)의 state.type 이 completed/canceled 가 아니면 B 는 아직 실행 불가로 본다.
    """
    blockers: list[str] = []
    inv = (issue.get("inverseRelations") or {}).get("nodes", [])
    for rel in inv:
        if rel.get("type") != "blocks":
            continue
        blocker = rel.get("issue") or {}
        state_type = (blocker.get("state") or {}).get("type", "")
        if state_type not in ("completed", "canceled"):
            blockers.append(blocker.get("identifier") or "?")
    return blockers


def fetch_queued_issues(api_key: str, team_id: str) -> list[dict]:
    """큐 상태 이슈를 조회하고 부모 이슈는 활성 리프 태스크로 확장해 반환한다.

    DayQueued/NightQueued/Queued 상태로 들어온 부모 이슈도 자동으로 자식 리프까지 펼쳐
    하나의 평면 리스트로 만든다. 자식이 없는 일반 이슈는 그대로 단일 항목으로 유지.
    """
    query = """
    query($teamId: ID!) {
        issues(
            filter: {
                team: { id: { eq: $teamId } }
                state: { name: { in: ["DayQueued", "NightQueued", "Queued"] } }
            }
            orderBy: createdAt
        ) {
            nodes {
                id
                identifier
                title
                description
                priority
                dueDate
                url
                labels { nodes { name } }
                state { id name }
                inverseRelations {
                    nodes {
                        type
                        issue { identifier state { type name } }
                    }
                }
            }
        }
    }
    """
    data = linear_request(api_key, query, {"teamId": team_id})
    if not data:
        return []
    nodes = data.get("issues", {}).get("nodes", [])

    # 부모 이슈 → 활성 리프 태스크로 확장 (중복 제거)
    # 자식이 없는 일반 이슈는 expand_to_leaves가 [issue]로 반환하므로 백워드 호환.
    seen_ids: set[str] = set()
    expanded: list[dict] = []
    for node in nodes:
        # blockedBy 가드: 미완료 선행 이슈가 있으면 순서 역전 머지를 막기 위해 이번 큐에서 제외.
        # (선행 이슈가 완료되면 다음 감지 라운드에 자연히 진행된다.)
        pending = incomplete_blockers(node)
        if pending:
            print(
                f"SKIP: {node.get('identifier')} — 미완료 선행(blockedBy) 이슈: {', '.join(pending)}",
                file=sys.stderr,
            )
            continue
        parent_identifier = node.get("identifier")
        for leaf in expand_to_leaves(api_key, team_id, node):
            if leaf["id"] in seen_ids:
                continue
            seen_ids.add(leaf["id"])
            # 자기 자신이 리프인 경우(자식 없음)는 parent_identifier 비움
            if leaf["id"] != node["id"]:
                leaf["_parent_identifier"] = parent_identifier
            expanded.append(leaf)
    nodes = expanded

    # identifier 숫자 순서로 정렬 (CE-1 → CE-2 → ... → CE-10)
    # 동일 번호 내에서는 priority로 2차 정렬
    import re
    def sort_key(x):
        match = re.search(r"-(\d+)$", x.get("identifier", ""))
        num = int(match.group(1)) if match else 9999
        priority = x.get("priority", 0) or 99
        return (num, priority)
    nodes.sort(key=sort_key)
    return nodes


def extract_task_info(issue: dict) -> dict:
    """Extract task information from a Linear issue."""
    identifier = issue["identifier"]  # e.g. "OPS-123"
    priority = from_linear_priority(issue.get("priority", 0))
    labels = [l["name"] for l in issue.get("labels", {}).get("nodes", [])]
    state_name = issue.get("state", {}).get("name", "")
    mode = "night" if state_name == "NightQueued" else "day"
    # "Queued" → DayQueued 동작과 동일 처리

    return {
        "issue_id": issue["id"],
        "identifier": identifier,
        "title": issue["title"],
        "description": issue.get("description") or "",
        "priority": priority,
        "labels": labels,
        "branch": f"ralph/{identifier}",
        "url": issue.get("url", ""),
        "mode": mode,
        # fetch_queued_issues가 부모 이슈에서 펼친 리프인 경우 부모 식별자를 저장
        # 자기 자신이 리프(자식 없음)인 경우는 None
        "parent_identifier": issue.get("_parent_identifier"),
    }


def generate_fix_plan(tasks: list[dict]) -> str:
    """Generate fix_plan.md content from task list."""
    lines = [
        "# Ralph Loop — 작업 큐 (Fix Plan)",
        "",
        "> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 순서대로 처리한다.",
        "> 완료 시 `- [x]`로 표시하고 커밋한다.",
        "> `- [!]`는 건너뛴 항목 (사유 기록 필수).",
        "",
        "---",
        "",
    ]

    grouped: dict[str, list[dict]] = {}
    for task in tasks:
        p = task["priority"]
        grouped.setdefault(p, []).append(task)

    for priority in ["P1", "P2", "P3"]:
        group = grouped.get(priority, [])
        if not group:
            continue

        lines.append(f"## {priority}: 기능 요구사항")
        lines.append("")

        for task in group:
            lines.append(f"- [ ] **{task['title']}**")
            if task["description"]:
                # description의 첫 줄만 요약으로 사용
                first_line = task["description"].split("\n")[0].strip()
                lines.append(f"  > 요청사항: {first_line}")
            lines.append("")

        lines.append("---")
        lines.append("")

    lines.append("## 진행 로그")
    lines.append("")
    lines.append("> Ralph가 작업하면서 여기에 기록을 남긴다.")
    lines.append("")
    lines.append("| 시각 | 항목 | 상태 | 비고 |")
    lines.append("|------|------|------|------|")

    return "\n".join(lines)


def generate_single_task_fix_plan(task: dict) -> str:
    """Generate fix_plan.md for a single task."""
    priority = task["priority"]
    lines = [
        "# Ralph Loop — 작업 큐 (Fix Plan)",
        "",
        "> Claude가 이 파일을 읽고 미완료(`- [ ]`) 항목을 처리한다.",
        "> 완료 시 `- [x]`로 표시하고 커밋한다.",
        "> `- [!]`는 건너뛴 항목 (사유 기록 필수).",
        "",
        "---",
        "",
        f"## {priority}: 기능 요구사항",
        "",
        f"- [ ] **{task['title']}**",
    ]
    if task["description"]:
        # description 내 체크박스를 일반 리스트로 변환 (stop hook 오판 방지)
        sanitized = task["description"].replace("- [ ] ", "- ").replace("- [x] ", "- ")
        lines.append(f"  > 요청사항: {sanitized}")
    lines.extend([
        "",
        "---",
        "",
        "## 진행 로그",
        "",
        "> Ralph가 작업하면서 여기에 기록을 남긴다.",
        "",
        "| 시각 | 항목 | 상태 | 비고 |",
        "|------|------|------|------|",
    ])
    return "\n".join(lines)


def update_issue_state(api_key: str, team_id: str, issue_id: str, state_name: str):
    """Update a Linear issue's workflow state."""
    state_id = find_state_id(api_key, team_id, state_name)
    if not state_id:
        print(f"WARN: '{state_name}' 상태를 찾을 수 없음.", file=sys.stderr)
        return

    mutation = """
    mutation($issueId: String!, $stateId: String!) {
        issueUpdate(id: $issueId, input: { stateId: $stateId }) {
            issue { id identifier state { name } }
        }
    }
    """
    linear_request(api_key, mutation, {"issueId": issue_id, "stateId": state_id})


def save_task_mapping(tasks: list[dict]):
    """Save task → Linear issue ID mapping for later result reporting."""
    mapping = {}
    for task in tasks:
        mapping[task["title"]] = {
            "issue_id": task["issue_id"],
            "identifier": task["identifier"],
            "priority": task["priority"],
            "description": task["description"],
            "branch": task["branch"],
            "url": task.get("url", ""),
            # 부모 이슈에서 펼친 자식이면 부모 식별자, 단일 이슈면 None
            "parent_identifier": task.get("parent_identifier"),
        }
    with open(TASK_MAPPING_PATH, "w") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)


def main():
    import argparse
    from pipeline_config import check_enabled

    check_enabled("FLOWOPS_LINEAR_WATCHER", "Linear 요구사항 감지")

    parser = argparse.ArgumentParser(description="Linear 요구사항 감지기")
    parser.add_argument("--dry-run", action="store_true", help="조회만 수행, 변경 없음")
    parser.add_argument("--per-task", action="store_true",
                        help="태스크별 개별 fix_plan 생성 (상태 미변경)")
    parser.add_argument("--limit", type=int, default=0,
                        help="처리할 이슈 수 제한 (0=전체, 1=순차 실행용)")
    parser.add_argument("--use-gpt-plan", action="store_true",
                        help="ChatGPT FC로 구조화된 fix_plan 생성 (fallback: 기존 방식)")
    args = parser.parse_args()

    api_key, team_id = get_env()

    # 1. DayQueued/NightQueued 이슈 조회
    issues = fetch_queued_issues(api_key, team_id)
    if not issues:
        print("EMPTY: DayQueued/NightQueued 이슈 없음.")
        sys.exit(2)

    # 2. 태스크 정보 추출 (--limit 적용)
    if args.limit > 0:
        issues = issues[:args.limit]
    tasks = [extract_task_info(issue) for issue in issues]
    print(f"FOUND: {len(tasks)}개 DayQueued/NightQueued 이슈{'(제한: ' + str(args.limit) + '개)' if args.limit > 0 else ''}")
    for t in tasks:
        print(f"  [{t['priority']}] {t['identifier']} {t['title']} → {t['branch']}")

    if args.dry_run:
        if args.per_task:
            for task in tasks:
                print(f"\n[DRY-RUN] {task['title']}:")
                print(generate_single_task_fix_plan(task))
        else:
            print("\n[DRY-RUN] fix_plan.md 미리보기:")
            print(generate_fix_plan(tasks))
        sys.exit(0)

    if args.per_task:
        # 태스크별 개별 fix_plan 생성
        os.makedirs(TASKS_DIR, exist_ok=True)
        for task in tasks:
            task_file = os.path.join(TASKS_DIR, f"{task['identifier']}.md")

            if args.use_gpt_plan:
                # ChatGPT FC로 구조화된 fix_plan 생성 시도
                try:
                    result = subprocess.run(
                        ["python3", os.path.join(os.path.dirname(__file__), "fix_plan_generator.py"),
                         "--title", task["title"],
                         "--description", task.get("description", ""),
                         "--priority", task["priority"],
                         "--output", task_file],
                        capture_output=True, text=True,
                        cwd=PROJECT_DIR,
                    )
                    if result.returncode == 0:
                        print(f"CREATED (GPT): {task_file}")
                        continue
                    else:
                        print(f"WARN: GPT plan 실패, fallback 사용: {result.stderr[:100]}")
                except Exception as e:
                    print(f"WARN: GPT plan 예외, fallback 사용: {e}")

            with open(task_file, "w") as f:
                f.write(generate_single_task_fix_plan(task))
            print(f"CREATED: {task_file}")

        save_task_mapping(tasks)
        print(f"CREATED: {TASK_MAPPING_PATH}")
        print(f"\nREADY: {len(tasks)}개 태스크 개별 fix_plan 생성 완료.")
    else:
        # 전체 fix_plan + 상태 변경
        fix_plan_content = generate_fix_plan(tasks)
        with open(FIX_PLAN_PATH, "w") as f:
            f.write(fix_plan_content)
        print(f"CREATED: {FIX_PLAN_PATH}")

        save_task_mapping(tasks)
        print(f"CREATED: {TASK_MAPPING_PATH}")

        for task in tasks:
            update_issue_state(api_key, team_id, task["issue_id"], "In Progress")
            print(f"UPDATED: [{task['priority']}] {task['identifier']} {task['title']} → In Progress")

        print(f"\nREADY: {len(tasks)}개 작업이 fix_plan.md에 등록되었습니다.")


if __name__ == "__main__":
    main()
