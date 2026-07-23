"""clickeye-llm(지식축적형 sLLM) 프록시 라우터.

딜리버리 콘솔 챗 패널이 호출한다. 인증(get_current_user)·딜리버리(프로젝트)
접근권 확인 후 내부 clickeye-llm 서비스(profile llm, 포트 8100)로 프록시한다.
직접 노출 대신 api 경유로 인증/스코프를 일원화한다.

딜리버리(delivery_id) == 프로젝트(projectId) 로 매핑된다(useProject 기반 콘솔).

clickeye-llm 미가용(연결 실패/타임아웃) 시 503 으로 명확히 degrade 한다
(profile llm 미기동일 수 있음). 500 을 내지 않는다.
"""

from __future__ import annotations

import contextlib
from typing import Any, Literal
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.governance import verify_governance_token
from app.config import settings
from app.core.exceptions import AppError
from app.core.logging import get_logger
from app.database import get_db
from app.dependencies import get_current_user, require_superadmin
from app.models.project import Project
from app.models.user import User
from app.services.llm_ingest import enqueue_ingest, resolve_project_by_team
from app.services.project_service import ProjectService

logger = get_logger(__name__)

router = APIRouter(prefix="/llm", tags=["llm"])

# 내부망 전용 프록시 — 짧은 타임아웃으로 빠르게 degrade. 생성(chat)은 sLLM 추론이
# 있어 여유를 두고, 조회(progress)는 더 짧게 잡는다.
_CHAT_TIMEOUT = 60.0
_READ_TIMEOUT = 30.0

_LLM_UNAVAILABLE = (
    "LLM 어시스턴트 미가용 — profile llm 미기동일 수 있습니다."
)


class LlmChatRequest(BaseModel):
    project_id: UUID = Field(..., description="딜리버리(프로젝트) ID. delivery_id 로 매핑.")
    query: str = Field(..., min_length=1, description="사용자 질문.")


async def _verify_project_access(db: AsyncSession, user: User, project_id: UUID) -> None:
    """딜리버리(프로젝트) 접근권 확인. superadmin 은 통과, 그 외는 소유자 검증.

    소유/조직 스코프는 기존 ProjectService.get_by_id(owner 검증, 미보유 시 404)를
    재사용한다. superadmin 은 전역 접근이므로 소유 검증을 건너뛴다.
    """
    role = getattr(user, "system_role", "") or ""
    if role == "superadmin":
        return
    # 미보유/미존재 시 AppError(404, PROJECT_NOT_FOUND) — 정보 노출 최소화.
    await ProjectService(db).get_by_id(project_id=project_id, owner_id=user.id)  # type: ignore[arg-type]


async def _proxy_post(path: str, payload: dict[str, Any], timeout: float) -> Any:
    """clickeye-llm 으로 POST 프록시. 미가용/타임아웃 시 AppError(503)."""
    try:
        async with httpx.AsyncClient(base_url=settings.clickeye_llm_url, timeout=timeout) as cli:
            resp = await cli.post(path, json=payload)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as exc:
        # clickeye-llm 이 응답은 했으나 오류(예: 502 임베딩 백엔드) — 원 상태코드 보존.
        logger.warning("llm_proxy_upstream_error", path=path, status=exc.response.status_code)
        detail = _LLM_UNAVAILABLE
        with contextlib.suppress(Exception):  # 본문 파싱 실패 시 기본 메시지 유지
            detail = exc.response.json().get("detail", detail)
        raise AppError("LLM_UPSTREAM_ERROR", detail, exc.response.status_code) from exc
    except httpx.HTTPError as exc:
        logger.warning("llm_proxy_unavailable", path=path, error=str(exc))
        raise AppError("LLM_UNAVAILABLE", _LLM_UNAVAILABLE, 503) from exc


