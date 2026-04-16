"""프로토타입 세션 서비스 — 세션 생성, 프로토타입 생성/조회/선택."""

from typing import Any
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
            user_input=data.user_input,
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

    async def generate_prototypes(
        self, session_id: UUID, user_id: UUID
    ) -> list[Prototype]:
        """프로토타입을 생성한다 (ClaudeService 연동)."""
        session = await self.get_session(session_id, user_id)

        if session.status == "completed":
            raise AppError(
                "ALREADY_GENERATED",
                "이미 프로토타입이 생성된 세션입니다",
                409,
            )

        # 상태 → generating
        session.status = "generating"  # type: ignore[assignment]
        await self.db.commit()

        try:
            # 사용자 입력 분석 → 솔루션 유형 결정
            raw_input = session.user_input
            user_input: dict[str, Any] = dict(raw_input) if raw_input else {}
            solution_type = self._claude.analyze_input(user_input)

            # 프로토타입 템플릿 생성
            templates = self._claude.generate_prototypes(
                solution_type, user_input
            )

            prototypes: list[Prototype] = []
            for tmpl in templates:
                proto = Prototype(
                    session_id=session.id,
                    name=tmpl["name"],
                    solution_type=tmpl["solution_type"],
                    config=tmpl["config"],
                    reasoning=tmpl.get("reasoning"),
                )
                self.db.add(proto)
                prototypes.append(proto)

            # 상태 → completed
            session.status = "completed"  # type: ignore[assignment]
            await self.db.commit()

            for proto in prototypes:
                await self.db.refresh(proto)

            return prototypes

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
            .order_by(Prototype.created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def select_prototype(
        self, session_id: UUID, user_id: UUID, data: PrototypeSelectRequest
    ) -> Prototype:
        """프로토타입을 선택한다 (기존 선택 해제 후 새로 선택)."""
        # 소유자 검증
        await self.get_session(session_id, user_id)

        # 대상 프로토타입 존재 확인
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

        # 기존 선택 해제
        await self.db.execute(
            update(Prototype)
            .where(Prototype.session_id == session_id)
            .values(is_selected=False)
        )

        # 새로 선택
        prototype.is_selected = True  # type: ignore[assignment]
        await self.db.commit()
        await self.db.refresh(prototype)
        return prototype

    async def delete_session(
        self, session_id: UUID, user_id: UUID
    ) -> None:
        """세션을 삭제한다 (CASCADE로 프로토타입도 삭제)."""
        session = await self.get_session(session_id, user_id)
        await self.db.delete(session)
        await self.db.commit()
