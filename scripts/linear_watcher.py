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
import sys

# linear_client를 같은 디렉토리에서 import
sys.path.insert(0, os.path.dirname(__file__))
from linear_client import (
    PROJECT_DIR,
    find_state_id,
    from_linear_priority,
    get_env,
    linear_request,
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


def apply_title_filters(
    nodes: list[dict],
    title_prefix: str | None = None,
    exclude_prefixes: list[str] | None = None,
) -> list[dict]:
    """제목 접두사 필터 (순수 함수) — include 먼저, exclude 나중.

    include(title_prefix)는 "이 프로젝트 티켓만" 을, exclude(exclude_prefixes)는 "이
    프로젝트 티켓은 빼고" 를 뜻한다. 둘 다 미지정이면 입력을 그대로 돌려준다(회귀 0).

    코디네이션 용도: 전용 러너가 `[수주:<key>] ` 접두사 티켓을 전담하는 동안, 기존 단일
    러너는 같은 접두사를 --exclude-prefix 로 빼서 티켓을 두 러너가 다투지 않게 한다.
    """
    if title_prefix:
        nodes = [n for n in nodes if (n.get("title") or "").startswith(title_prefix)]
    if exclude_prefixes:
        actives = [p for p in exclude_prefixes if p]
        if actives:
            nodes = [
                n
                for n in nodes
                if not any((n.get("title") or "").startswith(p) for p in actives)
            ]
    return nodes


def fetch_queued_issues(
    api_key: str,
    team_id: str,
    title_prefix: str | None = None,
    exclude_prefixes: list[str] | None = None,
) -> list[dict]:
    """큐 상태 이슈를 조회하고 부모 이슈는 활성 리프 태스크로 확장해 반환한다.

    DayQueued/NightQueued/Queued 상태로 들어온 부모 이슈도 자동으로 자식 리프까지 펼쳐
    하나의 평면 리스트로 만든다. 자식이 없는 일반 이슈는 그대로 단일 항목으로 유지.

    title_prefix(P5 다프로젝트): 지정 시 해당 접두사로 시작하는 이슈만 수집 —
    프로젝트 러너가 자기 프로젝트의 발급 티켓(`[수주:<intake8>]` 접두사, P6 규약)만
    집게 하여, 러너 간 티켓 중복 수거를 막는다. 미지정이면 기존 전체(회귀 0).

    exclude_prefixes(P5/CE-346): 지정 시 해당 접두사로 시작하는 이슈를 제외 —
    전용 러너가 맡은 프로젝트를 단일 러너가 함께 긁는 경합을 막는다.
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

    # P5 프로젝트 필터 — 확장 전에 적용(발급기는 부모·리프 모두에 접두사를 붙인다).
    nodes = apply_title_filters(nodes, title_prefix, exclude_prefixes)

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
    labels = [lbl["name"] for lbl in issue.get("labels", {}).get("nodes", [])]
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


def resolve_exclude_prefixes(cli_values: list[str] | None) -> list[str] | None:
    """--exclude-prefix(CLI) 와 WATCHER_EXCLUDE_PREFIXES(env)를 병합한다.

    파이프라인 본체를 수정하지 않고 단일 러너에 exclude 를 넣기 위한 경로 —
    `auto_dev_pipeline.sh` 는 이 인자를 넘기지 않지만 cron 라인의 env 는 상속된다.
    구분자가 **탭**인 이유: 접두사(`[수주:xxxxxxxx] `)는 공백을 포함하므로 공백 구분은 안전하지
    않다. 중복은 순서를 지키며 제거하고, 아무것도 없으면 None(=필터 없음, 회귀 0).
    """
    merged: list[str] = list(cli_values or [])
    merged.extend(p for p in os.environ.get("WATCHER_EXCLUDE_PREFIXES", "").split("\t") if p)
    deduped: list[str] = []
    for prefix in merged:
        if prefix and prefix not in deduped:
            deduped.append(prefix)
    return deduped or None


def main():
    import argparse

    from pipeline_config import check_enabled, is_enabled

    # --check-only 는 "할 일이 있는지" 를 exit code 로만 답하는 관측 모드다. 비활성 시
    # check_enabled 의 exit 0 을 그대로 쓰면 호출자(디스패처)가 "Queued 있음"으로 오판해
    # 러너를 스폰한다 — 이 모드에서만 비활성을 exit 2(할 일 없음)로 답한다.
    if "--check-only" in sys.argv[1:] and not is_enabled("FLOWOPS_LINEAR_WATCHER"):
        print("EMPTY: FLOWOPS_LINEAR_WATCHER 비활성 — 확인할 큐 없음.")
        sys.exit(2)

    check_enabled("FLOWOPS_LINEAR_WATCHER", "Linear 요구사항 감지")

    parser = argparse.ArgumentParser(description="Linear 요구사항 감지기")
    parser.add_argument("--dry-run", action="store_true", help="조회만 수행, 변경 없음")
    parser.add_argument("--per-task", action="store_true",
                        help="태스크별 개별 fix_plan 생성 (상태 미변경)")
    parser.add_argument("--limit", type=int, default=0,
                        help="처리할 이슈 수 제한 (0=전체, 1=순차 실행용)")
    parser.add_argument("--title-prefix", default=None,
                        help="P5 다프로젝트: 이 접두사로 시작하는 이슈만 수집 "
                             "(프로젝트 러너용, 미지정=전체)")
    parser.add_argument("--exclude-prefix", action="append", default=None,
                        dest="exclude_prefix",
                        help="이 접두사로 시작하는 이슈는 제외(반복 지정 가능). "
                             "전용 러너가 맡은 프로젝트를 단일 러너에서 빼는 용도. "
                             "env WATCHER_EXCLUDE_PREFIXES(탭 구분)와 병합된다")
    parser.add_argument("--check-only", action="store_true",
                        help="매칭 이슈 존재 여부만 확인하고 종료 — 어떤 파일도 쓰지 않는다 "
                             "(있음 0 / 없음 2). 디스패처의 Queued 사전확인용")
    args = parser.parse_args()

    api_key, team_id = get_env()

    # 1. DayQueued/NightQueued 이슈 조회
    issues = fetch_queued_issues(
        api_key,
        team_id,
        title_prefix=args.title_prefix,
        exclude_prefixes=resolve_exclude_prefixes(args.exclude_prefix),
    )
    if not issues:
        print("EMPTY: DayQueued/NightQueued 이슈 없음.")
        sys.exit(2)

    # 1-1. 존재 확인 전용 — fix_plan / .task_mapping.json / .ralph/tasks 를 오염시키지 않기
    #      위해 어떤 쓰기 경로에도 진입하지 않고 여기서 끝낸다.
    if args.check_only:
        print(f"FOUND: {len(issues)}개")
        sys.exit(0)

    # 2. 태스크 정보 추출 (--limit 적용)
    if args.limit > 0:
        issues = issues[:args.limit]
    tasks = [extract_task_info(issue) for issue in issues]
    limit_note = f"(제한: {args.limit}개)" if args.limit > 0 else ""
    print(f"FOUND: {len(tasks)}개 DayQueued/NightQueued 이슈{limit_note}")
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
