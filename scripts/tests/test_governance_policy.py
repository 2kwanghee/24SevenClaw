"""거버넌스 정책 외부화(`governance.policy.Policy`) 테스트 — 다프로젝트화 P0.

## 무엇을 지키는 테스트인가

`evaluate()` 는 원래부터 순수함수였으나 **정책**(계약면 경로·고위험 경로·이슈 키 형태·
토글·임계값)만은 모듈 상수와 `os.environ` 에 묶여 있었다. `Policy` 가 그 결합을 끊는다.
이 파일은 그 리팩터링이 지켜야 할 7개 불변식을 축별로 단언한다:

| 축 | 불변식 | 깨지면 |
|---|---|---|
| 1 | 정책 미주입 == `Policy.default()` 주입 (**전체 dict 동일**) | P0 수용기준 위반(회귀) |
| 2 | core 재노출 상수 == policy `DEFAULT_*`, shim 레거시 심볼 전량 생존 | 상수 드리프트·호출부 파손 |
| 3 | static 정책은 서버 `os.environ` 을 **읽지 않는다** | 프로젝트 간 정책 누출 |
| 4 | live 정책은 조회마다 env **재독**(스냅샷 금지) | 장기 실행 API 서버 동작 변화 |
| 5 | 주입한 정책이 실제 판정을 바꾼다 | 정책이 장식품(무시됨) |
| 6 | 부분 지정은 DEFAULT 승계, `to_dict`↔`from_dict` round-trip | DB 왕복에서 정책 손실 |
| 7 | 형식 불량 정책은 `PolicyError`(fail-closed), 단 D-4 범위는 명시적 정책에만 | 오타로 정책 무음 무시 |

Usage:
    cd ClickEye && pytest scripts/tests/test_governance_policy.py -v
"""

from __future__ import annotations

import os
import re
import sys

import pytest

_SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

# 커널은 저장소 루트의 governance 패키지에 단일 존재(SSOT). cwd 무관하게 import 되도록
# 저장소 루트(=scripts 의 상위)를 sys.path 에 추가한다. 기존 테스트 관례와 동일.
_REPO_ROOT = os.path.dirname(_SCRIPTS_DIR)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from governance import core as g  # noqa: E402
from governance import policy as gp  # noqa: E402
from governance.policy import Policy, PolicyError  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_toggles(monkeypatch):
    """모든 FLOWOPS_GOVERNANCE* 토글 제거 → 기본 on 상태에서 시작.

    이 픽스처가 없으면 개발자 셸/CI 의 토글이 새어 들어와 판정이 환경 의존이 된다.
    (기존 test_governance_parity.py / test_pre_merge_gate.py 와 동일한 관례.)
    """
    for k in list(os.environ):
        if k.startswith("FLOWOPS_GOVERNANCE"):
            monkeypatch.delenv(k, raising=False)
    yield


# ── infraeye3 프로파일 초안 ────────────────────────────────────────────────────
# "정책이 진짜 외부화되었는가"를 증명하려면 ClickEye 와 **경로·키 형태가 겹치지 않는**
# 제2 프로파일로 판정이 갈리는 것을 보여야 한다. 아래는 Spring/Flyway/MyBatis 스택인
# infraeye3 의 정책 초안이다(축 5 에서 사용).
INFRAEYE3_POLICY = {
    "contract_surface_prefixes": ["backend/src/main/java/", "backend/src/main/resources/mapper/"],
    "openapi_spec": "contracts/openapi.yaml",
    "generated_client_prefix": "frontend/src/api/generated/",
    "contracts_prefix": "contracts/",
    "high_prefixes": ["backend/src/main/resources/db/migration/", "infra/"],
    "high_path_patterns": [r"auth", r"(privilege|priv_|role_menu)"],
    "issue_key_shape": r"^(TASK|CYCLE)-[A-Z0-9]+-\d+$",
    "issue_key_search": r"(TASK|CYCLE)-[A-Z0-9]+-\d+",
}


# ═══════════════════════════════════════════════════════════════════════════════
# 축 1 — 회귀 0 (P0 최우선 수용기준)
# ═══════════════════════════════════════════════════════════════════════════════
# 정책 주입 리팩터링의 유일한 실패 모드는 "기존 호출부의 판정이 미묘하게 달라지는 것"이다.
# 코어 4키 서브셋만 비교하면 checks[].detail 문자열이나 risk_reasons 순서가 바뀌어도
# 통과해 버린다 — 파이프라인 로그·CI 어노테이션·HTTP 응답 스키마가 모두 그 dict 를 그대로
# 소비하므로 **전체 dict `==`** 로 비교한다.

