"""통합 서비스 API — Linear/Notion API 키 유효성 검증 및 초기 태스크 등록."""
from __future__ import annotations

import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.integrations import (
    IntegrationValidateResponse,
    LinearValidateRequest,
    LinearValidateResponse,
    NotionValidateRequest,
    NotionValidateResponse,
    RegisterInitialTasksRequest,
    RegisterInitialTasksResponse,
)

router = APIRouter(prefix="/integrations", tags=["integrations"])

_executor = ThreadPoolExecutor(max_workers=4)


async def _run_sync(func: Callable[..., Any], *args: Any) -> Any:
    """동기 함수를 별도 스레드에서 실행하는 헬퍼."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, func, *args)


@router.post(
    "/linear/validate",
    response_model=LinearValidateResponse,
    status_code=status.HTTP_200_OK,
)
async def validate_linear_credentials(
    data: LinearValidateRequest,
    user: User = Depends(get_current_user),
) -> LinearValidateResponse:
    """Linear API 키와 팀 ID를 실제 API 호출로 검증한다 (5초 타임아웃).

    성공 시 team_name 반환, 실패 시 error 반환.
    """
    from app.services import linear_service

    valid, team_name, error = await _run_sync(
        linear_service.validate_credentials_v2, data.api_key, data.team_id
    )
    return LinearValidateResponse(valid=valid, team_name=team_name, error=error)


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
    "/notion/validate",
    response_model=NotionValidateResponse,
    status_code=status.HTTP_200_OK,
)
async def validate_notion_credentials(
    data: NotionValidateRequest,
    user: User = Depends(get_current_user),
) -> NotionValidateResponse:
    """Notion API 키와 데이터베이스 ID를 실제 API 호출로 검증한다 (5초 타임아웃).

    성공 시 database_title 반환, 실패 시 HTTP 상태코드에 따른 한국어 에러 반환.
    """
    from app.services import notion_service

    valid, database_title, error = await _run_sync(
        notion_service.validate_credentials_v2, data.api_key, data.database_id
    )
    return NotionValidateResponse(valid=valid, database_title=database_title, error=error)


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
) -> RegisterInitialTasksResponse:
    """프로젝트 생성 완료 시 Linear/Notion에 초기 태스크를 등록한다.

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
