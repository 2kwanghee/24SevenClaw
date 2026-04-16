"""Claude AI 연동 서비스 (Phase 2: 규칙 기반 스텁).

Phase 3에서 실제 Claude API 연동으로 교체 예정.
현재는 솔루션 유형 기반 규칙 매칭으로 프로토타입을 생성한다.
"""

from typing import Any

# 솔루션 유형별 프로토타입 템플릿
PROTOTYPE_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "saas": [
        {
            "name": "SaaS 풀스택 (Next.js + FastAPI)",
            "solution_type": "saas",
            "config": {
                "frontend": "next.js",
                "backend": "fastapi",
                "database": "postgresql",
                "auth": "jwt",
                "deployment": "docker",
            },
            "reasoning": "SaaS 서비스에 최적화된 풀스택 구성입니다. "
            "Next.js의 SSR/SSG와 FastAPI의 고성능 비동기 처리를 결합합니다.",
        },
        {
            "name": "SaaS 경량 (React + Express)",
            "solution_type": "saas",
            "config": {
                "frontend": "react",
                "backend": "express",
                "database": "postgresql",
                "auth": "session",
                "deployment": "docker",
            },
            "reasoning": "빠른 프로토타이핑에 적합한 경량 SaaS 구성입니다. "
            "React SPA와 Express의 간결한 API 서버를 활용합니다.",
        },
    ],
    "rest-api": [
        {
            "name": "REST API (FastAPI + PostgreSQL)",
            "solution_type": "rest-api",
            "config": {
                "framework": "fastapi",
                "database": "postgresql",
                "auth": "jwt",
                "docs": "openapi",
                "deployment": "docker",
            },
            "reasoning": "고성능 REST API에 최적화된 구성입니다. "
            "FastAPI의 자동 문서 생성과 비동기 처리를 활용합니다.",
        },
        {
            "name": "REST API (Express + MongoDB)",
            "solution_type": "rest-api",
            "config": {
                "framework": "express",
                "database": "mongodb",
                "auth": "jwt",
                "docs": "swagger",
                "deployment": "docker",
            },
            "reasoning": "유연한 스키마가 필요한 API에 적합한 구성입니다. "
            "MongoDB의 문서 기반 저장소와 Express의 미들웨어 생태계를 활용합니다.",
        },
    ],
    "fullstack": [
        {
            "name": "풀스택 (Next.js + FastAPI)",
            "solution_type": "fullstack",
            "config": {
                "frontend": "next.js",
                "backend": "fastapi",
                "database": "postgresql",
                "auth": "jwt",
                "deployment": "docker-compose",
            },
            "reasoning": "풀스택 애플리케이션의 표준 구성입니다. "
            "Next.js의 풀스택 기능과 FastAPI의 고성능 API를 결합합니다.",
        },
        {
            "name": "풀스택 (Next.js + Prisma)",
            "solution_type": "fullstack",
            "config": {
                "frontend": "next.js",
                "backend": "next.js-api-routes",
                "database": "postgresql",
                "orm": "prisma",
                "auth": "next-auth",
                "deployment": "vercel",
            },
            "reasoning": "Next.js 단일 프레임워크로 프론트/백을 통합하는 구성입니다. "
            "Prisma ORM과 NextAuth로 빠르게 풀스택을 구축합니다.",
        },
    ],
    "internal-tool": [
        {
            "name": "내부 도구 (React Admin + FastAPI)",
            "solution_type": "internal-tool",
            "config": {
                "frontend": "react-admin",
                "backend": "fastapi",
                "database": "postgresql",
                "auth": "ldap",
                "deployment": "docker",
            },
            "reasoning": "내부 관리 도구에 최적화된 구성입니다. "
            "React Admin의 CRUD UI와 FastAPI의 빠른 API 개발을 결합합니다.",
        },
    ],
    "mvp": [
        {
            "name": "MVP (Next.js 풀스택)",
            "solution_type": "mvp",
            "config": {
                "frontend": "next.js",
                "backend": "next.js-api-routes",
                "database": "sqlite",
                "auth": "next-auth",
                "deployment": "vercel",
            },
            "reasoning": "최소 기능 제품을 빠르게 출시하기 위한 구성입니다. "
            "Next.js 하나로 프론트/백을 구현하고 Vercel로 즉시 배포합니다.",
        },
        {
            "name": "MVP (Flask + HTMX)",
            "solution_type": "mvp",
            "config": {
                "frontend": "htmx",
                "backend": "flask",
                "database": "sqlite",
                "auth": "session",
                "deployment": "railway",
            },
            "reasoning": "최소 복잡도로 동작하는 MVP 구성입니다. "
            "Flask + HTMX로 SPA 없이 인터랙티브한 웹 앱을 구현합니다.",
        },
    ],
}

# 기본 템플릿 (매칭 안 될 때)
DEFAULT_TEMPLATES: list[dict[str, Any]] = [
    {
        "name": "범용 웹 애플리케이션 (Next.js + FastAPI)",
        "solution_type": "custom",
        "config": {
            "frontend": "next.js",
            "backend": "fastapi",
            "database": "postgresql",
            "auth": "jwt",
            "deployment": "docker",
        },
        "reasoning": "범용적인 웹 애플리케이션 구성입니다. "
        "Next.js와 FastAPI의 검증된 조합을 활용합니다.",
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


class ClaudeService:
    """Claude AI 분석 서비스 (Phase 2: 규칙 기반 스텁).

    Phase 3에서 실제 Claude API로 교체 예정.
    """

    def analyze_input(self, user_input: dict[str, Any]) -> str:
        """사용자 입력에서 솔루션 유형을 추출한다.

        user_input 구조:
            - company_name: str
            - description: str (자연어 설명)
            - business_type: str (optional)
        """
        description = str(user_input.get("description", "")).lower()
        business_type = str(user_input.get("business_type", "")).lower()

        text = f"{description} {business_type}"

        # 키워드 매칭으로 솔루션 유형 결정
        for keyword, solution_type in KEYWORD_TYPE_MAP.items():
            if keyword in text:
                return solution_type

        return "fullstack"  # 기본값

    def generate_prototypes(
        self, solution_type: str, user_input: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """솔루션 유형에 맞는 프로토타입 템플릿을 반환한다."""
        templates = PROTOTYPE_TEMPLATES.get(solution_type, DEFAULT_TEMPLATES)
        return [dict(t) for t in templates]

    def recommend_pm_scores(
        self, solution_type: str, pm_specialties: list[str]
    ) -> dict[str, int]:
        """솔루션 유형에 따른 PM specialty 별 매칭 점수를 반환한다.

        Returns:
            dict[specialty, score(0~100)]
        """
        # 솔루션 유형 → 선호 specialty 매핑
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