# (이름, files, head, 토글env, usage, metrics)
_PARITY_CASES = [
    (
        # HIGH 강등 경로: contracts 변경 + generated 동반 → 드리프트 통과, merge=pr
        "high_pr",
        [
            "clickeye-contracts/protocol/commands.ts",
            "clickeye-contracts/generated/typescript/types.gen.ts",
        ],
        "ralph/CE-3",
        {},
        None,
        None,
    ),
    (
        # 블로킹 경로: 계약면 변경에 openapi.json 미동반 → verdict=fail
        "block_contract_drift",
        ["clickeye-api/app/api/v1/auth.py"],
        "ralph/CE-5",
        {},
        None,
        None,
    ),
    (
        # 정상 직접머지 경로(가장 흔한 케이스)
        "direct_low",
        ["clickeye-web/src/app/page.tsx"],
        "ralph/CE-2",
        {},
        None,
        None,
    ),
    (
        # 마스터 off → 축약 스키마로 단락. 키 집합 자체가 다른 분기이므로 별도 커버 필요.
        "master_off",
        ["clickeye-contracts/protocol/commands.ts"],
        "ralph/CE-6",
        {"FLOWOPS_GOVERNANCE": "false"},
        None,
        None,
    ),
    (
        # 슬래시 없는 브랜치 → 이슈 키 None → ticket_ref skip (issue_key=None 직렬화 경로)
        "branch_without_slash_skips_ticket",
        ["clickeye-web/src/app/page.tsx"],
        "main",
        {},
        None,
        None,
    ),
    (
        # 슬래시 있고 키 형태 불량 → ticket_ref fail. detail 에 정책 정규식이 삽입되므로
        # 정책 객체를 잘못 읽으면 문자열이 갈린다(전체 dict 비교가 잡는다).
        "malformed_issue_key_blocks",
        ["clickeye-web/src/app/page.tsx"],
        "ralph/bad_key",
        {},
        None,
        None,
    ),
    (
        # 개별 토글 off → skip detail 문자열 경로
        "contract_toggle_off",
        ["clickeye-api/app/api/v1/auth.py"],
        "ralph/CE-7",
        {"FLOWOPS_GOVERNANCE_CONTRACT": "false"},
        None,
        None,
    ),
    (
        # 위험강등 off → HIGH 인데도 direct 유지
        "risk_demote_off",
        [
            "clickeye-contracts/protocol/commands.ts",
            "clickeye-contracts/generated/typescript/types.gen.ts",
        ],
        "ralph/CE-8",
        {"FLOWOPS_GOVERNANCE_RISK_DEMOTE": "false"},
        None,
        None,
    ),
    (
        # ticket 토글 off → 형태 불량 키여도 skip(차단 안 됨)
        "ticket_toggle_off",
        ["clickeye-web/src/app/page.tsx"],
        "ralph/bad_key",
        {"FLOWOPS_GOVERNANCE_TICKET": "false"},
        None,
        None,
    ),
    (
        # trace 토글 off → plan_trace skip detail 이 project_dir 사유가 아닌 토글 사유
        "trace_toggle_off",
        ["clickeye-web/src/app/page.tsx"],
        "ralph/CE-12",
        {"FLOWOPS_GOVERNANCE_TRACE": "false"},
        None,
        None,
    ),
    (
        # 트리아지 report-only + review 밴드: usage(예산)와 metrics(커버리지/diff)를 모두
        # 주입해 관측 키(triage/risk_score/budget/triage_reasons)까지 동일성 범위에 넣는다.
        "triage_review_band",
        ["clickeye-web/src/app/page.tsx"],
        "ralph/CE-2",
        {"FLOWOPS_GOVERNANCE_TRIAGE": "on", "FLOWOPS_GOVERNANCE_TRIAGE_BUDGET_COST_WARN": "5"},
        {"cost": 6.0, "tokens": 100},
        {"coverage": 0.5, "diff_lines": 500},
    ),
    (
        # 트리아지 ENFORCE: band=block → verdict/merge 강등 + 합성 failure 문자열까지 동일해야 함
        "triage_enforce_block",
        [
            "clickeye-contracts/protocol/commands.ts",
            "clickeye-contracts/generated/typescript/types.gen.ts",
        ],
        "ralph/CE-9",
        {"FLOWOPS_GOVERNANCE_TRIAGE": "on", "FLOWOPS_GOVERNANCE_TRIAGE_ENFORCE": "on"},
        None,
        {"coverage": 0.5, "diff_lines": 500},
    ),
]


@pytest.mark.parametrize(
    "name,files,head,toggles,usage,metrics", _PARITY_CASES, ids=[c[0] for c in _PARITY_CASES]
)
def test_no_policy_equals_default_policy_full_dict(
    name, files, head, toggles, usage, metrics, monkeypatch
):
    """정책 미주입 결과 == `Policy.default()` 주입 결과 (**전체 dict 동일**).

    P0 의 최우선 수용기준. `evaluate()` 내부의 `pol = policy or Policy.default()` 가
    두 경로를 하나로 수렴시켜야 한다. 4키 서브셋이 아니라 전체 비교인 이유는
    checks[].detail / risk_reasons / triage_reasons 까지 소비자(파이프라인 로그·CI·HTTP
    응답)가 그대로 쓰기 때문이다.
    """
    for k, v in toggles.items():
        monkeypatch.setenv(k, v)

    implicit = g.evaluate("main", head, files=files, usage=usage, metrics=metrics)
    explicit = g.evaluate(
        "main", head, files=files, usage=usage, metrics=metrics, policy=Policy.default()
    )

    assert implicit == explicit, (
        f"{name}: 정책 미주입 ≠ default() 주입 (회귀)\n"
        f"implicit={implicit}\nexplicit={explicit}"
    )


def test_parity_cases_actually_exercise_distinct_verdicts():
    """축 1 케이스가 실제로 서로 다른 분기를 밟는지 확인(동일성 테스트의 자기 점검).

    모든 케이스가 우연히 같은 판정(예: 전부 direct/pass)이면 위 동일성 단언은 아무것도
    보증하지 않는다. block/pr/direct 와 governance off 분기가 모두 등장해야 한다.
    """
    seen = set()
    for _name, files, head, toggles, usage, metrics in _PARITY_CASES:
        prev = {k: os.environ.get(k) for k in toggles}
        try:
            os.environ.update(toggles)
            r = g.evaluate("main", head, files=files, usage=usage, metrics=metrics)
        finally:
            for k, v in prev.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        seen.add((r.get("governance"), r["merge_decision"], r["verdict"]))

    decisions = {d for _, d, _ in seen}
    assert {"block", "pr", "direct"} <= decisions, f"분기 커버리지 부족: {seen}"
    assert any(gov == "off" for gov, _, _ in seen), f"마스터 off 분기 미커버: {seen}"


