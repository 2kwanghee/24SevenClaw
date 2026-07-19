"""거버넌스 SSOT 패리티 테스트.

동일 입력 (files, head, 토글) 을 세 경로로 평가하여 핵심 판정
{merge_decision, tier, verdict, failures} 가 완전히 일치하는지 단언한다:
  (a) governance.core.evaluate 직접 호출(커널)
  (b) scripts/pre_merge_gate.py --diff-files subprocess(shim CLI)  → JSON + exit code
  (c) FastAPI TestClient POST /api/v1/governance/evaluate(HTTP 어댑터)

로직은 물리적으로 하나(커널)뿐이므로 세 경로는 반드시 같은 결과를 낸다. (c) 는 시스템
python 에 FastAPI/clickeye-api 가 설치돼 있지 않으면 자동 skip 한다(그래도 (a)==(b) 는
항상 검증). (c) 는 **설치된** 커널 패키지를 그대로 쓴다 — 저장소 루트를 sys.path 에
주입하지 않으므로 editable 설치가 깨졌다면 skip 이 아니라 실패로 드러난다.

Usage:
    cd ClickEye && pytest scripts/tests/test_governance_parity.py -v
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

_SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_SCRIPTS_DIR)

# 커널 import: 설치돼 있으면(uv true-editable) 그대로 쓰고, 없으면(시스템 python) 저장소
# 루트를 sys.path 에 얹어 원본 소스를 직접 import 한다. 후자는 path (a)/(b) 전용이며,
# path (c) 는 아래에서 별도로 "설치된" 패키지 여부를 검사한다.
try:  # noqa: SIM105
    import governance  # noqa: F401
except ImportError:
    if _REPO_ROOT not in sys.path:
        sys.path.insert(0, _REPO_ROOT)

from governance import core as g  # noqa: E402

_GATE_SCRIPT = os.path.join(_SCRIPTS_DIR, "pre_merge_gate.py")

# (이름, files, head, 토글env) — 토글은 케이스별로 os.environ 에 주입.
CASES = [
    (
        "high_pr",
        [
            "clickeye-contracts/protocol/commands.ts",
            "clickeye-contracts/generated/typescript/types.gen.ts",
        ],
        "ralph/CE-3",
        {},
    ),
    (
        "block_contract_drift",
        ["clickeye-api/app/api/v1/auth.py"],
        "ralph/CE-5",
        {},
    ),
    (
        "direct_low",
        ["clickeye-web/src/app/page.tsx"],
        "ralph/CE-2",
        {},
    ),
    (
        # 마스터 off → 축약 스키마로 우회(회귀 0). files 무관하게 direct/LOW/pass.
        "master_off",
        ["clickeye-contracts/protocol/commands.ts"],
        "ralph/CE-6",
        {"FLOWOPS_GOVERNANCE": "false"},
    ),
]

_CORE_KEYS = ("merge_decision", "tier", "verdict", "failures")


def _subset(d: dict) -> dict:
    return {k: d.get(k) for k in _CORE_KEYS}


@pytest.fixture(autouse=True)
def _clear_toggles(monkeypatch):
    for k in list(os.environ):
        if k.startswith("FLOWOPS_GOVERNANCE"):
            monkeypatch.delenv(k, raising=False)
    yield


def _fastapi_client():
    """FastAPI TestClient 준비. 의존성/앱 미설치면 None(→ path c skip).

    ImportError/ModuleNotFoundError 만 skip 사유로 삼는다. 그 외 예외(앱 팩토리 오류,
    라우터/서비스 버그 등)는 전파시켜 테스트가 실패하도록 한다(버그를 skip 으로 숨기지 않음).
    """
    try:
        pytest.importorskip("fastapi")
        from fastapi.testclient import TestClient

        # NOTE: 저장소 루트를 sys.path 에 주입하지 않는다 — path (c) 는 설치된 커널
        # 패키지를 통해 import 되어야 하며, editable 설치가 깨졌다면 여기서 실패해야 한다.
        from app.main import app  # type: ignore
    except (ImportError, ModuleNotFoundError):
        return None
    return TestClient(app)


@pytest.mark.parametrize("name,files,head,toggles", CASES, ids=[c[0] for c in CASES])
def test_parity_core_vs_shim(name, files, head, toggles, monkeypatch):
    for k, v in toggles.items():
        monkeypatch.setenv(k, v)

    # (a) 커널 직접
    a = g.evaluate("main", head, files=files)

    # (b) shim CLI subprocess
    env = dict(os.environ)
    r = subprocess.run(
        [
            sys.executable,
            _GATE_SCRIPT,
            "--base", "main",
            "--head", head,
            "--diff-files", ",".join(files),
            "--json",
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    b = json.loads(r.stdout)

    assert _subset(a) == _subset(b), f"{name}: core≠shim\ncore={_subset(a)}\nshim={_subset(b)}"
    # exit code 계약: fail 이면 2, 아니면 0
    expected_rc = 2 if a["verdict"] == "fail" else 0
    assert r.returncode == expected_rc, f"{name}: exit {r.returncode} != {expected_rc}"


@pytest.mark.parametrize("name,files,head,toggles", CASES, ids=[c[0] for c in CASES])
def test_parity_core_vs_http(name, files, head, toggles, monkeypatch):
    for k, v in toggles.items():
        monkeypatch.setenv(k, v)

    client = _fastapi_client()
    if client is None:
        pytest.skip("FastAPI/clickeye-api import 불가(시스템 python 의존성 미설치) → path c skip")

    a = g.evaluate("main", head, files=files)
    resp = client.post(
        "/api/v1/governance/evaluate",
        json={"base": "main", "head": head, "files": files},
    )
    assert resp.status_code == 200, f"{name}: HTTP {resp.status_code} {resp.text}"
    c = resp.json()
    assert _subset(a) == _subset(c), f"{name}: core≠http\ncore={_subset(a)}\nhttp={_subset(c)}"


def test_master_off_reduced_dict(monkeypatch):
    """마스터 off 시 축약 스키마(governance=off, pass/direct/LOW)를 세 경로에서 확인."""
    monkeypatch.setenv("FLOWOPS_GOVERNANCE", "false")
    head = "ralph/CE-6"
    files = ["clickeye-contracts/protocol/commands.ts"]

    # (a) 커널
    a = g.evaluate("main", head, files=files)
    assert a["governance"] == "off"
    assert a["verdict"] == "pass"
    assert a["merge_decision"] == "direct"
    assert a["tier"] == "LOW"

    # (b) shim CLI
    r = subprocess.run(
        [
            sys.executable, _GATE_SCRIPT,
            "--base", "main", "--head", head,
            "--diff-files", ",".join(files), "--json",
        ],
        capture_output=True, text=True, env=dict(os.environ),
    )
    b = json.loads(r.stdout)
    assert b["governance"] == "off" and b["verdict"] == "pass"
    assert b["merge_decision"] == "direct" and b["tier"] == "LOW"
    assert r.returncode == 0

    # (c) HTTP (설치 시)
    client = _fastapi_client()
    if client is not None:
        resp = client.post(
            "/api/v1/governance/evaluate",
            json={"base": "main", "head": head, "files": files},
        )
        assert resp.status_code == 200, resp.text
        c = resp.json()
        assert c["governance"] == "off" and c["verdict"] == "pass"
        assert c["merge_decision"] == "direct" and c["tier"] == "LOW"


def test_http_files_omitted_equals_empty():
    """HTTP 에서 files 미지정(None) → 커널 files=[] 호출과 동일 판정(git 미접근 불변식)."""
    client = _fastapi_client()
    if client is None:
        pytest.skip("FastAPI/clickeye-api import 불가 → skip")

    head = "ralph/CE-2"
    a = g.evaluate("main", head, files=[])  # 서비스가 files or [] 로 강제하는 값
    resp = client.post(
        "/api/v1/governance/evaluate",
        json={"base": "main", "head": head},  # files 키 자체를 생략
    )
    assert resp.status_code == 200, resp.text
    c = resp.json()
    assert _subset(a) == _subset(c), (
        f"files-omitted core≠http\ncore={_subset(a)}\nhttp={_subset(c)}"
    )


def test_triage_parity_across_paths(monkeypatch):
    """트리아지 ON + 동일 usage 를 3경로에 동일 주입 → 코어 서브셋 + 관측 키 일치.

    (a) 커널 직접  (b) shim CLI --usage-json  (c) HTTP 요청 usage 필드.
    ENFORCE 는 켜지 않는다(순수 관측). 예산 한도를 낮춰 band=review 를 유도.
    """
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE", "on")
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE_BUDGET_COST_WARN", "5")
    head = "ralph/CE-2"
    files = ["clickeye-web/src/app/page.tsx"]
    usage = {"cost": 6.0, "tokens": 100}

    # (a) 커널
    a = g.evaluate("main", head, files=files, usage=usage)
    assert a["triage"] == "review"

    # (b) shim CLI --usage-json
    r = subprocess.run(
        [
            sys.executable, _GATE_SCRIPT,
            "--base", "main", "--head", head,
            "--diff-files", ",".join(files),
            "--usage-json", json.dumps(usage),
            "--json",
        ],
        capture_output=True, text=True, env=dict(os.environ),
    )
    b = json.loads(r.stdout)
    assert _subset(a) == _subset(b), f"core≠shim\ncore={_subset(a)}\nshim={_subset(b)}"
    assert (a["triage"], a["risk_score"]) == (b["triage"], b["risk_score"])

    # (c) HTTP usage 필드
    client = _fastapi_client()
    if client is None:
        pytest.skip("FastAPI/clickeye-api import 불가 → path c skip")
    resp = client.post(
        "/api/v1/governance/evaluate",
        json={"base": "main", "head": head, "files": files, "usage": usage},
    )
    assert resp.status_code == 200, resp.text
    c = resp.json()
    assert _subset(a) == _subset(c), f"core≠http\ncore={_subset(a)}\nhttp={_subset(c)}"
    assert (a["triage"], a["risk_score"]) == (c["triage"], c["risk_score"])


def test_installed_kernel_is_true_editable():
    """governance 가 저장소 루트 원본 소스로 해석되는지(true-editable, SSOT 사본 없음).

    시스템 python(미설치, 저장소 루트를 sys.path 에 얹은 경우)과 uv 설치 환경(editable)
    모두에서 __file__ 은 저장소 루트 원본을 가리켜야 한다.
    """
    import governance

    gov_file = os.path.abspath(governance.__file__)
    expected_dir = os.path.join(_REPO_ROOT, "governance")
    assert gov_file.startswith(expected_dir + os.sep), (
        f"governance.__file__={gov_file} 가 저장소 루트 소스({expected_dir})가 아님 "
        f"→ site-packages 사본(SSOT 위반)일 수 있음"
    )
