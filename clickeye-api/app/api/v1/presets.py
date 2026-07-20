import logging
from uuid import UUID

import anthropic
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_locale, require_permission
from app.models.user import User
from app.schemas.preset import (
    MaturityAssessmentRequest,
    MaturityAssessmentResponse,
    MaturityQuestion,
    NaturalLanguageConfigRequest,
    NaturalLanguageConfigResponse,
    PresetApplyResponse,
    PresetListResponse,
    PresetResponse,
)
from app.services.claude_service import ClaudeService
from app.services.maturity_service import MaturityService
from app.services.preset_service import PresetService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/presets", tags=["presets"])


# ── 자연어 분석 → 추천 구성 매핑 ──────────────────────────────────────────────

# primary_tag → 추천 에이전트
_TAG_TO_AGENTS: dict[str, list[str]] = {
    "saas": ["fullstack", "backend", "frontend"],
    "rest-api": ["backend"],
    "fullstack": ["fullstack", "backend", "frontend"],
    "internal-tool": ["backend", "frontend"],
    "mvp": ["fullstack"],
    "mobile": ["frontend", "uiux"],
    "e-commerce": ["fullstack", "backend", "frontend"],
    "ai-platform": ["backend", "data"],
    "blockchain": ["backend"],
}

# features/key_requirements 키워드 → 스킬
_KEYWORD_TO_SKILLS: dict[str, str] = {
    "review": "code-review",
    "리뷰": "code-review",
    "test": "testing-basic",
    "테스트": "testing-basic",
    "generation": "code-generation",
    "생성": "code-generation",
    "security": "security-scan",
    "보안": "security-scan",
}

# features/key_requirements 키워드 → 파이프라인
_KEYWORD_TO_PIPELINES: dict[str, str] = {
    "review": "ai-review",
    "리뷰": "ai-review",
    "test": "simple-build",
    "테스트": "simple-build",
    "build": "simple-build",
    "deploy": "full-pipeline",
    "배포": "full-pipeline",
    "ci/cd": "full-pipeline",
}


def _extract_keyword_matches(text: str, mapping: dict[str, str]) -> list[str]:
    """텍스트에서 키워드를 찾아 매핑된 값의 중복 제거된 리스트를 반환."""
    lower = text.lower()
    result: list[str] = []
    for keyword, value in mapping.items():
        if keyword in lower and value not in result:
            result.append(value)
    return result


def _map_analysis_to_suggestions(
    analysis: dict,
) -> tuple[list[str], list[str], list[str]]:
    """analyze_solution() 결과를 suggested_agents/skills/pipelines로 변환."""
    primary_tag = (analysis.get("primary_tag") or "fullstack").lower()
    agents = ["harness"] + _TAG_TO_AGENTS.get(primary_tag, ["fullstack"])

    # features + key_requirements를 합쳐 키워드 매칭
    feature_text = " ".join(analysis.get("features", []) + analysis.get("key_requirements", []))
    skills = _extract_keyword_matches(feature_text, _KEYWORD_TO_SKILLS)
    pipelines = _extract_keyword_matches(feature_text, _KEYWORD_TO_PIPELINES)

    # 중복 제거 + 순서 유지
    agents = list(dict.fromkeys(agents))
    return agents, skills, pipelines


@router.get("/", response_model=PresetListResponse)
async def list_presets(
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    maturity_level: str | None = Query(None),
    solution_type: str | None = Query(None),
    user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
) -> PresetListResponse:
    """프리셋 목록 조회. maturity_level, solution_type 필터 지원."""
    service = PresetService(db)
    presets, total = await service.list_presets(
        offset=offset,
        limit=limit,
        maturity_level=maturity_level,
        solution_type=solution_type,
    )
    return PresetListResponse(
        items=[PresetResponse.model_validate(p) for p in presets],
        total=total,
    )


@router.get("/questions", response_model=list[MaturityQuestion])
async def get_maturity_questions(
    user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
) -> list[MaturityQuestion]:
    """성숙도 평가 질문지 조회."""
    service = MaturityService(db)
    return service.get_questions()


