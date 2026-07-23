"""ClaudeService 단위 테스트.

실제 API 호출 없이 anthropic 클라이언트를 mock하여 테스트한다.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from anthropic.types import TextBlock

from app.services.claude_service import ClaudeService  # noqa: E402

# ── 공통 픽스처 ────────────────────────────────────────────────────────────────


@pytest.fixture
def service() -> ClaudeService:
    return ClaudeService()


def _make_message(content: dict[str, Any]) -> MagicMock:
    """anthropic Message 응답 mock을 생성한다.

    content 리스트에 실제 TextBlock 인스턴스를 사용하여
    isinstance(block, TextBlock) 체크를 통과하게 한다.
    """
    block = TextBlock(type="text", text=json.dumps(content, ensure_ascii=False))
    msg = MagicMock()
    msg.content = [block]
    return msg


# ── 규칙 기반 동기 메서드 ─────────────────────────────────────────────────────


class TestAnalyzeInput:
    def test_saas_keyword(self, service: ClaudeService) -> None:
        assert service.analyze_input("SaaS 구독 서비스를 만들고 싶습니다") == "saas"

    def test_api_keyword(self, service: ClaudeService) -> None:
        assert service.analyze_input("REST API 서버가 필요합니다") == "rest-api"

    def test_fullstack_keyword(self, service: ClaudeService) -> None:
        assert service.analyze_input("풀스택 애플리케이션") == "fullstack"

    def test_internal_tool_keyword(self, service: ClaudeService) -> None:
        assert service.analyze_input("내부 관리 대시보드") == "internal-tool"

    def test_mvp_keyword(self, service: ClaudeService) -> None:
        assert service.analyze_input("MVP 프로토타입이 필요합니다") == "mvp"

    def test_default_fallback(self, service: ClaudeService) -> None:
        assert service.analyze_input("특이한 프로젝트 설명") == "fullstack"


class TestRecommendPmScores:
    def test_saas_preferred_specialties(self, service: ClaudeService) -> None:
        scores = service.recommend_pm_scores("saas", ["product", "backend"])
        assert scores["product"] >= 60
        assert scores["backend"] == 40

    def test_unknown_type_uses_custom_affinity(self, service: ClaudeService) -> None:
        scores = service.recommend_pm_scores("unknown", ["product"])
        assert scores["product"] >= 60


# ── Claude API 비동기 메서드 ──────────────────────────────────────────────────


class TestAnalyzeSolution:
    @pytest.mark.asyncio
    async def test_returns_structured_json(self, service: ClaudeService) -> None:
        expected = {
            "solution_type": "saas",
            "features": ["사용자 인증", "구독 관리"],
            "tech_stack": {
                "frontend": "next.js",
                "backend": "fastapi",
                "database": "postgresql",
                "auth": "jwt",
                "deployment": "docker",
            },
            "complexity": "medium",
            "target_users": "중소기업 팀",
            "key_requirements": ["다중 테넌트", "결제 연동"],
        }

        with patch.object(service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=_make_message(expected))
            mock_get_client.return_value = mock_client

            result = await service.analyze_solution(
                "SaaS 구독 서비스를 만들고 싶습니다",
                {"industry": "tech", "size": "small"},
            )

        assert result["solution_type"] == "saas"
        assert "사용자 인증" in result["features"]
        assert result["complexity"] == "medium"

    @pytest.mark.asyncio
    async def test_fallback_on_invalid_json(self, service: ClaudeService) -> None:
        """Claude가 유효하지 않은 JSON을 반환하면 규칙 기반 폴백을 사용한다."""
        block = TextBlock(type="text", text="죄송합니다, JSON이 아닌 텍스트입니다.")
        msg = MagicMock()
        msg.content = [block]

        with patch.object(service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=msg)
            mock_get_client.return_value = mock_client

            result = await service.analyze_solution("SaaS 서비스 설명", {})

        # 폴백은 규칙 기반으로 solution_type 추출
        assert result["solution_type"] == "saas"
        assert "features" in result

    @pytest.mark.asyncio
    async def test_passes_correct_context(self, service: ClaudeService) -> None:
        """org_context가 user_content에 포함되는지 확인한다."""
        expected = {
            "solution_type": "fullstack",
            "features": [],
            "tech_stack": {},
            "complexity": "low",
            "target_users": "",
            "key_requirements": [],
        }

        captured_kwargs: dict[str, Any] = {}

        async def capture_create(**kwargs: Any) -> Any:
            captured_kwargs.update(kwargs)
            return _make_message(expected)

        with patch.object(service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.messages.create = capture_create
            mock_get_client.return_value = mock_client

            await service.analyze_solution(
                "테스트 설명",
                {"industry": "finance", "size": "large"},
            )

        user_msg = captured_kwargs["messages"][0]["content"]
        assert "finance" in user_msg
        assert "large" in user_msg


class TestGenerateUiStructure:
    @pytest.mark.asyncio
    async def test_returns_ui_structure(self, service: ClaudeService) -> None:
        expected = {
            "menu_structure": {
                "nav_type": "sidebar",
                "items": [
                    {"label": "대시보드", "path": "/dashboard", "icon": "home", "children": []}
                ],
            },
            "pages": [
                {"name": "대시보드", "path": "/dashboard", "layout": "default", "components": []}
            ],
            "color_palette": {
                "primary": "#3B82F6",
                "secondary": "#64748B",
                "accent": "#F59E0B",
                "background": "#F8FAFC",
                "surface": "#FFFFFF",
                "text_primary": "#1E293B",
            },
            "typography": {"heading_font": "Inter", "body_font": "Inter"},
            "design_style": "minimal",
        }

        with patch.object(service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=_make_message(expected))
            mock_get_client.return_value = mock_client

            result = await service.generate_ui_structure(
                {"solution_type": "saas", "features": ["대시보드"]},
                variant_index=0,
            )

        assert "menu_structure" in result
        assert "color_palette" in result
        assert result["design_style"] == "minimal"

    @pytest.mark.asyncio
    async def test_variant_index_included_in_prompt(self, service: ClaudeService) -> None:
        """variant_index가 요청 메시지에 포함되는지 확인한다."""
        expected = {
            "menu_structure": {},
            "pages": [],
            "color_palette": {},
            "typography": {},
            "design_style": "corporate",
        }
        captured_kwargs: dict[str, Any] = {}

        async def capture_create(**kwargs: Any) -> Any:
            captured_kwargs.update(kwargs)
            return _make_message(expected)

        with patch.object(service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.messages.create = capture_create
            mock_get_client.return_value = mock_client

            await service.generate_ui_structure({}, variant_index=2)

        user_msg = captured_kwargs["messages"][0]["content"]
        assert "2" in user_msg

    @pytest.mark.asyncio
    async def test_fallback_on_invalid_json(self, service: ClaudeService) -> None:
        block = TextBlock(type="text", text="잘못된 응답")
        msg = MagicMock()
        msg.content = [block]

        with patch.object(service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=msg)
            mock_get_client.return_value = mock_client

            result = await service.generate_ui_structure({})

        assert result["menu_structure"] == {}
        assert result["pages"] == []


class TestRecommendPm:
    @pytest.mark.asyncio
    async def test_returns_recommendation(self, service: ClaudeService) -> None:
        pm_catalog = [
            {"id": "pm-001", "name": "김PM", "domain": "product", "specialty": "saas"},
            {"id": "pm-002", "name": "이PM", "domain": "backend", "specialty": "api"},
        ]
        expected = {
            "recommended_pm_id": "pm-001",
            "match_score": 88,
            "reasoning": "SaaS 도메인 전문가로 요구사항에 적합합니다.",
            "key_strengths": ["SaaS 경험", "product 역량"],
            "potential_gaps": ["모바일 경험 부족"],
            "alternatives": [{"pm_id": "pm-002", "match_score": 72, "reasoning": "백엔드 강점"}],
        }

        with patch.object(service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=_make_message(expected))
            mock_get_client.return_value = mock_client

            result = await service.recommend_pm(
                {"solution_type": "saas"},
                "saas-fullstack",
                pm_catalog,
            )

        assert result["recommended_pm_id"] == "pm-001"
        assert result["match_score"] == 88
        assert len(result["alternatives"]) == 1

    @pytest.mark.asyncio
    async def test_empty_catalog_returns_early(self, service: ClaudeService) -> None:
        """PM 카탈로그가 비어 있으면 Claude API를 호출하지 않는다."""
        with patch.object(service, "_get_client") as mock_get_client:
            result = await service.recommend_pm({}, "saas", [])

        mock_get_client.assert_not_called()
        assert result["recommended_pm_id"] is None
        assert result["match_score"] == 0

    @pytest.mark.asyncio
    async def test_fallback_on_invalid_json(self, service: ClaudeService) -> None:
        block = TextBlock(type="text", text="잘못된 응답")
        msg = MagicMock()
        msg.content = [block]

        with patch.object(service, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=msg)
            mock_get_client.return_value = mock_client

            result = await service.recommend_pm({}, "saas", [{"id": "pm-001"}])

        assert result["recommended_pm_id"] is None
