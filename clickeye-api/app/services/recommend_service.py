"""솔루션 유형 기반 규칙 매칭 추천 서비스."""

from typing import Any

from app.services.catalog_service import CatalogService

# 추천 서비스 전용 workflow 스킬 정의 (공개 catalog /skills와는 별도)
_WORKFLOW_SKILLS_CATALOG: list[dict[str, Any]] = [
    {
        "id": "tdd-smart-coding",
        "name": "TDD Smart Coding",
        "description": "테스트 주도 개발 워크플로 스킬",
        "type": "workflow",
        "category": "development",
    },
    {
        "id": "fullstack",
        "name": "Fullstack Development",
        "description": "풀스택 개발 워크플로 (FastAPI + Next.js)",
        "type": "workflow",
        "category": "development",
    },
    {
        "id": "code-review",
        "name": "Code Review",
        "description": "AI 기반 코드 리뷰 자동화",
        "type": "workflow",
        "category": "quality",
    },
    {
        "id": "github-mcp",
        "name": "GitHub MCP",
        "description": "GitHub 연동 외부 도구 (이슈, PR, 리뷰)",
        "type": "external-tool",
        "category": "integration",
    },
    {
        "id": "linear-mcp",
        "name": "Linear MCP",
        "description": "Linear 프로젝트 관리 연동",
        "type": "external-tool",
        "category": "integration",
    },
    {
        "id": "database",
        "name": "Database",
        "description": "데이터베이스 직접 연결 (PostgreSQL, MySQL, SQLite)",
        "type": "external-tool",
        "category": "integration",
    },
]

# 솔루션 유형 → 추천 에이전트 ID 매핑
AGENT_RULES: dict[str, list[str]] = {
    "saas": ["claude-code", "cursor"],
    "rest-api": ["claude-code", "codex"],
    "cli-tool": ["claude-code", "gemini-cli"],
    "data-pipeline": ["claude-code", "gemini-cli"],
    "mobile-app": ["cursor", "gemini-cli"],
    "fullstack": ["claude-code", "cursor"],
    "backend": ["claude-code", "codex"],
    "frontend": ["cursor", "claude-code"],
    "library": ["claude-code", "gemini-cli", "codex"],
    "automation": ["claude-code", "gemini-cli"],
}

# 솔루션 유형 → 추천 스킬 ID 매핑
SKILL_RULES: dict[str, list[str]] = {
    "saas": ["fullstack", "tdd-smart-coding", "code-review", "github-mcp"],
    "rest-api": ["tdd-smart-coding", "code-review", "database"],
    "cli-tool": ["tdd-smart-coding", "code-review"],
    "data-pipeline": ["tdd-smart-coding", "database"],
    "mobile-app": ["fullstack", "code-review", "github-mcp"],
    "fullstack": ["fullstack", "tdd-smart-coding", "code-review", "github-mcp"],
    "backend": ["tdd-smart-coding", "code-review", "database"],
    "frontend": ["fullstack", "code-review", "github-mcp"],
    "library": ["tdd-smart-coding", "code-review", "github-mcp"],
    "automation": ["tdd-smart-coding", "code-review", "linear-mcp"],
}

# 솔루션 유형 → 추천 파이프라인 ID 매핑
PIPELINE_RULES: dict[str, list[str]] = {
    "saas": ["harness", "tdd", "ai-critique", "lint-gate"],
    "rest-api": ["harness", "tdd", "lint-gate"],
    "cli-tool": ["tdd", "lint-gate"],
    "data-pipeline": ["tdd", "lint-gate"],
    "mobile-app": ["ai-critique", "lint-gate"],
    "fullstack": ["harness", "tdd", "ai-critique", "lint-gate"],
    "backend": ["harness", "tdd", "lint-gate"],
    "frontend": ["ai-critique", "lint-gate"],
    "library": ["tdd", "lint-gate", "ai-critique"],
    "automation": ["harness", "ralph-loop", "lint-gate"],
}

# ── 추천 사유 (reasoning) ──