@router.post(
    "/assess",
    response_model=MaturityAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assess_maturity(
    data: MaturityAssessmentRequest,
    user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
) -> MaturityAssessmentResponse:
    """성숙도 평가 수행 → 점수 + 추천 프리셋 반환."""
    service = MaturityService(db)
    result = await service.assess(
        user_id=user.id,  # type: ignore[arg-type]
        answers=data.answers,
        organization_id=data.organization_id,
    )
    return MaturityAssessmentResponse(**result)


@router.get("/{preset_id}", response_model=PresetResponse)
async def get_preset(
    preset_id: UUID,
    user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
) -> PresetResponse:
    """프리셋 상세 조회."""
    service = PresetService(db)
    preset = await service.get_by_id(preset_id)
    return PresetResponse.model_validate(preset)


@router.post(
    "/{preset_id}/apply",
    response_model=PresetApplyResponse,
    status_code=status.HTTP_200_OK,
)
async def apply_preset(
    preset_id: UUID,
    data: NaturalLanguageConfigRequest | None = None,
    project_id: UUID | None = Query(None),
    user: User = Depends(require_permission("project:update")),
    db: AsyncSession = Depends(get_db),
) -> PresetApplyResponse:
    """프리셋을 프로젝트에 적용."""
    if project_id is None:
        from app.core.exceptions import AppError

        raise AppError("PROJECT_ID_REQUIRED", "project_id 쿼리 파라미터가 필요합니다", 400)

    service = PresetService(db)
    result = await service.apply_preset(
        project_id=project_id,
        preset_id=preset_id,
        owner_id=user.id,  # type: ignore[arg-type]
    )
    return PresetApplyResponse(**result)


def _build_fallback_response(
    text: str,
    claude: ClaudeService,
    reasoning_prefix: str,
    confidence: float,
) -> NaturalLanguageConfigResponse:
    """Claude 호출 실패 시 키워드 기반 폴백 응답을 생성한다."""
    primary_tag = claude.analyze_input(text)
    analysis_stub = {
        "primary_tag": primary_tag,
        "features": [text],
        "key_requirements": [text],
    }
    agents, skills, pipelines = _map_analysis_to_suggestions(analysis_stub)
    return NaturalLanguageConfigResponse(
        suggested_agents=agents,
        suggested_skills=skills,
        suggested_pipelines=pipelines,
        confidence=confidence,
        reasoning=(
            f"{reasoning_prefix} 키워드 기반으로 "
            f"에이전트 {len(agents) - 1}개, 스킬 {len(skills)}개, "
            f"파이프라인 {len(pipelines)}개를 추천합니다."
        ),
        primary_tag=primary_tag,
        tags=[primary_tag],
    )


@router.post("/analyze-text", response_model=NaturalLanguageConfigResponse)
async def analyze_natural_language_text(
    data: NaturalLanguageConfigRequest,
    request: Request,
    user: User = Depends(require_permission("project:read")),
    db: AsyncSession = Depends(get_db),
) -> NaturalLanguageConfigResponse:
    """자연어 솔루션 설명을 Claude로 분석해 추천 구성 + 풍부한 메타데이터를 반환한다.

    위저드 Step 1 자동 채움(prefill) 용도로 tags/tech_stack/features 등을 함께 응답한다.
    Claude API 실패 시 에러 타입별로 분류된 안내 메시지와 키워드 기반 폴백을 반환한다.
    """
    locale = get_locale(user=user, request=request)
    claude = ClaudeService()
    try:
        analysis = await claude.analyze_solution(
            prompt=data.text,
            org_context={},
            locale=locale,
        )
        agents, skills, pipelines = _map_analysis_to_suggestions(analysis)
        return NaturalLanguageConfigResponse(
            suggested_agents=agents,
            suggested_skills=skills,
            suggested_pipelines=pipelines,
            confidence=0.85,
            reasoning=(
                f"AI 분석 결과 {analysis.get('primary_tag', 'fullstack')} 유형으로 판단했습니다. "
                f"에이전트 {len(agents) - 1}개, 스킬 {len(skills)}개, "
                f"파이프라인 {len(pipelines)}개를 추천합니다."
            ),
            primary_tag=analysis.get("primary_tag"),
            tags=analysis.get("tags", []),
            tech_stack=analysis.get("tech_stack", {}),
            features=analysis.get("features", []),
            complexity=analysis.get("complexity"),
            target_users=analysis.get("target_users"),
            key_requirements=analysis.get("key_requirements", []),
        )
    except anthropic.BadRequestError as exc:
        # 400 — 가장 흔한 케이스는 크레딧 부족, 그 외 잘못된 요청
        message = str(exc).lower()
        if "credit balance" in message or "billing" in message:
            logger.warning("analyze-text: Anthropic 크레딧 잔액 부족 — %s", exc)
            reasoning = "AI 분석 크레딧이 부족합니다. 관리자에게 Anthropic API 충전을 요청해주세요."
        else:
            logger.warning("analyze-text: Anthropic 요청 거부 — %s", exc)
            reasoning = "AI 분석 요청이 거부되었습니다 (잘못된 입력 또는 모델 제한)."
        return _build_fallback_response(data.text, claude, reasoning, confidence=0.4)
    except anthropic.AuthenticationError as exc:
        logger.error("analyze-text: Anthropic 인증 실패 — %s", exc)
        return _build_fallback_response(
            data.text,
            claude,
            "AI 키 설정 오류입니다. 관리자에게 ANTHROPIC_API_KEY 확인을 요청해주세요.",
            confidence=0.4,
        )
    except anthropic.RateLimitError as exc:
        logger.warning("analyze-text: Anthropic 요청량 초과 — %s", exc)
        return _build_fallback_response(
            data.text,
            claude,
            "AI 요청량이 일시적으로 초과되었습니다. 1~2분 후 다시 시도해주세요.",
            confidence=0.4,
        )
    except (anthropic.APIConnectionError, anthropic.APITimeoutError) as exc:
        logger.warning("analyze-text: Anthropic 네트워크 오류 — %s", exc)
        return _build_fallback_response(
            data.text,
            claude,
            "네트워크 연결 오류로 AI 분석에 실패했습니다. 잠시 후 다시 시도해주세요.",
            confidence=0.4,
        )
    except Exception as exc:
        logger.exception("analyze-text: 예기치 못한 오류 — %s", exc)
        return _build_fallback_response(
            data.text,
            claude,
            "AI 분석이 일시적으로 불가능합니다.",
            confidence=0.5,
        )


@router.post(
    "/seed",
    status_code=status.HTTP_200_OK,
)
async def seed_presets(
    user: User = Depends(require_permission("preset:manage")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    """시스템 프리셋 시드 데이터 로드 (관리자 전용)."""
    service = PresetService(db)
    count = await service.seed_presets()
    return {"seeded": count}
