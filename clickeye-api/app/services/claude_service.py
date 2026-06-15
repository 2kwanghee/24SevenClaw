"""Claude AI 연동 서비스.

규칙 기반 폴백 메서드(analyze_input)와
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

# ── 시스템 프롬프트 ────────────────────────────────────────────────────────────

_ANALYZE_SOLUTION_SYSTEM = (
    "You are a software architect specializing in analyzing natural language "
    "descriptions to extract structured requirements.\n\n"
    "Your task is to analyze the user's solution description "
    "and return a structured JSON object.\n\n"
    "IMPORTANT: Always respond with valid JSON only "
    "— no markdown, no code blocks, no extra text.\n\n"
    "Return exactly this JSON structure:\n"
    "{\n"
    '  "primary_tag": "<main category tag — e.g. saas, rest-api, fullstack, '
    "internal-tool, mvp, mobile, blockchain, ai-platform, e-commerce, "
    'or suggest a new tag if none fits>",\n'
    '  "tags": ["<tag1>", "<tag2>", ...],\n'
    '  "solution_type": "<same value as primary_tag — kept for backwards compatibility>",\n'
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

_GENERATE_UI_STRUCTURE_SYSTEM_KO = (
    "You are a UI/UX architect and tech stack advisor specializing in designing "
    "application structures with diverse technology combinations.\n\n"
    "VARIANT ROLES — each variant MUST be meaningfully different:\n"
    "- user_stack_recommended: Use the user's preferred tech stack (from user_tech_stack) as-is. "
    "Pair with the most standard architecture for that domain. Mark is_recommended=true.\n"
    "- alternative_stack: Propose a completely DIFFERENT primary tech stack from user_tech_stack. "
    "MUST NOT reuse the same frontend or backend framework. "
    "Example: if user chose Next.js+FastAPI, propose Vue.js+Django or Express+React. "
    "Keep a similar overall architecture pattern. Mark is_recommended=false.\n"
    "- different_architecture: Use a FUNDAMENTALLY different architectural pattern "
    "(serverless, microservices, edge-first, BFF, modular monolith, BaaS). "
    "Choose the best-fit stack for this architecture regardless of user preference. "
    "Mark is_recommended=false.\n\n"
    "If user_tech_stack is empty, freely propose three distinct stacks covering: "
    "(0) a popular mainstream stack, "
    "(1) a JS-ecosystem alternative, "
    "(2) a serverless/BaaS approach.\n\n"
    "COMPANY CONTEXT — adapt recommendations to the company profile:\n"
    "- company_size 'startup'/'small' → prefer simple stacks, managed services, "
    "avoid enterprise microservices in Variant 0. "
    "Variant 0 deployable by a 1-3 person team in 4-8 weeks.\n"
    "- company_size 'enterprise'/'mid-large' → emphasize auditability, "
    "role-based access, scalability. Variant 2 may include enterprise MSA.\n"
    "- industry 'fintech'/'healthcare' → prioritize compliance "
    "(audit logging, encryption at rest), avoid bleeding-edge stacks.\n"
    "- industry 'ecommerce' → include search/cart/payment patterns in pages.\n"
    "- business_type 'internal' → Variant 2 admin-portal/low-cost focused "
    "(e.g., Retool/Appsmith-like).\n"
    "- business_type 'b2c' → emphasize mobile-first, performance, "
    "public-facing patterns.\n\n"
    "PROS AND CONS: For each variant, list 2-3 concise pros and 1-2 cons "
    "specific to this stack+architecture combination in the context of the "
    "given solution AND company profile.\n\n"
    "QUANTITATIVE METRICS — realistic estimates calibrated to company_size:\n"
    "- estimated_weeks: development time range (min, max) for MVP.\n"
    "- team_size: min/max headcount with roles (e.g., ['BE','FE','DevOps']).\n"
    "- complexity_score (1-10): architectural/operational complexity.\n"
    "- scalability_score (1-10): user base capacity without redesign.\n"
    "- monthly_cost_usd: infra cost range (min,max) at MVP scale (~1k DAU).\n"
    "- maintenance_difficulty: 'low'/'medium'/'high'.\n"
    "- skill_requirements: 2-5 specific skills the team must have.\n"
    "- match_reasoning: one Korean sentence explaining why THIS company "
    "profile (size+industry+business_type) fits this variant. "
    "Reference at least one company attribute.\n\n"
    "IMPORTANT: Always respond with valid JSON only "
    "— no markdown, no code blocks, no extra text.\n\n"
    "Return exactly this JSON structure:\n"
    "{\n"
    '  "tech_stack_tags": ["<tech 1>", "<tech 2>", "<tech 3>"],\n'
    '  "architecture_pattern": "<Korean pattern, e.g. 모놀리식 3-tier>",\n'
    '  "variant_rationale": "<1-2 Korean sentences>",\n'
    '  "is_recommended": <true|false>,\n'
    '  "pros": ["<장점 1>", "<장점 2>", "<장점 3>"],\n'
    '  "cons": ["<단점 1>", "<단점 2>"],\n'
    '  "estimated_weeks": {"min": <int>, "max": <int>},\n'
    '  "team_size": {"min": <int>, "max": <int>, "roles": ["<role1>", "<role2>"]},\n'
    '  "complexity_score": <int 1-10>,\n'
    '  "scalability_score": <int 1-10>,\n'
    '  "monthly_cost_usd": {"min": <int>, "max": <int>},\n'
    '  "maintenance_difficulty": "<low|medium|high>",\n'
    '  "skill_requirements": ["<skill 1>", "<skill 2>"],\n'
    '  "match_reasoning": "<한국어 한 문장 — 회사 규모/산업/비즈니스타입 중 하나 이상 명시>",\n'
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

_GENERATE_UI_STRUCTURE_SYSTEM_EN = (
    "Generate ALL text values (architecture_pattern, variant_rationale, pros, cons, "
    "match_reasoning) in English.\n\n"
    "You are a UI/UX architect and tech stack advisor specializing in designing "
    "application structures with diverse technology combinations.\n\n"
    "VARIANT ROLES — each variant MUST be meaningfully different:\n"
    "- user_stack_recommended: Use the user's preferred tech stack (from user_tech_stack) as-is. "
    "Pair with the most standard architecture for that domain. Mark is_recommended=true.\n"
    "- alternative_stack: Propose a completely DIFFERENT primary tech stack from user_tech_stack. "
    "MUST NOT reuse the same frontend or backend framework. "
    "Example: if user chose Next.js+FastAPI, propose Vue.js+Django or Express+React. "
    "Keep a similar overall architecture pattern. Mark is_recommended=false.\n"
    "- different_architecture: Use a FUNDAMENTALLY different architectural pattern "
    "(serverless, microservices, edge-first, BFF, modular monolith, BaaS). "
    "Choose the best-fit stack for this architecture regardless of user preference. "
    "Mark is_recommended=false.\n\n"
    "If user_tech_stack is empty, freely propose three distinct stacks covering: "
    "(0) a popular mainstream stack, "
    "(1) a JS-ecosystem alternative, "
    "(2) a serverless/BaaS approach.\n\n"
    "COMPANY CONTEXT — adapt recommendations to the company profile:\n"
    "- company_size 'startup'/'small' → prefer simple stacks, managed services, "
    "avoid enterprise microservices in Variant 0. "
    "Variant 0 deployable by a 1-3 person team in 4-8 weeks.\n"
    "- company_size 'enterprise'/'mid-large' → emphasize auditability, "
    "role-based access, scalability. Variant 2 may include enterprise MSA.\n"
    "- industry 'fintech'/'healthcare' → prioritize compliance "
    "(audit logging, encryption at rest), avoid bleeding-edge stacks.\n"
    "- industry 'ecommerce' → include search/cart/payment patterns in pages.\n"
    "- business_type 'internal' → Variant 2 admin-portal/low-cost focused "
    "(e.g., Retool/Appsmith-like).\n"
    "- business_type 'b2c' → emphasize mobile-first, performance, "
    "public-facing patterns.\n\n"
    "PROS AND CONS: For each variant, list 2-3 concise pros and 1-2 cons "
    "specific to this stack+architecture combination in the context of the "
    "given solution AND company profile.\n\n"
    "QUANTITATIVE METRICS — realistic estimates calibrated to company_size:\n"
    "- estimated_weeks: development time range (min, max) for MVP.\n"
    "- team_size: min/max headcount with roles (e.g., ['BE','FE','DevOps']).\n"
    "- complexity_score (1-10): architectural/operational complexity.\n"
    "- scalability_score (1-10): user base capacity without redesign.\n"
    "- monthly_cost_usd: infra cost range (min,max) at MVP scale (~1k DAU).\n"
    "- maintenance_difficulty: 'low'/'medium'/'high'.\n"
    "- skill_requirements: 2-5 specific skills the team must have.\n"
    "- match_reasoning: one English sentence explaining why THIS company "
    "profile (size+industry+business_type) fits this variant. "
    "Reference at least one company attribute.\n\n"
    "IMPORTANT: Always respond with valid JSON only "
    "— no markdown, no code blocks, no extra text.\n\n"
    "Return exactly this JSON structure:\n"
    "{\n"
    '  "tech_stack_tags": ["<tech 1>", "<tech 2>", "<tech 3>"],\n'
    '  "architecture_pattern": "<e.g. Monolithic 3-tier>",\n'
    '  "variant_rationale": "<1-2 sentences>",\n'
    '  "is_recommended": <true|false>,\n'
    '  "pros": ["<pro 1>", "<pro 2>", "<pro 3>"],\n'
    '  "cons": ["<con 1>", "<con 2>"],\n'
    '  "estimated_weeks": {"min": <int>, "max": <int>},\n'
    '  "team_size": {"min": <int>, "max": <int>, "roles": ["<role1>", "<role2>"]},\n'
    '  "complexity_score": <int 1-10>,\n'
    '  "scalability_score": <int 1-10>,\n'
    '  "monthly_cost_usd": {"min": <int>, "max": <int>},\n'
    '  "maintenance_difficulty": "<low|medium|high>",\n'
    '  "skill_requirements": ["<skill 1>", "<skill 2>"],\n'
    '  "match_reasoning": "<one English sentence'
    " — mention at least one of company size, industry, or business type"
    '>",\n'
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

_DECOMPOSE_TASKS_SYSTEM = (
    "당신은 소프트웨어 프로젝트 오케스트레이터입니다. "
    "Claude Plan 모드처럼 요구사항을 정밀하게 분석하여 AI 팀이 실행 가능한 서브태스크로 분해합니다.\n\n"  # noqa: E501
    "분석 절차:\n"
    "1. 핵심 도메인과 기술 스택을 식별하세요.\n"
    "2. 구현 단계(setup→core→polish)로 분해하세요.\n"
    "3. 서브태스크 간 의존성을 매핑하세요.\n"
    "4. 각 서브태스크에 측정 가능한 완료 기준(AC)을 2~5개 작성하세요.\n\n"
    "규칙:\n"
    "- 사용자 입력을 그대로 옮기지 마세요. 실행 가능한 단위로 재구성하세요.\n"
    "- architect 태스크는 항상 포함하고 다른 태스크의 선행 조건으로 설정하세요.\n"
    "- 서브태스크는 최소 2개, 최대 10개.\n"
    "- 제목: 50자 이내, 명령형 동사로 시작 (예: '~를 구현한다', '~를 설계한다').\n"
    "- 설명: 무엇을, 왜, 어떻게 — 3~5문장 한국어.\n"
    "- phase: mvp=핵심 사용자 가치, v2=보강, future=nice-to-have.\n"
    "- 모든 텍스트를 한국어로 작성하세요.\n\n"
    "IMPORTANT: 유효한 JSON 배열만 반환하세요 — 마크다운, 코드블록, 추가 텍스트 없이.\n\n"
    "반환 형식 (JSON 배열):\n"
    "[\n"
    "  {\n"
    '    "assigned_role": "<architect|frontend|backend|qa|security|devops|reviewer>",\n'
    '    "title": "<50자 이내, 명령형 동사로 시작>",\n'
    '    "description": "<무엇을, 왜, 어떻게 — 3~5문장>",\n'
    '    "phase": "<mvp|v2|future>",\n'
    '    "priority": "<high|medium|low>",\n'
    '    "estimate_hours": <정수 1~40>,\n'
    '    "depends_on": ["<선행 서브태스크 title 정확히 인용>"],\n'
    '    "acceptance_criteria": ["<측정 가능한 완료 조건>", "..."]\n'
    "  }\n"
    "]"
)

_GENERATE_DRAFT_SYSTEM = (
    "You are a senior software engineer generating an initial draft plan "
    "for a development subtask in an AI team workflow.\n\n"
    "Given a subtask title, description, and session context, create a "
    "comprehensive initial draft in Korean that includes:\n"
    "1. 구현 접근 방법 및 핵심 결정 사항\n"
    "2. 단계별 실행 계획\n"
    "3. 주요 고려 사항 및 잠재 리스크\n"
    "4. 예상 산출물\n\n"
    "Write entirely in Korean. Be specific and actionable. "
    "Use markdown headings and bullet points. No JSON."
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

_SYSTEM_PROMPTS: dict[str, dict[str, str]] = {
    "generate_ui_structure": {
        "ko": _GENERATE_UI_STRUCTURE_SYSTEM_KO,
        "en": _GENERATE_UI_STRUCTURE_SYSTEM_EN,
    },
}


def _get_system_prompt(name: str, locale: str = "ko") -> str:
    """프롬프트 이름과 locale로 시스템 프롬프트를 반환한다. 없으면 ko 버전을 사용한다."""
    prompts = _SYSTEM_PROMPTS.get(name, {})
    return prompts.get(locale) or prompts.get("ko") or ""


def _extract_text(message: Message) -> str:
    """Message의 첫 번째 TextBlock에서 텍스트를 추출한다. 없으면 '{}'을 반환한다."""
    for block in message.content:
        if isinstance(block, TextBlock):
            return block.text
    return "{}"


# 기본 키워드 → 태그 매핑 (Claude API 미연결 시 폴백용)
_KEYWORD_TAG_MAP: dict[str, list[str]] = {
    "saas": ["saas", "구독", "subscription", "멀티테넌트", "multi-tenant"],
    "rest-api": ["api", "rest", "endpoint", "swagger", "openapi", "backend only"],
    "fullstack": ["fullstack", "풀스택", "full-stack", "full stack"],
    "internal-tool": ["admin", "관리", "내부", "dashboard", "대시보드", "erp", "crm", "백오피스"],
    "mvp": ["mvp", "프로토타입", "빠르게", "빠른 출시", "스타트업"],
    "mobile": ["모바일", "mobile", "ios", "android", "앱", "리액트 네이티브", "expo"],
    "e-commerce": ["쇼핑", "shop", "ecommerce", "e-commerce", "결제", "상품", "장바구니"],
    "ai-platform": ["ai", "인공지능", "머신러닝", "ml", "llm", "gpt", "chatbot", "챗봇"],
}


# ── ClaudeService ─────────────────────────────────────────────────────────────


class ClaudeService:
    """Claude AI 분석 서비스.

    규칙 기반 폴백 메서드(analyze_input)와 Anthropic SDK 기반 비동기 메서드를 모두 제공한다.

    폴백 메서드:
        analyze_input(prompt) → str  (primary_tag 추출)

    비동기 메서드:
        analyze_solution(prompt, org_context) → dict
        generate_ui_structure(requirements, variant_index, variant_config, catalog_entry) → dict
        recommend_pm(requirements, prototype_style, pm_catalog) → dict
    """

    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or settings.anthropic_api_key
        self._model = settings.anthropic_model_default
        self._timeout = settings.prototype_generation_timeout

    def _get_client(self) -> anthropic.AsyncAnthropic:
        if not self._api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY가 설정되지 않았습니다. .env 파일에 ANTHROPIC_API_KEY=sk-ant-... 를 추가하세요."  # noqa: E501
            )
        return anthropic.AsyncAnthropic(
            api_key=self._api_key,
            timeout=float(self._timeout),
        )

    # ── 폴백 동기 메서드 ─────────────────────────────────────────────────────

    def analyze_input(self, solution_prompt: str) -> str:
        """솔루션 프롬프트에서 대표 태그를 추출한다 (Claude API 미연결 폴백용)."""
        text = solution_prompt.lower()
        for tag, keywords in _KEYWORD_TAG_MAP.items():
            if any(kw in text for kw in keywords):
                return tag
        return "fullstack"

    def recommend_pm_scores(self, solution_type: str, pm_specialties: list[str]) -> dict[str, int]:
        """솔루션 타입에 따른 PM specialty별 매칭 점수를 반환한다.

        Returns:
            dict[specialty, score(0~100)]
        """
        affinity: dict[str, list[str]] = {
            "saas": ["product", "growth", "platform"],
            "rest-api": ["backend", "platform", "data"],
            "fullstack": ["product", "frontend", "backend"],
            "internal-tool": ["operations", "backend", "data"],
            "mvp": ["product", "growth", "frontend"],
            "mobile": ["product", "frontend", "growth"],
            "e-commerce": ["product", "growth", "backend"],
            "ai-platform": ["data", "backend", "product"],
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

    # ── Claude API 비동기 메서드 ──────────────────────────────────────────────

    async def analyze_solution(
        self,
        prompt: str,
        org_context: dict[str, Any],
        locale: str = "ko",
    ) -> dict[str, Any]:
        """자연어 솔루션 설명을 구조화된 요구사항 JSON으로 변환한다.

        Args:
            prompt: 사용자가 입력한 솔루션 설명 (자연어)
            org_context: 조직 컨텍스트 (industry, size, existing_stack 등)

        Returns:
            {
                primary_tag, tags, solution_type (=primary_tag for compat),
                features, tech_stack, complexity, target_users, key_requirements
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
            # primary_tag / solution_type 정합성 보장
            if "primary_tag" not in result:
                result["primary_tag"] = result.get("solution_type", "fullstack")
            if "solution_type" not in result:
                result["solution_type"] = result["primary_tag"]
            if "tags" not in result:
                result["tags"] = [result["primary_tag"]]
        except json.JSONDecodeError:
            logger.warning("analyze_solution: Claude 응답 JSON 파싱 실패, 스텁 폴백")
            primary_tag = self.analyze_input(prompt)
            result = {
                "primary_tag": primary_tag,
                "tags": [primary_tag],
                "solution_type": primary_tag,
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
        variant_config: dict[str, Any] | None = None,
        catalog_entry: dict[str, Any] | None = None,
        catalog_references: list[dict[str, Any]] | None = None,
        company_context: dict[str, Any] | None = None,
        avoid_tech_stacks: list[str] | None = None,
        locale: str = "ko",
    ) -> dict[str, Any]:
        """요구사항 기반 UI 구조 JSON(메뉴, 페이지, 컬러, 스택/아키텍처)을 생성한다.

        Args:
            requirements: analyze_solution()의 반환값
            variant_index: 변형 인덱스 (0=추천, 1=대안 스택, 2=대안 아키텍처 등)
            variant_config: 변형별 역할 정보 {role, is_recommended, user_tech_stack}
            catalog_entry: 단일 카탈로그 참조 엔트리 (폴백 베이스라인용)
            catalog_references: RAG 참조용 카탈로그 엔트리 목록 — 있으면 다수 참조 자료로 주입
            company_context: 회사 컨텍스트 — {company_size, industry, business_type,
                main_product, company_description}. 시스템 프롬프트의 회사별 가이드 활성화.

        Returns:
            {tech_stack_tags, architecture_pattern, variant_rationale, is_recommended,
             menu_structure, pages, color_palette, typography, design_style,
             estimated_weeks, team_size, complexity_score, scalability_score,
             monthly_cost_usd, maintenance_difficulty, skill_requirements, match_reasoning}
        """
        cfg = variant_config or {}
        role = cfg.get("role", "user_stack_recommended")
        user_tech_stack: list[str] = list(cfg.get("user_tech_stack") or [])
        is_recommended: bool = bool(cfg.get("is_recommended", variant_index == 0))

        catalog_context = ""
        if catalog_references:
            # 다수 카탈로그 엔트리를 RAG 참조 자료로 직렬화
            refs_text = (
                "\n\nCATALOG REFERENCES (use as reference material"
                " — combine/adapt to best fit user requirements):\n"
            )
            for i, ref in enumerate(catalog_references, 1):
                refs_text += (
                    f"\n[{i}] {ref.get('title', '')} (slug: {ref.get('slug', '')})\n"
                    f"  Design pattern: {ref.get('design_pattern', '')}\n"
                    f"  Architecture: {ref.get('architecture_pattern', '')}\n"
                    f"  Tech stack: {json.dumps(ref.get('tech_stack_tags', []))}\n"
                    f"  Design philosophy: {ref.get('design_philosophy', '')}\n"
                    f"  Pros: {json.dumps(ref.get('pros', []), ensure_ascii=False)}\n"
                    f"  Cons: {json.dumps(ref.get('cons', []), ensure_ascii=False)}\n"
                )
            catalog_context = refs_text
        elif catalog_entry:
            # 단일 엔트리 베이스라인 (하위 호환)
            catalog_context = (
                "\n\nCATALOG REFERENCE (use as baseline, adapt to user requirements):\n"
                f"Title: {catalog_entry.get('title', '')}\n"
                f"Design pattern: {catalog_entry.get('design_pattern', '')}\n"
                f"Architecture pattern: {catalog_entry.get('architecture_pattern', '')}\n"
                f"Tech stack: {json.dumps(catalog_entry.get('tech_stack_tags', []))}\n"
                f"Design philosophy: {catalog_entry.get('design_philosophy', '')}\n"
                f"Pros: {json.dumps(catalog_entry.get('pros', []), ensure_ascii=False)}\n"
                f"Cons: {json.dumps(catalog_entry.get('cons', []), ensure_ascii=False)}\n"
            )

        # 회사 컨텍스트 직렬화 — 시스템 프롬프트의 회사별 가이드에 사용
        company_block = ""
        if company_context:
            company_block = (
                "\n\nCompany context (use to calibrate variant complexity, "
                "team size, cost, and match_reasoning):\n"
                f"  company_size: {company_context.get('company_size') or 'unknown'}\n"
                f"  industry: {company_context.get('industry') or 'unknown'}\n"
                f"  business_type: {company_context.get('business_type') or 'unknown'}\n"
                f"  main_product: {company_context.get('main_product') or 'unknown'}\n"
                f"  company_description: {company_context.get('company_description') or 'unknown'}"
            )

        avoid_block = ""
        if avoid_tech_stacks:
            avoid_block = (
                f"\n\nAVOID these tech stacks (already used by other variants — "
                f"choose meaningfully different alternatives): "
                f"{json.dumps(avoid_tech_stacks, ensure_ascii=False)}"
            )

        user_content = (
            f"Requirements:\n{json.dumps(requirements, ensure_ascii=False)}\n\n"
            f"Variant index: {variant_index}\n"
            f"Variant role: {role}\n"
            f"User preferred tech stack: {json.dumps(user_tech_stack)}\n"
            f"is_recommended: {json.dumps(is_recommended)}"
            f"{company_block}"
            f"{avoid_block}"
            f"{catalog_context}\n\n"
            "Generate a unique UI structure following the variant role instructions. "
            "Calibrate quantitative metrics (estimated_weeks, team_size, complexity_score, "
            "scalability_score, monthly_cost_usd, maintenance_difficulty, skill_requirements) "
            "to the company context. The match_reasoning MUST reference at least one "
            "company attribute (size, industry, or business_type)."
        )

        client = self._get_client()
        message = await client.messages.create(
            model=self._model,
            max_tokens=2048,
            system=_get_system_prompt("generate_ui_structure", locale),
            messages=[{"role": "user", "content": user_content}],
        )

        raw = _extract_text(message)
        try:
            result: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("generate_ui_structure: Claude 응답 JSON 파싱 실패, 스텁 폴백")
            # 정량 지표(복잡도/확장성/필요역량 등)도 채워 3단계 화면이 비지 않게 한다.
            # 키 구조는 PrototypeSession 모델의 @property가 읽는 형태와 일치해야 한다.
            skills = (user_tech_stack or [])[:4] or [
                "백엔드 개발",
                "프론트엔드 개발",
                "DevOps",
            ]
            complexity = max(1, min(10, 4 + (variant_index % 3)))
            scalability = max(1, min(10, 7 - (variant_index % 3)))
            weeks_base = 4 + variant_index
            team_base = 2 + (variant_index % 2)
            cost_base = 300 + variant_index * 150
            result = {
                "tech_stack_tags": user_tech_stack or [],
                "architecture_pattern": "모놀리식 3-tier",
                "variant_rationale": "",
                "is_recommended": is_recommended,
                "menu_structure": {},
                "pages": [],
                "color_palette": {},
                "typography": {},
                "design_style": "minimal",
                "complexity_score": complexity,
                "scalability_score": scalability,
                "skill_requirements": skills,
                "estimated_weeks": {"min": weeks_base, "max": weeks_base + 3},
                "team_size": {
                    "min": team_base,
                    "max": team_base + 1,
                    "roles": ["백엔드", "프론트엔드"],
                },
                "monthly_cost_usd": {"min": cost_base, "max": cost_base + 400},
                "maintenance_difficulty": "중간",
            }
        if "is_recommended" not in result:
            result["is_recommended"] = is_recommended
        return result

    async def recommend_pm(
        self,
        requirements: dict[str, Any],
        prototype_style: str,
        pm_catalog: list[dict[str, Any]],
        locale: str = "ko",
    ) -> dict[str, Any]:
        """요구사항과 프로토타입 스타일에 맞는 PM을 카탈로그에서 추천한다.

        prompt caching: system 블록 + pm_catalog 블록에 ephemeral 캐시 적용.
        같은 카탈로그 기준 2회 연속 요청 시 입력 토큰 비용 ~90% 절감.

        Returns:
            {recommended_pm_id, match_score, reasoning,
             key_strengths, potential_gaps, alternatives[]}
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

        catalog_json = json.dumps(pm_catalog, ensure_ascii=False, default=str)
        requirements_json = json.dumps(requirements, ensure_ascii=False)

        client = self._get_client()
        message = await client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=[
                {
                    "type": "text",
                    "text": _RECOMMEND_PM_SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"PM catalog:\n{catalog_json}",
                            "cache_control": {"type": "ephemeral"},
                        },
                        {
                            "type": "text",
                            "text": (
                                f"Project requirements:\n{requirements_json}\n\n"
                                f"Selected prototype style: {prototype_style}"
                            ),
                        },
                    ],
                }
            ],
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

    # ── 오케스트레이터용 Claude 메서드 ────────────────────────────────────────

    async def decompose_tasks(
        self,
        session_title: str,
        session_description: str | None,
        hints: list[str] | None = None,
        analysis_result: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """세션 제목/설명을 분석해 서브태스크 목록을 생성한다.

        Returns:
            [{"title": str, "description": str, "assigned_role": str}, ...]
        """
        user_text = f"Session title: {session_title}\n"
        if session_description:
            user_text += f"Description: {session_description}\n"
        if hints:
            user_text += f"Hints: {', '.join(hints)}\n"
        if analysis_result:
            user_text += (
                "\nPre-analyzed requirements (이 정보를 활용해 분해 정확도를 높일 것):\n"
                + json.dumps(analysis_result, ensure_ascii=False, indent=2)
                + "\n"
            )

        client = self._get_client()
        message = await client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=[
                {
                    "type": "text",
                    "text": _DECOMPOSE_TASKS_SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_text}],
        )

        raw = _extract_text(message)
        try:
            parsed: list[dict[str, Any]] = json.loads(raw)
            if not isinstance(parsed, list):
                raise ValueError("응답이 배열이 아님")
        except (json.JSONDecodeError, ValueError):
            logger.warning("decompose_tasks: Claude 응답 파싱 실패, 빈 목록 반환")
            return []

        # phase/priority/estimate_hours/depends_on/acceptance_criteria를 description 마크다운에 병합
        result: list[dict[str, Any]] = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            desc_base = str(item.get("description", ""))
            phase = str(item.get("phase", "mvp"))
            priority = str(item.get("priority", "medium"))
            estimate = item.get("estimate_hours")
            depends_on: list[str] = list(item.get("depends_on") or [])
            ac_list: list[str] = list(item.get("acceptance_criteria") or [])

            md_parts = [desc_base]
            md_parts.append(
                f"\n**Phase**: {phase} | **Priority**: {priority}"
                + (f" | **Estimate**: {estimate}h" if estimate is not None else "")
            )
            if depends_on:
                md_parts.append("\n**Depends on**: " + ", ".join(str(d) for d in depends_on))
            if ac_list:
                md_parts.append("\n**Acceptance Criteria**:\n" + "\n".join(f"- {c}" for c in ac_list))  # noqa: E501

            result.append({
                "assigned_role": str(item.get("assigned_role", item.get("role", "architect"))),
                "title": str(item.get("title", ""))[:500],
                "description": "\n".join(md_parts)[:2000],
            })
        return result

    async def generate_draft(
        self,
        subtask_title: str,
        subtask_description: str | None,
        session_context: str,
    ) -> str:
        """서브태스크에 대한 초안 내용을 생성한다.

        Returns:
            마크다운 형식의 한국어 초안 문자열
        """
        user_text = (
            f"## 세션 컨텍스트\n{session_context}\n\n"
            f"## 서브태스크\n"
            f"제목: {subtask_title}\n"
            f"설명: {subtask_description or '없음'}\n\n"
            "위 서브태스크에 대한 초안을 작성해 주세요."
        )

        client = self._get_client()
        message = await client.messages.create(
            model=self._model,
            max_tokens=2048,
            system=[
                {
                    "type": "text",
                    "text": _GENERATE_DRAFT_SYSTEM,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_text}],
        )

        return _extract_text(message)
