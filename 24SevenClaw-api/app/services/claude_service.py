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
# variant_index: 0=추천(사용자 스택), 1=대안 스택, 2=대안 아키텍처
PROTOTYPE_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "saas": [
        {
            "title": "SaaS 표준형 (Next.js + FastAPI + PostgreSQL)",
            "description": "SaaS 서비스의 검증된 풀스택 조합. SSR/SSG와 비동기 API를 결합합니다.",
            "design_pattern": "saas-fullstack",
            "architecture_pattern": "모놀리식 3-tier",
            "tech_stack_tags": ["Next.js", "FastAPI", "PostgreSQL", "Docker"],
            "pros": ["검증된 조합, 레퍼런스 풍부", "SSR로 SEO·초기 로딩 우수", "비동기 API로 높은 처리량"],
            "cons": ["프론트/백 분리 배포로 운영 복잡도↑", "Python 서버 cold start 존재"],
            "ui_structure": {"frontend": "next.js", "backend": "fastapi", "database": "postgresql", "auth": "jwt", "deployment": "docker"},
            "menu_structure": {},
            "color_palette": {},
        },
        {
            "title": "SaaS 경량형 (Vue.js + Django + PostgreSQL)",
            "description": "Django의 강력한 ORM과 Vue.js의 반응형 UI를 조합한 대안 스택.",
            "design_pattern": "saas-django",
            "architecture_pattern": "MVC 모놀리식",
            "tech_stack_tags": ["Vue.js", "Django", "PostgreSQL", "Nginx"],
            "pros": ["Django 어드민으로 백오피스 즉시 확보", "배터리-인클루디드 프레임워크", "Python 생태계 재사용"],
            "cons": ["GIL로 동시성 제약", "Django REST Framework 설정 verbose"],
            "ui_structure": {"frontend": "vue.js", "backend": "django", "database": "postgresql", "auth": "session", "deployment": "nginx"},
            "menu_structure": {},
            "color_palette": {},
        },
        {
            "title": "SaaS 서버리스형 (React + AWS Lambda + DynamoDB)",
            "description": "서버 관리 없이 트래픽에 따라 자동 스케일링되는 서버리스 아키텍처.",
            "design_pattern": "saas-serverless",
            "architecture_pattern": "서버리스 이벤트 기반",
            "tech_stack_tags": ["React", "AWS Lambda", "DynamoDB", "API Gateway"],
            "pros": ["트래픽 0일 때 비용 없음", "인프라 관리 최소화", "자동 스케일링"],
            "cons": ["Cold start 지연 (첫 요청)", "복잡한 트랜잭션 처리 어려움", "벤더 락인(AWS)"],
            "ui_structure": {"frontend": "react", "backend": "aws-lambda", "database": "dynamodb", "auth": "cognito", "deployment": "serverless"},
            "menu_structure": {},
            "color_palette": {},
        },
    ],
    "rest-api": [
        {
            "title": "REST API 표준형 (FastAPI + PostgreSQL)",
            "description": "자동 OpenAPI 문서와 비동기 처리가 강점인 Python REST API.",
            "design_pattern": "api-first",
            "architecture_pattern": "API-first 모놀리식",
            "tech_stack_tags": ["FastAPI", "PostgreSQL", "Redis", "Docker"],
            "pros": ["자동 OpenAPI/Swagger 문서", "비동기로 높은 처리량", "Pydantic 검증 내장"],
            "cons": ["Python 생태계 의존", "대규모 시 수평 확장 설계 필요"],
            "ui_structure": {"framework": "fastapi", "database": "postgresql", "auth": "jwt", "docs": "openapi", "deployment": "docker"},
            "menu_structure": {},
            "color_palette": {},
        },
        {
            "title": "REST API Node.js형 (Express + MongoDB)",
            "description": "유연한 스키마와 JS 풀스택이 강점인 Node.js API 서버.",
            "design_pattern": "api-nodejs",
            "architecture_pattern": "API-first 모놀리식",
            "tech_stack_tags": ["Express", "MongoDB", "Node.js", "Docker"],
            "pros": ["JS 단일 언어로 프론트/백 통일", "유연한 스키마 설계", "npm 생태계 방대"],
            "cons": ["타입 안전성 약함 (TS 필수)", "MongoDB 트랜잭션 제약"],
            "ui_structure": {"framework": "express", "database": "mongodb", "auth": "jwt", "docs": "swagger", "deployment": "docker"},
            "menu_structure": {},
            "color_palette": {},
        },
        {
            "title": "REST API 고성능형 (Go Gin + PostgreSQL)",
            "description": "초저지연·고처리량이 필요한 API에 최적화된 Go 기반 구성.",
            "design_pattern": "api-go",
            "architecture_pattern": "마이크로서비스 지향",
            "tech_stack_tags": ["Go", "Gin", "PostgreSQL", "gRPC", "Kubernetes"],
            "pros": ["초고속 처리량 (동시 수만 req)", "메모리 효율 최고", "컴파일 타입 안전성"],
            "cons": ["Go 개발자 채용 풀 협소", "초기 개발 속도 느림", "제네릭 생태계 아직 성숙 중"],
            "ui_structure": {"framework": "gin", "database": "postgresql", "auth": "jwt", "deployment": "kubernetes"},
            "menu_structure": {},
            "color_palette": {},
        },
    ],
    "fullstack": [
        {
            "title": "풀스택 표준형 (Next.js + FastAPI + PostgreSQL)",
            "description": "프론트/백 분리 배포의 검증된 풀스택 구성.",
            "design_pattern": "fullstack-separated",
            "architecture_pattern": "풀스택 분리 배포",
            "tech_stack_tags": ["Next.js", "FastAPI", "PostgreSQL", "Docker Compose"],
            "pros": ["프론트/백 독립 배포·스케일링", "각 레이어 최적 기술 선택", "타입 공유 가능"],
            "cons": ["CORS·API 연동 설정 필요", "두 런타임 관리"],
            "ui_structure": {"frontend": "next.js", "backend": "fastapi", "database": "postgresql", "auth": "jwt", "deployment": "docker-compose"},
            "menu_structure": {},
            "color_palette": {},
        },
        {
            "title": "풀스택 통합형 (Remix + Prisma + PostgreSQL)",
            "description": "서버 컴포넌트와 로더로 프론트/백을 통합하는 현대적 풀스택.",
            "design_pattern": "fullstack-remix",
            "architecture_pattern": "풀스택 통합 SSR",
            "tech_stack_tags": ["Remix", "Prisma", "PostgreSQL", "Fly.io"],
            "pros": ["서버/클라이언트 코드 통합", "Form 기반 데이터 뮤테이션 내장", "빠른 페이지 전환"],
            "cons": ["Remix 학습 곡선", "생태계가 Next.js 대비 작음"],
            "ui_structure": {"frontend": "remix", "backend": "remix-loaders", "database": "postgresql", "orm": "prisma", "auth": "remix-auth", "deployment": "fly.io"},
            "menu_structure": {},
            "color_palette": {},
        },
        {
            "title": "풀스택 BaaS형 (Next.js + Supabase)",
            "description": "Supabase로 DB·Auth·Storage를 일괄 관리하는 서버리스 풀스택.",
            "design_pattern": "fullstack-baas",
            "architecture_pattern": "BaaS 기반 서버리스",
            "tech_stack_tags": ["Next.js", "Supabase", "PostgreSQL", "Vercel"],
            "pros": ["백엔드 코드 거의 불필요", "실시간 구독·Auth 즉시 사용", "Vercel+Supabase 무료 티어"],
            "cons": ["Supabase 벤더 의존", "복잡한 비즈니스 로직 구현 제약", "Row-level security 설계 필요"],
            "ui_structure": {"frontend": "next.js", "backend": "supabase", "database": "supabase-postgres", "auth": "supabase-auth", "deployment": "vercel"},
            "menu_structure": {},
            "color_palette": {},
        },
    ],
    "internal-tool": [
        {
            "title": "내부 도구 표준형 (React Admin + FastAPI)",
            "description": "CRUD 중심 관리 도구에 최적화된 React Admin + FastAPI 구성.",
            "design_pattern": "admin-dashboard",
            "architecture_pattern": "어드민 대시보드",
            "tech_stack_tags": ["React Admin", "FastAPI", "PostgreSQL", "Docker"],
            "pros": ["CRUD UI 자동 생성", "권한 관리 내장", "빠른 MVP 출시"],
            "cons": ["커스텀 UI 자유도 제한", "React Admin 의존성 큼"],
            "ui_structure": {"frontend": "react-admin", "backend": "fastapi", "database": "postgresql", "auth": "ldap", "deployment": "docker"},
            "menu_structure": {},
            "color_palette": {},
        },
        {
            "title": "내부 도구 로우코드형 (Retool + PostgreSQL)",
            "description": "개발 없이 드래그&드롭으로 내부 도구를 구성하는 로우코드 접근.",
            "design_pattern": "lowcode-tool",
            "architecture_pattern": "로우코드 플랫폼",
            "tech_stack_tags": ["Retool", "PostgreSQL", "REST API 연동"],
            "pros": ["개발 시간 90% 단축", "비개발자도 유지보수 가능", "다양한 DB·API 커넥터"],
            "cons": ["Retool 라이선스 비용", "복잡한 로직 구현 한계", "벤더 의존"],
            "ui_structure": {"frontend": "retool", "backend": "retool-queries", "database": "postgresql", "auth": "retool-auth", "deployment": "retool-cloud"},
            "menu_structure": {},
            "color_palette": {},
        },
        {
            "title": "내부 도구 자체 개발형 (Next.js + Supabase)",
            "description": "완전한 커스텀 UI가 필요한 내부 도구를 자체 개발하는 구성.",
            "design_pattern": "custom-internal",
            "architecture_pattern": "BaaS 기반 커스텀",
            "tech_stack_tags": ["Next.js", "Supabase", "shadcn/ui", "Vercel"],
            "pros": ["완전한 UI 자유도", "shadcn/ui 고품질 컴포넌트", "실시간 기능 즉시 사용"],
            "cons": ["초기 개발 공수↑", "보안 설계 직접 책임"],
            "ui_structure": {"frontend": "next.js", "backend": "supabase", "database": "supabase-postgres", "auth": "supabase-auth", "deployment": "vercel"},
            "menu_structure": {},
            "color_palette": {},
        },
    ],
    "mvp": [
        {
            "title": "MVP 빠른 배포형 (Next.js + Vercel)",
            "description": "Next.js 단일 프레임워크로 최단 시간 출시에 최적화된 MVP.",
            "design_pattern": "mvp-monolith",
            "architecture_pattern": "풀스택 모놀리식",
            "tech_stack_tags": ["Next.js", "Prisma", "SQLite→PostgreSQL", "Vercel"],
            "pros": ["push 즉시 Vercel 배포", "프론트/백 코드 통합", "무료 티어로 시작 가능"],
            "cons": ["트래픽 증가 시 리팩토링 필요", "API Routes 성능 한계"],
            "ui_structure": {"frontend": "next.js", "backend": "next.js-api-routes", "database": "sqlite", "auth": "next-auth", "deployment": "vercel"},
            "menu_structure": {},
            "color_palette": {},
        },
        {
            "title": "MVP 서버 렌더링형 (Flask + HTMX)",
            "description": "SPA 없이 서버 렌더링으로 구현하는 초경량 MVP.",
            "design_pattern": "mvp-server-rendered",
            "architecture_pattern": "서버 사이드 렌더링",
            "tech_stack_tags": ["Flask", "HTMX", "SQLite", "Railway"],
            "pros": ["JS 최소화, 빠른 로딩", "단일 Python 코드베이스", "Railway 무료 배포"],
            "cons": ["복잡한 인터랙션 구현 제약", "SPA 수준 UX 불가"],
            "ui_structure": {"frontend": "htmx", "backend": "flask", "database": "sqlite", "auth": "session", "deployment": "railway"},
            "menu_structure": {},
            "color_palette": {},
        },
        {
            "title": "MVP 노코드형 (Firebase + React)",
            "description": "Firebase BaaS로 백엔드를 대체하고 React로 빠르게 UI 구성.",
            "design_pattern": "mvp-firebase",
            "architecture_pattern": "BaaS 서버리스",
            "tech_stack_tags": ["React", "Firebase", "Firestore", "Firebase Hosting"],
            "pros": ["Auth·DB·Hosting 원스톱", "실시간 DB 즉시 사용", "무료 시작 가능"],
            "cons": ["Firebase 벤더 락인", "복잡한 쿼리 제약", "비용 예측 어려움"],
            "ui_structure": {"frontend": "react", "backend": "firebase", "database": "firestore", "auth": "firebase-auth", "deployment": "firebase-hosting"},
            "menu_structure": {},
            "color_palette": {},
        },
    ],
}