@pytest.mark.parametrize(
    "toggles",
    [
        {},
        {"FLOWOPS_GOVERNANCE": "false"},
        {"FLOWOPS_GOVERNANCE_CONTRACT": "false", "FLOWOPS_GOVERNANCE_TRACE": "false"},
        {"FLOWOPS_GOVERNANCE_RISK_DEMOTE": "false"},
        {"FLOWOPS_GOVERNANCE_TRIAGE": "on", "FLOWOPS_GOVERNANCE_TRIAGE_ENFORCE": "on"},
    ],
    ids=["all_default", "master_off", "contract_trace_off", "demote_off", "triage_enforce_on"],
)
def test_policy_summary_no_policy_equals_default(toggles, monkeypatch):
    """`policy_summary()` 도 미주입 == `default()` 주입 (HTTP `GET /governance/policy` 회귀 0).

    이 dict 는 웹 콘솔이 그대로 렌더하므로 gate_rules 순서·source_note 문자열까지 같아야 한다.
    """
    for k, v in toggles.items():
        monkeypatch.setenv(k, v)
    assert g.policy_summary() == g.policy_summary(Policy.default())


# ═══════════════════════════════════════════════════════════════════════════════
# 축 2 — 재노출 정합 (드리프트 방지 + 레거시 호출부 보존)
# ═══════════════════════════════════════════════════════════════════════════════

# (core 심볼명, policy 의 DEFAULT_* 값) — 값 비교 가능한 8개 중 6개.
# 정규식 2개는 pattern 문자열로 별도 비교한다(compile 객체는 flags 도 봐야 함).
_REEXPORTED_SCALARS = [
    ("CONTRACT_SURFACE_PREFIXES", gp.DEFAULT_CONTRACT_SURFACE_PREFIXES),
    ("OPENAPI_SPEC", gp.DEFAULT_OPENAPI_SPEC),
    ("GENERATED_CLIENT_PREFIX", gp.DEFAULT_GENERATED_CLIENT_PREFIX),
    ("CONTRACTS_PREFIX", gp.DEFAULT_CONTRACTS_PREFIX),
    ("HIGH_PREFIXES", gp.DEFAULT_HIGH_PREFIXES),
]


@pytest.mark.parametrize("attr,expected", _REEXPORTED_SCALARS, ids=[a for a, _ in _REEXPORTED_SCALARS])
def test_core_reexports_match_policy_defaults(attr, expected):
    """core 의 하위호환 상수가 policy 의 `DEFAULT_*` 와 값이 동일해야 한다.

    core.py 는 이 상수들을 `Policy.default()` 에서 파생시키므로 원리상 어긋날 수 없다.
    그러나 누군가 core.py 에 리터럴을 되살려 넣으면(과거 코드 복원 등) 판정은 policy 를,
    문서/로그는 core 를 보게 되어 **조용한 이중관리**가 발생한다. 그걸 잡는다.
    """
    assert getattr(g, attr) == expected


def test_core_reexported_regexes_match_policy_defaults():
    """정규식 재노출은 패턴 문자열 + flags 까지 policy 기본값과 일치해야 한다."""
    assert [p.pattern for p in g.HIGH_PATH_PATTERNS] == list(
        gp.DEFAULT_HIGH_PATH_PATTERN_SOURCES
    )
    # 고위험 경로 패턴은 대소문자 무시여야 한다(Auth/AUTH 도 HIGH).
    for p in g.HIGH_PATH_PATTERNS:
        assert p.flags & re.IGNORECASE, f"{p.pattern}: IGNORECASE 누락"
    assert g.ISSUE_KEY_RE.pattern == gp.DEFAULT_ISSUE_KEY_SHAPE
    assert g.ISSUE_KEY_SEARCH_RE.pattern == gp.DEFAULT_ISSUE_KEY_SEARCH


def test_core_triage_threshold_reexports_match_policy():
    """core 의 트리아지 임계 기본값 재노출이 policy 의 dict 와 일치해야 한다."""
    assert (
        gp.TRIAGE_THRESHOLD_DEFAULTS["FLOWOPS_GOVERNANCE_TRIAGE_SCORE_REVIEW"]
        == g.TRIAGE_SCORE_REVIEW_DEFAULT
    )
    assert (
        gp.TRIAGE_THRESHOLD_DEFAULTS["FLOWOPS_GOVERNANCE_TRIAGE_SCORE_BLOCK"]
        == g.TRIAGE_SCORE_BLOCK_DEFAULT
    )


# scripts/pre_merge_gate.py 는 얇은 shim 이며 `import pre_merge_gate as g; g.evaluate(...)`
# 형태의 레거시 호출부(파이프라인 보조 스크립트·수동 디버깅)를 계속 지원해야 한다.
_LEGACY_SHIM_SYMBOLS = [
    "CONTRACTS_PREFIX",
    "CONTRACT_SURFACE_PREFIXES",
    "GENERATED_CLIENT_PREFIX",
    "HIGH_PATH_PATTERNS",
    "HIGH_PREFIXES",
    "ISSUE_KEY_RE",
    "ISSUE_KEY_SEARCH_RE",
    "OPENAPI_SPEC",
    "assess_budget",
    "assess_rate",
    "check_contract_drift",
    "check_plan_trace",
    "check_ticket_ref",
    "classify_risk",
    "compute_risk_score",
    "evaluate",
    "extract_issue_key",
    "get_changed_files",
    "is_enabled",
    "is_opt_in",
    "policy_summary",
    "triage_band",
]


