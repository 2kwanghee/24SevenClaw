"""제어면 계약 v1(ControlPlane) 테스트 (다프로젝트화 P2, D-14).

검증 축:
  1. 최소 입력 — schema_version 만으로 성립, 나머지는 문서화된 기본값 승계
     (서비스 #2 가 최소 필드만 채워도 동작해야 한다).
  2. 축소 불가 — auto_stop_conditions 표준 9종은 무엇을 보내도 항상 포함.
     자기승인 금지(self_review_allowed)는 true 로 켤 수 없다.
  3. fail-closed — 알 수 없는 키(절 안팎)·타입 불량·미지원 버전은 전부 ControlPlaneError.
     템플릿 오타로 제어 항목이 조용히 무시되는 것이 가장 위험한 실패 모드다.
  4. policy 위임 — 판정면 검증은 Policy.from_dict 가 수행하고 PolicyError 는
     ControlPlaneError 로 승격된다(호출자가 한 종류만 처리).
  5. round-trip — to_dict → from_dict 동일. 미러(DeliveryProfile) 저장의 전제.
  6. content_signature — sha256 콘텐츠 해시(D-14 v1 무결성 근거).

Usage:
    cd ClickEye && pytest scripts/tests/test_governance_control.py -v
"""

from __future__ import annotations

import hashlib
import os
import sys

import pytest

_SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(_SCRIPTS_DIR)

try:  # noqa: SIM105
    import governance  # noqa: F401
except ImportError:
    if _REPO_ROOT not in sys.path:
        sys.path.insert(0, _REPO_ROOT)

from governance.control import (  # noqa: E402
    DEFAULT_CONCURRENCY,
    DEFAULT_RETRY_LIMITS,
    MANDATORY_AUTO_STOP_CONDITIONS,
    ControlPlane,
    ControlPlaneError,
    content_signature,
)
from governance.policy import Policy  # noqa: E402

MINIMAL = {"schema_version": "1.0"}


# ── 1. 최소 입력·기본값 승계 ─────────────────────────────────────────────────


def test_minimal_input_inherits_documented_defaults():
    cp = ControlPlane.from_dict(MINIMAL)
    assert cp.schema_version == "1.0"
    assert cp.tier == "lite"
    assert cp.mode == "MANUAL"                      # 무인이어도 초기 기본은 보수적
    assert cp.pause_strategy == "GRACEFUL"
    assert cp.auto_stop_conditions == MANDATORY_AUTO_STOP_CONDITIONS
    assert cp.retry_limits == DEFAULT_RETRY_LIMITS
    assert cp.concurrency == DEFAULT_CONCURRENCY
    assert cp.git_default_branch == "main"
    assert cp.blockers == {}
    # policy 미지정 → live 기본 정책(Policy.default 와 동일 의미)
    assert cp.policy.live is True


def test_schema_version_is_required():
    with pytest.raises(ControlPlaneError, match="schema_version"):
        ControlPlane.from_dict({})


@pytest.mark.parametrize("bad", ["0.9", "2.0", "v1", ""])
def test_unsupported_schema_version_rejected(bad):
    payload = {"schema_version": bad} if bad else {"schema_version": "  "}
    with pytest.raises(ControlPlaneError):
        ControlPlane.from_dict(payload)


# ── 2. 축소 불가 원칙 ────────────────────────────────────────────────────────


def test_auto_stop_conditions_cannot_be_reduced():
    """서비스 #2 가 1개만 보내도 표준 9종이 전부 포함된다 — 추가만 가능, 축소 불가."""
    cp = ControlPlane.from_dict(
        {"schema_version": "1.0", "auto_stop_conditions": ["custom_condition"]}
    )
    for mandatory in MANDATORY_AUTO_STOP_CONDITIONS:
        assert mandatory in cp.auto_stop_conditions
    assert "custom_condition" in cp.auto_stop_conditions
    # 중복 전송은 병합에서 흡수된다
    cp2 = ControlPlane.from_dict(
        {"schema_version": "1.0", "auto_stop_conditions": ["build_failure"]}
    )
    assert list(cp2.auto_stop_conditions).count("build_failure") == 1


def test_self_review_cannot_be_enabled():
    """자기승인 금지는 협상 대상이 아니다 — true 는 거부, false 명시는 허용."""
    with pytest.raises(ControlPlaneError, match="self_review_allowed"):
        ControlPlane.from_dict(
            {"schema_version": "1.0", "concurrency": {"self_review_allowed": True}}
        )
    cp = ControlPlane.from_dict(
        {"schema_version": "1.0", "concurrency": {"self_review_allowed": False}}
    )
    assert cp.concurrency == DEFAULT_CONCURRENCY


