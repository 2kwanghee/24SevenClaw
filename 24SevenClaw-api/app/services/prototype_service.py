"""프로토타입 세션 서비스 — 세션 생성, 프로토타입 생성/조회/선택."""

from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.prototype_session import Prototype, PrototypeSession
from app.schemas.prototype import PrototypeSelectRequest, PrototypeSessionCreate
from app.services.claude_service import ClaudeService


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