@pytest.mark.parametrize("symbol", _LEGACY_SHIM_SYMBOLS)
def test_shim_reexports_legacy_symbol(symbol):
    """레거시 심볼이 shim 에서 전량 살아 있어야 한다(호출부 파손 방지)."""
    import pre_merge_gate as shim

    assert hasattr(shim, symbol), f"pre_merge_gate.{symbol} 소실 → 레거시 호출부 파손"


def test_shim_reexports_new_policy_symbols():
    """신규 `Policy`/`PolicyError` 도 shim 을 통해 접근 가능해야 한다.

    shim 은 `from governance.core import *` 로 재노출하므로 core.__all__ 에 신규 심볼을
    넣는 것을 잊으면 여기서 드러난다.
    """
    import pre_merge_gate as shim

    assert shim.Policy is Policy
    assert shim.PolicyError is PolicyError


def test_shim_covers_core_all():
    """core.__all__ 전체가 shim 에 노출되는지(별표 import 계약)."""
    import pre_merge_gate as shim

    missing = [s for s in g.__all__ if not hasattr(shim, s)]
    assert not missing, f"shim 미노출 심볼: {missing}"


def test_legacy_positional_calls_still_work():
    """policy 가 **키워드 전용**으로 추가되었으므로 위치 인자 레거시 호출은 무변경이어야 한다.

    `check_contract_drift(files)` 뒤에 policy 를 위치 인자로 끼워 넣었다면 조용히
    시그니처가 깨졌을 것이다. 실제 레거시 호출 형태로 확인한다.
    """
    import pre_merge_gate as shim

    assert shim.classify_risk(["clickeye-infra/x.yml"])["tier"] == "HIGH"
    assert shim.check_ticket_ref("CE-1")["status"] == "pass"
    assert shim.check_contract_drift(["clickeye-api/app/api/v1/x.py"])["status"] == "fail"
    assert shim.extract_issue_key("ralph/CE-123") == "CE-123"
    assert shim.evaluate("main", "ralph/CE-2", ["clickeye-web/src/app/page.tsx"])[
        "merge_decision"
    ] == "direct"


# ═══════════════════════════════════════════════════════════════════════════════
# 축 3 — 토글 격리 (다프로젝트화의 핵심 불변식)
# ═══════════════════════════════════════════════════════════════════════════════
# static 정책이 서버 프로세스 env 를 폴백으로 읽으면, 한 프로젝트의 토글이 다른 프로젝트
# 판정에 새어 들어간다. FastAPI 한 프로세스가 N개 프로젝트를 판정하는 P4 구조에서는
# 치명적이다. static 은 env 를 **절대** 조회하지 않아야 한다.


def test_static_policy_ignores_env_toggle(monkeypatch):
    """env 에 CONTRACT=false 가 있어도 static 정책은 그 토글을 True(기본 의미)로 본다."""
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_CONTRACT", "false")
    static = Policy.from_dict({})
    assert static.live is False
    assert static.enabled("FLOWOPS_GOVERNANCE_CONTRACT") is True
    # 대조: live 정책은 env 를 읽는다
    assert Policy.default().enabled("FLOWOPS_GOVERNANCE_CONTRACT") is False


def test_static_policy_ignores_env_master_toggle(monkeypatch):
    """마스터 토글도 예외가 아니다 — env 로 거버넌스를 끌 수 없어야 한다(static)."""
    monkeypatch.setenv("FLOWOPS_GOVERNANCE", "false")
    assert Policy.from_dict({}).enabled("FLOWOPS_GOVERNANCE") is True
    assert Policy.default().enabled("FLOWOPS_GOVERNANCE") is False


def test_env_toggle_leak_does_not_reach_static_verdict(monkeypatch):
    """격리가 **판정에도** 반영되는지: env off 여도 static 정책은 계약 드리프트를 차단한다.

    `enabled()` 만 격리되고 `evaluate()` 가 여전히 모듈 상수/env 를 읽는다면 이 테스트만
    실패한다(격리 구멍 탐지).
    """
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_CONTRACT", "false")
    files = ["clickeye-api/app/api/v1/auth.py"]

    static = g.evaluate("main", "ralph/CE-20", files=files, policy=Policy.from_dict({}))
    assert static["checks"]["contract_drift"]["status"] == "fail"
    assert static["merge_decision"] == "block"
    assert static["verdict"] == "fail"

    # 대조: 정책 미주입(live)은 env 를 읽어 skip → 차단하지 않음.
    # (이 파일은 `auth` 고위험 패턴에도 걸리므로 tier=HIGH → merge=pr 이다. 요점은
    #  "block 이 아니다" 이며, 차단 여부가 정책 출처에 따라 갈리는 것을 보여준다.)
    live = g.evaluate("main", "ralph/CE-20", files=files)
    assert live["checks"]["contract_drift"]["status"] == "skip"
    assert live["verdict"] == "pass"
    assert live["merge_decision"] == "pr"
    assert live["failures"] == []


def test_static_policy_opt_in_toggle_defaults_off(monkeypatch):
    """opt-in 토글(트리아지)은 static 에서 미지정 = off — env 에 on 이 있어도 켜지지 않는다.

    켜지면 결과 dict 에 `triage` 등 신규 키가 생겨 다른 프로젝트의 응답 스키마가 오염된다.
    """
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE", "on")
    static = Policy.from_dict({})
    assert static.opt_in("FLOWOPS_GOVERNANCE_TRIAGE") is False

    r = g.evaluate(
        "main", "ralph/CE-21", files=["clickeye-web/src/app/page.tsx"], policy=static
    )
    assert "triage" not in r, f"static 정책에 트리아지 누출: {sorted(r)}"
    assert "risk_score" not in r

    # 대조: 정책 미주입(live)은 env 를 읽어 트리아지가 켜진다
    live = g.evaluate("main", "ralph/CE-21", files=["clickeye-web/src/app/page.tsx"])
    assert live["triage"] == "auto"