AGENT_REASONING: dict[str, dict[str, str]] = {
    "saas": {
        "claude-code": "SaaS는 복잡한 백엔드 로직과 API 설계가 핵심이므로 Claude Code가 적합합니다",
        "cursor": "프론트엔드 UI 작업이 많은 SaaS에서 IDE 통합 환경이 개발 속도를 높여줍니다",
    },
    "rest-api": {
        "claude-code": (
            "REST API 설계와 엔드포인트 구현에"
            " Claude Code의 체계적인 코드 생성이 효과적입니다"
        ),
        "codex": "반복적인 CRUD 엔드포인트 생성에 Codex의 빠른 코드 완성이 효율적입니다",
    },
    "cli-tool": {
        "claude-code": "CLI 커맨드 파싱과 옵션 처리에 Claude Code의 정확한 구현이 적합합니다",
        "gemini-cli": "CLI 환경에서 직접 사용하므로 Gemini CLI와의 워크플로 통합이 자연스럽습니다",
    },
    "data-pipeline": {
        "claude-code": "데이터 파이프라인의 복잡한 변환 로직에 Claude Code가 효과적입니다",
        "gemini-cli": "대용량 데이터 처리 스크립트 작성에 Gemini CLI의 터미널 통합이 편리합니다",
    },
    "mobile-app": {
        "cursor": "모바일 UI 개발에 Cursor의 실시간 프리뷰와 IDE 지원이 생산성을 높여줍니다",
        "gemini-cli": "크로스 플랫폼 설정과 빌드 스크립트 관리에 Gemini CLI가 유용합니다",
    },
    "fullstack": {
        "claude-code": "풀스택의 백엔드와 프론트엔드를 아우르는 코드 생성에 적합합니다",
        "cursor": "프론트엔드 UI 작업과 실시간 미리보기에 Cursor IDE가 효과적입니다",
    },
    "backend": {
        "claude-code": "백엔드 아키텍처 설계와 서비스 로직 구현에 Claude Code가 최적입니다",
        "codex": "데이터 모델과 CRUD 패턴의 빠른 생성에 Codex가 효율적입니다",
    },
    "frontend": {
        "cursor": "UI 컴포넌트 개발에 Cursor의 실시간 편집과 프리뷰가 탁월합니다",
        "claude-code": "복잡한 상태 관리와 비즈니스 로직 구현에 Claude Code가 도움됩니다",
    },
    "library": {
        "claude-code": "라이브러리 API 설계와 타입 시스템 구현에 Claude Code가 적합합니다",
        "gemini-cli": "문서 생성과 예제 코드 작성에 Gemini CLI의 빠른 반복이 유용합니다",
        "codex": "보일러플레이트 코드와 유틸리티 함수 생성에 Codex가 효율적입니다",
    },
    "automation": {
        "claude-code": "자동화 스크립트의 복잡한 조건 로직에 Claude Code가 정확합니다",
        "gemini-cli": "CLI 기반 자동화 워크플로에 Gemini CLI가 자연스럽게 통합됩니다",
    },
}

SKILL_REASONING: dict[str, dict[str, str]] = {
    "saas": {
        "fullstack": "SaaS는 프론트+백엔드 통합이 필수이므로 풀스택 워크플로가 효율적입니다",
        "tdd-smart-coding": "SaaS의 안정적인 배포를 위해 TDD 기반 개발이 품질을 보장합니다",
        "code-review": "다수 모듈이 연동되는 SaaS에서 코드 리뷰가 버그를 사전에 차단합니다",
        "github-mcp": "SaaS 팀 협업에 GitHub 통합이 코드 관리를 효율화합니다",
    },
    "rest-api": {
        "tdd-smart-coding": "API 엔드포인트의 계약 준수를 TDD로 검증하여 안정성을 높입니다",
        "code-review": "API 설계의 일관성과 보안을 코드 리뷰로 확보합니다",
        "database": "REST API는 데이터베이스 연동이 핵심이므로 DB 스킬이 필수입니다",
    },
    "cli-tool": {
        "tdd-smart-coding": "CLI 명령어의 입출력을 TDD로 검증하여 안정성을 확보합니다",
        "code-review": "CLI 인터페이스의 사용성을 코드 리뷰로 개선합니다",
    },
    "data-pipeline": {
        "tdd-smart-coding": "데이터 변환 로직의 정확성을 TDD로 보장합니다",
        "database": "파이프라인의 데이터 소스/싱크 관리에 DB 스킬이 필수입니다",
    },
    "mobile-app": {
        "fullstack": "모바일 앱의 프론트+백엔드 연동에 풀스택 워크플로가 필요합니다",
        "code-review": "모바일 UI의 사용성과 성능을 코드 리뷰로 확보합니다",
        "github-mcp": "앱 릴리즈 관리에 GitHub 통합이 유용합니다",
    },
    "fullstack": {
        "fullstack": "풀스택 프로젝트에 풀스택 개발 워크플로가 최적입니다",
        "tdd-smart-coding": "프론트+백엔드 양쪽의 테스트 커버리지를 TDD로 확보합니다",
        "code-review": "다층 아키텍처의 코드 품질을 리뷰로 유지합니다",
        "github-mcp": "팀 협업과 코드 관리에 GitHub 통합이 효율적입니다",
    },
    "backend": {
        "tdd-smart-coding": "서비스 로직의 정확성을 TDD로 검증합니다",
        "code-review": "API 설계와 보안을 코드 리뷰로 강화합니다",
        "database": "백엔드의 데이터 모델링과 쿼리 최적화에 DB 스킬이 핵심입니다",
    },
    "frontend": {
        "fullstack": "프론트엔드에서도 API 연동이 필요하므로 풀스택 워크플로가 유용합니다",
        "code-review": "UI 컴포넌트의 접근성과 성능을 코드 리뷰로 확인합니다",
        "github-mcp": "컴포넌트 라이브러리 관리에 GitHub 통합이 편리합니다",
    },
    "library": {
        "tdd-smart-coding": "라이브러리 API의 계약을 TDD로 검증하여 하위 호환성을 보장합니다",
        "code-review": "공개 API의 설계 품질을 코드 리뷰로 확보합니다",
        "github-mcp": "오픈소스 라이브러리 배포와 이슈 관리에 GitHub 통합이 필수입니다",
    },
    "automation": {
        "tdd-smart-coding": "자동화 스크립트의 예외 처리를 TDD로 검증합니다",
        "code-review": "자동화 워크플로의 신뢰성을 코드 리뷰로 확인합니다",
        "linear-mcp": "자동화 태스크를 Linear로 추적하여 진행 상황을 관리합니다",
    },
}

