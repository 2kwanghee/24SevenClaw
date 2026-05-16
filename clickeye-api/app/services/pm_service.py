"""PM 프로필 서비스 — PM 목록/추천/구성/평가."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import String as SAString
from sqlalchemy import case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.pm_composition import PMComposition
from app.models.pm_metrics import PMMetrics
from app.models.pm_profile import PMProfile
from app.models.pm_rating import PMRating
from app.models.prototype_session import Prototype, PrototypeSession
from app.schemas.pm_profile import (
    PMCompositionCreate,
    PMCompositionGroupedResponse,
    PMCompositionResponse,
    PMCompositionUpdate,
    PMProfileCreate,
    PMProfileUpdate,
    PMProfileWithMetrics,
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
        domain: str | None = None,
        specialty: str | None = None,
        is_active: bool | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[PMProfile], int]:
        """PM 프로필 목록을 반환한다.

        Args:
            domain: 도메인 필터 (예: "product", "backend")
            specialty: 전문분야 필터 — specialties 배열에 포함 여부
            is_active: 활성 상태 필터
            offset: 페이지 오프셋
            limit: 최대 반환 수
        """
        conditions: list[Any] = []
        if domain:
            conditions.append(PMProfile.domain == domain)
        if is_active is not None:
            conditions.append(PMProfile.is_active == is_active)
        if specialty:
            # JSON 배열에서 specialty 문자열 포함 여부 확인
            # SQLite/PostgreSQL 모두 호환: 텍스트로 캐스트 후 "specialty" 검색
            conditions.append(cast(PMProfile.specialties, SAString).contains(f'"{specialty}"'))

        count_stmt = select(func.count()).select_from(PMProfile).where(*conditions)
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

    async def get_profile(self, profile_id: UUID) -> PMProfileWithMetrics:
        """PM 프로필과 메트릭을 함께 조회한다."""
        profile = await self.db.get(PMProfile, profile_id)
        if profile is None:
            raise AppError("PM_PROFILE_NOT_FOUND", "PM 프로필을 찾을 수 없습니다", 404)

        # 메트릭 로드 (없으면 기본값 사용)
        stmt = select(PMMetrics).where(PMMetrics.pm_id == profile_id)
        result = await self.db.execute(stmt)
        metric = result.scalar_one_or_none()

        # SQLAlchemy Column 인스턴스 값은 Any로 취급
        raw: Any = profile
        return PMProfileWithMetrics(
            id=raw.id,
            name=raw.name,
            slug=raw.slug,
            avatar_url=raw.avatar_url,
            title=raw.title,
            description=raw.description,
            domain=raw.domain,
            specialties=list(raw.specialties or []),
            personality=dict(raw.personality or {}),
            is_active=bool(raw.is_active),
            created_at=raw.created_at,
            usage_count=int(metric.usage_count) if metric else 0,
            completed_projects=int(metric.completed_projects) if metric else 0,
            avg_rating=float(metric.avg_rating) if metric else 0.0,
            total_ratings=int(metric.total_ratings) if metric else 0,
            like_count=int(metric.like_count) if metric else 0,
            dislike_count=int(metric.dislike_count) if metric else 0,
            success_rate=float(metric.success_rate) if metric else 0.0,
            avg_completion_days=float(metric.avg_completion_days) if metric else 0.0,
        )

    # ── PM 프로필 관리 (admin) ──

    async def create_profile(self, data: PMProfileCreate) -> PMProfile:
        """PM 프로필을 생성한다."""
        existing = await self.db.execute(select(PMProfile).where(PMProfile.slug == data.slug))
        if existing.scalar_one_or_none() is not None:
            raise AppError("SLUG_CONFLICT", "이미 사용 중인 slug입니다", 409)

        profile = PMProfile(
            name=data.name,
            slug=data.slug,
            avatar_url=data.avatar_url,
            title=data.title,
            description=data.description,
            domain=data.domain,
            specialties=data.specialties,
            personality=data.personality,
            is_active=data.is_active,
            bio_long=data.bio_long,
            years_experience=data.years_experience,
            preferred_solution_types=data.preferred_solution_types,
            tech_stack_tags=data.tech_stack_tags,
            industry_tags=data.industry_tags,
            language=data.language,
            supported_platforms=data.supported_platforms or [],
        )
        self.db.add(profile)
        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def update_profile(self, profile_id: UUID, data: PMProfileUpdate) -> PMProfile:
        """PM 프로필을 수정한다."""
        profile = await self.db.get(PMProfile, profile_id)
        if profile is None:
            raise AppError("PM_PROFILE_NOT_FOUND", "PM 프로필을 찾을 수 없습니다", 404)

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(profile, key, value)
        profile.updated_at = datetime.now(UTC)  # type: ignore[assignment]

        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def delete_profile(self, profile_id: UUID) -> None:
        """PM 프로필을 삭제한다."""
        profile = await self.db.get(PMProfile, profile_id)
        if profile is None:
            raise AppError("PM_PROFILE_NOT_FOUND", "PM 프로필을 찾을 수 없습니다", 404)
        await self.db.delete(profile)
        await self.db.commit()

    async def delete_composition(self, composition_id: UUID) -> None:
        """PM 구성 컴포넌트를 삭제한다."""
        composition = await self.db.get(PMComposition, composition_id)
        if composition is None:
            raise AppError("COMPOSITION_NOT_FOUND", "PM 구성을 찾을 수 없습니다", 404)
        await self.db.delete(composition)
        await self.db.commit()

    # ── PM 추천 ──

    async def recommend_pms(
        self,
        prototype_id: UUID,
        session_id: UUID | None = None,
    ) -> list[dict[str, Any]]:
        """프로토타입에 적합한 PM을 추천한다.

        알고리즘:
            1. 도메인 기반 점수 (40%) — ClaudeService 룰 기반
            2. 전문분야 유사도 (30%) — design_pattern + 세션 프롬프트 키워드 매칭
            3. 평가지표 가중치 (30%) — avg_rating 기반

        Returns:
            list[{pm_profile: PMProfile, match_score: int, reasoning: str}]
            상위 3~5개 결과만 반환
        """
        # 프로토타입 조회
        prototype = await self.db.get(Prototype, prototype_id)
        if prototype is None:
            raise AppError("PROTOTYPE_NOT_FOUND", "프로토타입을 찾을 수 없습니다", 404)

        # 세션 컨텍스트 로드 (있는 경우)
        context_text = ""
        if session_id:
            session = await self.db.get(PrototypeSession, session_id)
            if session and session.solution_prompt:
                context_text = str(session.solution_prompt)

        # 활성 PM 프로필 조회
        stmt = select(PMProfile).where(PMProfile.is_active.is_(True))
        result = await self.db.execute(stmt)
        profiles = list(result.scalars().all())

        if not profiles:
            return []

        # 1단계: 도메인 기반 점수 (ClaudeService)
        design_pattern = str(prototype.design_pattern or "")
        domains = [str(p.domain or "") for p in profiles]
        domain_scores = self._claude.recommend_pm_scores(design_pattern, domains)

        # 2단계: 전문분야 유사도 키워드 준비
        combined_text = (design_pattern + " " + context_text).lower()
        keywords = [kw for kw in combined_text.split() if len(kw) > 2]

        # 3단계: 메트릭 일괄 로드 (N+1 방지)
        pm_ids = [p.id for p in profiles]
        metrics_stmt = select(PMMetrics).where(PMMetrics.pm_id.in_(pm_ids))
        metrics_result = await self.db.execute(metrics_stmt)
        metrics_by_pm: dict[Any, PMMetrics] = {m.pm_id: m for m in metrics_result.scalars().all()}

        # 4단계: 레지스트리 도메인 메타 기반 보너스 — PM 구성 슬러그의 domains 집합 수집
        # 모든 PM의 compositions를 한 번에 로드
        from app.models.registry import Agent, Skill

        comps_stmt = select(PMComposition).where(PMComposition.pm_id.in_(pm_ids))
        comps_result = await self.db.execute(comps_stmt)
        all_comps = list(comps_result.scalars().all())

        agent_slugs = {c.component_slug for c in all_comps if c.component_type == "agent"}
        skill_slugs = {c.component_slug for c in all_comps if c.component_type == "skill"}

        # 레지스트리에서 slug → domains 맵 구성
        reg_domain_map: dict[str, list[str]] = {}
        if agent_slugs:
            a_stmt = select(Agent).where(Agent.slug.in_(agent_slugs))
            for a in (await self.db.execute(a_stmt)).scalars().all():
                reg_domain_map[str(a.slug)] = list(a.domains or [])
        if skill_slugs:
            s_stmt = select(Skill).where(Skill.slug.in_(skill_slugs))
            for s in (await self.db.execute(s_stmt)).scalars().all():
                reg_domain_map[str(s.slug)] = list(s.domains or [])

        # PM별 레지스트리 도메인 집합
        pm_reg_domains: dict[Any, set[str]] = {}
        for comp in all_comps:
            _pid_c: Any = comp.pm_id
            if _pid_c not in pm_reg_domains:
                pm_reg_domains[_pid_c] = set()
            pm_reg_domains[_pid_c].update(reg_domain_map.get(str(comp.component_slug), []))

        # 세션 도메인 키워드 (design_pattern + context_text에서 추출)
        session_domain_tokens = {t.lower() for t in combined_text.split() if len(t) > 2}

        recommendations: list[dict[str, Any]] = []
        for profile in profiles:
            domain_key = str(profile.domain or "")
            domain_score = float(domain_scores.get(domain_key, 40))

            # 전문분야 유사도: 키워드가 specialties에 포함된 비율
            _specs: Any = profile.specialties
            pm_specialties = [s.lower() for s in (_specs or [])]
            if keywords and pm_specialties:
                matched = sum(
                    1 for kw in keywords if any(kw in spec or spec in kw for spec in pm_specialties)
                )
                specialty_score = min(matched / max(len(keywords), 1) * 200, 100.0)
            else:
                specialty_score = 50.0

            # 평가지표 점수: avg_rating(1~5) → 0~100 스케일
            _pid: Any = profile.id
            metric = metrics_by_pm.get(_pid)
            if metric and metric.total_ratings and int(metric.total_ratings) > 0:
                metric_score = float(metric.avg_rating or 0) / 5.0 * 100
            else:
                metric_score = 50.0  # 평가 없는 경우 중립값

            # 레지스트리 도메인 보너스: PM 구성 items의 domains가 세션 컨텍스트와 교집합
            reg_domains = pm_reg_domains.get(_pid, set())
            if reg_domains and session_domain_tokens:
                overlap = reg_domains & session_domain_tokens
                domain_bonus = min(len(overlap) / max(len(reg_domains), 1) * 100, 10.0)
            else:
                domain_bonus = 0.0

            # 가중 합산 (도메인 보너스는 최대 +10점)
            final_score = min(
                int(domain_score * 0.4 + specialty_score * 0.3 + metric_score * 0.3 + domain_bonus),
                100,
            )

            reasoning = (
                f"{profile.name}({profile.domain})은 "
                f"{design_pattern or '해당'} 프로젝트에 "
                f"도메인({int(domain_score)}pt)·"
                f"전문분야({int(specialty_score)}pt)·"
                f"평가({int(metric_score)}pt)"
                + (f"·레지스트리({int(domain_bonus)}pt)" if domain_bonus > 0 else "")
                + f" 기준으로 종합 {final_score}점입니다."
            )
            recommendations.append(
                {
                    "pm_profile": profile,
                    "match_score": final_score,
                    "reasoning": reasoning,
                }
            )

        # 점수 내림차순 정렬 후 상위 3~5개 반환
        recommendations.sort(key=lambda r: int(r["match_score"]), reverse=True)
        return recommendations[:5]

    # ── PM 구성 ──

    async def get_composition(self, pm_id: UUID) -> PMCompositionGroupedResponse:
        """PM 프로필의 구성 컴포넌트를 타입별로 그룹화하여 반환한다."""
        stmt = (
            select(PMComposition)
            .where(PMComposition.pm_id == pm_id)
            .order_by(PMComposition.display_order.asc())
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())

        grouped: dict[str, list[PMCompositionResponse]] = {
            "agents": [],
            "skills": [],
            "hooks": [],
            "mcp_servers": [],
            "plugins": [],
        }
        type_map = {
            "agent": "agents",
            "skill": "skills",
            "hook": "hooks",
            "mcp_server": "mcp_servers",
            "plugin": "plugins",
        }
        for item in items:
            key = type_map.get(str(item.component_type or ""), "agents")
            grouped[key].append(PMCompositionResponse.model_validate(item))

        return PMCompositionGroupedResponse(**grouped)

    async def create_composition(self, pm_id: UUID, data: PMCompositionCreate) -> PMComposition:
        """PM 구성 컴포넌트를 추가한다."""
        pm_profile = await self.db.get(PMProfile, pm_id)
        if pm_profile is None:
            raise AppError("PM_PROFILE_NOT_FOUND", "PM 프로필을 찾을 수 없습니다", 404)

        composition = PMComposition(
            pm_id=pm_id,
            component_type=data.component_type,
            component_slug=data.component_slug,
            component_name=data.component_name,
            config=data.config,
            display_order=data.display_order,
            is_required=data.is_required,
        )
        self.db.add(composition)
        await self.db.commit()
        await self.db.refresh(composition)
        return composition

    async def update_composition(
        self, composition_id: UUID, data: PMCompositionUpdate
    ) -> PMComposition:
        """PM 구성 컴포넌트를 수정한다."""
        composition = await self.db.get(PMComposition, composition_id)
        if composition is None:
            raise AppError("COMPOSITION_NOT_FOUND", "PM 구성을 찾을 수 없습니다", 404)

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(composition, key, value)

        await self.db.commit()
        await self.db.refresh(composition)
        return composition

    # ── PM 평가 ──

    async def rate_pm(self, pm_profile_id: UUID, user_id: UUID, data: PMRatingCreate) -> PMRating:
        """PM을 평가하고 메트릭을 갱신한다."""
        pm_profile = await self.db.get(PMProfile, pm_profile_id)
        if pm_profile is None:
            raise AppError("PM_PROFILE_NOT_FOUND", "PM 프로필을 찾을 수 없습니다", 404)

        rating = PMRating(
            pm_id=pm_profile_id,
            session_id=data.session_id,
            user_id=user_id,
            rating=data.rating,
            reaction=data.reaction,
            comment=data.comment,
        )
        self.db.add(rating)
        await self.db.commit()
        await self.db.refresh(rating)

        await self._update_metrics(pm_profile_id)

        return rating

    async def list_ratings(
        self, pm_profile_id: UUID, offset: int = 0, limit: int = 20
    ) -> tuple[list[PMRating], int]:
        """PM 평가 목록을 반환한다."""
        count_stmt = (
            select(func.count()).select_from(PMRating).where(PMRating.pm_id == pm_profile_id)
        )
        total_result = await self.db.execute(count_stmt)
        total = int(total_result.scalar_one())

        stmt = (
            select(PMRating)
            .where(PMRating.pm_id == pm_profile_id)
            .order_by(PMRating.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        ratings = list(result.scalars().all())
        return ratings, total

    async def get_metrics(self, pm_profile_id: UUID) -> PMMetrics:
        """PM 메트릭을 조회한다."""
        stmt = select(PMMetrics).where(PMMetrics.pm_id == pm_profile_id)
        result = await self.db.execute(stmt)
        metric = result.scalar_one_or_none()
        if metric is None:
            raise AppError("METRICS_NOT_FOUND", "PM 메트릭을 찾을 수 없습니다", 404)
        return metric

    async def _update_metrics(self, pm_profile_id: UUID) -> None:
        """평가 데이터로 PM 메트릭을 갱신한다."""
        stmt = select(
            func.count().label("total"),
            func.avg(PMRating.rating).label("avg_rating"),
            func.coalesce(func.sum(case((PMRating.reaction == "like", 1), else_=0)), 0).label(
                "like_count"
            ),
            func.coalesce(func.sum(case((PMRating.reaction == "dislike", 1), else_=0)), 0).label(
                "dislike_count"
            ),
        ).where(PMRating.pm_id == pm_profile_id)
        result = await self.db.execute(stmt)
        row = result.one()

        total_ratings = int(row.total)
        avg_rating = float(row.avg_rating) if row.avg_rating else 0.0
        like_count = int(row.like_count or 0)
        dislike_count = int(row.dislike_count or 0)

        stmt_metric = select(PMMetrics).where(PMMetrics.pm_id == pm_profile_id)
        metric_result = await self.db.execute(stmt_metric)
        metric = metric_result.scalar_one_or_none()

        if metric is None:
            metric = PMMetrics(
                pm_id=pm_profile_id,
                total_ratings=total_ratings,
                avg_rating=avg_rating,
                like_count=like_count,
                dislike_count=dislike_count,
                success_rate=min(avg_rating / 5.0 * 100, 100.0),
            )
            self.db.add(metric)
        else:
            metric.total_ratings = total_ratings  # type: ignore[assignment]
            metric.avg_rating = avg_rating  # type: ignore[assignment]
            metric.like_count = like_count  # type: ignore[assignment]
            metric.dislike_count = dislike_count  # type: ignore[assignment]
            success = avg_rating / 5.0 * 100
            metric.success_rate = success if success <= 100.0 else 100.0  # type: ignore[assignment]

        await self.db.commit()