def test_static_policy_opt_in_explicit_on_works():
    """static 에서 명시적으로 켜면 켜진다(격리가 '항상 off' 는 아님)."""
    static = Policy.from_dict({"toggles": {"FLOWOPS_GOVERNANCE_TRIAGE": True}})
    assert static.opt_in("FLOWOPS_GOVERNANCE_TRIAGE") is True
    r = g.evaluate(
        "main", "ralph/CE-22", files=["clickeye-web/src/app/page.tsx"], policy=static
    )
    assert r["triage"] == "auto" and "risk_score" in r


def test_static_policy_ignores_env_thresholds(monkeypatch):
    """임계값도 격리: static 은 env 를 무시하고 기본값(또는 명시된 값)을 쓴다."""
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE_SCORE_REVIEW", "0.99")
    key = "FLOWOPS_GOVERNANCE_TRIAGE_SCORE_REVIEW"

    assert Policy.from_dict({}).threshold(key) == pytest.approx(0.40)
    assert Policy.from_dict({"triage_thresholds": {key: 0.55}}).threshold(key) == pytest.approx(
        0.55
    )
    # 대조: live 는 env 를 읽는다
    assert Policy.default().threshold(key) == pytest.approx(0.99)


# ═══════════════════════════════════════════════════════════════════════════════
# 축 4 — 스냅샷 시점 (live 는 재독, 캐시 금지)
# ═══════════════════════════════════════════════════════════════════════════════
# 현행 `check_*` 는 호출마다 os.environ 을 읽는다. Policy 를 값객체로 옮기면서 생성 시점에
# 토글을 동결하면, 장기 실행 API 서버(프로세스 시작 시 Policy 생성)에서 env 변경이 반영되지
# 않아 오늘의 동작과 달라진다 = 회귀.


def test_live_policy_rereads_env_toggle(monkeypatch):
    """live 정책은 **생성 후** env 변경을 따라간다(토글 스냅샷 금지)."""
    pol = Policy.default()
    assert pol.enabled("FLOWOPS_GOVERNANCE_CONTRACT") is True
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_CONTRACT", "false")
    assert pol.enabled("FLOWOPS_GOVERNANCE_CONTRACT") is False, "live 정책이 토글을 캐시했다"
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_CONTRACT", "on")
    assert pol.enabled("FLOWOPS_GOVERNANCE_CONTRACT") is True


def test_live_policy_rereads_env_opt_in(monkeypatch):
    """opt-in 토글도 재독되어야 한다."""
    pol = Policy.default()
    assert pol.opt_in("FLOWOPS_GOVERNANCE_TRIAGE") is False
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_TRIAGE", "on")
    assert pol.opt_in("FLOWOPS_GOVERNANCE_TRIAGE") is True


def test_live_policy_rereads_env_threshold(monkeypatch):
    """임계값도 재독되어야 한다(예산 한도 핫리로드 경로)."""
    pol = Policy.default()
    key = "FLOWOPS_GOVERNANCE_TRIAGE_BUDGET_COST_LIMIT"
    assert pol.threshold(key) == pytest.approx(0.0)
    monkeypatch.setenv(key, "12.5")
    assert pol.threshold(key) == pytest.approx(12.5), "live 정책이 임계값을 캐시했다"


def test_live_policy_reread_changes_verdict(monkeypatch):
    """재독이 판정까지 흘러가는지: 같은 Policy 인스턴스로 두 번 평가하면 결과가 달라져야 한다."""
    pol = Policy.default()
    files = ["clickeye-api/app/api/v1/auth.py"]
    assert g.evaluate("main", "ralph/CE-30", files=files, policy=pol)["verdict"] == "fail"
    monkeypatch.setenv("FLOWOPS_GOVERNANCE_CONTRACT", "false")
    assert g.evaluate("main", "ralph/CE-30", files=files, policy=pol)["verdict"] == "pass"


# ═══════════════════════════════════════════════════════════════════════════════
# 축 5 — 정책 효력 (주입한 정책이 무시되지 않는가)
# ═══════════════════════════════════════════════════════════════════════════════
# 축 1(회귀 0)만 통과하고 축 5 가 실패하면 Policy 는 장식품이다 — 판정은 여전히 모듈 상수를
# 읽는다는 뜻. 두 축은 반드시 함께 통과해야 한다.


@pytest.fixture
def infraeye3() -> Policy:
    return Policy.from_dict(INFRAEYE3_POLICY)


def test_custom_contract_surface_detects_drift(infraeye3):
    """커스텀 계약면(Spring 컨트롤러) 단독 변경 → 드리프트 fail."""
    r = g.check_contract_drift(
        ["backend/src/main/java/com/x/api/DeviceController.java"], policy=infraeye3
    )
    assert r["status"] == "fail"
    assert "DeviceController" in r["detail"]


def test_custom_contract_surface_with_spec_passes(infraeye3):
    """커스텀 스펙(contracts/openapi.yaml) 동반 → pass."""
    r = g.check_contract_drift(
        [
            "backend/src/main/java/com/x/api/DeviceController.java",
            "contracts/openapi.yaml",
        ],
        policy=infraeye3,
    )
    assert r["status"] == "pass"


def test_same_file_passes_under_default_policy():
    """**판정이 갈린다**: 같은 파일이 기본(ClickEye) 정책에서는 계약면이 아니므로 pass.

    이것이 정책 외부화의 존재 이유다. 기본 정책에서도 fail 이면 경로 prefix 가 어딘가에
    하드코딩돼 있다는 뜻이다.
    """
    r = g.check_contract_drift(["backend/src/main/java/com/x/api/DeviceController.java"])
    assert r["status"] == "pass"
    assert r["detail"] == "계약면 변경 없음"


