"""시트 잔량 스냅샷 인제스트/조회 라우터 (CE-387).

러너 서버(`cswap --list --json`)發 배치 수신과, 관측 화면/향후 계정 효율 셀렉터가
참조할 최신 조회를 제공한다. 대화형 유저가 아니므로 `verify_governance_token`
(X-Governance-Token 헤더, `governance.py` 정의)만 검증하고 RBAC 는 요구하지 않는다
(운영 스냅샷 데이터로 판단, PII 아님).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.governance import verify_governance_token
from app.database import get_db
from app.schemas.seat_quota import (
    SeatQuotaLatestResponse,
    SeatQuotaSnapshotBatchRequest,
    SeatQuotaSnapshotResponse,
)
from app.services.seat_quota_service import SeatQuotaService

router = APIRouter(prefix="/ops/seat-quota", tags=["ops-seat-quota"])


@router.post(
    "/snapshots",
    response_model=SeatQuotaSnapshotResponse,
    dependencies=[Depends(verify_governance_token)],
)
async def create_snapshots(
    body: SeatQuotaSnapshotBatchRequest,
    db: AsyncSession = Depends(get_db),
) -> SeatQuotaSnapshotResponse:
    """cswap 배치 수신 — 계정 1개당 window 행(five_hour 1 + seven_day 1 + scoped N).

    개별 계정 파싱/DB 오류는 해당 계정만 skip 하고 나머지는 정상 처리한다.
    """
    result = await SeatQuotaService(db).record_batch(body)
    return SeatQuotaSnapshotResponse(**result)


@router.get(
    "/latest",
    response_model=SeatQuotaLatestResponse,
    dependencies=[Depends(verify_governance_token)],
)
async def get_latest(
    db: AsyncSession = Depends(get_db),
) -> SeatQuotaLatestResponse:
    """계정+window+scope_name 조합별 최신 스냅샷 1건씩 조회."""
    items = await SeatQuotaService(db).latest()
    return SeatQuotaLatestResponse(items=items)
