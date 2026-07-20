"""솔루션 분석 스키마 — 7-Step 위저드 1단계 AI 분석 요청/응답."""

from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# UIStructureSchema
# ---------------------------------------------------------------------------


class UIPageSchema(BaseModel):
    """단일 UI 페이지 정의."""

    key: str = Field(..., description="페이지 고유 키 (예: dashboard, settings)")
    title: str = Field(..., description="페이지 제목")
    path: str = Field(..., description="라우트 경로 (예: /dashboard)")
    components: list[str] = Field(default_factory=list, description="사용되는 컴포넌트 목록")
    is_auth_required: bool = Field(default=True, description="인증 필요 여부")


class UINavigationSchema(BaseModel):
    """네비게이션 구조 정의."""

    type: str = Field(..., description="네비게이션 유형 (sidebar | topbar | bottom-tab)")
    items: list[dict[str, Any]] = Field(default_factory=list, description="네비게이션 항목")


class UIStructureSchema(BaseModel):
    """UI 전체 구조 — 프로토타입 ui_structure 필드에 저장되는 형태."""

    layout: str = Field(
        ...,
        description="레이아웃 유형 (dashboard | landing | wizard | minimal)",
    )
    pages: list[UIPageSchema] = Field(default_factory=list, description="페이지 목록")
    navigation: UINavigationSchema | None = Field(None, description="네비게이션 구조")
    color_scheme: str = Field(
        default="system",
        description="색상 모드 (light | dark | system)",
    )
    primary_color: str | None = Field(None, description="주 색상 (hex 코드)")
    design_system: str = Field(
        default="shadcn",
        description="디자인 시스템 (shadcn | mui | antd | tailwind)",
    )
    extra: dict[str, Any] = Field(default_factory=dict, description="추가 설정")

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# SolutionAnalyzeRequest / SolutionAnalyzeResponse
# ---------------------------------------------------------------------------


class SolutionAnalyzeRequest(BaseModel):
    """솔루션 분석 요청 — 자연어 프롬프트를 받아 UI 구조·PM 추천 등을 반환한다."""

    prompt: str = Field(
        ...,
        min_length=10,
        max_length=4000,
        description="구축하고 싶은 솔루션을 자연어로 설명",
    )
    domain: str | None = Field(
        None,
        max_length=100,
        description="도메인 힌트 (예: fintech, healthcare, e-commerce)",
    )
    target_platform: str | None = Field(
        None,
        max_length=50,
        description="타겟 플랫폼 (web | mobile | desktop | api)",
    )
    preferred_stack: list[str] = Field(
        default_factory=list,
        description="선호 기술 스택 (예: ['next.js', 'fastapi', 'postgresql'])",
    )


class SolutionAnalyzeResponse(BaseModel):
    """솔루션 분석 결과."""

    summary: str = Field(..., description="솔루션 한 줄 요약")
    detected_domain: str | None = Field(None, description="감지된 도메인")
    complexity: str = Field(
        ...,
        description="복잡도 수준 (simple | moderate | complex | enterprise)",
    )
    parsed_requirements: dict[str, Any] = Field(
        default_factory=dict,
        description="파싱된 요구사항 (기능 목록, 비기능 요구사항 등)",
    )
    recommended_ui_structure: UIStructureSchema = Field(..., description="추천 UI 구조")
    recommended_pm_slugs: list[str] = Field(
        default_factory=list,
        description="추천 PM 슬러그 목록 (우선순위 순)",
    )
    estimated_agents: list[str] = Field(
        default_factory=list,
        description="필요한 에이전트 슬러그 목록",
    )
    estimated_skills: list[str] = Field(
        default_factory=list,
        description="필요한 스킬 슬러그 목록",
    )
    confidence_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="분석 신뢰도 (0.0 ~ 1.0)",
    )
    reasoning: str | None = Field(None, description="분석 근거 설명")