def test_custom_issue_key_shape_and_search(infraeye3):
    """3세그먼트 이슈 키(TASK-GATE-001)를 커스텀 정책이 추출·검증한다."""
    assert g.extract_issue_key("ralph/TASK-GATE-001", policy=infraeye3) == "TASK-GATE-001"
    assert g.check_ticket_ref("TASK-GATE-001", policy=infraeye3)["status"] == "pass"
    assert g.extract_issue_key("feature/device/CYCLE-20260726-00", policy=infraeye3) == (
        "CYCLE-20260726-00"
    )


def test_same_issue_key_fails_under_default_policy():
    """**판정이 갈린다**: 같은 키가 기본 정책 shape `^[A-Z0-9]+-\\d+$` 에서는 fail.

    이슈 키 정규식을 모듈 상수로 두면 안 되는 이유. 덤으로 기본 탐색 정규식은
    `TASK-GATE-001` 에서 부분 매치 `GATE-001` 을 뽑아버린다 — 프로젝트 정책을 주입하지
    않으면 **틀린 키로 조용히 통과**할 수 있다는 뜻이므로 함께 못박는다.
    """
    assert g.check_ticket_ref("TASK-GATE-001")["status"] == "fail"
    assert g.extract_issue_key("ralph/TASK-GATE-001") == "GATE-001"


def test_custom_high_prefix_demotes_to_pr(infraeye3):
    """커스텀 고위험 prefix(Flyway 마이그레이션) → tier HIGH + merge_decision pr."""
    files = ["backend/src/main/resources/db/migration/V1_5_0__baseline.sql"]
    assert g.classify_risk(files, policy=infraeye3)["tier"] == "HIGH"

    r = g.evaluate("main", "ralph/TASK-GATE-001", files=files, policy=infraeye3)
    assert r["tier"] == "HIGH"
    assert r["verdict"] == "pass"
    assert r["merge_decision"] == "pr"
    assert r["issue_key"] == "TASK-GATE-001"


@pytest.mark.parametrize(
    "path",
    [
        "backend/src/main/java/com/x/service/RoleMenuPrivilegeService.java",  # privilege
        "backend/src/main/resources/mapper/role_menu_priv_mapper.xml",       # role_menu
        "backend/src/main/java/com/x/auth/JwtFilter.java",                   # auth
        "backend/src/main/java/com/x/dao/priv_dao.java",                     # priv_
    ],
)
def test_custom_high_patterns_match(path, infraeye3):
    """커스텀 고위험 정규식(auth / privilege|priv_|role_menu)이 실제로 적용된다."""
    assert g.classify_risk([path], policy=infraeye3)["tier"] == "HIGH"


def test_custom_policy_does_not_inherit_clickeye_high_prefixes(infraeye3):
    """ClickEye 고위험 경로는 이 정책에서 LOW — 기본값이 남아 있으면 오탐이 된다."""
    assert g.classify_risk(["clickeye-infra/docker/x.yml"], policy=infraeye3)["tier"] == "LOW"
    assert g.classify_risk(["clickeye-contracts/protocol/x.ts"], policy=infraeye3)["tier"] == "LOW"
    # 대조: 기본 정책에서는 둘 다 HIGH
    assert g.classify_risk(["clickeye-infra/docker/x.yml"])["tier"] == "HIGH"


def test_infraeye3_draft_misses_camelcase_priv_abbreviation(infraeye3):
    """⚠️ 초안 정규식의 알려진 공백: `priv_` 는 언더스코어를 요구하므로 CamelCase
    `RoleMenuPrivService.java` 는 매치되지 않아 LOW 로 분류된다.

    프로덕션 버그가 아니라 **정책 데이터(프로파일 초안)의 커버리지 문제**다. 판정 권위는
    주입된 정규식이므로 커널은 정확히 지시받은 대로 동작한다. 실제 infraeye3 프로파일을
    확정할 때 `priv` 또는 `Priv` 를 패턴에 추가해야 함을 이 테스트가 기록한다.
    """
    r = g.classify_risk(
        ["backend/src/main/java/com/x/service/RoleMenuPrivService.java"], policy=infraeye3
    )
    assert r["tier"] == "LOW"


def test_policy_summary_exposes_injected_policy(infraeye3):
    """`policy_summary(pol)` 이 주입 정책을 노출하고 source_note 가 live/static 을 구분한다.

    웹 콘솔이 "이 프로젝트의 고위험 경로"를 보여주려면 이 값이 정본이어야 한다.
    """
    s = g.policy_summary(infraeye3)
    assert s["high_risk"]["prefixes"] == [
        "backend/src/main/resources/db/migration/",
        "infra/",
    ]
    assert s["high_risk"]["patterns"] == [r"auth", r"(privilege|priv_|role_menu)"]
    # static 요약은 "주입된 프로젝트 정책(DeliveryProfile) 기준" 임을 명시한다
    assert "DeliveryProfile" in s["source_note"], s["source_note"]
    # live 요약은 "API 서버 env 기준값" 문구로 구분된다(둘을 혼동하면 관측이 거짓 보고가 된다)
    assert "API 서버 env" in g.policy_summary(Policy.default())["source_note"]


# ═══════════════════════════════════════════════════════════════════════════════
# 축 6 — 부분 지정 승계 / 직렬화
# ═══════════════════════════════════════════════════════════════════════════════
# DeliveryProfile.policy 는 보통 몇 필드만 오버라이드한다. 미지정 필드가 None/빈값으로
# 덮이면 계약면 검사가 조용히 무력화된다(가장 위험한 실패 모드).