async def _proxy_get(path: str, timeout: float) -> Any:
    """clickeye-llm 으로 GET 프록시. 미가용/타임아웃 시 AppError(503)."""
    try:
        async with httpx.AsyncClient(base_url=settings.clickeye_llm_url, timeout=timeout) as cli:
            resp = await cli.get(path)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as exc:
        logger.warning("llm_proxy_upstream_error", path=path, status=exc.response.status_code)
        raise AppError("LLM_UPSTREAM_ERROR", _LLM_UNAVAILABLE, exc.response.status_code) from exc
    except httpx.HTTPError as exc:
        logger.warning("llm_proxy_unavailable", path=path, error=str(exc))
        raise AppError("LLM_UNAVAILABLE", _LLM_UNAVAILABLE, 503) from exc


@router.post("/chat")
async def chat(
    body: LlmChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """RAG Q&A 프록시. 프로젝트 접근권 확인 후 clickeye-llm /chat 호출.

    delivery_id = project_id. 응답: {answer, sources[]}.
    """
    await _verify_project_access(db, user, body.project_id)
    return await _proxy_post(
        "/chat",
        {"delivery_id": str(body.project_id), "query": body.query},
        _CHAT_TIMEOUT,
    )


class LlmOrgChatRequest(BaseModel):
    query: str = Field(..., min_length=1, description="사용자 질문(조직 관점).")
    org_id: UUID | None = Field(
        default=None,
        description="조직 ID. superadmin 만 임의 지정 가능. 그 외는 요청자 소속 조직 강제.",
    )


# 조직 챗 하이브리드 주입용 활성 프로젝트 상한(사실 정확성 vs 컨텍스트 길이 균형).
_ORG_ACTIVE_PROJECTS_LIMIT = 50


@router.post("/chat/org")
async def chat_org(
    body: LlmOrgChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """조직 관점 RAG Q&A(포트폴리오, CE-312) — DB 하이브리드 + org 네임스페이스 RAG.

    "지금 어떤 서비스 생산 중이야?" 류 질의에 실제 활성 딜리버리를 답한다.
    - 스코프: 요청자 organization_id 강제. superadmin 은 body.org_id 로 임의 조직 지정 가능.
      org 미지정/미소속이면 400.
    - 하이브리드: 해당 org 활성 프로젝트(status != "deleted") 최신순 최대 50건을
      DB 조회 → extra_context('확정 사실')로 구성해 llm /chat 에 전달(RAG보다 우선).
    - delivery_id = f"org:{org_id}" (조직 네임스페이스 격리). 미가용 시 503.
    """
    role = getattr(user, "system_role", "") or ""
    is_superadmin = role == "superadmin"
    org_id = body.org_id if (is_superadmin and body.org_id is not None) else user.organization_id
    if org_id is None:
        raise AppError("ORG_REQUIRED", "조직 스코프가 필요합니다(소속 조직 없음).", 400)

    result = await db.execute(
        select(Project.name, Project.status, Project.updated_at)
        .where(Project.organization_id == org_id, Project.status != "deleted")
        .order_by(Project.updated_at.desc())
        .limit(_ORG_ACTIVE_PROJECTS_LIMIT)
    )
    rows = result.all()

    if rows:
        lines = "\n".join(f"- {name} (상태 {status})" for name, status, _ in rows)
        extra_context = f"현재 진행 중 딜리버리 {len(rows)}건:\n{lines}"
    else:
        extra_context = "현재 진행 중인 딜리버리가 없습니다."

    return await _proxy_post(
        "/chat",
        {
            "delivery_id": f"org:{org_id}",
            "query": body.query,
            "extra_context": extra_context,
        },
        _CHAT_TIMEOUT,
    )


@router.get("/progress/{project_id}")
async def progress(
    project_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """진행상황 요약 프록시. 프로젝트 접근권 확인 후 clickeye-llm /progress 호출."""
    await _verify_project_access(db, user, project_id)
    return await _proxy_get(f"/progress/{project_id}", _READ_TIMEOUT)


class LlmFeedbackRequest(BaseModel):
    """챗 답변 피드백(P2-MVP). delivery_id 는 서버가 project_id 로 강제 매핑."""

    project_id: UUID = Field(..., description="딜리버리(프로젝트) ID. delivery_id 로 매핑.")
    chat_id: str | None = Field(default=None, description="평가 대상 /chat 응답의 chat_id.")
    query: str = Field(..., min_length=1, description="당시 사용자 질문.")
    answer: str = Field(..., min_length=1, description="당시 어시스턴트 답변 원문.")
    rating: Literal["up", "down"] = Field(..., description="평가(👍 up / 👎 down).")
    comment: str | None = Field(default=None, description="선택 코멘트(주로 down 사유).")
    sources: list[str] | None = Field(
        default=None, description="답변에 사용된 source_id 목록."
    )


@router.post("/feedback")
async def feedback(
    body: LlmFeedbackRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """피드백 저장 프록시. 프로젝트 접근권 확인 후 clickeye-llm /feedback 호출.

    delivery_id = project_id(서버측 강제 — 클라이언트 임의 지정 불가). 응답: {feedback_id}.
    """
    await _verify_project_access(db, user, body.project_id)
    return await _proxy_post(
        "/feedback",
        {
            "delivery_id": str(body.project_id),
            "chat_id": body.chat_id,
            "query": body.query,
            "answer": body.answer,
            "rating": body.rating,
            "comment": body.comment,
            "sources": body.sources,
        },
        _READ_TIMEOUT,
    )


class LlmIngestRequest(BaseModel):
    project_id: UUID = Field(..., description="딜리버리(프로젝트) ID. delivery_id 로 매핑.")
    documents: list[dict[str, Any]] = Field(..., description="주입 문서 목록(source_id/text 등).")


@router.post("/ingest")
async def ingest(
    body: LlmIngestRequest,
    user: User = Depends(require_superadmin),
) -> dict[str, Any]:
    """지식 주입 프록시(내부/테스트). superadmin 전용."""
    return await _proxy_post(
        "/ingest",
        {"delivery_id": str(body.project_id), "documents": body.documents},
        _CHAT_TIMEOUT,
    )


class LlmPipelineIngestRequest(BaseModel):
    """파이프라인/웹훅 머신 인제스트 요청 (P1.6).

    호출자(bash 파이프라인·Linear 웹훅)는 project_id 를 모를 수 있어 team_id 만
    넘긴다 — 해석(team→project 역매핑)은 API(SSOT)가 수행한다.
    """

    team_id: str | None = Field(default=None, description="Linear team ID(역매핑용, 선택).")
    project_id: UUID | None = Field(default=None, description="프로젝트 ID(있으면 우선).")
    source_id: str = Field(..., min_length=1, description="KB 문서 source_id(증분 갱신 키).")
    text: str = Field(..., min_length=1, description="인제스트할 텍스트.")
    metadata: dict[str, Any] | None = None


@router.post(
    "/ingest/pipeline",
    status_code=202,
    dependencies=[Depends(verify_governance_token)],
)
async def ingest_pipeline(
    body: LlmPipelineIngestRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """머신 인제스트 (P1.6) — 파이프라인/웹훅發. X-Governance-Token 보호(JWT 아님).

    항상 202(비블로킹 계약 — 호출측 파이프라인을 절대 죽이지 않는다):
    - FEATURE_LLM_AUTOINGEST off → {status: disabled} (에러 아님).
    - project_id 우선, 없으면 team_id → project 역매핑(정확히 1건일 때만).
    - 매핑 실패 → {status: skipped, reason} / 성공 → enqueue(fire-and-forget) 후
      {status: queued, project_id}.
    """
    if not settings.feature_llm_autoingest:
        return {"status": "disabled"}

    project_id = body.project_id
    if project_id is None:
        if not body.team_id:
            return {"status": "skipped", "reason": "project_id/team_id 모두 미지정"}
        project_id = await resolve_project_by_team(db, body.team_id)
        if project_id is None:
            return {
                "status": "skipped",
                "reason": f"team→project 역매핑 실패(0건 또는 복수건): {body.team_id}",
            }

    enqueue_ingest(project_id, body.source_id, body.text, body.metadata)
    return {"status": "queued", "project_id": str(project_id)}
