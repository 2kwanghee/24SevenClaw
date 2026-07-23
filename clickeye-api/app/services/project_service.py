import re
import secrets
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.agent_connection import AgentConnection
from app.models.artifact import Artifact
from app.models.central_contract import CustomerContractOverride
from app.models.license import License
from app.models.orchestrator import OrchestratorSession
from app.models.project import Project
from app.models.project_config import ProjectConfig
from app.models.project_linear_credentials import ProjectLinearCredentials
from app.models.rbac import OrganizationMembership
from app.models.ticket import Ticket
from app.models.user import User
from app.models.user_anthropic_credentials import UserAnthropicCredentials
from app.models.user_linear_credentials import UserLinearCredentials
from app.schemas.project import ProjectCreate, ProjectResetResponse, ProjectResponse, ProjectUpdate
from app.services.base import BaseService
from app.services.rbac_service import RBACService
from app.utils.db import get_or_404


def _slugify(text: str) -> str:
    """간단한 slug 생성: 소문자 + 하이픈."""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    return re.sub(r"-+", "-", slug).strip("-")


KeyStatus = Literal["fresh", "stale", "no_saved_key", "never_downloaded", "n/a"]


def _compute_key_status(
    last_zip_at: datetime | None,
    last_env_at: datetime | None,
    creds_updated_at: datetime | None,
    auth_method: str = "api_key",
) -> KeyStatus:
    """creds_updated_at과 마지막 다운로드 시각을 비교하여 키 상태를 반환.

    oauth_browser 모드는 Anthropic 자격증명 불필요 → 항상 "n/a" 반환.
    """
    if auth_method == "oauth_browser":
        return "n/a"
    if creds_updated_at is None:
        return "no_saved_key"
    last_dl = max(
        (t for t in [last_zip_at, last_env_at] if t is not None),
        default=None,
    )
    if last_dl is None:
        return "never_downloaded"
    if creds_updated_at.tzinfo is None:
        creds_ts = creds_updated_at.replace(tzinfo=UTC)
    else:
        creds_ts = creds_updated_at
    dl_ts = last_dl.replace(tzinfo=UTC) if last_dl.tzinfo is None else last_dl
    return "fresh" if dl_ts >= creds_ts else "stale"


def annotate_key_status(
    resp: ProjectResponse,
    project: "Project",
    anthropic_creds_updated_at: datetime | None,
    linear_creds_updated_at: datetime | None,
) -> ProjectResponse:
    """ProjectResponse에 key status 필드를 채운다."""
    # 위저드(prototype-session)는 폐기됨 — auth_method 는 항상 api_key.
    auth_method: str = "api_key"
    resp.anthropic_key_status = _compute_key_status(
        project.last_zip_downloaded_at,  # type: ignore[arg-type]
        project.last_env_downloaded_at,  # type: ignore[arg-type]
        anthropic_creds_updated_at,
        auth_method=auth_method,
    )
    resp.linear_key_status = _compute_key_status(  # type: ignore[assignment]  # TODO: 타입 정합
        project.last_zip_downloaded_at,  # type: ignore[arg-type]
        project.last_env_downloaded_at,  # type: ignore[arg-type]
        linear_creds_updated_at,
    )
    return resp


