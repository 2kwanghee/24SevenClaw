"""시트 잔량 스냅샷 서비스 (CE-387).

cswap `--list --json` 배치를 계정별 window 행(five_hour 1 + seven_day 1 +
scoped N)으로 전개해 원장에 적재하고, 계정+window+scope_name 조합별 최신
스냅샷을 조회한다.

개별 계정 파싱 실패(이형 데이터)는 해당 계정만 skip 하고 나머지는 정상 처리한다
(배치 전체를 막지 않는다 — 도메인 제약, .ralph/refined/CE-387.md).
"""

from __future__ import annotations

import contextlib
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.llm_usage_ledger import LlmUsageLedger
from app.models.seat_quota_snapshot import SeatQuotaSnapshot, SeatQuotaWindow
from app.models.user import User
from app.models.user_anthropic_credentials import UserAnthropicCredentials
from app.schemas.observability import SeatObservabilityEntry, SeatObservabilityResponse
from app.schemas.seat_quota import (
    SeatQuotaLatestEntry,
    SeatQuotaSnapshotBatchRequest,
    SeatQuotaSnapshotIn,
)
from app.services.base import BaseService
from app.services.seat_service import SEAT_CREDENTIAL_TYPE

# 시트(구독 계정) 매칭 대상 credential_type — seat_service.SEAT_CREDENTIAL_TYPE 과 동일.
_SEAT_CREDENTIAL_TYPE = SEAT_CREDENTIAL_TYPE


def account_to_rows(account: SeatQuotaSnapshotIn) -> list[dict[str, Any]]:
    """계정 1개(cswap 원문) → window 행 dict 리스트(five_hour 1 + seven_day 1 + scoped N).

    DB 세션과 분리된 순수 함수 — 단위 테스트 용이성을 위해 여기서 seat_id/
    captured_at 은 채우지 않는다(호출자가 채운다).
    """
    captured_common = {
        "usage_fetched_at": account.usage_fetched_at,
        "account_email": account.email,
        "organization_uuid": account.organization_uuid,
        "raw": account.model_dump(by_alias=True, mode="json"),
    }

    rows: list[dict[str, Any]] = []

    five_hour = account.usage.five_hour
    rows.append(
        {
            **captured_common,
            "window": SeatQuotaWindow.five_hour,
            "scope_name": None,
            "pct": five_hour.pct,
            "resets_at": five_hour.resets_at,
            "expected_pct": None,
            "ahead_of_pace": None,
            "projected_exhaustion_at": None,
            "will_last_to_reset": None,
        }
    )

    seven_day = account.usage.seven_day
    rows.append(
        {
            **captured_common,
            "window": SeatQuotaWindow.seven_day,
            "scope_name": None,
            "pct": seven_day.pct,
            "resets_at": seven_day.resets_at,
            "expected_pct": seven_day.expected_pct,
            "ahead_of_pace": seven_day.ahead_of_pace,
            "projected_exhaustion_at": seven_day.projected_exhaustion_at,
            "will_last_to_reset": seven_day.will_last_to_reset,
        }
    )

    for scope in account.usage.scoped:
        rows.append(
            {
                **captured_common,
                "window": SeatQuotaWindow.scoped,
                "scope_name": scope.name,
                "pct": scope.pct,
                "resets_at": scope.resets_at,
                "expected_pct": scope.expected_pct,
                "ahead_of_pace": scope.ahead_of_pace,
                "projected_exhaustion_at": scope.projected_exhaustion_at,
                "will_last_to_reset": scope.will_last_to_reset,
            }
        )

    return rows