PIPELINE_REASONING: dict[str, dict[str, str]] = {
    "saas": {
        "harness": "SaaS의 다층 아키텍처에서 4단계 품질 통제가 안정적인 배포를 보장합니다",
        "tdd": "핵심 비즈니스 로직의 정확성을 TDD 파이프라인으로 검증합니다",
        "ai-critique": "복잡한 SaaS 코드를 AI 리뷰로 품질을 한 단계 높입니다",
        "lint-gate": "코드 일관성과 스타일을 린트 게이트로 자동 통제합니다",
    },
    "rest-api": {
        "harness": "API 엔드포인트의 품질을 하네스 파이프라인으로 체계적으로 관리합니다",
        "tdd": "API 계약과 응답 형식을 TDD로 보장합니다",
        "lint-gate": "API 코드의 일관성을 린트 게이트로 유지합니다",
    },
    "cli-tool": {
        "tdd": "CLI 명령어의 동작을 TDD 파이프라인으로 자동 검증합니다",
        "lint-gate": "CLI 코드의 품질을 린트 게이트로 통제합니다",
    },
    "data-pipeline": {
        "tdd": "데이터 변환의 정확성을 TDD 파이프라인으로 검증합니다",
        "lint-gate": "파이프라인 코드의 일관성을 린트 게이트로 유지합니다",
    },
    "mobile-app": {
        "ai-critique": "모바일 UI 코드를 AI 리뷰로 사용성과 성능을 개선합니다",
        "lint-gate": "크로스 플랫폼 코드의 일관성을 린트 게이트로 통제합니다",
    },
    "fullstack": {
        "harness": "풀스택 프로젝트의 복잡성을 하네스 4단계 통제로 관리합니다",
        "tdd": "프론트+백엔드 양쪽의 테스트를 TDD 파이프라인으로 자동화합니다",
        "ai-critique": "다층 코드의 품질을 AI 리뷰로 종합적으로 평가합니다",
        "lint-gate": "프로젝트 전체의 코드 일관성을 린트 게이트로 통제합니다",
    },
    "backend": {
        "harness": "서버 로직의 안정성을 하네스 파이프라인으로 체계적으로 확보합니다",
        "tdd": "서비스 로직과 API 계약을 TDD로 자동 검증합니다",
        "lint-gate": "백엔드 코드의 일관성을 린트 게이트로 유지합니다",
    },
    "frontend": {
        "ai-critique": "UI 컴포넌트의 접근성과 성능을 AI 리뷰로 개선합니다",
        "lint-gate": "프론트엔드 코드의 스타일과 품질을 린트 게이트로 통제합니다",
    },
    "library": {
        "tdd": "라이브러리 API의 하위 호환성을 TDD 파이프라인으로 보장합니다",
        "lint-gate": "라이브러리 코드의 품질 표준을 린트 게이트로 유지합니다",
        "ai-critique": "공개 API의 설계 품질을 AI 리뷰로 한층 높입니다",
    },
    "automation": {
        "harness": "자동화 워크플로의 신뢰성을 하네스 4단계 통제로 확보합니다",
        "ralph-loop": "반복적인 자동화 작업을 Ralph 루프로 자율 실행합니다",
        "lint-gate": "자동화 스크립트의 품질을 린트 게이트로 통제합니다",
    },
}

