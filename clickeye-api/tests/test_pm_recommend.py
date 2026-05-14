"""PM 추천 로직 회귀 테스트 — _compute_rule_scores 단위 테스트."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.services.prototype_service import PrototypeService

pytestmark = pytest.mark.no_db


def _make_profile(
    slug: str,
    domain: str,
    specialties: list[str],
    industry_tags: list[str],
    tech_stack_tags: list[str],
) -> Any:
    p = SimpleNamespace()
    p.id = uuid4()
    p.slug = slug
    p.domain = domain
    p.specialties = specialties
    p.industry_tags = industry_tags
    p.tech_stack_tags = tech_stack_tags
    return p


def _make_service() -> PrototypeService:
    """DB 없이 서비스 인스턴스를 생성한다."""
    svc = object.__new__(PrototypeService)
    svc._claude = MagicMock()  # type: ignore[attr-defined]
    svc._claude.recommend_pm_scores.return_value = {}  # 빈 domain 점수 → 기본 40
    return svc  # type: ignore[return-value]


class TestJaccard:
    def test_identical_sets(self) -> None:
        assert PrototypeService._jaccard({"a", "b"}, {"a", "b"}) == pytest.approx(1.0)

    def test_disjoint_sets(self) -> None:
        assert PrototypeService._jaccard({"a"}, {"b"}) == pytest.approx(0.0)

    def test_partial_overlap(self) -> None:
        assert PrototypeService._jaccard({"a", "b"}, {"b", "c"}) == pytest.approx(1 / 3)

    def test_empty_set_a(self) -> None:
        assert PrototypeService._jaccard(set(), {"a"}) == 0.0

    def test_empty_set_b(self) -> None:
        assert PrototypeService._jaccard({"a"}, set()) == 0.0


class TestComputeRuleScoresV2:
    """PM_RECO_V2_ENABLED=true 시나리오."""

    @pytest.fixture()
    def svc(self) -> PrototypeService:
        return _make_service()

    def test_manufacturing_python_session_forge_mech_top(self, svc: PrototypeService) -> None:
        """제조 + Python 세션 → forge-mech가 가장 높은 rule_score."""
        forge_mech = _make_profile(
            "forge-mech", "backend",
            ["IoT", "MES", "Python", "FastAPI"],
            ["manufacturing"],
            ["Python", "FastAPI", "MQTT", "PostgreSQL"],
        )
        fin_shield = _make_profile(
            "fin-shield", "security",
            ["PCI-DSS", "MyData", "KYC"],
            ["finance"],
            ["Java", "Spring", "Redis"],
        )
        atlas = _make_profile(
            "atlas", "fullstack",
            ["web", "mobile"],
            [],  # 범용 PM
            ["React", "Node.js", "TypeScript"],
        )
        profiles = [forge_mech, fin_shield, atlas]
        metrics_by_pm: dict[Any, Any] = {}

        with patch("app.config.settings") as mock_settings:
            mock_settings.pm_reco_v2_enabled = True
            result = svc._compute_rule_scores(
                profiles,
                design_pattern="backend",
                context_text="제조 IoT MES",
                metrics_by_pm=metrics_by_pm,
                user_industry="manufacturing",
                user_tech_stack=["Python", "FastAPI"],
            )

        scores = {p.slug: result[p.id]["rule_score"] for p in profiles}
        assert scores["forge-mech"] > scores["fin-shield"], (
            f"forge-mech({scores['forge-mech']:.1f}) should beat "
            f"fin-shield({scores['fin-shield']:.1f})"
        )
        assert scores["forge-mech"] > scores["atlas"], (
            f"forge-mech({scores['forge-mech']:.1f}) should beat atlas({scores['atlas']:.1f})"
        )

    def test_finance_security_session_fin_shield_top3(self, svc: PrototypeService) -> None:
        """금융 + 보안 세션 → fin-shield가 상위 점수 달성."""
        fin_shield = _make_profile(
            "fin-shield", "security",
            ["PCI-DSS", "MyData", "KYC", "security", "compliance"],
            ["finance"],
            ["Java", "Spring", "Redis", "Vault"],
        )
        forge_mech = _make_profile(
            "forge-mech", "backend",
            ["IoT", "MES", "Python"],
            ["manufacturing"],
            ["Python", "MQTT"],
        )
        edu_spark = _make_profile(
            "edu-spark", "frontend",
            ["LMS", "SCORM", "React"],
            ["education"],
            ["React", "TypeScript"],
        )
        profiles = [fin_shield, forge_mech, edu_spark]
        metrics_by_pm: dict[Any, Any] = {}

        with patch("app.config.settings") as mock_settings:
            mock_settings.pm_reco_v2_enabled = True
            result = svc._compute_rule_scores(
                profiles,
                design_pattern="security",
                context_text="금융 PCI-DSS KYC compliance",
                metrics_by_pm=metrics_by_pm,
                user_industry="finance",
                user_tech_stack=["Java", "Spring"],
            )

        scores = {p.slug: result[p.id]["rule_score"] for p in profiles}
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top3_slugs = [slug for slug, _ in ranked[:3]]
        assert "fin-shield" in top3_slugs, (
            f"fin-shield should be in top-3, got ranking: {ranked}"
        )

    def test_no_tag_match_still_returns_result(self, svc: PrototypeService) -> None:
        """태그 미매칭 시에도 모든 PM에 대해 결과가 반환된다 (회귀 방지)."""
        atlas = _make_profile("atlas", "fullstack", ["web"], [], [])
        pixel = _make_profile("pixel", "frontend", ["ui", "design"], ["media"], ["React"])
        profiles = [atlas, pixel]
        metrics_by_pm: dict[Any, Any] = {}

        with patch("app.config.settings") as mock_settings:
            mock_settings.pm_reco_v2_enabled = True
            result = svc._compute_rule_scores(
                profiles,
                design_pattern="unknown-pattern",
                context_text="xyz",
                metrics_by_pm=metrics_by_pm,
                user_industry="healthcare",
                user_tech_stack=["Rust"],
            )

        assert len(result) == 2, "모든 PM에 대해 점수가 반환되어야 한다"
        for p in profiles:
            assert "rule_score" in result[p.id]
            assert "dimension_scores" in result[p.id]
            assert "match_reasons" in result[p.id]

    def test_dimension_scores_and_match_reasons_populated(self, svc: PrototypeService) -> None:
        """v2 활성화 시 dimension_scores, match_reasons 필드가 올바르게 채워진다."""
        forge_mech = _make_profile(
            "forge-mech", "backend",
            ["IoT", "Python"],
            ["manufacturing"],
            ["Python", "FastAPI"],
        )
        profiles = [forge_mech]
        metrics_by_pm: dict[Any, Any] = {}

        with patch("app.config.settings") as mock_settings:
            mock_settings.pm_reco_v2_enabled = True
            result = svc._compute_rule_scores(
                profiles,
                design_pattern="backend",
                context_text="IoT",
                metrics_by_pm=metrics_by_pm,
                user_industry="manufacturing",
                user_tech_stack=["Python", "FastAPI"],
            )

        info = result[forge_mech.id]
        dim = info["dimension_scores"]
        reasons = info["match_reasons"]

        assert set(dim.keys()) == {"domain", "specialty", "industry", "stack", "metric"}
        assert dim["industry"] == 100  # 완전 매칭
        assert dim["stack"] > 0  # Python, FastAPI 모두 매칭 → Jaccard > 0
        assert any("산업" in r for r in reasons)
        assert any("스택" in r for r in reasons)


class TestComputeRuleScoresV1:
    """PM_RECO_V2_ENABLED=false (기본) 시나리오 — 기존 로직 유지 확인."""

    @pytest.fixture()
    def svc(self) -> PrototypeService:
        return _make_service()

    def test_v1_industry_binary_scoring(self, svc: PrototypeService) -> None:
        """v1 모드: 업종 매칭 시 100, 미매칭 시 30."""
        matching_pm = _make_profile("m", "backend", [], ["manufacturing"], [])
        other_pm = _make_profile("o", "backend", [], ["finance"], [])
        profiles = [matching_pm, other_pm]
        metrics_by_pm: dict[Any, Any] = {}

        with patch("app.config.settings") as mock_settings:
            mock_settings.pm_reco_v2_enabled = False
            result = svc._compute_rule_scores(
                profiles,
                design_pattern="backend",
                context_text="",
                metrics_by_pm=metrics_by_pm,
                user_industry="manufacturing",
            )

        assert result[matching_pm.id]["industry"] == pytest.approx(100.0)
        assert result[other_pm.id]["industry"] == pytest.approx(30.0)