class SeatQuotaService(BaseService):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    async def _resolve_seat_id(self, email: str) -> Any | None:
        """account_email → users.email 매칭 → 해당 유저의 구독 시트(oauth_token) id.

        매칭 실패(유저 없음/시트 미등록) 시 None — 행을 버리지 않고 seat_id=NULL 로
        적재한다(축 손실 허용, 데이터 손실 불허 — 도메인 제약).
        """
        user_id = await self.db.scalar(select(User.id).where(User.email == email))
        if user_id is None:
            return None
        seat_id = await self.db.scalar(
            select(UserAnthropicCredentials.id).where(
                UserAnthropicCredentials.user_id == user_id,
                UserAnthropicCredentials.credential_type == _SEAT_CREDENTIAL_TYPE,
            )
        )
        return seat_id

    async def record_batch(self, req: SeatQuotaSnapshotBatchRequest) -> dict[str, Any]:
        """배치 전체를 적재한다. 계정 단위 파싱/DB 오류는 skip 하고 계속 진행한다."""
        captured_at = datetime.now(UTC)
        rows_created = 0
        accounts_processed = 0
        accounts_skipped = 0

        for account in req.accounts:
            try:
                seat_id = await self._resolve_seat_id(account.email)
                row_dicts = account_to_rows(account)
            except (SQLAlchemyError, ValueError, AttributeError, KeyError):
                with contextlib.suppress(SQLAlchemyError):
                    await self.db.rollback()
                accounts_skipped += 1
                continue

            try:
                for row in row_dicts:
                    snapshot = SeatQuotaSnapshot(
                        captured_at=captured_at,
                        seat_id=seat_id,
                        **row,
                    )
                    self.db.add(snapshot)
                await self.db.commit()
                rows_created += len(row_dicts)
                accounts_processed += 1
            except SQLAlchemyError:
                await self.db.rollback()
                accounts_skipped += 1
                continue

        return {
            "rows_created": rows_created,
            "accounts_processed": accounts_processed,
            "accounts_skipped": accounts_skipped,
        }

    async def latest(self) -> list[SeatQuotaLatestEntry]:
        """계정+window+scope_name 조합별 최신 captured_at 1건씩 조회.

        상관 서브쿼리로 조합별 최신 captured_at 을 구한 뒤 원행과 조인한다(동시
        captured_at 동률 시 id 로 결정론적 정렬).
        """
        latest_per_group = (
            select(
                SeatQuotaSnapshot.account_email,
                SeatQuotaSnapshot.window,
                SeatQuotaSnapshot.scope_name,
                func.max(SeatQuotaSnapshot.captured_at).label("max_captured_at"),
            )
            .group_by(
                SeatQuotaSnapshot.account_email,
                SeatQuotaSnapshot.window,
                SeatQuotaSnapshot.scope_name,
            )
            .subquery()
        )

        stmt = (
            select(SeatQuotaSnapshot)
            .join(
                latest_per_group,
                (SeatQuotaSnapshot.account_email == latest_per_group.c.account_email)
                & (SeatQuotaSnapshot.window == latest_per_group.c.window)
                & (
                    SeatQuotaSnapshot.scope_name.is_(None) & latest_per_group.c.scope_name.is_(None)
                    | (SeatQuotaSnapshot.scope_name == latest_per_group.c.scope_name)
                )
                & (SeatQuotaSnapshot.captured_at == latest_per_group.c.max_captured_at),
            )
            .order_by(
                SeatQuotaSnapshot.account_email,
                SeatQuotaSnapshot.window,
                SeatQuotaSnapshot.scope_name,
                SeatQuotaSnapshot.id,
            )
        )
        result = await self.db.execute(stmt)
        rows = result.scalars().all()
        return [SeatQuotaLatestEntry.model_validate(row) for row in rows]

    async def screen_view(self) -> SeatObservabilityResponse:
        """관측 화면 계약 (CE-388) — `latest()` 결과를 계정 단위로 묶어 시트 상태와
        최근 24h 소비(ledger 합)를 얹는다. `latest()` 자체의 쿼리는 건드리지 않는다.
        """
        entries = await self.latest()

        seat_ids = {e.seat_id for e in entries if e.seat_id is not None}
        seat_status_by_id = await self._seat_status_by_id(seat_ids)
        usage_24h_by_seat = await self._usage_24h_by_seat(seat_ids)

        by_account: dict[str, list[SeatQuotaLatestEntry]] = defaultdict(list)
        seat_id_by_account: dict[str, UUID | None] = {}
        for e in entries:
            by_account[e.account_email].append(e)
            seat_id_by_account[e.account_email] = e.seat_id

        items = []
        for email, windows in sorted(by_account.items()):
            seat_id = seat_id_by_account[email]
            usage_24h = usage_24h_by_seat.get(seat_id, (0, 0)) if seat_id is not None else (0, 0)
            items.append(
                SeatObservabilityEntry(
                    account_email=email,
                    seat_id=seat_id,
                    seat_status=seat_status_by_id.get(seat_id) if seat_id is not None else None,
                    windows=windows,
                    usage_24h_input_tokens=usage_24h[0],
                    usage_24h_output_tokens=usage_24h[1],
                )
            )
        return SeatObservabilityResponse(items=items)

    async def _seat_status_by_id(self, seat_ids: set[UUID]) -> dict[UUID, str]:
        if not seat_ids:
            return {}
        rows = await self.db.execute(
            select(UserAnthropicCredentials.id, UserAnthropicCredentials.seat_status).where(
                UserAnthropicCredentials.id.in_(seat_ids)
            )
        )
        return {r.id: r.seat_status for r in rows}

    async def _usage_24h_by_seat(self, seat_ids: set[UUID]) -> dict[UUID, tuple[int, int]]:
        if not seat_ids:
            return {}
        since = datetime.now(UTC) - timedelta(hours=24)
        rows = await self.db.execute(
            select(
                LlmUsageLedger.seat_id,
                func.sum(LlmUsageLedger.input_tokens).label("input_tokens"),
                func.sum(LlmUsageLedger.output_tokens).label("output_tokens"),
            )
            .where(LlmUsageLedger.seat_id.in_(seat_ids), LlmUsageLedger.created_at >= since)
            .group_by(LlmUsageLedger.seat_id)
        )
        return {r.seat_id: (int(r.input_tokens or 0), int(r.output_tokens or 0)) for r in rows}