def test_partial_policy_inherits_defaults():
    """일부 필드만 지정 → 나머지는 DEFAULT 승계, live 는 False."""
    pol = Policy.from_dict({"high_prefixes": ["infra/"]})
    assert pol.high_prefixes == ("infra/",)
    assert pol.live is False
    # 미지정 필드는 기본 정책 그대로
    assert pol.contract_surface_prefixes == gp.DEFAULT_CONTRACT_SURFACE_PREFIXES
    assert pol.openapi_spec == gp.DEFAULT_OPENAPI_SPEC
    assert pol.generated_client_prefix == gp.DEFAULT_GENERATED_CLIENT_PREFIX
    assert pol.contracts_prefix == gp.DEFAULT_CONTRACTS_PREFIX
    assert pol.issue_key_re.pattern == gp.DEFAULT_ISSUE_KEY_SHAPE
    assert pol.issue_key_search_re.pattern == gp.DEFAULT_ISSUE_KEY_SEARCH
    assert [p.pattern for p in pol.high_path_patterns] == list(
        gp.DEFAULT_HIGH_PATH_PATTERN_SOURCES
    )
    # 승계된 계약면 검사가 여전히 작동해야 한다(무력화 방지)
    assert g.check_contract_drift(["clickeye-api/app/api/v1/x.py"], policy=pol)["status"] == "fail"


def test_from_dict_none_is_live_default():
    """`from_dict(None)`(프로파일에 정책 미설정) → live 기본 정책."""
    pol = Policy.from_dict(None)
    assert pol.live is True
    assert pol.high_prefixes == gp.DEFAULT_HIGH_PREFIXES
    assert pol == Policy.default()


def test_from_dict_empty_is_static_default():
    """`from_dict({})` → 값은 DEFAULT 와 같지만 **static**(env 미조회)."""
    pol = Policy.from_dict({})
    assert pol.live is False
    assert pol.high_prefixes == gp.DEFAULT_HIGH_PREFIXES
    assert pol.to_dict() == Policy.default().to_dict()


@pytest.mark.parametrize(
    "data",
    [
        INFRAEYE3_POLICY,
        {},
        {"high_prefixes": ["infra/"]},
        {
            "toggles": {"FLOWOPS_GOVERNANCE_CONTRACT": False},
            "triage_thresholds": {"FLOWOPS_GOVERNANCE_TRIAGE_SCORE_REVIEW": 0.6},
        },
    ],
    ids=["infraeye3", "empty", "partial", "toggles_thresholds"],
)
def test_to_dict_from_dict_round_trip(data):
    """`to_dict()` → `from_dict()` round-trip 동일 (DB 왕복에서 정책 손실 없음)."""
    pol = Policy.from_dict(data)
    again = Policy.from_dict(pol.to_dict())
    assert again.to_dict() == pol.to_dict()
    assert again.live is False
    # 판정 동일성까지 확인 — 직렬화 손실은 결국 판정 차이로 드러난다
    files = ["backend/src/main/java/com/x/api/DeviceController.java", "clickeye-infra/x.yml"]
    assert g.evaluate("main", "ralph/CE-40", files=files, policy=pol) == g.evaluate(
        "main", "ralph/CE-40", files=files, policy=again
    )


def test_to_dict_is_json_serializable():
    """`to_dict()` 산출물은 JSON 직렬화 가능해야 한다(DeliveryProfile 컬럼 저장)."""
    import json

    payload = json.dumps(Policy.from_dict(INFRAEYE3_POLICY).to_dict())
    assert Policy.from_dict(json.loads(payload)).to_dict() == Policy.from_dict(
        INFRAEYE3_POLICY
    ).to_dict()


@pytest.mark.parametrize(
    "raw,expected",
    [
        (True, True),
        (False, False),
        ("on", True),
        ("true", True),
        ("1", True),
        ("yes", True),
        ("false", False),
        ("off", False),
        ("0", False),
        ("no", False),
        ("  ON  ", True),
    ],
    ids=lambda v: repr(v),
)
def test_toggle_accepts_bool_and_env_style_strings(raw, expected):
    """토글 값은 불리언과 env 문자열 표기('on'/'false') 둘 다 수용해야 한다.

    프로파일 JSON 을 사람이 손으로 쓰거나 .env 를 그대로 복사해 넣는 경로가 실제로 있다.
    """
    pol = Policy.from_dict({"toggles": {"FLOWOPS_GOVERNANCE_CONTRACT": raw}})
    assert pol.enabled("FLOWOPS_GOVERNANCE_CONTRACT") is expected


@pytest.mark.parametrize("raw", [0.6, "0.6", 1, "1"], ids=["float", "str_float", "int", "str_int"])
def test_threshold_accepts_numeric_and_numeric_string(raw):
    """임계값은 숫자와 숫자 문자열을 모두 수용(JSON/env 혼용 경로)."""
    key = "FLOWOPS_GOVERNANCE_TRIAGE_SCORE_REVIEW"
    assert Policy.from_dict({"triage_thresholds": {key: raw}}).threshold(key) == pytest.approx(
        float(raw)
    )


def test_policy_is_frozen():
    """Policy 는 frozen dataclass — 판정 중 변형되면 프로젝트 간 오염이 발생한다."""
    pol = Policy.from_dict({})
    with pytest.raises(Exception):  # noqa: B017 - FrozenInstanceError(dataclasses)
        pol.openapi_spec = "x"  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════════════════════
# 축 7 — fail-closed (D-4)
# ═══════════════════════════════════════════════════════════════════════════════
# 형식 불량 정책을 "무시하고 기본값으로 진행"하면, 오타 하나로 프로젝트 정책이 조용히
# 사라지고 게이트는 통과한다(fail-open). 명시적으로 주어진 정책이 깨졌다면 반드시 던진다.