# ── 3. fail-closed ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "bad,fragment",
    [
        ([], "control_plane"),                                        # dict 아님
        ({"schema_version": "1.0", "oops": 1}, "알 수 없는 키"),        # 최상위 오타
        ({"schema_version": "1.0", "global": {"mod": "AUTO"}}, "알 수 없는 키"),  # 절 내부 오타
        ({"schema_version": "1.0", "global": {"mode": "YOLO"}}, "global.mode"),
        ({"schema_version": "1.0", "global": {"pause_strategy": "NOW"}}, "pause_strategy"),
        ({"schema_version": "1.0", "tier": "enterprise-x"}, "tier"),
        ({"schema_version": "1.0", "retry_limits": {"ticket_retries": 0}}, "1 이상"),
        ({"schema_version": "1.0", "retry_limits": {"ticket_retries": True}}, "1 이상"),
        ({"schema_version": "1.0", "retry_limits": {"unknown_limit": 3}}, "알 수 없는 키"),
        ({"schema_version": "1.0", "concurrency": {"max_parallel_agents": -1}}, "1 이상"),
        ({"schema_version": "1.0", "gates": {"deploy": ["x"]}}, "알 수 없는 키"),
        ({"schema_version": "1.0", "gates": {"test": "npm test"}}, "배열"),
        ({"schema_version": "1.0", "git": {"forbidden": [""]}}, "git.forbidden"),
        ({"schema_version": "1.0", "provenance": {"who": "svc2"}}, "알 수 없는 키"),
        ({"schema_version": "1.0", "provenance": {"template_id": 3}}, "provenance.template_id"),
        ({"schema_version": "1.0", "blockers": {"B-1": {"owner": "운영팀"}}}, "desc"),
        ({"schema_version": "1.0", "blockers": {"B-1": {"desc": "d", "owner": "o", "open": "yes"}}}, "불리언"),
        ({"schema_version": "1.0", "auto_stop_conditions": "build_failure"}, "배열"),
    ],
)
def test_fail_closed(bad, fragment):
    with pytest.raises(ControlPlaneError, match=fragment):
        ControlPlane.from_dict(bad)


# ── 4. policy 위임 ──────────────────────────────────────────────────────────


def test_policy_section_delegates_to_policy_from_dict():
    cp = ControlPlane.from_dict(
        {
            "schema_version": "1.0",
            "policy": {"high_prefixes": ["infra/"], "issue_key_shape": r"^(TASK)-\d+$"},
        }
    )
    assert isinstance(cp.policy, Policy)
    assert cp.policy.live is False                     # 명시 정책은 static(env 미조회)
    assert cp.policy.high_prefixes == ("infra/",)
    assert cp.policy_raw == {"high_prefixes": ["infra/"], "issue_key_shape": r"^(TASK)-\d+$"}


def test_policy_error_is_promoted_to_control_plane_error():
    """호출자(API 422 변환)는 ControlPlaneError 한 종류만 처리하면 된다."""
    with pytest.raises(ControlPlaneError, match="policy"):
        ControlPlane.from_dict({"schema_version": "1.0", "policy": {"typo_key": 1}})
    with pytest.raises(ControlPlaneError, match="policy"):
        ControlPlane.from_dict(
            {"schema_version": "1.0", "policy": {"issue_key_shape": "[bad"}}
        )


# ── 5. round-trip ───────────────────────────────────────────────────────────

FULL = {
    "schema_version": "1.0",
    "tier": "enterprise",
    "provenance": {"template_id": "legacy-modernize-v2", "generated_by": "service-2"},
    "policy": {"high_prefixes": ["infra/", "db/migration/"]},
    "global": {"mode": "AUTO", "pause_strategy": "IMMEDIATE"},
    "auto_stop_conditions": ["ddl_missing"],
    "retry_limits": {"ticket_retries": 5},
    "concurrency": {"max_parallel_agents": 8, "reviewers_per_task": 2},
    "gates": {"compile": ["./gradlew build -x test"], "check": ["./gradlew check"]},
    "git": {"forbidden": ["push --force", "add -A"], "default_branch": "develop"},
    "blockers": {"B-1": {"desc": "DDL 미확보", "owner": "운영팀", "blocks": "baseline", "open": True}},
}


def test_round_trip_full_payload():
    cp = ControlPlane.from_dict(FULL)
    mirrored = ControlPlane.from_dict(cp.to_dict())
    assert cp.to_dict() == mirrored.to_dict()
    # 대표 값 스팟 체크
    assert mirrored.tier == "enterprise"
    assert mirrored.mode == "AUTO"
    assert mirrored.retry_limits["ticket_retries"] == 5
    assert mirrored.retry_limits["shard_rework"] == 3          # 미지정 키는 기본 유지
    assert mirrored.git_default_branch == "develop"
    assert "ddl_missing" in mirrored.auto_stop_conditions
    assert mirrored.blockers["B-1"]["open"] is True


def test_to_dict_exports_only_specified_policy():
    """policy 는 원본 지정분만 내보낸다 — 전체 Policy.to_dict 를 내보내면 미지정 필드가
    명시 지정으로 굳어 기본 정책 개선이 미러에 이관되지 않는다."""
    cp = ControlPlane.from_dict(
        {"schema_version": "1.0", "policy": {"high_prefixes": ["infra/"]}}
    )
    assert cp.to_dict()["policy"] == {"high_prefixes": ["infra/"]}
    # policy 미지정이면 키 자체가 없다
    assert "policy" not in ControlPlane.from_dict(MINIMAL).to_dict()


def test_blockers_default_open_true():
    cp = ControlPlane.from_dict(
        {"schema_version": "1.0", "blockers": {"B-2": {"desc": "d", "owner": "o"}}}
    )
    assert cp.blockers["B-2"]["open"] is True


# ── 6. content_signature ────────────────────────────────────────────────────


def test_content_signature_is_prefixed_sha256():
    raw = b"schema_version: '1.0'\n"
    sig = content_signature(raw)
    assert sig == "sha256:" + hashlib.sha256(raw).hexdigest()
    # 원문 1바이트 변화 → 다른 서명 (source_yaml 재대조의 근거)
    assert content_signature(raw + b" ") != sig
