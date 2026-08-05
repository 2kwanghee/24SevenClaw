#!/usr/bin/env python3
"""Linear GraphQL API 공용 클라이언트.

모든 linear_*.py 스크립트가 이 모듈을 import하여 사용한다.
"""

import json
import os
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen

LINEAR_API_URL = "https://api.linear.app/graphql"

PROJECT_DIR = os.path.join(os.path.dirname(__file__), "..")

sys.path.insert(0, os.path.dirname(__file__))
from env_loader import load_env as _load_env_file


def _resolve(key: str, env_vars: dict[str, str]) -> str | None:
    """설정값 1개 해석 — **프로세스 환경이 `.env` 를 이긴다**(CE-383).

    전에는 `env_vars.get(key) or os.getenv(key)` 로 `.env` 가 이겼다. 그래서 호출부가
    `LINEAR_TEAM_ID=<팀>` 을 주입해도 **조용히 무시됐다.** 실측(2026-08-05 E2E):
    `runner_dispatcher.sh` 가 딜리버리 팀을 주입했는데 `linear_watcher.py` 는 `.env` 의
    자체 개발 팀을 조회해 발급된 티켓을 찾지 못했다 — 발급은 SIP, 조회는 CE.

    셸 쪽은 이미 반대였다: `auto_dev_pipeline.sh` 가 `[ -z "${LINEAR_TEAM_ID:-}" ]` 가드로
    **환경을 우선**한다. 같은 레포에서 셸과 파이썬이 반대로 동작하는 것이 함정이었다.
    명시적 주입이 파일 기본값을 이기는 쪽으로 통일한다(12-factor 관례와도 일치).
    """
    return os.getenv(key) or env_vars.get(key)


def get_env(team: str | None = None):
    """Load LINEAR_API_KEY and team ID. **환경변수 > `.env`** (CE-383).

    Args:
        team: 팀 이름 (dev, docs, delivery). None이면 LINEAR_TEAM_ID 폴백.
    Returns:
        (api_key, team_id) 튜플
    """
    env_vars = _load_env_file()

    api_key = _resolve("LINEAR_API_KEY", env_vars)

    team_id = None
    if team:
        team_id = _resolve(f"LINEAR_TEAM_ID_{team.upper()}", env_vars)

    if not team_id:
        # 폴백 1: LINEAR_TEAM_ID (하위 호환 — 단일팀 프로젝트 · 호출부 주입 지점)
        team_id = _resolve("LINEAR_TEAM_ID", env_vars)

    if not team_id:
        # 폴백 2: LINEAR_TEAM_ID_DEV (멀티팀에서 기본 팀으로 사용)
        team_id = _resolve("LINEAR_TEAM_ID_DEV", env_vars)

    if not api_key or not team_id:
        print("Error: LINEAR_API_KEY and LINEAR_TEAM_ID required.", file=sys.stderr)
        print("  .env에 LINEAR_TEAM_ID 또는 LINEAR_TEAM_ID_DEV를 설정하세요.", file=sys.stderr)
        sys.exit(1)

    return api_key, team_id


def get_all_team_ids() -> dict[str, str]:
    """Return all configured team IDs as {name: id} dict."""
    env_vars = _load_env_file()
    teams = {}
    prefix = "LINEAR_TEAM_ID_"
    for k, v in env_vars.items():
        if k.startswith(prefix) and v:
            name = k[len(prefix):].lower()
            teams[name] = v
    # 환경변수에서도 탐색
    for k, v in os.environ.items():
        if k.startswith(prefix) and v:
            name = k[len(prefix):].lower()
            if name not in teams:
                teams[name] = v
    return teams


def linear_request(api_key: str, query: str, variables: dict | None = None):
    """Make a GraphQL request to the Linear API."""
    body = {"query": query}
    if variables:
        body["variables"] = variables

    data = json.dumps(body).encode("utf-8")
    req = Request(LINEAR_API_URL, data=data, method="POST")
    req.add_header("Authorization", api_key)
    req.add_header("Content-Type", "application/json")

    try:
        with urlopen(req) as resp:
            result = json.loads(resp.read())
    except HTTPError as e:
        err_body = e.read().decode()
        print(f"Linear API Error ({e.code}): {err_body}", file=sys.stderr)
        return None

    if "errors" in result:
        for err in result["errors"]:
            print(f"Linear GraphQL Error: {err.get('message', err)}", file=sys.stderr)
        return None

    return result.get("data")


# ── Workflow State 캐시 ──

_state_cache: dict[str, list[dict]] = {}


def get_workflow_states(api_key: str, team_id: str) -> list[dict]:
    """Get all workflow states for a team (cached)."""
    if team_id in _state_cache:
        return _state_cache[team_id]

    query = """
    query($teamId: String!) {
        team(id: $teamId) {
            states { nodes { id name type } }
        }
    }
    """
    data = linear_request(api_key, query, {"teamId": team_id})
    if not data or not data.get("team"):
        print("Error: 팀 정보를 가져올 수 없습니다.", file=sys.stderr)
        sys.exit(1)

    states = data["team"]["states"]["nodes"]
    _state_cache[team_id] = states
    return states


def find_state_id(api_key: str, team_id: str, state_name: str) -> str | None:
    """Find workflow state ID by name."""
    states = get_workflow_states(api_key, team_id)
    for s in states:
        if s["name"] == state_name:
            return s["id"]
    return None


# ── Priority 매핑 ──
# Linear: 0=None, 1=Urgent, 2=High, 3=Medium, 4=Low
# 프로젝트: P1(긴급), P2(일반), P3(낮음)

PRIORITY_TO_LINEAR = {"P1": 1, "P2": 3, "P3": 4}
PRIORITY_FROM_LINEAR = {0: "P2", 1: "P1", 2: "P1", 3: "P2", 4: "P3"}


def to_linear_priority(p: str) -> int:
    return PRIORITY_TO_LINEAR.get(p, 3)


def from_linear_priority(p: int) -> str:
    return PRIORITY_FROM_LINEAR.get(p, "P2")