class ProjectService(BaseService):
    def __init__(self, db: AsyncSession):
        super().__init__(db)

    async def get_user_creds_timestamps(
        self, user_id: UUID
    ) -> tuple[datetime | None, datetime | None]:
        """사용자의 (anthropic_updated_at, linear_updated_at) 반환. N+1 방지용."""
        anthropic_result = await self.db.execute(
            select(UserAnthropicCredentials.updated_at).where(
                UserAnthropicCredentials.user_id == user_id
            )
        )
        anthropic_ts = anthropic_result.scalar_one_or_none()

        linear_result = await self.db.execute(
            select(UserLinearCredentials.updated_at).where(UserLinearCredentials.user_id == user_id)
        )
        linear_ts = linear_result.scalar_one_or_none()

        return anthropic_ts, linear_ts

    async def get_project_linear_creds_timestamp(self, project_id: UUID) -> datetime | None:
        """프로젝트별 Linear 자격증명의 updated_at 반환."""
        result = await self.db.execute(
            select(ProjectLinearCredentials.updated_at).where(
                ProjectLinearCredentials.project_id == project_id
            )
        )
        return result.scalar_one_or_none()

    async def create(self, user: User, data: ProjectCreate) -> Project:
        owner_id = user.id
        primary_org_id = user.organization_id
        target_org_id = data.organization_id or primary_org_id

        # 대상 org를 명시했고 primary org와 다르면 인가 검증 (IDOR 방지)
        if data.organization_id is not None and data.organization_id != primary_org_id:
            await self._authorize_target_org(user, data.organization_id)

        slug = _slugify(data.name)

        # slug 중복 시 숫자 접미사 추가
        base_slug = slug
        counter = 1
        while True:
            stmt = select(Project).where(Project.owner_id == owner_id, Project.slug == slug)
            result = await self.db.execute(stmt)
            if result.scalar_one_or_none() is None:
                break
            slug = f"{base_slug}-{counter}"
            counter += 1

        project = Project(
            owner_id=owner_id,
            name=data.name,
            slug=slug,
            description=data.description,
            organization_id=target_org_id,
        )
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def _authorize_target_org(self, user: User, organization_id: UUID) -> None:
        """요청한 organization_id에 프로젝트를 생성할 권한을 검증한다.

        control_tower:write 권한 보유자는 임의 조직 지정 가능,
        그 외에는 해당 조직의 활성 멤버십이 있어야 한다. 없으면 거부.
        """
        if RBACService(self.db).check_permission(user, "control_tower:write"):
            return
        result = await self.db.execute(
            select(OrganizationMembership)
            .where(
                OrganizationMembership.user_id == user.id,
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.is_active == True,  # noqa: E712
            )
            .limit(1)
        )
        # 존재 여부만 확인 (중복 활성 행이 있어도 500 방지 위해 first())
        if result.scalars().first() is None:
            raise AppError("FORBIDDEN", "해당 조직에 프로젝트를 생성할 권한이 없습니다", 403)

    async def get_by_id(self, project_id: UUID, owner_id: UUID) -> Project:
        return await get_or_404(
            self.db,
            Project,
            Project.id == project_id,
            Project.owner_id == owner_id,
            code="PROJECT_NOT_FOUND",
            message="프로젝트를 찾을 수 없습니다",
        )

    async def list_by_owner(
        self,
        owner_id: UUID,
        offset: int = 0,
        limit: int = 20,
        search: str | None = None,
        status_filter: str | None = None,
    ) -> tuple[list[Project], int]:
        # 기본 조건: 소유자 + 삭제되지 않은 것
        conditions = [Project.owner_id == owner_id, Project.status != "deleted"]

        # 상태 필터 (active/archived)
        if status_filter in ("active", "archived"):
            conditions.append(Project.status == status_filter)

        # 이름 검색 (ILIKE)
        if search:
            conditions.append(Project.name.ilike(f"%{search}%"))

        # 총 개수
        count_stmt = select(func.count()).select_from(Project).where(*conditions)
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        # 목록 조회
        stmt = (
            select(Project)
            .where(*conditions)
            .order_by(Project.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        projects = list(result.scalars().all())
        return projects, int(total)

    async def update(self, project_id: UUID, owner_id: UUID, data: ProjectUpdate) -> Project:
        project = await self.get_by_id(project_id, owner_id)

        update_data = data.model_dump(exclude_unset=True)
        if "name" in update_data:
            update_data["slug"] = _slugify(str(update_data["name"]))

        for key, value in update_data.items():
            setattr(project, key, value)

        project.updated_at = datetime.now(UTC)  # type: ignore[assignment]
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def delete(self, project_id: UUID, owner_id: UUID, is_superadmin: bool = False) -> None:
        """프로젝트 소프트 삭제 (status="deleted").

        is_superadmin=True 이면 owner 스코프를 우회하여 타 조직 프로젝트도 삭제할 수 있다
        (컨트롤타워/플랫폼 관리 경로). 소프트 삭제이므로 FK 연쇄는 발생하지 않는다
        (상태 플래그만 변경 — 별도 마이그레이션 불필요).
        """
        if is_superadmin:
            project = await self.get_for_admin(project_id)
        else:
            project = await self.get_by_id(project_id, owner_id)
        project.status = "deleted"  # type: ignore[assignment]
        project.updated_at = datetime.now(UTC)  # type: ignore[assignment]
        await self.db.commit()

    async def reset(self, project_id: UUID, owner_id: UUID) -> ProjectResetResponse:
        """프로젝트를 초기 상태로 되돌린다. 식별자/소유자/이름/조직은 보존."""
        from app.ws.hub import agent_hub

        project = await self.get_by_id(project_id, owner_id)

        # 1. 활성 WS 소켓 해제 (agent_connections row 삭제 전)
        await agent_hub.disconnect_project(project_id)

        # 2. 자식 row 삭제 (라이선스 제외 — 별도 처리)
        counts: dict[str, int] = {}
        child_models = (
            AgentConnection,
            Artifact,
            OrchestratorSession,
            ProjectConfig,
            Ticket,
            CustomerContractOverride,
        )
        for model in child_models:
            result = await self.db.execute(delete(model).where(model.project_id == project_id))
            counts[model.__tablename__] = result.rowcount  # type: ignore[attr-defined]  # TODO: 타입 정합

        # 3. 라이선스 재발급 (없으면 스킵)
        new_key: str | None = None
        old_license = (
            await self.db.execute(select(License).where(License.project_id == project_id))
        ).scalar_one_or_none()
        if old_license is not None:
            plan = old_license.plan
            max_agents = old_license.max_agents
            expires_at = old_license.expires_at
            await self.db.delete(old_license)
            await self.db.flush()
            new_key = secrets.token_urlsafe(32)
            self.db.add(
                License(
                    project_id=project_id,
                    license_key=new_key,
                    plan=plan,
                    max_agents=max_agents,
                    expires_at=expires_at,
                )
            )
        counts["licenses"] = 1 if old_license is not None else 0

        # 4. 프로젝트 컬럼 리셋
        project.settings = {}  # type: ignore[assignment]
        project.pm_profile_id = None  # type: ignore[assignment]
        project.requirements_text = None  # type: ignore[assignment]
        project.setup_token_hash = None  # type: ignore[assignment]
        project.bootstrap_status = "skipped"  # type: ignore[assignment]
        project.bootstrap_completed_at = None  # type: ignore[assignment]
        project.last_zip_downloaded_at = None  # type: ignore[assignment]
        project.last_env_downloaded_at = None  # type: ignore[assignment]
        project.initial_task_url = None  # type: ignore[assignment]
        project.project_type = "legacy"  # type: ignore[assignment]
        project.status = "active"  # type: ignore[assignment]
        project.updated_at = datetime.now(UTC)  # type: ignore[assignment]

        await self.db.commit()
        return ProjectResetResponse(
            project_id=project_id,
            new_license_key=new_key,
            deleted_counts=counts,
        )

    async def get_for_admin(self, project_id: UUID) -> Project:
        """관리자 전용 — owner 체크 없이 프로젝트 조회."""
        return await get_or_404(
            self.db,
            Project,
            Project.id == project_id,
            Project.status != "deleted",
            code="PROJECT_NOT_FOUND",
            message="프로젝트를 찾을 수 없습니다",
        )
