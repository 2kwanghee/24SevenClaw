"""LLM 폴백(카탈로그/stub) 경로에서도 프로토타입 정량 지표가 채워지는지 검증.

3단계 위저드 화면의 복잡도/확장성/필요역량 노출은 PrototypeSession 모델의
@property(ui_structure 키 읽기)에 의존한다. LLM generate_ui_structure가 실패해
카탈로그 폴백으로 떨어져도 이 지표들이 비어선 안 된다.
"""

from app.services.prototype_service import (
    _build_proto_from_catalog,
    _default_metrics,
)


def test_default_metrics_has_core_quantitative_fields() -> None:
    m = _default_metrics(0, ["FastAPI", "Next.js", "PostgreSQL", "Redis", "Celery"])
    assert isinstance(m["complexity_score"], int)
    assert 1 <= m["complexity_score"] <= 10
    assert 1 <= m["scalability_score"] <= 10
    # skill_requirements는 tech_stack_tags 상위 4개에서 파생
    assert m["skill_requirements"] == ["FastAPI", "Next.js", "PostgreSQL", "Redis"]
    assert m["estimated_weeks"]["min"] <= m["estimated_weeks"]["max"]
    assert m["team_size"]["min"] <= m["team_size"]["max"]
    assert m["monthly_cost_usd"]["min"] <= m["monthly_cost_usd"]["max"]


def test_default_metrics_fallback_skills_when_no_tech_stack() -> None:
    m = _default_metrics(1, [])
    assert m["skill_requirements"]  # 비어 있지 않은 기본 목록
    assert len(m["skill_requirements"]) >= 1


def test_default_metrics_vary_by_variant_index() -> None:
    # 카드/비교표가 모두 동일값으로 보이지 않도록 variant별 소폭 변주
    scores = {(_default_metrics(i)["complexity_score"],
               _default_metrics(i)["scalability_score"]) for i in range(3)}
    assert len(scores) > 1


def test_build_proto_from_catalog_populates_metrics() -> None:
    catalog_entry = {
        "title": "구독 관리 SaaS",
        "description": "구독 결제/요금제 관리",
        "design_pattern": "dashboard",
        "architecture_pattern": "모놀리식 3-tier",
        "tech_stack_tags": ["FastAPI", "Next.js", "PostgreSQL"],
        "pros": ["빠른 개발"],
        "cons": ["확장 한계"],
        "ui_structure": {"menu_structure": {}},
        "menu_structure": {},
        "color_palette": {},
    }
    proto = _build_proto_from_catalog(
        session_id="00000000-0000-0000-0000-000000000000",
        idx=0,
        catalog_entry=catalog_entry,
        role_config={"is_recommended": True},
        user_tech_stack=[],
    )
    # 모델 @property가 ui_structure에서 읽어 응답 스키마로 노출됨
    assert proto.complexity_score is not None
    assert proto.scalability_score is not None
    assert proto.skill_requirements  # 비어 있지 않음
    assert proto.skill_requirements == ["FastAPI", "Next.js", "PostgreSQL"]


def test_build_proto_from_catalog_none_entry_still_has_metrics() -> None:
    proto = _build_proto_from_catalog(
        session_id="00000000-0000-0000-0000-000000000000",
        idx=2,
        catalog_entry=None,
        role_config={},
        user_tech_stack=["Django"],
    )
    assert proto.complexity_score is not None
    assert proto.scalability_score is not None
    assert proto.skill_requirements


def test_build_proto_from_catalog_preserves_existing_metrics() -> None:
    # 카탈로그 ui_structure에 이미 지표가 있으면 덮어쓰지 않는다(setdefault)
    catalog_entry = {
        "title": "T",
        "tech_stack_tags": ["FastAPI"],
        "ui_structure": {"complexity_score": 9, "skill_requirements": ["기존스킬"]},
    }
    proto = _build_proto_from_catalog(
        session_id="00000000-0000-0000-0000-000000000000",
        idx=0,
        catalog_entry=catalog_entry,
        role_config={},
        user_tech_stack=[],
    )
    assert proto.complexity_score == 9
    assert proto.skill_requirements == ["기존스킬"]
