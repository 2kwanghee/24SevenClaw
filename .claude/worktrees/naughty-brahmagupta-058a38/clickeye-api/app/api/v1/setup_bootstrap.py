"""부트스트랩 엔드포인트 — 로컬 ZIP 셋업 시 요구사항 조회 및 결과 등록."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.orchestrator import OrchestratorSession, SubTask
from app.models.project import Project
from app.models.project_linear_credentials import ProjectLinearCredentials
from app.services import setup_token_service

router = APIRouter(prefix="/projects", tags=["setup-bootstrap"])
_security = HTTPBearer()

_VALID_ROLES = {"backend", "frontend", "qa", "architect", "designer", "devops", "pm", "fullstack"}


# ── 의존성: setup_token 검증 ───────────────────────────────────────────────────

async def _verify_setup_token(
    project_id: UUID,
    credentials: HTTPAuthorizationCredentials = Depends(_security),
    db: AsyncSession = Depends(get_db),
) -> tuple[Project, UUID]:
    """setup_token을 검증하고 (project, user_id) 쌍을 반환한다."""
    token = credentials.credentials
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="프로젝트를 찾을 수 없습니다",
        )

    stored_hash: str | None = project.setup_token_hash  # type: ignore[assignment]
    claims = setup_token_service.verify(token, stored_hash)
    if claims is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않거나 만료된 setup_token입니다",
        )
    return project, claims.user_id


# ── 스키마 ────────────────────────────────────────────────────────────────────

class RequirementsResponse(BaseModel):
    requirements_text: str | None
    project_name: str
    has_linear_credentials: bool


class BootstrapSubtask(BaseModel):
    role: str = Field(..., max_length=50)
    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    linear_issue_id: str | None = None
    linear_identifier: str | None = None
    linear_state: str | None = None
    linear_url: str | None = None


class OrchestratorBootstrapRequest(BaseModel):
    subtasks: list[BootstrapSubtask] = Field(..., min_length=1, max_length=50)
    decompose_method: Literal["claude-cli", "rule-based", "manual"] = "manual"
    notes: str | None = None


class OrchestratorBootstrapResponse(BaseModel):
    session_id: UUID
    subtask_count: int


class BootstrapStatusRequest(BaseModel):
    status: Literal["running", "failed"]
    error: str | None = None


# ── 엔드포인트 ────────────────────────────────────────────────────────────────

@router.get("/{project_id}/setup/requirements", response_model=RequirementsResponse)
async def get_requirements(
    auth: tuple[Project, UUID] = Depends(_verify_setup_token),
    db: AsyncSession = Depends(get_db),
) -> RequirementsResponse:
    """로컬 부트스트랩 스크립트가 호출해 요구사항을 가져간다."""
    project, _ = auth

    has_linear = False
    result = await db.execute(
        select(ProjectLinearCredentials).where(
            ProjectLinearCredentials.project_id == project.id
        )
    )
    if result.scalar_one_or_none() is not None:
        has_linear = True

    return RequirementsResponse(
        requirements_text=project.requirements_text,
        project_name=str(project.name),
        has_linear_credentials=has_linear,
    )


@router.post(
    "/{project_id}/setup/orchestrator-bootstrap",
    response_model=OrchestratorBootstrapResponse,
    status_code=status.HTTP_201_CREATED,
)
async def orchestrator_bootstrap(
    body: OrchestratorBootstrapRequest,
    auth: tuple[Project, UUID] = Depends(_verify_setup_token),
    db: AsyncSession = Depends(get_db),
) -> OrchestratorBootstrapResponse:
    """로컬 분해 + Linear 등록 결과를 받아 OrchestratorSession/SubTask를 생성한다.

    멱등: 이미 completed면 409 + 기존 session_id 반환.
    """
    project, user_id = auth

    if project.bootstrap_status == "completed":
        existing = await db.execute(
            select(OrchestratorSession).where(
                OrchestratorSession.project_id == project.id
            ).order_by(OrchestratorSession.created_at.asc()).limit(1)
        )
        sess = existing.scalar_one_or_none()
        if sess is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "이미 부트스트랩이 완료된 프로젝트입니다",
                    "session_id": str(sess.id),
                },
            )

    session = OrchestratorSession(
        id=uuid.uuid4(),
        project_id=project.id,
        title=f"[자동] {project.name} 초기 요구사항 분해",
        description=(body.notes or project.requirements_text or "")[:2000],
        phase="integrating",
        created_by=user_id,
    )
    db.add(session)
    await db.flush()

    for idx, st in enumerate(body.subtasks):
        role = st.role if st.role in _VALID_ROLES else "architect"
        subtask = SubTask(
            id=uuid.uuid4(),
            session_id=session.id,
            title=st.title[:500],
            description=(st.description or "")[:2000],
            assigned_role=role,
            status="pending",
            order_index=idx,
            linear_identifier=st.linear_identifier,
            linear_issue_id=st.linear_issue_id,
            linear_state=st.linear_state or ("Backlog" if st.linear_issue_id else None),
        )
        db.add(subtask)

    now = datetime.now(UTC)
    project.bootstrap_status = "completed"  # type: ignore[assignment]
    project.bootstrap_completed_at = now  # type: ignore[assignment]
    project.setup_token_hash = None  # type: ignore[assignment]  # 완료 후 즉시 무효화

    await db.commit()
    return OrchestratorBootstrapResponse(
        session_id=session.id,
        subtask_count=len(body.subtasks),
    )


@router.post("/{project_id}/setup/bootstrap-status", status_code=status.HTTP_204_NO_CONTENT)
async def update_bootstrap_status(
    body: BootstrapStatusRequest,
    auth: tuple[Project, UUID] = Depends(_verify_setup_token),
    db: AsyncSession = Depends(get_db),
) -> None:
    """로컬 부트스트랩의 진행 상태(running/failed)를 기록한다."""
    project, _ = auth
    if project.bootstrap_status == "completed":
        return
    project.bootstrap_status = body.status  # type: ignore[assignment]
    await db.commit()
