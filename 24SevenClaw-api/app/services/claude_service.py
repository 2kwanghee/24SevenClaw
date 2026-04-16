"""Claude AI 연동 서비스.

기존 규칙 기반 스텁 메서드(analyze_input, generate_prototypes, recommend_pm_scores)와
실제 Anthropic SDK 기반 async 메서드(analyze_solution, generate_ui_structure, recommend_pm)를
함께 제공한다.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import anthropic
from anthropic.types import Message, TextBlock

from app.config import settings

logger = logging.getLogger(__name__)

# ── 규칙 기반 스텁 데이터 (Phase 2 하위 호환) ────────────────────────────────

# 솔루션 유형별 프로토타입 템플릿 (새 Prototype 모델 필드 기준)
PROTOTYPE_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "saas": [
        {
            "title": "SaaS 풀스택 (Next.js + FastAPI)",
            "description": (
                "SaaS 서비스에 최적화된 풀스택 구성입니다. "
                "Next.js의 SSR/SSG와 FastAPI의 고성능 비동기 처리를 결합합니다."
            ),
            "design_pattern": "saas-fullstack",
            "ui_structure": {
                "frontend": "next.js",
                "backend": "fastapi",
                "database": "postgresql",
                "auth": "jwt",
                "deployment": "docker",
            },
            "menu_structure": {},
            "color_palette": {},
        },
        {
            "title": "SaaS 경량 (React + Express)",
            "description": (
                "빠른 프로토타이핑에 적합한 경량 SaaS 구성입니다. "
                "React SPA와 Express의 간결한 API 서버를 활용합니다."
            ),
            "design_pattern": "saas-lightweight",
            "ui_structure": {
                "frontend": "react",
                "backend": "express",
                "database": "postgresql",
                "auth": "session",
                "deployment": "docker",
            },
            "menu_structure": {},
            "color_palette": {},
        },
    ],
    "rest-api": [
        {
            "title": "REST API (FastAPI + PostgreSQL)",
            "description": (
                "고성능 REST API에 최적화된 구성입니다. "
                "FastAPI의 자동 문서 생성과 비동기 처리를 활용합니다."
            ),
            "design_pattern": "api-first",
            "ui_structure": {
                "framework": "fastapi",
                "database": "postgresql",
                "auth": "jwt",
                "docs": "openapi",
                "deployment": "docker",
            },
            "menu_structure": {},
            "color_palette": {},
        },
        {
            "title": "REST API (Express + MongoDB)",
            "description": (
                "유연한 스키마가 필요한 API에 적합한 구성입니다. "
                "MongoDB의 문서 기반 저장소와 Express의 미들웨어 생태계를 활용합니다."
            ),
            "design_pattern": "api-first",
            "ui_structure": {
                "framework": "express",
                "database": "mongodb",
                "auth": "jwt",
                "docs": "swagger",
                "deployment": "docker",
            },
            "menu_structure": {},
            "color_palette": {},
        },
    ],
    "fullstack": [
        {
            "title": "풀스택 (Next.js + FastAPI)",
            "description": (
                "풀스택 애플리케이션의 표준 구성입니다. "
                "Next.js의 풀스택 기능과 FastAPI의 고성능 API를 결합합니다."
            ),
            "design_pattern": "fullstack-separated",
            "ui_structure": {
                "frontend": "next.js",
                "backend": "fastapi",
                "database": "postgresql",
                "auth": "jwt",
                "deployment": "docker-compose",
            },
            "menu_structure": {},
            "color_palette": {},
        },
        {
            "title": "풀스택 (Next.js + Prisma)",
            "description": (
                "Next.js 단일 프레임워크로 프론트/백을 통합하는 구성입니다. "
                "Prisma ORM과 NextAuth로 빠르게 풀스택을 구축합니다."
            ),
            "design_pattern": "fullstack-monolith",
            "ui_structure": {
                "frontend": "next.js",
                "backend": "next.js-api-routes",
                "database": "postgresql",
                "orm": "prisma",
                "auth": "next-auth",
                "deployment": "vercel",
            },
            "menu_structure": {},
            "color_palette": {},
        },
    ],
    "internal-tool": [
        {
            "title": "내부 도구 (React Admin + FastAPI)",
            "description": (
                "내부 관리 도구에 최적화된 구성입니다. "
                "React Admin의 CRUD UI와 FastAPI의 빠른 API 개발을 결합합니다."
            ),
            "design_pattern": "admin-dashboard",
            "ui_structure": {
                "frontend": "react-admin",
                "backend": "fastapi",
                "database": "postgresql",
                "auth": "ldap",
                "deployment": "docker",
            },
            "menu_structure": {},
            "color_palette": {},
        },
    ],
    "mvp": [
        {
            "title": "MVP (Next.js 풀스택)",
            "description": (
                "최소 기능 제품을 빠르게 출시하기 위한 구성입니다. "
                "Next.js 하나로 프론트/백을 구현하고 Vercel로 즉시 배포합니다."
            ),
            "design_pattern": "mvp-monolith",
            "ui_structure": {
                "frontend": "next.js",
                "backend": "next.js-api-routes",
                "database": "sqlite",
                "auth": "next-auth",
                "deployment": "vercel",
            },
            "menu_structure": {},
            "color_palette": {},
        },
        {
            "title": "MVP (Flask + HTMX)",
            "description": (
                "최소 복잡도로 동작하는 MVP 구성입니다. "
                "Flask + HTMX로 SPA 없이 인터랙티브한 웹 앱을 구현합니다."
            ),
            "design_pattern": "mvp-server-rendered",
            "ui_structure": {
                "frontend": "htmx",
                "backend": "flask",
                "database": "sqlite",
                "auth": "session",
                "deployment": "railway",
            },
            "menu_structure": {},
            "color_palette": {},
        },
    ],
}

# 기본 템플릿 (매칭 안 될 때)
DEFAULT_TEMPLATES: list[dict[str, Any]] = [
    {
        "title": "범용 웹 애플리케이션 (Next.js + FastAPI)",
        "description": (
            "범용적인 웹 애플리케이션 구성입니다. "
            "Next.js와 FastAPI의 검증된 조합을 활용합니다."
        ),
        "design_pattern": "fullstack-separated",
        "ui_structure": {
            "frontend": "next.js",
            "backend": "fastapi",
            "database": "postgresql",
            "auth": "jwt",
            "deployment": "docker",
        },
        "menu_structure": {},
        "color_palette": {},
    },
]

# 키워드 → 솔루션 유형 매핑 (자연어 분석 스텁)
KEYWORD_TYPE_MAP: dict[str, str] = {
    "saas": "saas",
    "구독": "saas",
    "subscription": "saas",
    "api": "rest-api",
    "rest": "rest-api",
    "endpoint": "rest-api",
    "fullstack": "fullstack",
    "풀스택": "fullstack",
    "full-stack": "fullstack",
    "admin": "internal-tool",
    "관리": "internal-tool",
    "내부": "internal-tool",
    "dashboard": "internal-tool",
    "대시보드": "internal-tool",
    "mvp": "mvp",
    "프로토타입": "mvp",
    "prototype": "mvp",
    "빠르게": "mvp",
}

# ── 시스템 프롬프트 ────────────────────────────────────────────────────────────

_ANALYZE_SOLUTION_SYSTEM = (
    "You are a software architect specializing in analyzing natural language "
    "descriptions to extract structured requirements.\n\n"
    "Your task is to analyze the user's solution description "
    "and return a structured JSON object.\n\n"
    "IMPORTANT: Always respond with valid JSON only "
    "— no markdown, no code blocks, no extra text.\n\n"
    'Return exactly this JSON structure:\n'
    "{\n"
    '  "solution_type": "<one of: saas, rest-api, fullstack, internal-tool, mvp>",\n'
    '  "features": ["<feature 1>", "<feature 2>", ...],\n'
    '  "tech_stack": {\n'
    '    "frontend": "<framework or null>",\n'
    '    "backend": "<framework>",\n'
    '    "database": "<db type>",\n'
    '    "auth": "<auth method>",\n'
    '    "deployment": "<deployment target>"\n'
    "  },\n"
    '  "complexity": "<one of: low, medium, high>",\n'
    '  "target_users": "<description of target users>",\n'
    '  "key_requirements": ["<requirement 1>", "<requirement 2>", ...]\n'
    "}"
)

_GENERATE_UI_STRUCTURE_SYSTEM = (
    "You are a UI/UX architect specializing in designing application structures.\n\n"
    "Your task is to generate a detailed UI structure for an application "
    "based on provided requirements.\n"
    "If variant_index is provided, generate an alternative design variant "
    "(0 = primary, 1 = alternative, etc.).\n\n"
    "IMPORTANT: Always respond with valid JSON only "
    "— no markdown, no code blocks, no extra text.\n\n"
    "Return exactly this JSON structure:\n"
    "{\n"
    '  "menu_structure": {\n'
    '    "nav_type": "<sidebar | topbar | hybrid>",\n'
    '    "items": [\n'
    "      {\n"
    '        "label": "<menu label>",\n'
    '        "path": "<route path>",\n'
    '        "icon": "<icon name>",\n'
    '        "children": []\n'
    "      }\n"
    "    ]\n"
    "  },\n"
    '  "pages": [\n'
    "    {\n"
    '      "name": "<page name>",\n'
    '      "path": "<route>",\n'
    '      "layout": "<layout type>",\n'
    '      "components": ["<component 1>", "<component 2>"]\n'
    "    }\n"
    "  ],\n"
    '  "color_palette": {\n'
    '    "primary": "<hex color>",\n'
    '    "secondary": "<hex color>",\n'
    '    "accent": "<hex color>",\n'
    '    "background": "<hex color>",\n'
    '    "surface": "<hex color>",\n'
    '    "text_primary": "<hex color>"\n'
    "  },\n"
    '  "typography": {\n'
    '    "heading_font": "<font family>",\n'
    '    "body_font": "<font family>"\n'
    "  },\n"
    '  "design_style": "<one of: minimal, corporate, playful, dark, light>"\n'
    "}"
)

_RECOMMEND_PM_SYSTEM = (
    "You are a PM matchmaker specializing in matching project managers "
    "to software projects.\n\n"
    "Your task is to analyze project requirements and recommend the most "
    "suitable PM from the provided catalog.\n\n"
    "IMPORTANT: Always respond with valid JSON only "
    "— no markdown, no code blocks, no extra text.\n\n"
    "Return exactly this JSON structure:\n"
    "{\n"
    '  "recommended_pm_id": "<UUID of the best PM or null if catalog is empty>",\n'
    '  "match_score": <integer 0-100>,\n'
    '  "reasoning": "<detailed explanation of why this PM is the best match>",\n'
    '  "key_strengths": ["<strength 1>", "<strength 2>"],\n'
    '  "potential_gaps": ["<gap 1>"],\n'
    '  "alternatives": [\n'
    "    {\n"
    '      "pm_id": "<UUID>",\n'
    '      "match_score": <integer 0-100>,\n'
    '      "reasoning": "<brief explanation>"\n'
    "    }\n"
    "  ]\n"
    "}"
)


# ── 유틸리티 ──────────────────────────────────────────────────────────────────


def _extract_text(message: Message) -> str:
    """Message의 첫 번째 TextBlock에서 텍스트를 추출한다. 없으면 '{}'을 반환한다."""
    for block in message.content:
        if isinstance(block, TextBlock):
            return block.text
    return "{}"


# ── ClaudeService ─────────────────────────────────────────────────────────────


class ClaudeService:
    """Claude AI 분석 서비스.

    규칙 기반 동기 메서드(하위 호환)와 Anthropic SDK 기반 비동기 메서드를 모두 제공한다.

    동기 메서드 (Phase 2 하위 호환):
        analyze_input(prompt) → str
        generate_prototypes(solution_type, prompt) → list[dict]
        recommend_pm_scores(solution_type, pm_specialties) → dict[str, int]

    비동기 메서드 (Phase 3 Claude API):
        analyze_solution(prompt, org_context) → dict
        generate_ui_structure(requirements, variant_index) → dict
        recommend_pm(requirements, prototype_style, pm_catalog) → dict
    """

    def __init__(self) -> None:
        self._api_key = settings.anthropic_api_key
        self._model = settings.anthropic_model_default
        self._timeout = settings.prototype_generation_timeout

    def _get_client(self) -> anthropic.AsyncAnthropic:
        return anthropic.AsyncAnthropic(
            api_key=self._api_key,
            timeout=float(self._timeout),
        )

    # ── 규칙 기반 동기 메서드 (Phase 2 하위 호환) ────────────────────────────

    def analyze_input(self, solution_prompt: str) -> str:
        """솔루션 프롬프트에서 솔루션 유형을 추출한다."""
        text = solution_prompt.lower()
        for keyword, solution_type in KEYWORD_TYPE_MAP.items():
            if keyword in text:
                return solution_type
        return "fullstack"

    def generate_prototypes(
        self, solution_type: str, solution_prompt: str
    ) -> list[dict[str, Any]]:
        """솔루션 유형에 맞는 프로토타입 템플릿을 반환한다."""
        templates = PROTOTYPE_TEMPLATES.get(solution_type, DEFAULT_TEMPLATES)
        return [dict(t) for t in templates]

    def recommend_pm_scores(
        self, solution_type: str, pm_specialties: list[str]
    ) -> dict[str, int]:
        """솔루션 유형에 따른 PM specialty별 매칭 점수를 반환한다.

        Returns:
            dict[specialty, score(0~100)]
        """
        affinity: dict[str, list[str]] = {
            "saas": ["product", "growth", "platform"],
            "rest-api": ["backend", "platform", "data"],
            "fullstack": ["product", "frontend", "backend"],
            "internal-tool": ["operations", "backend", "data"],
            "mvp": ["product", "growth", "frontend"],
            "custom": ["product", "backend"],
        }
        preferred = affinity.get(solution_type, affinity["custom"])
        scores: dict[str, int] = {}
        for spec in pm_specialties:
            if spec in preferred:
                rank = preferred.index(spec)
                scores[spec] = max(60, 95 - rank * 15)
            else:
                scores[spec] = 40
        return scores

    # ── Claude API 비동기 메서드 (Phase 3) ───────────────────────────────────

    async def analyze_solution(
        self,
        prompt: str,
        org_context: dict[str, Any],
    ) -> dict[str, Any]:
        """자연어 솔루션 설명을 구조화된 요구사항 JSON으로 변환한다.

        Args:
            prompt: 사용자가 입력한 솔루션 설명 (자연어)
            org_context: 조직 컨텍스트 (industry, size, existing_stack 등)

        Returns:
            {
                solution_type, features, tech_stack,
                complexity, target_users, key_requirements
            }
        """
        user_content = (
            f"Solution description:\n{prompt}\n\n"
            f"Organization context:\n{json.dumps(org_context, ensure_ascii=False)}"
        )

        client = self._get_client()
        message = await client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=_ANALYZE_SOLUTION_SYSTEM,
            messages=[{"role": "user", "content": user_content}],
        )

        raw = _extract_text(message)
        try:
            result: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("analyze_solution: Claude 응답 JSON 파싱 실패, 스텁 폴백")
            result = {
                "solution_type": self.analyze_input(prompt),
                "features": [],
                "tech_stack": {},
                "complexity": "medium",
                "target_users": "",
                "key_requirements": [],
            }
        return result

    async def generate_ui_structure(
        self,
        requirements: dict[str, Any],
        variant_index: int = 0,
    ) -> dict[str, Any]:
        """요구사항 기반 UI 구조 JSON(메뉴, 페이지, 컬러)을 생성한다.

        Args:
            requirements: analyze_solution()의 반환값
            variant_index: 변형 인덱스 (0=기본, 1=대안 디자인, …)

        Returns:
            {menu_structure, pages, color_palette, typography, design_style}
        """
        user_content = (
            f"Requirements:\n{json.dumps(requirements, ensure_ascii=False)}\n\n"
            f"Design variant index: {variant_index}\n"
            "Generate a unique UI structure for this variant index. "
            "Variant 0 should be the primary/recommended design, "
            "variant 1 an alternative color scheme, "
            "variant 2+ additional creative interpretations."
        )

        client = self._get_client()
        message = await client.messages.create(
            model=self._model,
            max_tokens=2048,
            system=_GENERATE_UI_STRUCTURE_SYSTEM,
            messages=[{"role": "user", "content": user_content}],
        )

        raw = _extract_text(message)
        try:
            result: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("generate_ui_structure: Claude 응답 JSON 파싱 실패, 스텁 폴백")
            result = {
                "menu_structure": {},
                "pages": [],
                "color_palette": {},
                "typography": {},
                "design_style": "minimal",
            }
        return result

    async def recommend_pm(
        self,
        requirements: dict[str, Any],
        prototype_style: str,
        pm_catalog: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """요구사항과 프로토타입 스타일에 맞는 PM을 카탈로그에서 추천한다.

        Args:
            requirements: analyze_solution()의 반환값
            prototype_style: 선택된 프로토타입의 design_pattern
            pm_catalog: PM 프로필 목록 (id, name, domain, specialty, skills 등)

        Returns:
            {
                recommended_pm_id, match_score, reasoning,
                key_strengths, potential_gaps, alternatives
            }
        """
        if not pm_catalog:
            return {
                "recommended_pm_id": None,
                "match_score": 0,
                "reasoning": "PM 카탈로그가 비어 있습니다.",
                "key_strengths": [],
                "potential_gaps": [],
                "alternatives": [],
            }

        user_content = (
            f"Project requirements:\n{json.dumps(requirements, ensure_ascii=False)}\n\n"
            f"Selected prototype style: {prototype_style}\n\n"
            f"PM catalog:\n{json.dumps(pm_catalog, ensure_ascii=False, default=str)}"
        )

        client = self._get_client()
        message = await client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=_RECOMMEND_PM_SYSTEM,
            messages=[{"role": "user", "content": user_content}],
        )

        raw = _extract_text(message)
        try:
            result: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("recommend_pm: Claude 응답 JSON 파싱 실패, 스텁 폴백")
            result = {
                "recommended_pm_id": None,
                "match_score": 0,
                "reasoning": "PM 추천 분석 중 오류가 발생했습니다.",
                "key_strengths": [],
                "potential_gaps": [],
                "alternatives": [],
            }
        return result