# 솔루션 유형 한국어 표시명
SOLUTION_TYPE_NAMES: dict[str, str] = {
    "saas": "SaaS",
    "rest-api": "REST API",
    "cli-tool": "CLI 도구",
    "data-pipeline": "데이터 파이프라인",
    "mobile-app": "모바일 앱",
    "fullstack": "풀스택",
    "backend": "백엔드",
    "frontend": "프론트엔드",
    "library": "라이브러리",
    "automation": "자동화",
}

# 기본 추천 (미등록 솔루션 유형)
DEFAULT_AGENT_IDS = ["claude-code"]
DEFAULT_SKILL_IDS = ["tdd-smart-coding", "code-review"]
DEFAULT_PIPELINE_IDS = ["tdd", "lint-gate"]

DEFAULT_AGENT_REASONING: dict[str, str] = {
    "claude-code": "범용적인 코드 생성에 Claude Code가 안정적입니다",
}
DEFAULT_SKILL_REASONING: dict[str, str] = {
    "tdd-smart-coding": "TDD 워크플로로 코드 품질을 확보합니다",
    "code-review": "코드 리뷰로 버그를 사전에 차단합니다",
}
DEFAULT_PIPELINE_REASONING: dict[str, str] = {
    "tdd": "TDD 파이프라인으로 테스트를 자동화합니다",
    "lint-gate": "린트 게이트로 코드 일관성을 유지합니다",
}


def _inject_reasoning(
    items: list[dict[str, Any]],
    reasoning_map: dict[str, str],
) -> list[dict[str, Any]]:
    """각 추천 항목에 reasoning 필드를 주입한다."""
    return [{**item, "reasoning": reasoning_map.get(item["id"], "")} for item in items]


def _build_summary(
    solution_type: str,
    agents: list[dict[str, Any]],
    skills: list[dict[str, Any]],
    pipelines: list[dict[str, Any]],
) -> str:
    """추천 요약 문장을 생성한다."""
    name = SOLUTION_TYPE_NAMES.get(solution_type, solution_type)
    parts: list[str] = []
    if agents:
        parts.append(f"{len(agents)}개의 에이전트")
    if skills:
        parts.append(f"{len(skills)}개의 스킬")
    if pipelines:
        parts.append(f"{len(pipelines)}개의 파이프라인")
    items_text = ", ".join(parts) if parts else "항목"
    return f"{name} 프로젝트에 최적화된 {items_text}을 추천합니다."


class RecommendService:
    """규칙 기반 추천 서비스."""

    def __init__(self) -> None:
        self._catalog = CatalogService()

    def recommend(self, solution_type: str) -> dict[str, Any]:
        """솔루션 유형에 따른 추천 결과를 반환한다."""
        normalized = solution_type.lower().strip()

        agent_ids = AGENT_RULES.get(normalized, DEFAULT_AGENT_IDS)
        skill_ids = SKILL_RULES.get(normalized, DEFAULT_SKILL_IDS)
        pipeline_ids = PIPELINE_RULES.get(normalized, DEFAULT_PIPELINE_IDS)

        agents_catalog = self._catalog.get("platforms")
        skills_catalog = _WORKFLOW_SKILLS_CATALOG
        pipelines_catalog = self._catalog.get("pipelines")

        agents = [a for a in agents_catalog if a["id"] in agent_ids]
        skills = [s for s in skills_catalog if s["id"] in skill_ids]
        pipelines = [p for p in pipelines_catalog if p["id"] in pipeline_ids]

        # reasoning 주입
        agent_reasoning = AGENT_REASONING.get(normalized, DEFAULT_AGENT_REASONING)
        skill_reasoning = SKILL_REASONING.get(normalized, DEFAULT_SKILL_REASONING)
        pipeline_reasoning = PIPELINE_REASONING.get(
            normalized, DEFAULT_PIPELINE_REASONING
        )

        agents = _inject_reasoning(agents, agent_reasoning)
        skills = _inject_reasoning(skills, skill_reasoning)
        pipelines = _inject_reasoning(pipelines, pipeline_reasoning)

        summary = _build_summary(normalized, agents, skills, pipelines)

        return {
            "solution_type": normalized,
            "agents": agents,
            "skills": skills,
            "pipelines": pipelines,
            "summary": summary,
        }
