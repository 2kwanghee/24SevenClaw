"""인테이크 수주 API — Chunk A1.

- 접수: POST /intake (X-ClickEye-Service-Key 머신 헤더 인증, 202 pending_review)
- 검토: GET /intake, POST /intake/{id}/accept·reject (JWT admin+)
- 키 관리: /intake/service-keys (superadmin, 평문 1회 반환·해시 저장)

전 라우트에 FEATURE_INTAKE 킬스위치(기본 off → 404, 존재 은닉) 적용 — 회귀 0.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.governance import verify_governance_token
from app.config import settings
from app.database import get_db
from app.dependencies import require_permission, require_superadmin
from app.models.intake import IntakeRequest
from app.models.user import User
from app.schemas.intake import (
    IntakeAcceptedResponse,
    IntakeCreate,
    IntakeIssuePendingItem,
    IntakeRefinePendingItem,
    IntakeRejectRequest,
    IntakeResponse,
    RefineSubmit,
    ServiceKeyCreate,
    ServiceKeyCreatedResponse,
    ServiceKeyResponse,
    TicketsRecordRequest,
)
from app.services.intake_service import IntakeService


def require_intake_feature() -> None:
    """인테이크 수주 feature flag 가드 (require_ops_feature 패턴).

    `feature_intake = False`(기본) 이면 전 intake endpoint 404 (킬스위치).
    인증보다 먼저 평가되어 존재 자체를 은닉한다.
    """
    if not settings.feature_intake:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found")


router = APIRouter(
    prefix="/intake",
    tags=["intake"],
    dependencies=[Depends(require_intake_feature)],
)


# ---------------------------------------------------------------------------
# 접수 (머신 헤더 인증)
# ---------------------------------------------------------------------------


@router.post("", response_model=IntakeAcceptedResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_intake(
    data: IntakeCreate,
    x_clickeye_service_key: str | None = Header(default=None),
    idempotency_key: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> IntakeAcceptedResponse:
    """요구사항 정의서(structured/document/url)를 접수한다.

    Idempotency-Key 재수신 시 기존 레코드를 그대로 반환한다(202 동일).
    """
    service = IntakeService(db)
    key = await service.authenticate_key(x_clickeye_service_key)
    intake = await service.create_intake(key, data, idempotency_key)
    return IntakeAcceptedResponse(intake_id=intake.id, status=str(intake.status))


# ---------------------------------------------------------------------------
# 검토 (JWT admin+)
# ---------------------------------------------------------------------------


@router.get("", response_model=list[IntakeResponse])
async def list_intakes(
    status_filter: str | None = None,
    user: User = Depends(require_permission("control_tower:read")),
    db: AsyncSession = Depends(get_db),
):
    """검토 목록 — superadmin 전체 / admin 자기 조직 키 접수분만. ?status_filter= 필터."""
    return await IntakeService(db).list_intakes(user, status_filter)


@router.post("/{intake_id}/accept", response_model=IntakeResponse)
async def accept_intake(
    intake_id: UUID,
    user: User = Depends(require_permission("control_tower:write")),
    db: AsyncSession = Depends(get_db),
):
    """승인 — Project(딜리버리) 생성 + accepted 전이 + KB 인제스트 훅."""
    return await IntakeService(db).accept(intake_id, user)


@router.post("/{intake_id}/reject", response_model=IntakeResponse)
async def reject_intake(
    intake_id: UUID,
    body: IntakeRejectRequest | None = None,
    user: User = Depends(require_permission("control_tower:write")),
    db: AsyncSession = Depends(get_db),
):
    """반려 — rejected 전이, 사유는 payload 에 기록."""
    reason = body.reason if body is not None else None
    return await IntakeService(db).reject(intake_id, user, reason)


# ---------------------------------------------------------------------------
# 정제 배치 (머신 — X-Governance-Token, /llm/ingest/pipeline 패턴)
# ---------------------------------------------------------------------------
#
# A3-full: 정제 LLM 실행은 로컬 배치(scripts/intake_refine.sh, claude -p)만 한다.
# 서버는 대기 목록 제공/결과 저장(상태 조율)만 담당한다 — 실행 플레인 분리.


@router.get(
    "/refine/pending",
    response_model=list[IntakeRefinePendingItem],
    dependencies=[Depends(verify_governance_token)],
)
async def list_refine_pending(
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """정제 대기 목록 — status=pending_review & refine_status=pending 만 반환한다."""
    return await IntakeService(db).list_refine_pending(limit)


@router.post("/{intake_id}/refined", response_model=IntakeResponse)
async def submit_refined(
    intake_id: UUID,
    body: RefineSubmit,
    _token: None = Depends(verify_governance_token),
    db: AsyncSession = Depends(get_db),
):
    """정제 결과 제출 — refined + 저장. 공백만이면 skipped. pending_review 아니면 409."""
    return await IntakeService(db).submit_refined(intake_id, body.refined_text)


# ---------------------------------------------------------------------------
# 티켓 전량 자동 발급 (머신 — X-Governance-Token, 정제 배치와 동일 패턴 · P6, D-12)
# ---------------------------------------------------------------------------
#
# 분해 LLM 실행은 로컬 배치(scripts/intake_issue.sh, claude -p 구독 세션)만 한다.
# 서버는 대기 목록 제공/기계 수락/발급 원장 기록(상태 조율)만 담당한다.


@router.get(
    "/issue/pending",
    response_model=list[IntakeIssuePendingItem],
    dependencies=[Depends(verify_governance_token)],
)
async def list_issue_pending(
    limit: int = Query(default=10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> list[IntakeRequest]:
    """발급 대기 목록 — 정제 완료(refined) & 미발급(tickets_status=none), FIFO.

    accepted 는 항상 포함되고, pending_review 는 기계 수락 opt-in
    (FLOWOPS_INTAKE_AUTO_ACCEPT)일 때만 포함된다 — 배치는 응답의 status 로
    auto-accept 선행 여부를 분기한다. 필터는 서버가 강제한다(fail-closed).
    """
    return await IntakeService(db).list_issue_pending(limit)


@router.post("/{intake_id}/auto-accept", response_model=IntakeResponse)
async def auto_accept_intake(
    intake_id: UUID,
    _token: None = Depends(verify_governance_token),
    db: AsyncSession = Depends(get_db),
) -> IntakeRequest:
    """기계 수락 — 사람 확인 없이 accepted 전이 + Project 생성 (D-12).

    안전장치는 서비스가 강제한다: opt-in 토글 off → 403, 정제 미완료 → 409,
    기계 소유자(활성 superadmin) 부재 → 409. 콜백(at-least-once)은 사람 수락과 동일.
    """
    return await IntakeService(db).machine_accept(intake_id)


@router.post("/{intake_id}/tickets", response_model=IntakeResponse)
async def record_issued_tickets(
    intake_id: UUID,
    body: TicketsRecordRequest,
    _token: None = Depends(verify_governance_token),
    db: AsyncSession = Depends(get_db),
) -> IntakeRequest:
    """발급 원장 확정 — 배치가 Linear 발급을 **전량 성공**한 뒤에만 호출한다.

    멱등: 이미 issued 면 no-op 으로 기존 기록을 반환(재실행·재시도 안전).
    부분 발급 기록은 계약상 불가(min 1 + 배치의 all-or-nothing 규약).
    발급 완료는 콜백으로 서비스 #2 에 푸시된다(tickets_status/tickets 포함).
    """
    return await IntakeService(db).record_issued_tickets(
        intake_id, [t.model_dump() for t in body.tickets]
    )


# ---------------------------------------------------------------------------
# 서비스 키 관리 (superadmin)
# ---------------------------------------------------------------------------


@router.post(
    "/service-keys",
    response_model=ServiceKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_service_key(
    data: ServiceKeyCreate,
    _user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
) -> ServiceKeyCreatedResponse:
    """서비스 키 발급 — 평문 키는 이 응답에서 1회만 노출된다(DB 는 sha256 해시만)."""
    raw, key = await IntakeService(db).create_service_key(data.name, data.organization_id)
    return ServiceKeyCreatedResponse(
        id=key.id,
        name=str(key.name),
        organization_id=key.organization_id,
        is_active=bool(key.is_active),
        created_at=key.created_at,
        key=raw,
    )


@router.get("/service-keys", response_model=list[ServiceKeyResponse])
async def list_service_keys(
    _user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """서비스 키 목록 — 해시/평문 미노출(응답 스키마 강제)."""
    return await IntakeService(db).list_service_keys()


@router.delete("/service-keys/{key_id}", response_model=ServiceKeyResponse)
async def deactivate_service_key(
    key_id: UUID,
    _user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db),
):
    """서비스 키 비활성화 — 이후 해당 키 인증은 401 (레코드는 감사용으로 보존)."""
    return await IntakeService(db).deactivate_service_key(key_id)