_BAD_POLICIES = [
    # 컨테이너 형식
    ("list_not_dict", []),
    ("str_not_dict", "{}"),
    ("int_not_dict", 3),
    # 오타로 정책이 조용히 무시되는 것 방지
    ("unknown_key", {"high_prefix": ["infra/"]}),
    ("unknown_key_typo_toggles", {"toggle": {}}),
    # 문자열 배열 필드
    ("high_prefixes_str", {"high_prefixes": "infra/"}),
    ("high_prefixes_dict", {"high_prefixes": {"a": 1}}),
    ("high_prefixes_empty_elem", {"high_prefixes": ["infra/", ""]}),
    ("high_prefixes_blank_elem", {"high_prefixes": ["   "]}),
    ("high_prefixes_non_str_elem", {"high_prefixes": ["infra/", 7]}),
    ("high_prefixes_none_elem", {"high_prefixes": [None]}),
    ("contract_surface_str", {"contract_surface_prefixes": "backend/"}),
    # 문자열 필드
    ("openapi_spec_empty", {"openapi_spec": ""}),
    ("openapi_spec_blank", {"openapi_spec": "   "}),
    ("openapi_spec_non_str", {"openapi_spec": 3}),
    ("openapi_spec_none", {"openapi_spec": None}),
    ("generated_prefix_empty", {"generated_client_prefix": ""}),
    ("contracts_prefix_non_str", {"contracts_prefix": ["contracts/"]}),
    # 정규식 컴파일
    ("bad_regex_high_pattern", {"high_path_patterns": ["("]}),
    ("bad_regex_high_pattern_repeat", {"high_path_patterns": ["*"]}),
    ("bad_regex_issue_key_shape", {"issue_key_shape": "([A-Z"}),
    ("bad_regex_issue_key_search", {"issue_key_search": "a{2,1}"}),
    # 토글
    ("toggles_not_dict", {"toggles": []}),
    ("toggles_empty_key", {"toggles": {"": True}}),
    ("toggles_unparsable_str", {"toggles": {"FLOWOPS_GOVERNANCE_CONTRACT": "maybe"}}),
    ("toggles_non_bool", {"toggles": {"FLOWOPS_GOVERNANCE_CONTRACT": 3}}),
    ("toggles_none", {"toggles": {"FLOWOPS_GOVERNANCE_CONTRACT": None}}),
    ("toggles_list_value", {"toggles": {"FLOWOPS_GOVERNANCE_CONTRACT": [True]}}),
    # 임계값
    ("thresholds_not_dict", {"triage_thresholds": []}),
    ("thresholds_empty_key", {"triage_thresholds": {"": 1}}),
    ("thresholds_non_numeric_str", {"triage_thresholds": {"K": "abc"}}),
    ("thresholds_bool", {"triage_thresholds": {"K": True}}),
    ("thresholds_none", {"triage_thresholds": {"K": None}}),
    ("thresholds_list", {"triage_thresholds": {"K": [1]}}),
]


@pytest.mark.parametrize("name,data", _BAD_POLICIES, ids=[n for n, _ in _BAD_POLICIES])
def test_from_dict_rejects_malformed_policy(name, data):
    """형식 불량 정책은 `PolicyError`(fail-closed) — 조용한 기본값 폴백 금지."""
    with pytest.raises(PolicyError):
        Policy.from_dict(data)  # type: ignore[arg-type]


def test_policy_error_is_value_error():
    """`PolicyError` 는 `ValueError` 하위 — 기존 `except ValueError` 어댑터가 그대로 잡는다."""
    assert issubclass(PolicyError, ValueError)
    with pytest.raises(ValueError):
        Policy.from_dict({"unknown": 1})


def test_unknown_key_error_lists_allowed_keys():
    """오타 진단 가능성: 알 수 없는 키 오류가 허용 키 목록을 담아야 한다."""
    with pytest.raises(PolicyError) as ei:
        Policy.from_dict({"high_prefix": ["infra/"]})
    msg = str(ei.value)
    assert "high_prefix" in msg
    assert "high_prefixes" in msg and "issue_key_shape" in msg


def test_d4_scope_unset_env_still_means_on():
    """**D-4 적용 범위 축소**: fail-closed 는 *명시적으로 주어진 정책*에만 적용된다.

    정책 미주입 경로의 "미설정=on"(is_enabled) / "미설정=off"(is_opt_in) 의미는 P0 에서
    불변이다 — 그것을 바꾸는 것 자체가 파이프라인 전체 회귀이기 때문이다. 제어면을 DB 로
    승격하는 P4 단계에서 티어별로 전환한다. 이 테스트는 그 경계를 못박는다.
    """
    assert g.is_enabled("FLOWOPS_GOVERNANCE_ANYTHING_UNSET") is True
    assert g.is_opt_in("FLOWOPS_GOVERNANCE_ANYTHING_UNSET") is False
    assert Policy.default().enabled("FLOWOPS_GOVERNANCE_ANYTHING_UNSET") is True
    assert Policy.default().opt_in("FLOWOPS_GOVERNANCE_ANYTHING_UNSET") is False


def test_d4_scope_unset_threshold_falls_back_deterministically(monkeypatch):
    """임계값 파싱 불가(env 오타)는 기존과 동일하게 기본값 폴백 — 여기서 던지면 회귀다.

    env 는 사람이 손으로 쓰는 면이라 게이트를 크래시시키면 파이프라인이 멈춘다. D-4 는
    DB 정책(구조화 입력)에만 적용한다.
    """
    key = "FLOWOPS_GOVERNANCE_TRIAGE_SCORE_REVIEW"
    monkeypatch.setenv(key, "not-a-number")
    assert Policy.default().threshold(key) == pytest.approx(0.40)
