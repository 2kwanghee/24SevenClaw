"""PM 프로필·컴포지션·메트릭 DB 초기 시딩 스크립트.

멱등성: slug 기준으로 이미 존재하는 레코드는 건너뜀.

Usage (standalone):
    uv run python -m scripts.seed_pm_data

Usage (pytest fixture):
    from scripts.seed_pm_data import seed_pm_data

    @pytest.fixture
    async def seeded_pms(db_session: AsyncSession) -> dict:
        return await seed_pm_data(db_session)
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.pm_composition import PMComposition
from app.models.pm_metrics import PMMetrics
from app.models.pm_profile import PMProfile

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


async def _get_or_create_profile(
    db: AsyncSession, profile_data: dict[str, Any]
) -> tuple[UUID, bool]:
    """PM 프로필을 조회하거나 새로 생성한다.

    Returns:
        (pm_id, was_created)
    """
    slug: str = profile_data["slug"]
    row = await db.execute(select(PMProfile).where(PMProfile.slug == slug))
    existing: PMProfile | None = row.scalar_one_or_none()
    if existing is not None:
        logger.debug("건너뜀(기존): pm_profiles.slug=%s", slug)
        return UUID(str(existing.id)), False

    profile = PMProfile(
        name=profile_data["name"],
        slug=slug,
        avatar_url=profile_data.get("avatar_url"),
        title=profile_data.get("title"),
        description=profile_data.get("description"),
        domain=profile_data.get("specialty"),
        specialties=profile_data.get("skills", []),
        personality=profile_data.get("personality_traits", {}),
        is_active=profile_data.get("is_active", True),
    )
    db.add(profile)
    await db.flush()
    logger.info("생성: PMProfile slug=%s id=%s", slug, profile.id)
    return UUID(str(profile.id)), True


async def _get_or_create_composition(
    db: AsyncSession, pm_id: UUID, comp: dict[str, Any]
) -> bool:
    """PM 컴포지션을 조회하거나 생성한다. 신규 생성 여부 반환."""
    comp_type: str = comp["component_type"]
    comp_slug: str = comp["component_slug"]

    row = await db.execute(
        select(PMComposition).where(
            PMComposition.pm_id == pm_id,
            PMComposition.component_type == comp_type,
            PMComposition.component_slug == comp_slug,
        )
    )
    if row.scalar_one_or_none() is not None:
        logger.debug(
            "건너뜀(기존): pm_compositions pm_id=%s type=%s slug=%s",
            pm_id, comp_type, comp_slug,
        )
        return False

    composition = PMComposition(
        pm_id=pm_id,
        component_type=comp_type,
        component_slug=comp_slug,
        component_name=comp["component_name"],
        config=comp.get("config", {}),
        display_order=comp.get("display_order", 0),
        is_required=comp.get("is_required", False),
    )
    db.add(composition)
    logger.info(
        "생성: PMComposition pm_id=%s type=%s slug=%s", pm_id, comp_type, comp_slug
    )
    return True


async def _get_or_create_metrics(db: AsyncSession, pm_id: UUID) -> bool:
    """PM 메트릭 초기값을 조회하거나 생성한다. 신규 생성 여부 반환."""
    row = await db.execute(select(PMMetrics).where(PMMetrics.pm_id == pm_id))
    if row.scalar_one_or_none() is not None:
        logger.debug("건너뜀(기존): pm_metrics pm_id=%s", pm_id)
        return False

    metrics = PMMetrics(
        pm_id=pm_id,
        usage_count=0,
        completed_projects=0,
        avg_rating=0.0,
        total_ratings=0,
        success_rate=0.0,
        avg_completion_days=0.0,
    )
    db.add(metrics)
    logger.info("생성: PMMetrics pm_id=%s", pm_id)
    return True


async def seed_pm_data(
    db: AsyncSession,
    data_dir: Path | None = None,
) -> dict[str, Any]:
    """PM 프로필·컴포지션·메트릭을 DB에 시딩한다 (멱등성 보장).

    pytest fixture 활용 예::

        @pytest.fixture
        async def seeded_pms(db_session: AsyncSession) -> dict:
            return await seed_pm_data(db_session)

    Args:
        db: SQLAlchemy async 세션.
        data_dir: 데이터 파일 디렉토리 (None이면 프로젝트 루트의 data/ 사용).

    Returns:
        {
            "pm_ids": list[UUID],        # 처리된 모든 PM ID (신규 + 기존)
            "profiles_created": int,     # 신규 생성된 프로필 수
            "compositions_created": int, # 신규 생성된 컴포지션 수
            "metrics_created": int,      # 신규 생성된 메트릭 수
        }
    """
    effective_dir = data_dir if data_dir is not None else _DATA_DIR
    profiles_path = effective_dir / "pm_seed_profiles.json"
    compositions_path = effective_dir / "pm_compositions.json"

    profiles_raw: list[dict[str, Any]] = _load_json(profiles_path)["profiles"]
    compositions_map: dict[str, list[dict[str, Any]]] = (
        _load_json(compositions_path)["compositions"]
        if compositions_path.exists()
        else {}
    )

    pm_ids: list[UUID] = []
    profiles_created = 0
    compositions_created = 0
    metrics_created = 0

    for profile_data in profiles_raw:
        pm_id, created = await _get_or_create_profile(db, profile_data)
        pm_ids.append(pm_id)
        if created:
            profiles_created += 1

        slug: str = profile_data["slug"]
        for comp in compositions_map.get(slug, []):
            if await _get_or_create_composition(db, pm_id, comp):
                compositions_created += 1

        if await _get_or_create_metrics(db, pm_id):
            metrics_created += 1

    await db.commit()

    return {
        "pm_ids": pm_ids,
        "profiles_created": profiles_created,
        "compositions_created": compositions_created,
        "metrics_created": metrics_created,
    }


async def main() -> None:
    """스탠드얼론 실행 진입점."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    async with async_session() as db:
        result = await seed_pm_data(db)

    print(
        "시딩 완료 — "
        f"프로필 {result['profiles_created']}개, "
        f"컴포지션 {result['compositions_created']}개, "
        f"메트릭 {result['metrics_created']}개 생성"
    )


if __name__ == "__main__":
    asyncio.run(main())
