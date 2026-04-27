"""통합 서비스 API — Linear/Notion API 키 유효성 검증 및 초기 태스크 등록."""
from __future__ import annotations

import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.integrations import (
    IntegrationValidateResponse,
    LinearValidateRequest,
    NotionValidateRequest,
    ProjectLinearStatusResponse,
    RegisterInitialTasksRequest,
    RegisterInitialTasksResponse,
)

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get(
    "/projects/{project_id}/linear-credentials/status",
    response_model=ProjectLinearStatusResponse,
    status_code=status.HTTP_200_OK,
)
async def get_project_linear_status(
    project_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectLinearStatusResponse:
    """프로젝트에 저장된 Linear 자격증명 상태 조회 (API 키는 마스킹)."""
    from app.core.crypto import decrypt
    from app.models.project_linear_credentials import ProjectLinearCredentials

    result = await db.execute(
        select(ProjectLinearCredentials).where(
            ProjectLinearCredentials.project_id == project_id
        )
    )
    creds = result.scalar_one_or_none()
    if creds is None:
        return ProjectLinearStatusResponse(
            credentials_saved=False,
            team_id=None,
            api_key_masked=None,
        )

    try:
        plain = decrypt(str(creds.encrypted_api_key))
        masked = plain[:12] + "****"
    except Exception:
        masked = "****"

    return ProjectLinearStatusResponse(
        credentials_saved=True,
        team_id=str(creds.team_id),
        api_key_masked=masked,
    )

_executor = ThreadPoolExecutor(max_workers=4)


async def _run_sync(func: Callable[..., Any], *args: Any) -> Any:
    """동기 함수를 별도 스레드에서 실행하는 헬퍼."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, func, *args)


@router.post(
    "/validate/linear",
    response_model=IntegrationValidateResponse,
    status_code=status.HTTP_200_OK,
)
async def validate_linear(
    data: LinearValidateRequest,
    user: User = Depends(get_current_user),
) -> IntegrationValidateResponse:
    """Linear API 키와 팀 ID를 실제 API 호출로 검증한다."""
    from app.services import linear_service

    valid, message = await _run_sync(
        linear_service.validate_credentials, data.api_key, data.team_id
    )
    return IntegrationValidateResponse(valid=valid, message=message)


@router.post(
    "/validate/notion",
    response_model=IntegrationValidateResponse,
    status_code=status.HTTP_200_OK,
)
async def validate_notion(
    data: NotionValidateRequest,
    user: User = Depends(get_current_user),
) -> IntegrationValidateResponse:
    """Notion API 키와 데이터베이스 ID를 실제 API 호출로 검증한다."""
    from app.services import notion_service

    valid, message = await _run_sync(
        notion_service.validate_credentials, data.api_key, data.database_id
    )
    return IntegrationValidateResponse(valid=valid, message=message)


@router.post(
    "/projects/{project_id}/initial-tasks",
    response_model=RegisterInitialTasksResponse,
    status_code=status.HTTP_200_OK,
)
async def register_initial_tasks(
    project_id: UUID,
    data: RegisterInitialTasksRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RegisterInitialTasksResponse:
    """프로젝트 생성 완료 시 Linear/Notion에 초기 태스크를 등록하고 프로젝트별 자격증명을 저장한다.

    실패해도 200을 반환하며, errors 필드에 오류 내용을 포함한다.
    """
    linear_created = False
    linear_issue_url: str | None = None
    notion_created = False
    notion_page_url: str | None = None
    errors: list[str] = []

    if data.linear_api_key and data.linear_team_id:
        try:
            from app.services import linear_service

            url = await _run_sync(
                linear_service.create_initial_task,
                data.linear_api_key,
                data.linear_team_id,
                data.project_name,
            )
            linear_created = True
            linear_issue_url = url
        except Exception as exc:
            errors.append(f"Linear 태스크 등록 실패: {exc}")

        # 프로젝트별 Linear 자격증명 저장 (upsert)
        if data.save_credentials:
            try:
                from app.core.crypto import encrypt
                from app.models.project_linear_credentials import ProjectLinearCredentials

                result = await db.execute(
                    select(ProjectLinearCredentials).where(
                        ProjectLinearCredentials.project_id == project_id
                    )
                )
                creds = result.scalar_one_or_none()
                encrypted_key = encrypt(data.linear_api_key)
                now = datetime.now(UTC)

                if creds is None:
                    creds = ProjectLinearCredentials(
                        project_id=project_id,
                        encrypted_api_key=encrypted_key,
                        team_id=data.linear_team_id,
                    )
                    db.add(creds)
                else:
                    creds.encrypted_api_key = encrypted_key  # type: ignore[assignment]
                    creds.team_id = data.linear_team_id  # type: ignore[assignment]
                    creds.updated_at = now  # type: ignore[assignment]

                await db.commit()
            except Exception as exc:
                errors.append(f"Linear 자격증명 저장 실패: {exc}")

    if data.notion_api_key and data.notion_database_id:
        try:
            from app.services import notion_service

            url = await _run_sync(
                notion_service.create_initial_task,
                data.notion_api_key,
                data.notion_database_id,
                data.project_name,
            )
            notion_created = True
            notion_page_url = url
        except Exception as exc:
            errors.append(f"Notion 태스크 등록 실패: {exc}")

    return RegisterInitialTasksResponse(
        linear_created=linear_created,
        linear_issue_url=linear_issue_url,
        notion_created=notion_created,
        notion_page_url=notion_page_url,
        errors=errors,
    )
