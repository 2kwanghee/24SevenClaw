#!/usr/bin/env python3
"""티켓 전량 발급기 (다프로젝트화 P6, D-12) — 분해 JSON → Linear 이슈 + 의존 체인.

무인 발급 배치(scripts/intake_issue.sh)가 호출한다. 분해(LLM)는 배치의 claude -p
(구독 세션) 몫이고, 이 모듈은 그 결과 JSON 을 **검증하고 발급**하는 결정적 부분만 맡는다.

## 입력 계약 (분해 JSON)

{"tickets": [{
    "key": "T1",                 # 로컬 키 — depends_on 참조용, 티켓 간 유일
    "title": "설계: DB 스키마",
    "description": "…",          # 선택
    "labels": ["api"],           # 선택 — Linear 라벨명
    "priority": 2,               # 선택 — Linear 우선순위(0~4)
    "depends_on": ["T0"]         # 선택 — 선행 티켓 로컬 키
}]}

## 전량 아니면 전무 (고아 티켓 방지)

검증(스키마·중복 키·미지 참조·순환)은 **네트워크 호출 전에** 끝난다 — 불량 JSON 은 발급 0건.
원격 부분 실패에는 3상 발급으로 대응한다:

  1상  전 티켓을 **Backlog(비활성)** 상태로 생성 — watcher 는 Queued 계열만 집으므로
       이 시점의 티켓은 실행되지 않는다.
  2상  depends_on → Linear blockedBy 관계 배선 — linear_watcher.py 가 이미
       "선행 미완료 시 실행 불가" 판정을 하므로 순차 A-Z 가 기존 코드 무변경으로 성립.
  3상  목표 상태(DayQueued/NightQueued)로 **역위상 순서** 승격 — 의존자(잎)부터,
       뿌리를 마지막에. 승격이 중간에 실패해도 이미 승격된 티켓은 전부 미승격(Backlog)
       선행에 막혀 있어 실행 불가 — 부분 실패가 부분 실행으로 이어지지 않는다.

어느 상이든 실패하면 exit 2 + 생성된 이슈 목록을 stderr 로 남긴다(수동 정리 힌트).
성공 시에만 stdout 에 발급 원장 JSON 을 출력한다 — 배치는 이것을
POST /intake/{id}/tickets 로 확정한다.

사용:
  python3 scripts/linear_issuer.py --input decomposition.json --state NightQueued \
      [--title-prefix "[수주] "] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

sys.path.insert(0, "scripts")

from linear_client import find_state_id, get_env, linear_request  # noqa: E402

VALID_STATES = ("DayQueued", "NightQueued", "Queued")
INERT_STATE = "Backlog"  # 1상 생성 상태 — watcher 가 절대 집지 않는 비활성 자리
_TICKET_KEYS = ("key", "title", "description", "labels", "priority", "depends_on")
MAX_TICKETS = 100  # 폭주 분해 방지 상한 — 초과는 분해 프롬프트 문제다


class DecompositionError(ValueError):
    """분해 JSON 형식 불량 — 발급 0건으로 거부한다(fail-closed)."""


def validate_decomposition(data: Any) -> list[dict[str, Any]]:
    """분해 JSON 전량 검증 — 네트워크 호출 전 완료. 위반 시 DecompositionError."""
    if not isinstance(data, dict):
        raise DecompositionError(f"최상위: 객체여야 함 (받은 값: {type(data).__name__})")
    unknown_top = sorted(set(data) - {"tickets"})
    if unknown_top:
        raise DecompositionError(f"최상위: 알 수 없는 키 {unknown_top}")
    tickets = data.get("tickets")
    if not isinstance(tickets, list) or not tickets:
        raise DecompositionError("tickets: 비어있지 않은 배열이어야 함")
    if len(tickets) > MAX_TICKETS:
        raise DecompositionError(f"tickets: {len(tickets)}건 — 상한 {MAX_TICKETS} 초과(분해 폭주)")

    seen: set[str] = set()
    for i, t in enumerate(tickets):
        if not isinstance(t, dict):
            raise DecompositionError(f"tickets[{i}]: 객체여야 함")
        unknown = sorted(set(t) - set(_TICKET_KEYS))
        if unknown:
            raise DecompositionError(f"tickets[{i}]: 알 수 없는 키 {unknown}")
        key = t.get("key")
        if not isinstance(key, str) or not key.strip():
            raise DecompositionError(f"tickets[{i}].key: 비어있지 않은 문자열이어야 함")
        if key in seen:
            raise DecompositionError(f"tickets[{i}].key: 중복 '{key}'")
        seen.add(key)
        title = t.get("title")
        if not isinstance(title, str) or not title.strip():
            raise DecompositionError(f"tickets[{i}].title: 비어있지 않은 문자열이어야 함")
        if "description" in t and not isinstance(t["description"], str):
            raise DecompositionError(f"tickets[{i}].description: 문자열이어야 함")
        if "labels" in t:
            labels = t["labels"]
            if not isinstance(labels, list) or any(
                not isinstance(x, str) or not x.strip() for x in labels
            ):
                raise DecompositionError(f"tickets[{i}].labels: 문자열 배열이어야 함")
        if "priority" in t:
            p = t["priority"]
            if isinstance(p, bool) or not isinstance(p, int) or not 0 <= p <= 4:
                raise DecompositionError(f"tickets[{i}].priority: 0~4 정수여야 함")
        if "depends_on" in t:
            deps = t["depends_on"]
            if not isinstance(deps, list) or any(not isinstance(d, str) for d in deps):
                raise DecompositionError(f"tickets[{i}].depends_on: 문자열 배열이어야 함")

    # 참조 무결성 — 미지 키·자기 참조는 배선 불가이므로 거부
    for t in tickets:
        for dep in t.get("depends_on") or []:
            if dep == t["key"]:
                raise DecompositionError(f"{t['key']}: 자기 자신에 의존할 수 없음")
            if dep not in seen:
                raise DecompositionError(f"{t['key']}: 미지의 선행 키 '{dep}'")
    return tickets


def topo_sort(tickets: list[dict[str, Any]]) -> list[str]:
    """위상 정렬(Kahn) — 순환이면 DecompositionError 에 잔여 노드를 명시한다.

    반환 순서 = 뿌리(선행 없음)부터. 동순위는 입력 순서 보존(결정적).
    """
    keys = [t["key"] for t in tickets]
    deps: dict[str, list[str]] = {t["key"]: list(t.get("depends_on") or []) for t in tickets}
    order: list[str] = []
    remaining = dict(deps)
    while remaining:
        ready = [k for k in keys if k in remaining and not remaining[k]]
        if not ready:
            cycle = sorted(remaining)
            raise DecompositionError(f"의존 순환 감지 — 관련 티켓: {cycle}")
        for k in ready:
            order.append(k)
            del remaining[k]
        for k in remaining:
            remaining[k] = [d for d in remaining[k] if d not in order]
    return order


def promotion_order(tickets: list[dict[str, Any]]) -> list[str]:
    """3상 승격 순서 = 역위상(잎부터, 뿌리 마지막).

    승격이 중간에 실패해도 이미 승격된 티켓은 전부 미승격 선행에 막혀 있으므로
    부분 실패 = 실행 0건 이라는 불변식이 성립한다.
    """
    return list(reversed(topo_sort(tickets)))


# ── Linear 발급 (얇은 원격 계층 — 테스트는 linear_request 를 목킹) ────────────


def _resolve_label_ids(api_key: str, team_id: str, labels: list[str]) -> list[str]:
    """라벨명 → ID. 미지 라벨은 조용히 제외(라벨은 발급을 막을 사유가 아니다)."""
    try:
        from linear_tracker import _resolve_label_ids as resolve

        return resolve(api_key, team_id, labels)
    except Exception:  # noqa: BLE001 — 라벨 실패는 비차단(제목/본문이 본질)
        return []


def issue_all(
    tickets: list[dict[str, Any]],
    *,
    target_state: str,
    title_prefix: str = "",
) -> list[dict[str, str]]:
    """3상 발급 본체. 성공 시 발급 원장을 반환, 실패 시 RuntimeError.

    실패 메시지에는 그때까지 생성된 이슈 식별자를 포함한다(수동 정리 힌트).
    """
    api_key, team_id = get_env()

    inert_id = find_state_id(api_key, team_id, INERT_STATE)
    target_id = find_state_id(api_key, team_id, target_state)
    if not inert_id or not target_id:
        raise RuntimeError(f"상태 조회 실패: {INERT_STATE}={inert_id}, {target_state}={target_id}")

    order = topo_sort(tickets)
    by_key = {t["key"]: t for t in tickets}
    created: dict[str, dict[str, str]] = {}  # key → {identifier, issue_id, title}

    def _created_hint() -> str:
        return ", ".join(f"{k}={v['identifier']}" for k, v in created.items()) or "(없음)"

    # ── 1상: 전량 Backlog(비활성) 생성 ──────────────────────────────────────
    create_mutation = """
    mutation($input: IssueCreateInput!) {
        issueCreate(input: $input) { issue { id identifier title } }
    }
    """
    for key in order:
        t = by_key[key]
        input_data: dict[str, Any] = {
            "teamId": team_id,
            "title": f"{title_prefix}{t['title']}"[:255],
            "description": (t.get("description") or "")[:10000],
            "stateId": inert_id,
        }
        if t.get("priority") is not None:
            input_data["priority"] = t["priority"]
        label_ids = _resolve_label_ids(api_key, team_id, t.get("labels") or [])
        if label_ids:
            input_data["labelIds"] = label_ids
        data = linear_request(api_key, create_mutation, {"input": input_data})
        # GraphQL 은 실패 시 {"issueCreate": null} 을 줄 수 있다 — .get(k, {}) 는
        # 키가 null 로 존재하면 기본값을 쓰지 않으므로 `or {}` 로 이중 방어한다.
        issue = ((data or {}).get("issueCreate") or {}).get("issue")
        if not issue:
            raise RuntimeError(
                f"1상 생성 실패: {key} — 생성됨(Backlog 잔류, 수동 정리): {_created_hint()}"
            )
        created[key] = {
            "key": key,
            "identifier": issue["identifier"],
            "issue_id": issue["id"],
            "title": issue["title"],
        }

    # ── 2상: depends_on → blockedBy 배선 ───────────────────────────────────
    # relatedIssueId(선행) blocks issueId(후행). watcher 가 선행 미완료를 차단한다.
    relation_mutation = """
    mutation($input: IssueRelationCreateInput!) {
        issueRelationCreate(input: $input) { issueRelation { id } }
    }
    """
    for key in order:
        for dep in by_key[key].get("depends_on") or []:
            data = linear_request(
                api_key,
                relation_mutation,
                {
                    "input": {
                        "issueId": created[dep]["issue_id"],
                        "relatedIssueId": created[key]["issue_id"],
                        "type": "blocks",
                    }
                },
            )
            if not (data or {}).get("issueRelationCreate"):
                raise RuntimeError(
                    f"2상 배선 실패: {dep} blocks {key} — "
                    f"전량 Backlog 잔류(실행 불가), 수동 정리: {_created_hint()}"
                )

    # ── 3상: 역위상 승격 — 잎부터, 뿌리 마지막(부분 실패 = 실행 0건 불변식) ──
    update_mutation = """
    mutation($issueId: String!, $stateId: String!) {
        issueUpdate(id: $issueId, input: { stateId: $stateId }) { success }
    }
    """
    for key in promotion_order(tickets):
        data = linear_request(
            api_key,
            update_mutation,
            {"issueId": created[key]["issue_id"], "stateId": target_id},
        )
        if not ((data or {}).get("issueUpdate") or {}).get("success"):
            raise RuntimeError(
                f"3상 승격 실패: {key} — 승격분은 전부 미승격 선행에 막혀 실행 불가. "
                f"수동 정리: {_created_hint()}"
            )

    return [created[t["key"]] for t in tickets]  # 입력 순서로 반환


def main() -> int:
    p = argparse.ArgumentParser(description="분해 JSON → Linear 티켓 전량 발급 (P6)")
    p.add_argument("--input", required=True, help="분해 JSON 파일 경로 (- 는 stdin)")
    p.add_argument("--state", default="NightQueued", choices=VALID_STATES,
                   help="발급 목표 상태 (기본 NightQueued)")
    p.add_argument("--title-prefix", default="", help="티켓 제목 접두사")
    p.add_argument("--dry-run", action="store_true",
                   help="검증+위상 계획만 출력, 네트워크 호출 없음")
    args = p.parse_args()

    try:
        raw = sys.stdin.read() if args.input == "-" else open(args.input, encoding="utf-8").read()
        data = json.loads(raw)
    except (OSError, json.JSONDecodeError) as e:
        print(f"[issuer] 입력 로드 실패(발급 0건): {e}", file=sys.stderr)
        return 2

    try:
        tickets = validate_decomposition(data)
        order = topo_sort(tickets)
    except DecompositionError as e:
        print(f"[issuer] 분해 JSON 불량(발급 0건): {e}", file=sys.stderr)
        return 2

    if args.dry_run:
        print(json.dumps(
            {"plan": order, "promotion": promotion_order(tickets), "count": len(tickets)},
            ensure_ascii=False,
        ))
        return 0

    try:
        ledger = issue_all(tickets, target_state=args.state, title_prefix=args.title_prefix)
    except RuntimeError as e:
        print(f"[issuer] 발급 실패: {e}", file=sys.stderr)
        return 2

    print(json.dumps({"tickets": ledger}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
