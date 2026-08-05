#!/usr/bin/env python3
"""`linear_client.get_env` 우선순위 테스트 (CE-383).

**이 테스트가 없어서 결함이 통과했다.** CE-382 에서 팀 분리를 넣을 때 나는
`get_env()`/`get_env("delivery")` 가 각각 다른 값을 돌려주는 것만 확인했다 — 즉 `.env` 에
키가 둘 있는지만 봤다. 정작 **호출부의 주입이 통하는지**는 검증하지 않았다.

실측(2026-08-05 E2E): `runner_dispatcher.sh` 가 `LINEAR_TEAM_ID=<딜리버리팀>` 을 주입했는데
`env_vars.get(key) or os.getenv(key)` 라서 `.env` 가 이겼다. 결과적으로 **발급은 SIP 팀,
조회는 CE 팀** — 파이프라인이 자기가 발급한 티켓을 찾지 못했다.

같은 레포의 셸 쪽은 이미 반대였다(`auto_dev_pipeline.sh` 의 `[ -z "${LINEAR_TEAM_ID:-}" ]`
가드 = 환경 우선). 셸과 파이썬이 반대로 동작하는 것 자체가 함정이었다.

실행: `python3 scripts/tests/test_get_env_precedence.py`
"""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]

PASS = 0
FAIL = 0


def check(label: str, expected: object, actual: object) -> None:
    global PASS, FAIL
    if expected == actual:
        PASS += 1
        print(f"  ✓ {label}")
    else:
        FAIL += 1
        print(f"  ✗ {label}\n      기대={expected!r}\n      실제={actual!r}")


def load_module(env_file: Path):
    """`.env` 경로를 고정한 linear_client 를 새로 로드한다(모듈 캐시 회피)."""
    spec = importlib.util.spec_from_file_location(
        f"lc_{env_file.stem}_{id(env_file)}", _ROOT / "scripts" / "linear_client.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # `_load_env_file` 이 레포 `.env` 를 읽으므로 테스트용 파일로 갈아끼운다.
    parsed: dict[str, str] = {}
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        parsed[k.strip()] = v.strip()
    mod._load_env_file = lambda: parsed  # type: ignore[assignment]
    return mod


def with_env(**kv):
    """os.environ 을 일시 치환하는 컨텍스트."""

    class _Ctx:
        def __enter__(self):
            self.saved = {k: os.environ.get(k) for k in kv}
            for k, v in kv.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

        def __exit__(self, *a):
            for k, v in self.saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    return _Ctx()


with tempfile.TemporaryDirectory() as d:
    envf = Path(d) / ".env"
    envf.write_text(
        "LINEAR_API_KEY=key-from-dotenv\n"
        "LINEAR_TEAM_ID=team-CE-from-dotenv\n"
        "LINEAR_TEAM_ID_DELIVERY=team-SIP-from-dotenv\n",
        encoding="utf-8",
    )
    lc = load_module(envf)

    print("[1/3] 프로세스 환경이 .env 를 이긴다 (핵심 — 이게 결함이었다)")
    with with_env(LINEAR_TEAM_ID="team-INJECTED"):
        _, tid = lc.get_env()
        check("LINEAR_TEAM_ID 주입이 .env 를 이긴다", "team-INJECTED", tid)
    with with_env(LINEAR_API_KEY="key-INJECTED"):
        api, _ = lc.get_env()
        check("LINEAR_API_KEY 주입이 .env 를 이긴다", "key-INJECTED", api)
    with with_env(LINEAR_TEAM_ID_DELIVERY="team-SIP-INJECTED"):
        _, tid = lc.get_env("delivery")
        check("팀별 키 주입이 .env 를 이긴다", "team-SIP-INJECTED", tid)

    print("[2/3] 주입이 없으면 .env 그대로 (회귀 0)")
    with with_env(LINEAR_TEAM_ID=None, LINEAR_API_KEY=None, LINEAR_TEAM_ID_DELIVERY=None):
        api, tid = lc.get_env()
        check("자체개발 팀은 .env 값", "team-CE-from-dotenv", tid)
        check("API 키는 .env 값", "key-from-dotenv", api)
        _, dtid = lc.get_env("delivery")
        check("딜리버리 팀은 .env 값", "team-SIP-from-dotenv", dtid)

    print("[3/3] 폴백 순서 불변 — 팀별 키 → LINEAR_TEAM_ID → _DEV")
    envf2 = Path(d) / ".env2"
    envf2.write_text("LINEAR_API_KEY=k\nLINEAR_TEAM_ID_DEV=team-DEV\n", encoding="utf-8")
    lc2 = load_module(envf2)
    with with_env(LINEAR_TEAM_ID=None, LINEAR_TEAM_ID_DELIVERY=None, LINEAR_API_KEY=None):
        _, tid = lc2.get_env()
        check("LINEAR_TEAM_ID 없으면 _DEV 폴백", "team-DEV", tid)
        # 팀별 키가 없으면 LINEAR_TEAM_ID → _DEV 로 내려간다(요청한 팀이 없어도 죽지 않는다).
        _, tid = lc2.get_env("delivery")
        check("팀별 키 부재 시 폴백까지 내려간다", "team-DEV", tid)

print()
if FAIL:
    print(f"실패 {FAIL}건 / 통과 {PASS}건")
    sys.exit(1)
print(f"전체 통과: {PASS}건")
