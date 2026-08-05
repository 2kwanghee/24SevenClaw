"""시트 프로비저닝 동기화 API (CE-400) — DB 구독 시트를 러너 로컬 원장으로 배선.

머신 전용(러너 프로세스가 호출) — verify_governance_token(X-Governance-Token)만 검증,
RBAC 없음(seat_quota.py와 동일 인증 패턴). 평문 토큰을 반환하는 두 번째(유일한) 경로 —
seat-token(governance.py)과 마찬가지로 로그/예외에 토큰 값 노출 금지.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.governance import verify_governance_token
from app.database import get_db
from app.schemas.seat import SeatProvisionItem, SeatProvisionResponse
from app.services.seat_service import SeatService

router = APIRouter(prefix="/ops/seats", tags=["ops-seats"])


@router.get(
    "/provision",
    response_model=SeatProvisionResponse,
    dependencies=[Depends(verify_governance_token)],
)
async def get_provision_seats(
    db: AsyncSession = Depends(get_db),
) -> SeatProvisionResponse:
    """전체 등록 시트(active/exhausted/blocked 모두 포함, seat_status로 구분) + 평문 토큰을 반환.

    scripts/seat_sync.py 가 이 응답을 받아 active는 등재, active가 아니면 이미 로컬에
    등재된 시트만 disabled로 반영한다(응답 자체는 필터링하지 않고 전체를 내려준다 —
    스크립트가 분기).
    """
    rows = await SeatService(db).list_all_for_provision()
    return SeatProvisionResponse(
        seats=[
            SeatProvisionItem(
                seat_id=seat.id,
                user_id=seat.user_id,
                email=email,
                seat_status=str(seat.seat_status),
                token=token,
            )
            for seat, email, token in rows
        ]
    )
