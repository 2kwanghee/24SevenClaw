"""PM 프로필 서비스 — PM 목록/추천/구성/평가."""

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.pm_profile import PMComposition, PMMetric, PMProfile, PMRating
from app.models.prototype_session import Prototype
from app.schemas.pm_profile import (
    PMCompositionCreate,
    PMCompositionUpdate,
    PMRatingCreate,
)
from app.services.claude_service import ClaudeService


class PMService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._claude = ClaudeService()

    # ── PM 프로필 조회 ──

    async def list_profiles(
        self,
        specialty: str | None = None,
        is_active: bool | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[PMProfile], int]:
        """PM 프로필 목록을 반환한다."""
        conditions = []
        if specialty:
            conditions.append(PMProfile.specialty == specialty)
        if is_active is not None:
            conditions.append(PMProfile.is_active == is_active)

        count_stmt = (
            select(func.count()).select_from(PMProfile).where(*conditions)
        )
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = (
            select(PMProfile)
            .where(*conditions)
            .order_by(PMProfile.name.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        profiles = list(result.scalars().all())
        return profiles, int(total)

    async def get_profile(self, profile_id: UUID) -> PMProfile:
        """PM 프로필을 조회한다."""
        profile = await self.db.get(PMProfile, profile_id)
        if profile is None:
            raise AppError(
                "PM_PROFILE_NOT_FOUND", "PM 프로필을 찾을 수 없습니다", 404
            )
        return profile

    # ── PM 추천 ──

    async def recommend_pms(
        self, prototype_id: UUID
    ) -> list[dict[str, Any]]:
        """프로토타입에 적합한 PM을 추천한다.

        Returns:
            list[{pm_profile: PMProfile, match_score: int, reasoning: str}]
        """
        # 프로토타입 조회
        prototype = await self.db.get(Prototype, prototype_id)
        if prototype is None:
            raise AppError(
                "PROTOTYPE_NOT_FOUND", "프로토타입을 찾을 수 없습니다", 404
            )

        # 활성 PM 프로필 조회
        stmt = select(PMProfile).where(PMProfile.is_active.is_(True))
        result = await self.db.execute(stmt)
        profiles = list(result.scalars().all())

        if not profiles:
            return []

        # ClaudeService로 매칭 점수 계산
        design_pattern = str(prototype.design_pattern or "")
        specialties = [str(p.specialty) for p in profiles]
        scores = self._claude.recommend_pm_scores(design_pattern, specialties)

        recommendations: list[dict[str, Any]] = []
        for profile in profiles:
            score = scores.get(str(profile.specialty), 40)
            reasoning = (
                f"{profile.name}({profile.specialty})은 "
                f"{design_pattern} 프로젝트에 "
                f"매칭 점수 {score}점으로 추천됩니다."
            )
            recommendations.append(
                {
                    "pm_profile": profile,
                    "match_score": score,
                    "reasoning": reasoning,
                }
            )

        # 점수 내림차순 정렬
        recommendations.sort(key=lambda r: int(r["match_score"]), reverse=True)
        return recommendations

    # ── PM 구성 ──

    async def get_composition(
        self, prototype_id: UUID
    ) -> list[PMComposition]:
        """프로토타입의 PM 구성을 조회한다."""
        stmt = (
            select(PMComposition)
            .where(PMComposition.prototype_id == prototype_id)
            .order_by(PMComposition.match_score.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_composition(
        self, prototype_id: UUID, data: PMCompositionCreate
    ) -> PMComposition:
        """PM 구성을 생성한다."""
        # 프로토타입 존재 확인
        prototype = await self.db.get(Prototype, prototype_id)
        if prototype is None:
            raise AppError(
                "PROTOTYPE_NOT_FOUND", "프로토타입을 찾을 수 없습니다", 404
            )

        # PM 프로필 존재 확인
        pm_profile = await self.db.get(PMProfile, data.pm_profile_id)
        if pm_profile is None:
            raise AppError(
                "PM_PROFILE_NOT_FOUND", "PM 프로필을 찾을 수 없습니다", 404
            )

        # 매칭 점수 계산
        design_pattern = str(prototype.design_pattern or "")
        scores = self._claude.recommend_pm_scores(
            design_pattern, [str(pm_profile.specialty)]
        )
        match_score = scores.get(str(pm_profile.specialty), 40)

        reasoning = (
            f"{pm_profile.name}이(가) {data.role} 역할로 "
            f"{design_pattern} 프로젝트에 배정되었습니다."
        )

        composition = PMComposition(
            prototype_id=prototype_id,
            pm_profile_id=data.pm_profile_id,
            role=data.role,
            assigned_agents=data.assigned_agents,
            assigned_skills=data.assigned_skills,
            match_score=match_score,
            reasoning=reasoning,
        )
        self.db.add(composition)
        await self.db.commit()
        await self.db.refresh(composition)
        return composition

    async def update_composition(
        self, composition_id: UUID, data: PMCompositionUpdate
    ) -> PMComposition:
        """PM 구성을 수정한다."""
        composition = await self.db.get(PMComposition, composition_id)
        if composition is None:
            raise AppError(
                "COMPOSITION_NOT_FOUND", "PM 구성을 찾을 수 없습니다", 404
            )

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(composition, key, value)

        await self.db.commit()
        await self.db.refresh(composition)
        return composition

    # ── PM 평가 ──

    async def rate_pm(
        self, pm_profile_id: UUID, user_id: UUID, data: PMRatingCreate
    ) -> PMRating:
        """PM을 평가하고 메트릭을 갱신한다."""
        # PM 프로필 존재 확인
        pm_profile = await self.db.get(PMProfile, pm_profile_id)
        if pm_profile is None:
            raise AppError(
                "PM_PROFILE_NOT_FOUND", "PM 프로필을 찾을 수 없습니다", 404
            )

        rating = PMRating(
            pm_profile_id=pm_profile_id,
            project_id=data.project_id,
            user_id=user_id,
            score=data.score,
            comment=data.comment,
        )
        self.db.add(rating)
        await self.db.commit()
        await self.db.refresh(rating)

        # 메트릭 갱신
        await self._update_metrics(pm_profile_id)

        return rating

    async def get_metrics(self, pm_profile_id: UUID) -> PMMetric:
        """PM 메트릭을 조회한다."""
        stmt = select(PMMetric).where(
            PMMetric.pm_profile_id == pm_profile_id
        )
        result = await self.db.execute(stmt)
        metric = result.scalar_one_or_none()
        if metric is None:
            raise AppError(
                "METRICS_NOT_FOUND", "PM 메트릭을 찾을 수 없습니다", 404
            )
        return metric

    async def _update_metrics(self, pm_profile_id: UUID) -> None:
        """평가 데이터로 PM 메트릭을 갱신한다."""
        # 평균 점수 및 총 프로젝트 수 계산
        stmt = select(
            func.count().label("total"),
            func.avg(PMRating.score).label("avg_score"),
        ).where(PMRating.pm_profile_id == pm_profile_id)
        result = await self.db.execute(stmt)
        row = result.one()

        total = int(row.total)
        avg_rating = float(row.avg_score) if row.avg_score else 0.0

        # 메트릭 upsert
        stmt_metric = select(PMMetric).where(
            PMMetric.pm_profile_id == pm_profile_id
        )
        metric_result = await self.db.execute(stmt_metric)
        metric = metric_result.scalar_one_or_none()

        if metric is None:
            metric = PMMetric(
                pm_profile_id=pm_profile_id,
                total_projects=total,
                avg_rating=avg_rating,
                success_rate=min(avg_rating / 5.0 * 100, 100.0),
            )
            self.db.add(metric)
        else:
            metric.total_projects = total  # type: ignore[assignment]
            metric.avg_rating = avg_rating  # type: ignore[assignment]
            success = avg_rating / 5.0 * 100
            metric.success_rate = success if success <= 100.0 else 100.0  # type: ignore[assignment]

        await self.db.commit()
