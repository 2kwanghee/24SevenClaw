"""프로토타입 세션 서비스 — 세션 생성, 프로토타입 생성/조회/선택/확정."""

import asyncio
import logging
import re
import time
import uuid as _uuid_mod
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.pm_metrics import PMMetrics
from app.models.pm_profile import PMProfile
from app.models.pm_recommendation_log import PMRecommendationLog
from app.models.project import Project
from app.models.prototype_session import Prototype, PrototypeSession
from app.schemas.prototype import (
    FinalizeRequest,
    PrototypeSelectRequest,
    PrototypeSessionCreate,
    PrototypeSessionUpdate,
)
from app.services.app_setting_service import AppSettingService
from app.services.claude_service import ClaudeService
from app.services.prototype_catalog_service import PrototypeCatalogService

logger = logging.getLogger(__name__)


def _slugify(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    return re.sub(r"-+", "-", slug).strip("-")


class PrototypeService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._claude = ClaudeService()

    async def create_session(self, user_id: UUID, data: PrototypeSessionCreate) -> PrototypeSession:
        """프로토타입 세션을 생성한다."""
        session = PrototypeSession(
            organization_id=data.organization_id,
            user_id=user_id,
            solution_prompt=data.solution_prompt,
            status="pending",
            extra={"user_tech_stack": list(data.tech_stack)},
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_session(self, session_id: UUID, user_id: UUID) -> PrototypeSession:
        """세션을 조회한다. 소유자 검증 포함."""
        stmt = select(PrototypeSession).where(
            PrototypeSession.id == session_id,
            PrototypeSession.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()
        if session is None:
            raise AppError("SESSION_NOT_FOUND", "프로토타입 세션을 찾을 수 없습니다", 404)
        return session

    async def list_sessions(
        self, user_id: UUID, offset: int = 0, limit: int = 20
    ) -> tuple[list[PrototypeSession], int]:
        """사용자의 세션 목록을 반환한다."""
        conditions = [PrototypeSession.user_id == user_id]

        count_stmt = select(func.count()).select_from(PrototypeSession).where(*conditions)
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

    async def get_session_status(self, session_id: UUID, user_id: UUID) -> PrototypeSession:
        """세션 상태를 조회한다."""
        return await self.get_session(session_id, user_id)

    async def start_generation(self, session_id: UUID, user_id: UUID) -> PrototypeSession:
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

        절차:
        1. analyze_solution으로 요구사항 구조화 (실패 시 규칙 기반 폴백)
        2. AppSetting에서 variant_count 조회 (기본 3)
        3. PrototypeCatalogService로 태그 매칭 카탈로그 엔트리 조회
        4. generate_ui_structure × variant_count — 변형별 UI 구조 생성
           - AI 모드: 카탈로그 엔트리를 참조 자료로 Claude 프롬프트에 주입
           - 폴백 모드: 카탈로그 엔트리에서 직접 구조 데이터 사용
        5. 변형 루프 완료 후 session.status = "completed"
        6. 루프 외부 예외 발생 시 session.status = "failed"
        """
        stmt = select(PrototypeSession).where(
            PrototypeSession.id == session_id,
            PrototypeSession.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        session = result.scalar_one_or_none()
        if session is None:
            return

        prompt = str(session.solution_prompt or "")

        # 재진입(race condition) 방어: 기존 프로토타입을 모두 제거하고 새로 생성
        await self.db.execute(
            delete(Prototype).where(Prototype.session_id == session_id)
        )
        await self.db.commit()

        try:
            extra: dict[str, Any] = session.extra or {}  # type: ignore[assignment]
            user_tech_stack: list[str] = list(extra.get("user_tech_stack", []))
            org_context: dict[str, Any] = {"user_tech_stack": user_tech_stack}

            # 1. 요구사항 분석 — Claude API, 실패 시 규칙 기반 폴백
            try:
                requirements = await self._claude.analyze_solution(prompt, org_context)
            except Exception:
                logger.warning(
                    "analyze_solution API 실패, 규칙 기반 폴백 사용 (session_id=%s)", session_id
                )
                primary_tag = self._claude.analyze_input(prompt)
                requirements = {
                    "primary_tag": primary_tag,
                    "tags": [primary_tag],
                    "solution_type": primary_tag,
                    "features": [],
                    "tech_stack": {},
                    "complexity": "medium",
                    "target_users": "",
                    "key_requirements": [],
                }

            await self.db.execute(
                update(PrototypeSession)
                .where(PrototypeSession.id == session_id)
                .values(parsed_requirements=requirements)
            )
            await self.db.commit()

            # 2. variant_count + rag_top_k 조회 (app_settings 테이블)
            setting_svc = AppSettingService(self.db)
            variant_count = await setting_svc.get_variant_count()
            rag_top_k = await setting_svc.get_rag_top_k()

            # 3. 카탈로그 태그 매칭 — rag_top_k개 조회 (AI 모드 RAG 컨텍스트용)
            candidate_tags: list[str] = list(requirements.get("tags") or [])
            primary_tag_val = str(
                requirements.get("primary_tag") or requirements.get("solution_type") or "fullstack"
            )
            if primary_tag_val not in candidate_tags:
                candidate_tags.insert(0, primary_tag_val)

            catalog_svc = PrototypeCatalogService(self.db)
            catalog_entries = await catalog_svc.match_by_tags(
                candidate_tags=candidate_tags, limit=rag_top_k
            )

            # RAG 참조용 전체 직렬화 (rag_top_k개)
            catalog_refs: list[dict[str, Any]] = [
                _catalog_entry_to_dict(e) for e in catalog_entries
            ]
            # 폴백용 top-variant_count 엔트리 (실패 시 카탈로그 직접 사용)
            fallback_entries = catalog_refs[:variant_count]

            # 4. variant별 역할 목록 생성
            variant_roles = _build_variant_roles(variant_count, user_tech_stack)

            for idx in range(variant_count):
                proto: Prototype
                role_config = variant_roles[idx]
                catalog_entry_dict = fallback_entries[idx] if idx < len(fallback_entries) else None

                try:
                    ui_data = await self._claude.generate_ui_structure(
                        requirements,
                        idx,
                        role_config,
                        catalog_entry=catalog_entry_dict,
                        catalog_references=catalog_refs if catalog_refs else None,
                    )
                    design_style = str(ui_data.get("design_style", "minimal"))
                    arch_pattern = str(ui_data.get("architecture_pattern", design_style))
                    proto = Prototype(
                        session_id=session.id,
                        variant_index=idx,
                        title=f"프로토타입 {idx + 1} — {arch_pattern}",
                        design_pattern=design_style,
                        menu_structure=ui_data.get("menu_structure"),
                        ui_structure=ui_data,
                        color_palette=ui_data.get("color_palette"),
                        status="ready",
                    )
                except Exception:
                    # API 실패 → 카탈로그 엔트리 기반 폴백
                    logger.warning(
                        "generate_ui_structure 실패 (variant=%d), 카탈로그 폴백 (session_id=%s)",
                        idx,
                        session_id,
                    )
                    try:
                        proto = _build_proto_from_catalog(
                            session_id=session.id,
                            idx=idx,
                            catalog_entry=catalog_entry_dict,
                            role_config=role_config,
                            user_tech_stack=user_tech_stack,
                        )
                    except Exception:
                        proto = Prototype(
                            session_id=session.id,
                            variant_index=idx,
                            title=f"프로토타입 {idx + 1}",
                            status="failed",
                        )

                self.db.add(proto)
                await self.db.commit()

            # 5. 세션 완료 처리
            await self.db.execute(
                update(PrototypeSession)
                .where(PrototypeSession.id == session_id)
                .values(status="completed")
            )
            await self.db.commit()

        except Exception:
            logger.exception(
                "run_generation 실패 (session_id=%s)", session_id
            )
            await self.db.execute(
                update(PrototypeSession)
                .where(PrototypeSession.id == session_id)
                .values(status="failed")
            )
            await self.db.commit()
            raise

    async def list_prototypes(self, session_id: UUID, user_id: UUID) -> list[Prototype]:
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
            raise AppError("PROTOTYPE_NOT_FOUND", "프로토타입을 찾을 수 없습니다", 404)

        # 세션의 selected_prototype_id 업데이트
        await self.db.execute(
            update(PrototypeSession)
            .where(PrototypeSession.id == session_id)
            .values(selected_prototype_id=data.prototype_id)
        )
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def delete_session(self, session_id: UUID, user_id: UUID) -> None:
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
                raise AppError("PROTOTYPE_NOT_FOUND", "프로토타입을 찾을 수 없습니다", 404)
            update_values["selected_prototype_id"] = data.selected_prototype_id

        if data.selected_pm_id is not None:
            # PM 프로필 존재 확인
            pm = await self.db.get(PMProfile, data.selected_pm_id)
            if pm is None:
                raise AppError("PM_PROFILE_NOT_FOUND", "PM 프로필을 찾을 수 없습니다", 404)
            update_values["selected_pm_id"] = data.selected_pm_id
            # 추천 로그에 선택된 PM 기록 (품질 지표 수집용)
            await self.db.execute(
                update(PMRecommendationLog)
                .where(PMRecommendationLog.session_id == session_id)
                .values(selected_pm_id=data.selected_pm_id)
            )

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

    def _compute_rule_scores(
        self,
        profiles: list[PMProfile],
        design_pattern: str,
        context_text: str,
        metrics_by_pm: dict[Any, PMMetrics],
    ) -> dict[Any, dict[str, float]]:
        """규칙 기반 점수 계산. {pm_id: {domain, specialty, metric, rule_score}} 반환."""
        domains = [str(p.domain or "") for p in profiles]
        domain_scores_map = self._claude.recommend_pm_scores(design_pattern, domains)

        combined_text = (design_pattern + " " + context_text).lower()
        keywords = [kw for kw in combined_text.split() if len(kw) > 2]

        result: dict[Any, dict[str, float]] = {}
        for profile in profiles:
            domain_key = str(profile.domain or "")
            domain_score = float(domain_scores_map.get(domain_key, 40))

            _specs: Any = profile.specialties
            pm_specialties = [s.lower() for s in (_specs or [])]
            if keywords and pm_specialties:
                matched = sum(
                    1 for kw in keywords if any(kw in spec or spec in kw for spec in pm_specialties)
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

            rule_score = domain_score * 0.4 + specialty_score * 0.3 + metric_score * 0.3
            result[_pid] = {
                "domain": domain_score,
                "specialty": specialty_score,
                "metric": metric_score,
                "rule_score": rule_score,
            }
        return result

    async def recommend_pms_for_session(
        self, session_id: UUID, user_id: UUID
    ) -> list[dict[str, Any]]:
        """세션의 선택된 프로토타입 기반으로 PM을 추천한다 (하이브리드 Claude+Rule).

        Claude 점수 × 0.7 + 규칙 점수 × 0.3으로 최종 순위 결정.
        Claude API 실패 시 규칙 기반 단독으로 폴백하며 결과를 로그에 기록한다.
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
            raise AppError("PROTOTYPE_NOT_FOUND", "프로토타입을 찾을 수 없습니다", 404)

        context_text = str(session.solution_prompt or "")
        design_pattern = str(prototype.design_pattern or "")

        # 활성 PM 프로필 조회
        stmt = select(PMProfile).where(PMProfile.is_active.is_(True))
        result = await self.db.execute(stmt)
        profiles = list(result.scalars().all())

        if not profiles:
            return []

        # 메트릭 일괄 로드 (N+1 방지)
        pm_ids = [p.id for p in profiles]
        metrics_stmt = select(PMMetrics).where(PMMetrics.pm_id.in_(pm_ids))
        metrics_result = await self.db.execute(metrics_stmt)
        metrics_by_pm: dict[Any, PMMetrics] = {m.pm_id: m for m in metrics_result.scalars().all()}

        # 규칙 기반 점수 계산
        rule_detail = self._compute_rule_scores(
            profiles, design_pattern, context_text, metrics_by_pm
        )

        # Claude 하이브리드 추천 시도
        pm_catalog = [
            {
                "id": str(p.id),
                "name": p.name,
                "title": p.title or "",
                "domain": p.domain or "",
                "specialties": list(p.specialties or []),
                "tech_stack_tags": list(getattr(p, "tech_stack_tags", None) or []),
                "industry_tags": list(getattr(p, "industry_tags", None) or []),
                "preferred_solution_types": list(
                    getattr(p, "preferred_solution_types", None) or []
                ),
                "bio_long": getattr(p, "bio_long", None) or "",
            }
            for p in profiles
        ]

        ui_structure: Any = prototype.ui_structure or {}
        requirements = {
            "solution_prompt": context_text,
            "solution_type": design_pattern,
            "architecture_pattern": ui_structure.get("architecture_pattern", ""),
            "tech_stack": ui_structure.get("tech_stack_tags", []),
            "pros": ui_structure.get("pros", []),
            "cons": ui_structure.get("cons", []),
        }

        claude_raw: dict[str, Any] | None = None
        is_fallback = False
        start_ms = int(time.monotonic() * 1000)

        try:
            claude_result = await self._claude.recommend_pm(
                requirements=requirements,
                prototype_style=design_pattern,
                pm_catalog=pm_catalog,
            )
            claude_raw = claude_result
        except Exception as e:
            logger.warning("recommend_pms_for_session: Claude 호출 실패, 폴백 → %s", e)
            is_fallback = True

        latency_ms = int(time.monotonic() * 1000) - start_ms

        # Claude 결과로 점수 맵 구성
        claude_scores: dict[str, float] = {}
        if not is_fallback and claude_raw:
            rec_pm_id = str(claude_raw.get("recommended_pm_id") or "")
            rec_score = float(claude_raw.get("match_score") or 0)
            if rec_pm_id:
                claude_scores[rec_pm_id] = rec_score
            for alt in claude_raw.get("alternatives", []):
                alt_id = str(alt.get("pm_id") or "")
                alt_score = float(alt.get("match_score") or 0)
                if alt_id:
                    claude_scores[alt_id] = alt_score

        # 하이브리드 최종 점수 산출
        recommendations: list[dict[str, Any]] = []
        final_ranking_log: list[dict[str, Any]] = []

        profile_by_id = {str(p.id): p for p in profiles}
        for pm_id_str, profile in profile_by_id.items():
            rule_info = rule_detail.get(profile.id, {})
            rule_score = rule_info.get("rule_score", 50.0)

            if not is_fallback and pm_id_str in claude_scores:
                claude_score = claude_scores[pm_id_str]
                final_score = claude_score * 0.7 + rule_score * 0.3
            else:
                claude_score = 0.0
                final_score = rule_score

            final_score_int = int(final_score)

            rec_pm_id = str(claude_raw.get("recommended_pm_id") if claude_raw else None)
            if not is_fallback and claude_raw and rec_pm_id == pm_id_str:
                reasoning = str(claude_raw.get("reasoning") or "")
            else:
                rs = rule_info
                reasoning = (
                    f"{profile.name}({profile.domain})은 "
                    f"{design_pattern or '해당'} 프로젝트에 "
                    f"도메인({int(rs.get('domain', 0))}pt)·"
                    f"전문분야({int(rs.get('specialty', 0))}pt)·"
                    f"평가({int(rs.get('metric', 0))}pt) 기준으로 "
                    f"종합 {final_score_int}점입니다."
                )

            recommendations.append(
                {
                    "pm_profile": profile,
                    "match_score": final_score_int,
                    "reasoning": reasoning,
                }
            )
            final_ranking_log.append(
                {
                    "pm_id": pm_id_str,
                    "claude_score": claude_score,
                    "rule_score": rule_score,
                    "final_score": final_score,
                }
            )

        recommendations.sort(key=lambda r: int(r["match_score"]), reverse=True)
        top5 = recommendations[:5]

        # 추천 로그 기록
        try:
            log_entry = PMRecommendationLog(
                id=_uuid_mod.uuid4(),
                session_id=session_id,
                input_snapshot={
                    "solution_prompt": context_text[:500],
                    "design_pattern": design_pattern,
                    "pm_catalog_size": len(profiles),
                    "tech_stack": ui_structure.get("tech_stack_tags", []),
                },
                claude_raw=claude_raw,
                final_ranking=final_ranking_log,
                latency_ms=latency_ms,
                is_fallback=is_fallback,
            )
            self.db.add(log_entry)
            await self.db.commit()
        except Exception as e:
            logger.warning("recommend_pms_for_session: 로그 저장 실패 → %s", e)

        return top5

    async def recommend_components_for_session(
        self, session_id: UUID, user_id: UUID
    ) -> dict[str, Any]:
        """선택된 프로토타입의 카탈로그 엔트리 기반으로 에이전트/스킬을 추천한다.

        선택된 프로토타입이 없으면 AppError(409).
        카탈로그 엔트리 매칭 순서:
          1. prototype.design_pattern == catalog.design_pattern
          2. prototype.ui_structure.primary_tag == catalog.primary_tag
          3. 폴백: design_pattern 키워드 기반 기본값
        """
        from app.engine.catalog import AGENTS, SKILLS
        from app.models.prototype_catalog import PrototypeCatalogEntry

        session = await self.get_session(session_id, user_id)
        if session.selected_prototype_id is None:
            raise AppError(
                "NO_PROTOTYPE_SELECTED",
                "컴포넌트 추천을 위해 먼저 프로토타입을 선택하세요",
                409,
            )

        prototype = await self.db.get(Prototype, session.selected_prototype_id)
        if prototype is None:
            raise AppError("PROTOTYPE_NOT_FOUND", "프로토타입을 찾을 수 없습니다", 404)

        valid_agent_ids = {a["id"] for a in AGENTS}
        valid_skill_ids = {s["id"] for s in SKILLS}

        # 1차 매칭: design_pattern 일치
        catalog_entry = None
        if prototype.design_pattern:
            stmt = (
                select(PrototypeCatalogEntry)
                .where(
                    PrototypeCatalogEntry.design_pattern == prototype.design_pattern,
                    PrototypeCatalogEntry.is_active.is_(True),
                )
                .order_by(PrototypeCatalogEntry.priority.desc())
                .limit(1)
            )
            catalog_entry = (await self.db.execute(stmt)).scalar_one_or_none()

        # 2차 매칭: primary_tag 일치
        if catalog_entry is None:
            ui: dict[str, Any] = prototype.ui_structure or {}  # type: ignore[assignment]
            primary_tag = ui.get("primary_tag") or ui.get("solution_type")
            if primary_tag:
                stmt = (
                    select(PrototypeCatalogEntry)
                    .where(
                        PrototypeCatalogEntry.primary_tag == primary_tag,
                        PrototypeCatalogEntry.is_active.is_(True),
                    )
                    .order_by(PrototypeCatalogEntry.priority.desc())
                    .limit(1)
                )
                catalog_entry = (await self.db.execute(stmt)).scalar_one_or_none()

        if catalog_entry is not None:
            rec_agents = [
                a for a in list(catalog_entry.recommended_agents or []) if a in valid_agent_ids
            ]
            rec_skills = [
                s for s in list(catalog_entry.recommended_skills or []) if s in valid_skill_ids
            ]
            return {
                "agents": rec_agents,
                "skills": rec_skills,
                "excluded_agents": list(catalog_entry.excluded_agents or []),
                "catalog_entry_slug": catalog_entry.slug,
                "reasoning": f"{catalog_entry.title} 카탈로그 기반 추천",
            }

        # 폴백: design_pattern 키워드 기반 기본 추천
        return _default_component_recommendation(prototype, valid_agent_ids, valid_skill_ids)

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

        # slug 생성 (중복 시 숫자 접미사, 삭제된 프로젝트는 충돌에서 제외)
        slug = _slugify(data.project_name)
        base_slug = slug
        counter = 1
        while True:
            stmt = select(Project).where(
                Project.owner_id == user_id,
                Project.slug == slug,
                Project.status != "deleted",
            )
            result = await self.db.execute(stmt)
            if result.scalars().first() is None:
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

        # Linear/Notion 초기 태스크 자동 등록 (실패해도 프로젝트 생성은 성공으로 처리)
        initial_task_url = await self._register_initial_tasks(data)
        if initial_task_url:
            await self.db.execute(
                update(Project)
                .where(Project.id == project.id)
                .values(initial_task_url=initial_task_url)
            )
            await self.db.commit()
            await self.db.refresh(project)

        return project

    async def _register_initial_tasks(self, data: FinalizeRequest) -> str | None:
        """Linear/Notion 초기 태스크를 생성하고 URL을 반환한다. 실패 시 None 반환."""
        from app.services import linear_service, notion_service

        if data.linear_api_key and data.linear_team_id:
            try:
                url = await asyncio.to_thread(
                    linear_service.create_initial_task,
                    data.linear_api_key,
                    data.linear_team_id,
                    data.project_name,
                )
                if url:
                    return url
            except Exception as exc:
                logger.warning("Linear 초기 태스크 생성 실패: %s", exc)

        if data.notion_api_key and data.notion_database_id:
            try:
                url = await asyncio.to_thread(
                    notion_service.create_initial_task,
                    data.notion_api_key,
                    data.notion_database_id,
                    data.project_name,
                )
                if url:
                    return url
            except Exception as exc:
                logger.warning("Notion 초기 태스크 생성 실패: %s", exc)

        return None


# ── 헬퍼 함수 ────────────────────────────────────────────────────────────────


def _default_component_recommendation(
    prototype: "Prototype",
    valid_agent_ids: set[str],
    valid_skill_ids: set[str],
) -> dict[str, Any]:
    """카탈로그 엔트리 없을 때 design_pattern 키워드 기반 기본 추천."""
    pattern = (prototype.design_pattern or "").lower()
    ui: dict[str, Any] = prototype.ui_structure or {}  # type: ignore[assignment]
    solution_type = (ui.get("primary_tag") or ui.get("solution_type") or "").lower()
    tag = pattern or solution_type

    agents: list[str] = []
    if any(k in tag for k in ("fullstack", "saas", "mvp")):
        agents = ["fullstack", "backend", "frontend"]
    elif any(k in tag for k in ("rest", "api", "backend")):
        agents = ["backend"]
    elif any(k in tag for k in ("internal", "lowcode", "tool")):
        agents = ["frontend", "backend"]
    elif any(k in tag for k in ("mobile",)):
        agents = ["frontend"]
    else:
        agents = ["fullstack"]

    return {
        "agents": [a for a in agents if a in valid_agent_ids],
        "skills": [],
        "excluded_agents": [],
        "catalog_entry_slug": None,
        "reasoning": "카탈로그 엔트리 미매칭 — 기본값 반환",
    }


def _build_variant_roles(variant_count: int, user_tech_stack: list[str]) -> list[dict[str, Any]]:
    """variant_count만큼 역할 config 목록을 생성한다."""
    base_roles = [
        {"role": "user_stack_recommended", "is_recommended": True},
        {"role": "alternative_stack", "is_recommended": False},
        {"role": "different_architecture", "is_recommended": False},
    ]
    roles = []
    for i in range(variant_count):
        base = base_roles[min(i, len(base_roles) - 1)].copy()
        if i >= len(base_roles):
            base = {"role": f"variant_{i}", "is_recommended": False}
        base["user_tech_stack"] = user_tech_stack
        roles.append(base)
    return roles


def _catalog_entry_to_dict(entry: Any) -> dict[str, Any]:
    """PrototypeCatalogEntry SQLAlchemy 모델을 dict로 변환한다."""
    return {
        "id": str(entry.id),
        "slug": entry.slug,
        "title": entry.title,
        "description": entry.description or "",
        "tags": list(entry.tags or []),
        "primary_tag": entry.primary_tag or "",
        "design_pattern": entry.design_pattern or "",
        "architecture_pattern": entry.architecture_pattern or "",
        "tech_stack_tags": list(entry.tech_stack_tags or []),
        "pros": list(entry.pros or []),
        "cons": list(entry.cons or []),
        "ui_structure": dict(entry.ui_structure or {}),
        "menu_structure": dict(entry.menu_structure or {}),
        "color_palette": dict(entry.color_palette or {}),
        "design_philosophy": entry.design_philosophy or "",
        "implementation_constraints": list(entry.implementation_constraints or []),
        "recommended_agents": list(entry.recommended_agents or []),
        "optional_agents": list(entry.optional_agents or []),
        "excluded_agents": list(entry.excluded_agents or []),
        "recommended_skills": list(entry.recommended_skills or []),
        "agent_strategy": entry.agent_strategy or "",
        "task_distribution_guide": entry.task_distribution_guide or "",
    }


def _build_proto_from_catalog(
    session_id: Any,
    idx: int,
    catalog_entry: dict[str, Any] | None,
    role_config: dict[str, Any],
    user_tech_stack: list[str],
) -> "Prototype":
    """카탈로그 엔트리를 베이스로 Prototype 모델 인스턴스를 생성한다."""
    if catalog_entry is None:
        return Prototype(
            session_id=session_id,
            variant_index=idx,
            title=f"프로토타입 {idx + 1}",
            status="ready",
        )

    stub_ui = dict(catalog_entry.get("ui_structure") or {})
    stub_ui["is_recommended"] = role_config.get("is_recommended", idx == 0)
    stub_ui["tech_stack_tags"] = (
        user_tech_stack
        if idx == 0 and user_tech_stack
        else catalog_entry.get("tech_stack_tags", [])
    )
    stub_ui["architecture_pattern"] = catalog_entry.get(
        "architecture_pattern"
    ) or catalog_entry.get("design_pattern", "")
    stub_ui["variant_rationale"] = catalog_entry.get("description", "")
    stub_ui["pros"] = catalog_entry.get("pros", [])
    stub_ui["cons"] = catalog_entry.get("cons", [])

    return Prototype(
        session_id=session_id,
        variant_index=idx,
        title=catalog_entry["title"],
        description=catalog_entry.get("description"),
        design_pattern=catalog_entry.get("design_pattern"),
        menu_structure=catalog_entry.get("menu_structure"),
        ui_structure=stub_ui,
        color_palette=catalog_entry.get("color_palette"),
        status="ready",
    )
