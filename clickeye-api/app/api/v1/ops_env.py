"""운영 패널 관리형 환경변수 CRUD + 수동 적용 endpoint (superadmin 전용).

feature flag `feature_ops_panel` OFF 시 모든 endpoint 404.
"적용"은 수동 — render 는 파일을 렌더하고 재생성 명령 문자열을 반환할 뿐,
docker/재생성을 절대 실행하지 않는다.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_ops_feature, require_superadmin
from app.models.user import User
from app.schemas.ops import (
    EnvRenderRequest,
    EnvRenderResult,
    EnvVarItem,
    EnvVarUpsert,
    WebhookEnvRenderResult,
    WebhookEnvStatus,
)
from app.services.ops import env_service, webhook_env_service

router = APIRouter(
    prefix="/admin/ops",
    tags=["ops"],
    dependencies=[Depends(require_ops_feature), Depends(require_superadmin)],
)


@router.get("/env", response_model=list[EnvVarItem])
async def list_env(db: AsyncSession = Depends(get_db)) -> list[EnvVarItem]:
    """관리형 env 키 조회(제외 키 포함, 시크릿 값 미반환)."""
    return await env_service.list_env(db)


@router.put("/env/{key}", status_code=204)
async def upsert_env(
    key: str,
    data: EnvVarUpsert,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_superadmin),
) -> None:
    """env 값 upsert. 편집 제외/미허용 키는 400."""
    await env_service.upsert(db, key, data.value, user.id)  # type: ignore[arg-type]


@router.delete("/env/{key}", status_code=204)
async def delete_env(
    key: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_superadmin),
) -> None:
    """env 값 삭제. 편집 제외/미허용 키는 400, 미존재는 404."""
    await env_service.delete(db, key, user.id)  # type: ignore[arg-type]


@router.post("/env/render", response_model=EnvRenderResult)
async def render_env(
    data: EnvRenderRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_superadmin),
) -> EnvRenderResult:
    """env 파일 렌더 + 재생성 명령 문자열 반환(docker/재생성 미실행)."""
    if not data.confirm:
        from app.core.exceptions import AppError

        raise AppError(
            "OPS_ENV_RENDER_UNCONFIRMED",
            "렌더를 확정하려면 confirm=true 가 필요합니다.",
            400,
        )
    return await env_service.render_to_file(db, user.id)  # type: ignore[arg-type]


@router.get("/env/webhook/status", response_model=WebhookEnvStatus)
async def webhook_env_status(db: AsyncSession = Depends(get_db)) -> WebhookEnvStatus:
    """webhook.env 현재 상태 + MAP 후보 프로젝트 목록(시크릿 값 미반환)."""
    return await webhook_env_service.preview(db)


@router.post("/env/webhook/render", response_model=WebhookEnvRenderResult)
async def render_webhook_env(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_superadmin),
) -> WebhookEnvRenderResult:
    """webhook.env 의 WEBHOOK_SECRET_MAP 라인 렌더 + 재기동 명령 문자열 반환.

    MAP 라인만 교체하며 다른 라인은 보존한다. docker/재기동은 실행하지 않는다.
    """
    return await webhook_env_service.render(db, user.id)  # type: ignore[arg-type]
