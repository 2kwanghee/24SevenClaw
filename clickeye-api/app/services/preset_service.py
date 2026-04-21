import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.preset import Preset
from app.models.project import Project

SEED_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "presets"


class PresetService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_presets(
        self,
        offset: int = 0,
        limit: int = 20,
        maturity_level: str | None = None,
        solution_type: str | None = None,
    ) -> tuple[list[Preset], int]:
        conditions = [Preset.is_active.is_(True)]

        if maturity_level:
            conditions.append(Preset.maturity_level == maturity_level)

        count_stmt = (
            select(func.count()).select_from(Preset).where(*conditions)
        )
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = (
            select(Preset)
            .where(*conditions)
            .order_by(Preset.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        presets = list(result.scalars().all())

        # solution_type 필터 (JSON 배열 내부 검색은 Python에서 처리)
        if solution_type:
            presets = [p for p in presets if solution_type in (p.solution_types or [])]
            total = len(presets)

        return presets, int(total)

    async def get_by_id(self, preset_id: UUID) -> Preset:
        stmt = select(Preset).where(Preset.id == preset_id, Preset.is_active.is_(True))
        result = await self.db.execute(stmt)
        preset = result.scalar_one_or_none()
        if preset is None:
            raise AppError("PRESET_NOT_FOUND", "프리셋을 찾을 수 없습니다", 404)
        return preset

    async def apply_preset(
        self, project_id: UUID, preset_id: UUID, owner_id: UUID
    ) -> dict:
        """프리셋을 프로젝트에 적용하여 settings에 기본 구성을 저장한다."""
        # 프로젝트 소유권 확인
        proj_stmt = select(Project).where(
            Project.id == project_id, Project.owner_id == owner_id
        )
        proj_result = await self.db.execute(proj_stmt)
        project = proj_result.scalar_one_or_none()
        if project is None:
            raise AppError("PROJECT_NOT_FOUND", "프로젝트를 찾을 수 없습니다", 404)

        preset = await self.get_by_id(preset_id)

        # 프로젝트 settings에 프리셋 구성 병합
        current_settings = dict(project.settings or {})
        current_settings["preset_id"] = str(preset.id)
        current_settings["preset_slug"] = preset.slug
        current_settings["agents"] = preset.default_agents or []
        current_settings["skills"] = preset.default_skills or []
        current_settings["pipelines"] = preset.default_pipelines or []

        project.settings = current_settings  # type: ignore[assignment]
        project.updated_at = datetime.now(UTC)  # type: ignore[assignment]
        await self.db.commit()
        await self.db.refresh(project)

        return {
            "project_id": project.id,
            "preset_id": preset.id,
            "applied_agents": preset.default_agents or [],
            "applied_skills": preset.default_skills or [],
            "applied_pipelines": preset.default_pipelines or [],
        }

    async def seed_presets(self) -> int:
        """시드 데이터로 시스템 프리셋을 초기 로드한다."""
        count = 0
        for filename in ["starter.json", "intermediate.json", "advanced.json"]:
            filepath = SEED_DIR / filename
            if not filepath.exists():
                continue

            data = json.loads(filepath.read_text(encoding="utf-8"))
            slug = data["slug"]

            # 이미 존재하면 건너뜀
            stmt = select(Preset).where(Preset.slug == slug)
            result = await self.db.execute(stmt)
            if result.scalar_one_or_none() is not None:
                continue

            preset = Preset(
                name=data["name"],
                slug=slug,
                maturity_level=data["maturity_level"],
                solution_types=data.get("solution_types", []),
                default_agents=data.get("default_agents", []),
                default_skills=data.get("default_skills", []),
                default_pipelines=data.get("default_pipelines", []),
                description=data.get("description"),
                is_system=data.get("is_system", True),
            )
            self.db.add(preset)
            count += 1

        if count > 0:
            await self.db.commit()
        return count
