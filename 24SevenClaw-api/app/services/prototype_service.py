"""프로토타입 세션 서비스 — 세션 생성, 프로토타입 생성/조회/선택/확정."""

import re
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.pm_metrics import PMMetrics
from app.models.pm_profile import PMProfile
from app.models.project import Project
from app.models.prototype_session import Prototype, PrototypeSession
from app.schemas.prototype import (
    FinalizeRequest,
    PrototypeSelectRequest,
    PrototypeSessionCreate,
    PrototypeSessionUpdate,
)
from app.services.claude_service import ClaudeService


def _slugify(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    return re.sub(r"-+", "-", slug).strip("-")


class PrototypeService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._claude = ClaudeService()

    async def create_session(
        self, user_id: UUID, data: PrototypeSessionCreate
    ) -> PrototypeSession:
        """프로토타입 세션을 생성한다."""
        session = PrototypeSession(
            organization_id=data.organization_id,
            user_id=user_id,
            solution_prompt=data.solution_prompt,
            status="pending",
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_session(
        self, session_id: UUID, user_id: UUID
    ) -> PrototypeSession:
        """세션을 조회한다. 소유자 검증 포함."""
        stmt = select(PrototypeSession).where(
            PrototypeSession.id == session_id,
            PrototypeSession.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()
        if session is None:
            raise AppError(
                "SESSION_NOT_FOUND", "프로토타입 세션을 찾을 수 없습니다", 404
            )
        return session

    async def list_sessions(
        self, user_id: UUID, offset: int = 0, limit: int = 20
    ) -> tuple[list[PrototypeSession], int]:
        """사용자의 세션 목록을 반환한다."""
        conditions = [PrototypeSession.user_id == user_id]

        count_stmt = (
            select(func.count())
            .select_from(PrototypeSession)
            .where(*conditions)
        )
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = (
            select(PrototypeSession)
            .where(*conditions)
            .order_by(PrototypeSession.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        sessions = list(result.scalars().all())
        return sessions, int(total)

    async def get_session_status(
        self, session_id: UUID, user_id: UUID
    ) -> PrototypeSession:
        """세션 상태를 조회한다."""
        return await self.get_session(session_id, user_id)

    async def start_generation(
        self, session_id: UUID, user_id: UUID
    ) -> PrototypeSession:
        """생성 시작: status를 generating으로 변경하고 세션을 반환한다.

        이미 generating/completed 상태이면 AppError(409)를 발생시킨다.
        """
        session = await self.get_session(session_id, user_id)

        if session.status in ("generating", "completed"):
            raise AppError(
                "ALREADY_GENERATED",
                "이미 프로토타입이 생성된 세션입니다",
                409,
            )

        session.status = "generating"  # type: ignore[assignment]
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def run_generation(self, session_id: UUID, user_id: UUID) -> None:
        """백그라운드에서 실제 프로토타입 생성 작업을 수행한다.

        이 메서드는 BackgroundTasks에 의해 독립 DB 세션으로 호출된다.
        성공 시 status=completed, 실패 시 status=failed.
        """
        stmt = select(PrototypeSession).where(
            PrototypeSession.id == session_id,
            PrototypeSession.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()
        if session is None:
            return

        try:
            prompt = str(session.solution_prompt or "")
            solution_type = self._claude.analyze_input(prompt)

            templates = self._claude.generate_prototypes(solution_type, prompt)

            for idx, tmpl in enumerate(templates):
                proto = Prototype(
                    session_id=session.id,
                    variant_index=idx,
                    title=tmpl["title"],
                    description=tmpl.get("description"),
                    design_pattern=tmpl.get("design_pattern"),
                    menu_structure=tmpl.get("menu_structure"),
                    ui_structure=tmpl.get("ui_structure"),
                    color_palette=tmpl.get("color_palette"),
                    status="draft",
                )
                self.db.add(proto)

            session.status = "completed"  # type: ignore[assignment]
            await self.db.commit()

        except Exception:
            session.status = "failed"  # type: ignore[assignment]
            await self.db.commit()
            raise

    async def list_prototypes(
        self, session_id: UUID, user_id: UUID
    ) -> list[Prototype]:
        """세션의 프로토타입 목록을 반환한다."""
        # 소유자 검증
        await self.get_session(session_id, user_id)

        stmt = (
            select(Prototype)
            .where(Prototype.session_id == session_id)
            .order_by(Prototype.variant_index.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def select_prototype(
        self, session_id: UUID, user_id: UUID, data: PrototypeSelectRequest
    ) -> PrototypeSession:
        """프로토타입을 선택한다 — session.selected_prototype_id를 업데이트한다."""
        session = await self.get_session(session_id, user_id)

        # 대상 프로토타입 존재 및 소유 확인
        stmt = select(Prototype).where(
            Prototype.id == data.prototype_id,
            Prototype.session_id == session_id,
        )
        result = await self.db.execute(stmt)
        prototype = result.scalar_one_or_none()
        if prototype is None:
            raise AppError(
                "PROTOTYPE_NOT_FOUND", "프로토타입을 찾을 수 없습니다", 404
            )

        # 세션의 selected_prototype_id 업데이트
        await self.db.execute(
            update(PrototypeSession)
            .where(PrototypeSession.id == session_id)
            .values(selected_prototype_id=data.prototype_id)
        )
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def delete_session(
        self, session_id: UUID, user_id: UUID
    ) -> None:
        """세션을 삭제한다 (CASCADE로 프로토타입도 삭제)."""
        session = await self.get_session(session_id, user_id)
        await self.db.delete(session)
        await self.db.commit()

    async def update_session(
        self, session_id: UUID, user_id: UUID, data: PrototypeSessionUpdate
    ) -> PrototypeSession:
        """세션의 선택 정보(프로토타입/PM/스텝)를 업데이트한다."""
        session = await self.get_session(session_id, user_id)

        update_values: dict[str, Any] = {}

        if data.selected_prototype_id is not None:
            # 프로토타입이 이 세션에 속하는지 확인
            stmt = select(Prototype).where(
                Prototype.id == data.selected_prototype_id,
                Prototype.session_id == session_id,
            )
            result = await self.db.execute(stmt)
            if result.scalar_one_or_none() is None:
                raise AppError(
                    "PROTOTYPE_NOT_FOUND", "프로토타입을 찾을 수 없습니다", 404
                )
            update_values["selected_prototype_id"] = data.selected_prototype_id

        if data.selected_pm_id is not None:
            # PM 프로필 존재 확인
            pm = await self.db.get(PMProfile, data.selected_pm_id)
            if pm is None:
                raise AppError(
                    "PM_PROFILE_NOT_FOUND", "PM 프로필을 찾을 수 없습니다", 404
                )
            update_values["selected_pm_id"] = data.selected_pm_id

        if data.current_step is not None:
            update_values["current_step"] = data.current_step

        if update_values:
            await self.db.execute(
                update(PrototypeSession)
                .where(PrototypeSession.id == session_id)
                .values(**update_values)
            )
            await self.db.commit()
            await self.db.refresh(session)

        return session

    async def recommend_pms_for_session(
        self, session_id: UUID, user_id: UUID
    ) -> list[dict[str, Any]]:
        """세션의 선택된 프로토타입 기반으로 PM을 추천한다.

        selected_prototype_id가 없으면 AppError(409)를 발생시킨다.
        """
        session = await self.get_session(session_id, user_id)

        if session.selected_prototype_id is None:
            raise AppError(
                "NO_PROTOTYPE_SELECTED",
                "PM 추천을 위해 먼저 프로토타입을 선택해야 합니다",
                409,
            )

        prototype_id: UUID = session.selected_prototype_id  # type: ignore[assignment]

        prototype = await self.db.get(Prototype, prototype_id)
        if prototype is None:
            raise AppError(
                "PROTOTYPE_NOT_FOUND", "프로토타입을 찾을 수 없습니다", 404
            )

        context_text = str(session.solution_prompt or "")

        # 활성 PM 프로필 조회
        stmt = select(PMProfile).where(PMProfile.is_active.is_(True))
        result = await self.db.execute(stmt)
        profiles = list(result.scalars().all())

        if not profiles:
            return []

        design_pattern = str(prototype.design_pattern or "")
        domains = [str(p.domain or "") for p in profiles]
        domain_scores = self._claude.recommend_pm_scores(design_pattern, domains)

        combined_text = (design_pattern + " " + context_text).lower()
        keywords = [kw for kw in combined_text.split() if len(kw) > 2]

        # 메트릭 일괄 로드 (N+1 방지)
        pm_ids = [p.id for p in profiles]
        metrics_stmt = select(PMMetrics).where(PMMetrics.pm_id.in_(pm_ids))
        metrics_result = await self.db.execute(metrics_stmt)
        metrics_by_pm: dict[Any, PMMetrics] = {
            m.pm_id: m for m in metrics_result.scalars().all()
        }

        recommendations: list[dict[str, Any]] = []
        for profile in profiles:
            domain_key = str(profile.domain or "")
            domain_score = float(domain_scores.get(domain_key, 40))

            _specs: Any = profile.specialties
            pm_specialties = [s.lower() for s in (_specs or [])]
            if keywords and pm_specialties:
                matched = sum(
                    1
                    for kw in keywords
                    if any(kw in spec or spec in kw for spec in pm_specialties)
                )
                specialty_score = min(matched / max(len(keywords), 1) * 200, 100.0)
            else:
                specialty_score = 50.0

            _pid: Any = profile.id
            metric = metrics_by_pm.get(_pid)
            if metric and metric.total_ratings and int(metric.total_ratings) > 0:
                metric_score = float(metric.avg_rating or 0) / 5.0 * 100
            else:
                metric_score = 50.0

            final_score = int(
                domain_score * 0.4
                + specialty_score * 0.3
                + metric_score * 0.3
            )

            reasoning = (
                f"{profile.name}({profile.domain})은 "
                f"{design_pattern or '해당'} 프로젝트에 "
                f"도메인({int(domain_score)}pt)·"
                f"전문분야({int(specialty_score)}pt)·"
                f"평가({int(metric_score)}pt) 기준으로 "
                f"종합 {final_score}점입니다."
            )
            recommendations.append(
                {
                    "pm_profile": profile,
                    "match_score": final_score,
                    "reasoning": reasoning,
                }
            )

        recommendations.sort(key=lambda r: int(r["match_score"]), reverse=True)
        return recommendations[:5]

    async def finalize_session(
        self, session_id: UUID, user_id: UUID, data: FinalizeRequest
    ) -> Project:
        """세션을 확정하고 최종 프로젝트를 생성한다.

        선택된 프로토타입과 PM이 없으면 AppError(409)를 발생시킨다.
        """
        session = await self.get_session(session_id, user_id)

        if session.selected_prototype_id is None:
            raise AppError(
                "NO_PROTOTYPE_SELECTED",
                "최종 프로젝트 생성을 위해 먼저 프로토타입을 선택해야 합니다",
                409,
            )
        if session.selected_pm_id is None:
            raise AppError(
                "NO_PM_SELECTED",
                "최종 프로젝트 생성을 위해 먼저 PM을 선택해야 합니다",
                409,
            )

        # slug 생성 (중복 시 숫자 접미사)
        slug = _slugify(data.project_name)
        base_slug = slug
        counter = 1
        while True:
            stmt = select(Project).where(
                Project.owner_id == user_id, Project.slug == slug
            )
            result = await self.db.execute(stmt)
            if result.scalar_one_or_none() is None:
                break
            slug = f"{base_slug}-{counter}"
            counter += 1

        project = Project(
            owner_id=user_id,
            name=data.project_name,
            slug=slug,
            description=data.description,
            prototype_session_id=session_id,
            pm_profile_id=session.selected_pm_id,
            project_type="wizard",
        )
        self.db.add(project)

        # 세션 상태를 finalized로 변경
        await self.db.execute(
            update(PrototypeSession)
            .where(PrototypeSession.id == session_id)
            .values(status="finalized")
        )

        await self.db.commit()
        await self.db.refresh(project)
        return project
