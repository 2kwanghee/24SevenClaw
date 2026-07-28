"""제어면 계약 v1 — 서비스 #2 가 자동 생성하는 제어면 YAML 의 검증기 (다프로젝트화 P2).

## 위치와 경계

이 모듈은 판정면 `Policy`(governance/policy.py)의 **형제 값객체**다
(docs/multiproject-delivery.md §3-4 — 판정면 정책과 실행면 제어를 한 객체에 섞으면
커널의 순수성이 깨진다). `policy` 절의 검증은 `Policy.from_dict()` 에 위임하고
여기서 재구현하지 않는다.

stdlib 전용(커널 제약 유지). **YAML 텍스트 파싱은 여기서 하지 않는다** — PyYAML 은
clickeye-api 서비스층의 의존성이고, 이 모듈은 파싱된 dict 만 받는다. 덕분에 파이프라인
스크립트(시스템 python3)도 JSON 미러를 이 검증기로 재검증할 수 있다.

## 신뢰 모델 (D-14, v1)

기계 저작물의 신뢰 근거는 소유권이 아니라 출처 인증이다. v1 에서는:
- **인증**: 수신 채널의 서비스 키(IntakeServiceKey) 인증이 담당한다.
- **무결성**: `content_signature()` — 수신 YAML 원문 바이트의 `sha256:<hex>`.
  `DeliveryProfile.source_signature` 에 저장되어 `source_yaml` 과 재대조 가능하다.
- 비대칭 서명(서버가 원문 키를 저장하지 않으므로 HMAC 검증 불가)은 후속 결정.

## fail-closed

형식 불량은 전부 `ControlPlaneError` — 호출자(API)는 이를 422 + 기계가 소비 가능한
거부 사유로 변환해 서비스 #2 콜백에 싣는다. 알 수 없는 키는 절 안팎을 불문하고 거부한다:
템플릿 오타로 제어 항목이 조용히 무시되는 것이 가장 위험한 실패 모드이기 때문이다.

## 축소 불가 원칙

`auto_stop_conditions` 표준 목록(MANDATORY_AUTO_STOP_CONDITIONS)은 **항상 포함**된다.
서비스 #2 는 조건을 추가할 수만 있고 뺄 수 없다 — 참조 구조(infraeye3 CONTROL.yaml)의
"에이전트가 이 목록을 축소할 수 없다"를 기계 저작자에게도 동일 적용한 것이다.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

from governance.policy import Policy, PolicyError

SUPPORTED_SCHEMA_VERSIONS = ("1.0",)

VALID_TIERS = ("lite", "standard", "enterprise")
VALID_MODES = ("MANUAL", "AUTO", "PAUSED")
VALID_PAUSE_STRATEGIES = ("GRACEFUL", "IMMEDIATE")

# 무인 운전에서도 반드시 정지하는 조건 — 축소 불가(추가만 허용).
MANDATORY_AUTO_STOP_CONDITIONS = (
    "external_data_transmission",
    "cost_incurring_operation",
    "data_deletion_or_irreversible_change",
    "security_policy_change",
    "public_api_or_schema_break",
    "unresolved_requirement_with_large_impact",
    "global_blocking_decision",
    "build_failure",
    "governance_violation",
)

# retry_limits 의 허용 키와 기본값. ticket_retries 는 P1 완주 오케스트레이터
# (FLOWOPS_COMPLETION_MAX_RETRIES)가 이관받는 자리다.
DEFAULT_RETRY_LIMITS: dict[str, int] = {
    "interview_rounds": 3,
    "shard_rework": 3,
    "build_recovery": 3,
    "ticket_retries": 3,
}

DEFAULT_CONCURRENCY: dict[str, int] = {
    "max_parallel_projects": 1,   # P5(다프로젝트 동시 실행) 전까지 1
    "max_parallel_agents": 4,
    "reviewers_per_task": 2,
}

_GATE_KINDS = ("compile", "test", "check")
_GIT_KEYS = ("forbidden", "per_use_approval", "default_branch")
_BLOCKER_KEYS = ("desc", "owner", "blocks", "open")
_PROVENANCE_KEYS = ("template_id", "reason", "generated_by", "generated_at")


class ControlPlaneError(ValueError):
    """제어면 YAML 이 형식 불량이다. 호출자는 422 + 거부 콜백으로 변환한다(fail-closed)."""


def content_signature(yaml_bytes: bytes) -> str:
    """수신 YAML 원문의 콘텐츠 해시 — `sha256:<hex>` (D-14 v1 무결성 근거)."""
    return "sha256:" + hashlib.sha256(yaml_bytes).hexdigest()


def _require_dict(value: Any, *, name: str) -> dict:
    if not isinstance(value, dict):
        raise ControlPlaneError(f"{name}: 객체(mapping)여야 함 (받은 값: {type(value).__name__})")
    return value


def _require_str(value: Any, *, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ControlPlaneError(f"{name}: 비어있지 않은 문자열이어야 함")
    return value


def _require_str_list(value: Any, *, name: str) -> tuple[str, ...]:
    if isinstance(value, str) or not isinstance(value, (list, tuple)):
        raise ControlPlaneError(f"{name}: 문자열 배열이어야 함")
    out: list[str] = []
    for i, v in enumerate(value):
        if not isinstance(v, str) or not v.strip():
            raise ControlPlaneError(f"{name}[{i}]: 비어있지 않은 문자열이어야 함")
        out.append(v)
    return tuple(out)


def _require_positive_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ControlPlaneError(f"{name}: 1 이상의 정수여야 함 (받은 값: {value!r})")
    return value


def _reject_unknown(data: dict, allowed: tuple[str, ...], *, name: str) -> None:
    unknown = sorted(set(data) - set(allowed))
    if unknown:
        raise ControlPlaneError(f"{name}: 알 수 없는 키 {unknown} (허용: {sorted(allowed)})")


@dataclass(frozen=True)
class ControlPlane:
    """검증된 제어면 v1. `DeliveryProfile` 미러와 실행면 소비자가 읽는 형태."""

    schema_version: str
    tier: str = "lite"
    policy: Policy = field(default_factory=Policy.default)
    policy_raw: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)
    mode: str = "MANUAL"
    pause_strategy: str = "GRACEFUL"
    auto_stop_conditions: tuple[str, ...] = MANDATORY_AUTO_STOP_CONDITIONS
    retry_limits: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_RETRY_LIMITS))
    concurrency: dict[str, int] = field(default_factory=lambda: dict(DEFAULT_CONCURRENCY))
    gates: dict[str, tuple[str, ...]] = field(default_factory=dict)
    git_forbidden: tuple[str, ...] = ()
    git_per_use_approval: tuple[str, ...] = ()
    git_default_branch: str = "main"
    blockers: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Any) -> ControlPlane:
        """파싱된 YAML dict → 검증된 ControlPlane. 형식 불량은 `ControlPlaneError`.

        미지정 절은 문서화된 기본값을 승계한다(서비스 #2 가 최소 필드만 채워도 동작).
        알 수 없는 키는 절 안팎 모두 거부한다.
        """
        top = _require_dict(data, name="control_plane")

        allowed_top = (
            "schema_version",
            "provenance",
            "tier",
            "policy",
            "global",
            "auto_stop_conditions",
            "retry_limits",
            "concurrency",
            "gates",
            "git",
            "blockers",
        )
        _reject_unknown(top, allowed_top, name="control_plane")

        # ── schema_version — 유일한 필수 절. 버전 협상의 앵커. ──────────────
        if "schema_version" not in top:
            raise ControlPlaneError("schema_version: 필수 (예: '1.0')")
        version = _require_str(top["schema_version"], name="schema_version")
        if version not in SUPPORTED_SCHEMA_VERSIONS:
            raise ControlPlaneError(
                f"schema_version: 미지원 버전 '{version}' (지원: {list(SUPPORTED_SCHEMA_VERSIONS)})"
            )

        kwargs: dict[str, Any] = {"schema_version": version}

        if "tier" in top:
            tier = _require_str(top["tier"], name="tier")
            if tier not in VALID_TIERS:
                raise ControlPlaneError(f"tier: '{tier}' (허용: {list(VALID_TIERS)})")
            kwargs["tier"] = tier

        if "provenance" in top:
            prov = _require_dict(top["provenance"], name="provenance")
            _reject_unknown(prov, _PROVENANCE_KEYS, name="provenance")
            for k, v in prov.items():
                _require_str(v, name=f"provenance.{k}")
            kwargs["provenance"] = dict(prov)

        # ── policy — 판정면 위임(재구현 금지). PolicyError 는 승격해 한 종류로 통일. ──
        if "policy" in top:
            raw_policy = _require_dict(top["policy"], name="policy")
            try:
                kwargs["policy"] = Policy.from_dict(raw_policy)
            except PolicyError as e:
                raise ControlPlaneError(f"policy: {e}") from e
            kwargs["policy_raw"] = dict(raw_policy)

        if "global" in top:
            g = _require_dict(top["global"], name="global")
            _reject_unknown(g, ("mode", "pause_strategy"), name="global")
            if "mode" in g:
                mode = _require_str(g["mode"], name="global.mode")
                if mode not in VALID_MODES:
                    raise ControlPlaneError(f"global.mode: '{mode}' (허용: {list(VALID_MODES)})")
                kwargs["mode"] = mode
            if "pause_strategy" in g:
                ps = _require_str(g["pause_strategy"], name="global.pause_strategy")
                if ps not in VALID_PAUSE_STRATEGIES:
                    raise ControlPlaneError(
                        f"global.pause_strategy: '{ps}' (허용: {list(VALID_PAUSE_STRATEGIES)})"
                    )
                kwargs["pause_strategy"] = ps

        # ── auto_stop_conditions — 축소 불가: 표준 9종 ∪ 추가분 순서 보존 병합. ──
        if "auto_stop_conditions" in top:
            extra = _require_str_list(top["auto_stop_conditions"], name="auto_stop_conditions")
            merged = list(MANDATORY_AUTO_STOP_CONDITIONS)
            for c in extra:
                if c not in merged:
                    merged.append(c)
            kwargs["auto_stop_conditions"] = tuple(merged)

        if "retry_limits" in top:
            rl = _require_dict(top["retry_limits"], name="retry_limits")
            _reject_unknown(rl, tuple(DEFAULT_RETRY_LIMITS), name="retry_limits")
            limits = dict(DEFAULT_RETRY_LIMITS)
            for k, v in rl.items():
                limits[k] = _require_positive_int(v, name=f"retry_limits.{k}")
            kwargs["retry_limits"] = limits

        if "concurrency" in top:
            cc = _require_dict(top["concurrency"], name="concurrency")
            allowed_cc = (*DEFAULT_CONCURRENCY, "self_review_allowed")
            _reject_unknown(cc, allowed_cc, name="concurrency")
            conc = dict(DEFAULT_CONCURRENCY)
            for k, v in cc.items():
                if k == "self_review_allowed":
                    # 자기승인 금지는 불변 원칙이다 — true 로 켜려는 시도는 거부한다.
                    if v is not False:
                        raise ControlPlaneError(
                            "concurrency.self_review_allowed: false 만 허용 "
                            "(자기승인 금지는 협상 대상이 아니다)"
                        )
                    continue
                conc[k] = _require_positive_int(v, name=f"concurrency.{k}")
            kwargs["concurrency"] = conc

        if "gates" in top:
            gd = _require_dict(top["gates"], name="gates")
            _reject_unknown(gd, _GATE_KINDS, name="gates")
            kwargs["gates"] = {
                k: _require_str_list(v, name=f"gates.{k}") for k, v in gd.items()
            }

        if "git" in top:
            git = _require_dict(top["git"], name="git")
            _reject_unknown(git, _GIT_KEYS, name="git")
            if "forbidden" in git:
                kwargs["git_forbidden"] = _require_str_list(git["forbidden"], name="git.forbidden")
            if "per_use_approval" in git:
                kwargs["git_per_use_approval"] = _require_str_list(
                    git["per_use_approval"], name="git.per_use_approval"
                )
            if "default_branch" in git:
                kwargs["git_default_branch"] = _require_str(
                    git["default_branch"], name="git.default_branch"
                )

        if "blockers" in top:
            bl = _require_dict(top["blockers"], name="blockers")
            blockers: dict[str, dict[str, Any]] = {}
            for bid, entry in bl.items():
                _require_str(bid, name="blockers.<id>")
                e = _require_dict(entry, name=f"blockers.{bid}")
                _reject_unknown(e, _BLOCKER_KEYS, name=f"blockers.{bid}")
                for req in ("desc", "owner"):
                    if req not in e:
                        raise ControlPlaneError(f"blockers.{bid}: '{req}' 필수")
                    _require_str(e[req], name=f"blockers.{bid}.{req}")
                if "blocks" in e:
                    _require_str(e["blocks"], name=f"blockers.{bid}.blocks")
                if "open" in e and not isinstance(e["open"], bool):
                    raise ControlPlaneError(f"blockers.{bid}.open: 불리언이어야 함")
                blockers[bid] = {"open": True, **e}
            kwargs["blockers"] = blockers

        return cls(**kwargs)

    def to_dict(self) -> dict[str, Any]:
        """JSON 직렬화 가능한 미러 형태. `from_dict()` 로 round-trip 가능하다.

        policy 절은 **원본 지정분(policy_raw)** 만 내보낸다 — `Policy.to_dict()` 전체를
        내보내면 미지정 필드가 명시 지정으로 굳어 기본 정책 개선이 이관되지 않는다.
        """
        out: dict[str, Any] = {
            "schema_version": self.schema_version,
            "tier": self.tier,
            "global": {"mode": self.mode, "pause_strategy": self.pause_strategy},
            "auto_stop_conditions": list(self.auto_stop_conditions),
            "retry_limits": dict(self.retry_limits),
            "concurrency": dict(self.concurrency),
        }
        if self.provenance:
            out["provenance"] = dict(self.provenance)
        if self.policy_raw:
            out["policy"] = dict(self.policy_raw)
        if self.gates:
            out["gates"] = {k: list(v) for k, v in self.gates.items()}
        git: dict[str, Any] = {}
        if self.git_forbidden:
            git["forbidden"] = list(self.git_forbidden)
        if self.git_per_use_approval:
            git["per_use_approval"] = list(self.git_per_use_approval)
        if self.git_default_branch != "main":
            git["default_branch"] = self.git_default_branch
        if git:
            out["git"] = git
        if self.blockers:
            out["blockers"] = {k: dict(v) for k, v in self.blockers.items()}
        return out
