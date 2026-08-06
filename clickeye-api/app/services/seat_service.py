"""구독 시트 서비스 (다프로젝트화 P4).

시트 = 팀원이 등록한 본인 구독 계정의 OAuth 토큰(`claude setup-token`). 사용자당 1개
(UniqueConstraint(user_id, credential_type)) — ToS 방어 패턴이다. 저장은 Fernet 암호화
(기존 anthropic_credentials 경로와 동일한 app.core.crypto 재사용)이며, 복호화 평문이
서비스 밖으로 나가는 경로는 머신 수령(resolve_token_for_project) 하나뿐이다.

프로젝트 ↔ 시트 배정은 v1 에서 Project.settings JSON 의 seat_user_id 키로 표현한다
(컬럼 승격은 P5). 배정이 없으면 프로젝트 소유자의 시트로 폴백한다.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt, encrypt
from app.core.exceptions import AppError
from app.models.project import Project
from app.models.user import User
from app.models.user_anthropic_credentials import UserAnthropicCredentials

logger = logging.getLogger(__name__)

# 시트는 credential_type='oauth_token' 행이다(api_key 행과 공존).
SEAT_CREDENTIAL_TYPE = "oauth_token"
SEAT_STATUS_ACTIVE = "active"
# Project.settings 안의 배정 키(v1 — 컬럼 승격은 P5).
SEAT_SETTINGS_KEY = "seat_user_id"


class SeatService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── 시트 등록/조회/해제 ────────────────────────────────────────────────
    async def get_seat(self, user_id: UUID) -> UserAnthropicCredentials | None:
        result = await self.db.execute(
            select(UserAnthropicCredentials).where(
                UserAnthropicCredentials.user_id == user_id,
                UserAnthropicCredentials.credential_type == SEAT_CREDENTIAL_TYPE,
            )
        )
        return result.scalar_one_or_none()

    async def register(self, user_id: UUID, oauth_token: str) -> UserAnthropicCredentials:
        """본인 시트를 등록하거나 교체한다(upsert). 교체 시 상태를 active 로 되돌린다."""
        now = datetime.now(UTC)
        encrypted = encrypt(oauth_token)

        seat = await self.get_seat(user_id)
        if seat is None:
            seat = UserAnthropicCredentials(
                user_id=user_id,
                credential_type=SEAT_CREDENTIAL_TYPE,
                encrypted_api_key=encrypted,
                seat_status=SEAT_STATUS_ACTIVE,
            )
            self.db.add(seat)
        else:
            seat.encrypted_api_key = encrypted  # type: ignore[assignment]
            # 소진/차단 상태로 남아있던 시트를 새 토큰으로 교체하면 다시 쓸 수 있어야 한다.
            seat.seat_status = SEAT_STATUS_ACTIVE  # type: ignore[assignment]
            seat.updated_at = now  # type: ignore[assignment]

        await self.db.commit()
        await self.db.refresh(seat)
        logger.info("seat_registered", extra={"seat_id": str(seat.id), "user_id": str(user_id)})
        return seat

    async def get_seat_or_404(self, user_id: UUID) -> UserAnthropicCredentials:
        seat = await self.get_seat(user_id)
        if seat is None:
            raise AppError("SEAT_NOT_FOUND", "등록된 구독 시트가 없습니다", 404)
        return seat

    async def delete(self, user_id: UUID) -> None:
        seat = await self.get_seat_or_404(user_id)
        seat_id = str(seat.id)
        await self.db.delete(seat)
        await self.db.commit()
        logger.info("seat_deleted", extra={"seat_id": seat_id, "user_id": str(user_id)})

    # ── 러너 프로비저닝(전체 시트 동기화) ───────────────────────────────────
    async def list_all_for_provision(
        self,
    ) -> list[tuple[UserAnthropicCredentials, str, str | None]]:
        """전체 oauth_token 시트를 (seat, email, plain_token) 튜플 목록으로 반환한다(러너 프로비저닝
        전용).

        복호화 평문은 이 메서드가 반환하는 목적(SeatProvisionResponse)으로만 흘러가야 한다 —
        로그/예외 메시지에 노출 금지. **active 시트만 복호화한다** — 비-active 시트는 로컬
        disabled 처리에 seat_id/status 만 필요하고 seat_sync 가 토큰을 쓰지 않으므로,
        평문 노출 표면을 불필요하게 넓히지 않는다(사후 리뷰 발견물 반영).
        """
        result = await self.db.execute(
            select(UserAnthropicCredentials, User.email)
            .join(User, User.id == UserAnthropicCredentials.user_id)
            .where(UserAnthropicCredentials.credential_type == SEAT_CREDENTIAL_TYPE)
        )
        rows = result.all()
        items = [
            (
                seat,
                email,
                decrypt(str(seat.encrypted_api_key)) if seat.seat_status == "active" else None,
            )
            for seat, email in rows
        ]
        logger.info("seat_provision_pulled", extra={"count": len(items)})
        return items

    # ── 프로젝트 배정 ──────────────────────────────────────────────────────
    async def assign_to_project(self, project: Project, seat_user_id: UUID | None) -> UUID | None:
        """프로젝트에 시트를 배정하거나(seat_user_id) 해제한다(None).

        배정 대상이 시트를 갖고 있지 않으면 404 — 죽은 배정을 남기지 않는다.
        반환값은 배정 후의 seat_user_id(해제 시 None).
        """
        settings_map: dict[str, Any] = dict(project.settings or {})

        if seat_user_id is None:
            settings_map.pop(SEAT_SETTINGS_KEY, None)
        else:
            if await self.get_seat(seat_user_id) is None:
                raise AppError(
                    "SEAT_NOT_FOUND",
                    "배정 대상 사용자에게 등록된 구독 시트가 없습니다",
                    404,
                )
            settings_map[SEAT_SETTINGS_KEY] = str(seat_user_id)

        project.settings = settings_map  # type: ignore[assignment]
        project.updated_at = datetime.now(UTC)  # type: ignore[assignment]
        await self.db.commit()
        await self.db.refresh(project)
        logger.info(
            "seat_assigned",
            extra={
                "project_id": str(project.id),
                "seat_user_id": str(seat_user_id) if seat_user_id else None,
            },
        )
        return seat_user_id

    # ── 머신 수령 ──────────────────────────────────────────────────────────
    async def resolve_token_for_project(
        self, project: Project
    ) -> tuple[UserAnthropicCredentials, str]:
        """프로젝트 실행에 쓸 시트와 복호화 평문 토큰을 반환한다.

        우선순위: 배정 시트(settings.seat_user_id) → 프로젝트 소유자 시트.
        어느 쪽도 없으면 404, 찾은 시트가 active 가 아니면 409(폴백하지 않는다 —
        차단/소진 시트를 조용히 우회하면 감사가 무의미해진다).
        """
        assigned_user_id = self._assigned_seat_user_id(project)

        source = "assigned"
        seat = await self.get_seat(assigned_user_id) if assigned_user_id else None
        if seat is None:
            source = "owner"
            seat = await self.get_seat(project.owner_id)  # type: ignore[arg-type]
        if seat is None:
            raise AppError(
                "SEAT_NOT_FOUND",
                "프로젝트에 사용할 구독 시트가 없습니다(배정/소유자 모두 미등록)",
                404,
            )

        if str(seat.seat_status) != SEAT_STATUS_ACTIVE:
            raise AppError(
                "SEAT_NOT_AVAILABLE",
                f"구독 시트를 사용할 수 없습니다(상태: {seat.seat_status})",
                409,
            )

        # 수령은 감사 대상 — 키 이름/식별자만 남기고 토큰 본문은 절대 로그하지 않는다.
        # (프로젝트 축이므로 인테이크 전용 DeliveryEvent 는 쓰지 않는다. v1 = 로그.)
        logger.info(
            "seat_token_issued",
            extra={
                "project_id": str(project.id),
                "seat_id": str(seat.id),
                "seat_user_id": str(seat.user_id),
                "seat_source": source,
            },
        )
        return seat, decrypt(str(seat.encrypted_api_key))

    @staticmethod
    def _assigned_seat_user_id(project: Project) -> UUID | None:
        """settings.seat_user_id 를 UUID 로 해석한다. 값이 불량이면 무시(소유자 폴백)."""
        settings_map: dict[str, Any] = dict(project.settings or {})
        raw = settings_map.get(SEAT_SETTINGS_KEY)
        if not raw:
            return None
        try:
            return UUID(str(raw))
        except ValueError:
            logger.warning(
                "seat_assignment_malformed",
                extra={"project_id": str(project.id)},
            )
            return None
