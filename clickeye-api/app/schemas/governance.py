"""거버넌스 게이트 HTTP 스키마.

커널(governance.core.evaluate)의 입력/출력을 그대로 옮긴다. 로직은 없다.
응답은 마스터 off 시 축약 스키마도 허용해야 하므로 permissive(extra allow)로 둔다.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# ── 정책 출처 값(policy_source) ──────────────────────────────────────────────
# project_id 로 정책을 주입할 때, 실제로 무엇이 적용됐는지 응답에 드러내기 위한 값.
# 폴백(프로파일 미등록·DB 미주입)을 조용히 숨기지 않는 것이 목적이다.
POLICY_SOURCE_PROFILE = "project_profile"  # DeliveryProfile.policy 적용(static, env 무시)
POLICY_SOURCE_NO_PROFILE = "default_no_profile"  # 프로파일 미등록 → 기본 정책 폴백
POLICY_SOURCE_NO_DB = "default_no_db"  # DB 세션 미주입 → 조회 불가, 기본 정책 폴백


class GovernanceEvaluateRequest(BaseModel):
    base: str = "main"
    head: str
    # 원격 HTTP 호출자는 git 접근이 없으므로 변경 파일을 명시적으로 넘긴다.
    files: list[str] | None = None
    # plan-trace 검사용 본문(선택). 없으면 원격에서는 skip(비블로킹).
    plan_text: str | None = None
    # ── 프로젝트 식별(선택) ──────────────────────────────────────────────────
    # 두 가지 용도를 겸한다(둘 다 project_id 미지정 시 기존 동작 그대로):
    #  1) 정책 주입(다프로젝트화 P0): DeliveryProfile.policy → Policy.from_dict() → 커널.
    #     프로파일 미등록이면 기본 정책 폴백(응답 policy_source 로 명시).
    #  2) 트리아지 예산(항목 G, opt-in): 서비스가 원장(LlmLedgerService)으로 usage 를
    #     구성해 커널에 주입한다. usage 를 직접 주면 그 값이 우선(원장 조회 skip).
    #     둘 다 없으면 usage=None → 예산 skip(비블로킹, 하위호환).
    project_id: UUID | None = None
    usage: dict[str, Any] | None = None
    metrics: dict[str, Any] | None = None
    # ── team→project 역매핑(P1.6, 선택·하위호환) ─────────────────────────────
    # 파이프라인/웹훅 호출자는 project_id 를 모르고 Linear team_id 만 안다. project_id
    # 미지정 + 이 값이 있으면 서비스가 project_linear_credentials 로 역매핑해 **KB
    # 인제스트 용도로만** 사용한다(위 project_id 의 트리아지 예산(usage 조회) 축에는
    # 불개입 — 기존 로직 불변).
    linear_team_id: str | None = None


class GovernanceEvaluateResponse(BaseModel):
    """evaluate() 반환 dict 형식화. 축약(off)/전체(on)/트리아지 스키마를 모두 수용."""

    governance: str
    verdict: str
    tier: str
    merge_decision: str
    failures: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    issue_key: str | None = None
    checks: dict[str, Any] = Field(default_factory=dict)
    risk_reasons: list[str] = Field(default_factory=list)
    changed_files: int | None = None
    # ── 트리아지 관측 키(트리아지 opt-in 시에만 채워짐; 기본 미포함) ──────────────
    # 전부 기본 None → 엔드포인트의 response_model_exclude_none=True 로 off 시 응답에서 제외.
    # (triage_reasons 도 [] 대신 None 기본이어야 off 응답에 빈 리스트가 새지 않음.)
    triage: str | None = None
    risk_score: float | None = None
    triage_reasons: list[str] | None = None
    budget: dict[str, Any] | None = None
    # ── 정책 출처(다프로젝트화 P0) ────────────────────────────────────────────
    # project_id 를 준 경우에만 채워진다(미지정이면 None → exclude_none 으로 응답 제외 →
    # 기존 호출자 응답 바이트 불변). 값은 POLICY_SOURCE_* 상수 참조 — 프로파일 미등록
    # 폴백을 조용히 숨기지 않기 위한 관측 키다.
    policy_source: str | None = None

    model_config = {"extra": "allow"}


# ── 정책 조회(GET /governance/policy) ────────────────────────────────────────
# 커널 policy_summary() 반환 dict 를 그대로 형식화한다. 로직 없음(읽기 전용 노출).
class GovernanceGateRule(BaseModel):
    """단일 머지-게이트 룰의 요약."""

    key: str
    label: str
    mode: str  # "block"(차단) | "warn"(권고)
    enabled: bool


class GovernanceHighRisk(BaseModel):
    """고위험(HIGH) 분류 기준 — 직접머지 금지·PR 강등 대상."""

    prefixes: list[str]
    patterns: list[str]


class GovernancePolicyResponse(BaseModel):
    """전역 머지-게이트 정책 요약. 커널(governance.core.policy_summary)의 SSOT 노출."""

    governance_enabled: bool
    gate_rules: list[GovernanceGateRule]
    high_risk: GovernanceHighRisk
    # 토글명 → 현재 상태(bool). API 서버 프로세스 env 기준(source_note 참조).
    toggles: dict[str, bool]
    risk_demote_to_pr: bool
    source_note: str
    # ── 어댑터 전용 필드(커널 policy_summary() 키 아님) ──────────────────────────
    # project_id 쿼리로 프로젝트 정책을 요청한 경우에만 채워진다(미지정이면 None →
    # 엔드포인트 exclude_none 으로 응답 제외 → 기존 응답 키셋 불변). POLICY_SOURCE_* 참조.
    policy_source: str | None = None