# 기본 템플릿 (매칭 안 될 때) — 3-variant 구조
DEFAULT_TEMPLATES: list[dict[str, Any]] = [
    {
        "title": "범용 풀스택 (Next.js + FastAPI)",
        "description": "범용적인 웹 애플리케이션의 검증된 조합.",
        "design_pattern": "fullstack-separated",
        "architecture_pattern": "풀스택 분리 배포",
        "tech_stack_tags": ["Next.js", "FastAPI", "PostgreSQL", "Docker"],
        "pros": ["검증된 조합, 레퍼런스 풍부", "프론트/백 독립 스케일링", "타입 안전성 우수"],
        "cons": ["두 런타임 관리 필요", "CORS 설정 초기 공수"],
        "ui_structure": {"frontend": "next.js", "backend": "fastapi", "database": "postgresql", "auth": "jwt", "deployment": "docker"},
        "menu_structure": {},
        "color_palette": {},
    },
    {
        "title": "범용 Node.js형 (Express + React + MongoDB)",
        "description": "JS 단일 언어로 풀스택을 구성하는 대안 조합.",
        "design_pattern": "js-fullstack",
        "architecture_pattern": "MERN 스택",
        "tech_stack_tags": ["React", "Express", "MongoDB", "Node.js"],
        "pros": ["JS 단일 언어 사용", "npm 생태계 방대", "유연한 스키마"],
        "cons": ["MongoDB 트랜잭션 제약", "타입 안전성 TS 설정 필요"],
        "ui_structure": {"frontend": "react", "backend": "express", "database": "mongodb", "auth": "jwt", "deployment": "docker"},
        "menu_structure": {},
        "color_palette": {},
    },
    {
        "title": "범용 서버리스형 (Next.js + Supabase)",
        "description": "인프라 관리 없이 빠르게 구축하는 BaaS 기반 구성.",
        "design_pattern": "baas-serverless",
        "architecture_pattern": "BaaS 기반 서버리스",
        "tech_stack_tags": ["Next.js", "Supabase", "PostgreSQL", "Vercel"],
        "pros": ["서버 관리 불필요", "Auth·DB·Storage 즉시 사용", "빠른 배포"],
        "cons": ["벤더 의존", "복잡한 로직 구현 한계"],
        "ui_structure": {"frontend": "next.js", "backend": "supabase", "database": "supabase-postgres", "auth": "supabase-auth", "deployment": "vercel"},
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
    "(0) a popular mainstream stack, (1) a JS-ecosystem alternative, (2) a serverless/BaaS approach.\n\n"
    "PROS AND CONS: For each variant, list 2-3 concise pros and 1-2 cons specific to this "
    "stack+architecture combination in the context of the given solution.\n\n"
    "IMPORTANT: Always respond with valid JSON only "
    "— no markdown, no code blocks, no extra text.\n\n"
    "Return exactly this JSON structure:\n"
    "{\n"
    '  "tech_stack_tags": ["<tech 1>", "<tech 2>", "<tech 3>"],\n'
    '  "architecture_pattern": "<human-readable pattern in Korean, e.g. 모놀리식 3-tier | 마이크로서비스 | 서버리스>",\n'
    '  "variant_rationale": "<1-2 sentences in Korean explaining why this stack+architecture fits>",\n'
    '  "is_recommended": <true|false>,\n'
    '  "pros": ["<장점 1>", "<장점 2>", "<장점 3>"],\n'
    '  "cons": ["<단점 1>", "<단점 2>"],\n'
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
    "You are a software project orchestrator specializing in decomposing "
    "development sessions into focused subtasks for an AI team.\n\n"
    "Given a session title and description, create 2-5 focused subtasks. "
    "Each subtask must be assigned to exactly one of these roles: "
    "architect, frontend, backend, qa, security, devops, reviewer.\n\n"
    "Rules:\n"
    "- Cover all clearly implied technical domains; omit unrelated ones.\n"
    "- If unsure, use the default set: architect → backend → qa.\n"
    "- Write titles and descriptions in Korean.\n\n"
    "IMPORTANT: Always respond with valid JSON only "
    "— no markdown, no code blocks, no extra text.\n\n"
    "Return exactly this JSON structure (array):\n"
    "[\n"
    "  {\n"
    '    "title": "<concise subtask title in Korean>",\n'
    '    "description": "<what this subtask should accomplish, 1-2 sentences>",\n'
    '    "assigned_role": "<one of: architect, frontend, backend, qa, security, devops, reviewer>"\n'
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
        variant_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """요구사항 기반 UI 구조 JSON(메뉴, 페이지, 컬러, 스택/아키텍처)을 생성한다.

        Args:
            requirements: analyze_solution()의 반환값
            variant_index: 변형 인덱스 (0=추천, 1=대안 스택, 2=대안 아키텍처)
            variant_config: 변형별 역할 정보 {role, is_recommended, user_tech_stack}

        Returns:
            {tech_stack_tags, architecture_pattern, variant_rationale, is_recommended,
             menu_structure, pages, color_palette, typography, design_style}
        """
        cfg = variant_config or {}
        role = cfg.get("role", "user_stack_recommended")
        user_tech_stack: list[str] = list(cfg.get("user_tech_stack") or [])
        is_recommended: bool = bool(cfg.get("is_recommended", variant_index == 0))

        user_content = (
            f"Requirements:\n{json.dumps(requirements, ensure_ascii=False)}\n\n"
            f"Variant index: {variant_index}\n"
            f"Variant role: {role}\n"
            f"User preferred tech stack: {json.dumps(user_tech_stack)}\n"
            f"is_recommended: {json.dumps(is_recommended)}\n\n"
            "Generate a unique UI structure following the variant role instructions. "
            "Ensure tech_stack_tags, architecture_pattern, variant_rationale, "
            "and is_recommended are included in the response."
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
                "tech_stack_tags": user_tech_stack or [],
                "architecture_pattern": "모놀리식 3-tier",
                "variant_rationale": "",
                "is_recommended": is_recommended,
                "menu_structure": {},
                "pages": [],
                "color_palette": {},
                "typography": {},
                "design_style": "minimal",
            }
        # is_recommended가 누락된 경우 role 기반으로 채움
        if "is_recommended" not in result:
            result["is_recommended"] = is_recommended
        return result

    async def recommend_pm(
        self,
        requirements: dict[str, Any],
        prototype_style: str,
        pm_catalog: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """요구사항과 프로토타입 스타일에 맞는 PM을 카탈로그에서 추천한다.

        prompt caching: system 블록 + pm_catalog 블록에 ephemeral 캐시 적용.
        같은 카탈로그 기준 2회 연속 요청 시 입력 토큰 비용 ~90% 절감.

        Returns:
            {recommended_pm_id, match_score, reasoning, key_strengths, potential_gaps, alternatives[]}
            alternatives 각 항목도 match_score(0-100) 포함.
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

        client = self._get_client()
        message = await client.messages.create(
            model=self._model,
            max_tokens=1024,
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
            result: list[dict[str, Any]] = json.loads(raw)
            if not isinstance(result, list):
                raise ValueError("응답이 배열이 아님")
        except (json.JSONDecodeError, ValueError):
            logger.warning("decompose_tasks: Claude 응답 파싱 실패, 빈 목록 반환")
            result = []
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
