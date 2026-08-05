"""시트 잔량 스냅샷 원장 모델 (CE-387).

러너 서버 `cswap --list --json`(schemaVersion 1)이 보고하는 계정별 사용량 윈도우
(5시간/7일/스코프별)를 주기 적재한다. 관측 화면과 향후 계정 효율 셀렉터가 공통으로
참조할 판단 근거이며, 이 모델 자체는 셀렉터 로직을 갖지 않는다(순수 원장).

`llm_usage_ledger.py`의 컬럼 정의 스타일(Column/Uuid/Enum/JSONB/ForeignKey SET NULL/
Index)을 그대로 재사용한다.
"""

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class SeatQuotaWindow(StrEnum):
    five_hour = "five_hour"
    seven_day = "seven_day"
    scoped = "scoped"


class SeatQuotaSnapshot(Base):
    """계정 1개 × 윈도우(five_hour/seven_day/scoped) 1개 = 1행.

    단일 계정 스냅샷을 한 행으로 합치지 않는다(정합성 불변식 — five_hour 1 +
    seven_day 1 + scoped N행 구성). `seat_id` 는 account_email 로 user_anthropic_
    credentials 를 매칭한 결과이며, 매칭 실패 시 NULL 로 적재한다(행을 버리지
    않음 — llm_usage_ledger 의 seat_id 축 손실 흡수 원칙과 동일).
    """

    __tablename__ = "seat_quota_snapshots"

    __table_args__ = (
        Index(
            "ix_seat_quota_snapshots_account_window_scope",
            "account_email",
            "window",
            "scope_name",
        ),
    )

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    # 서버 수신 시각(적재 시점) — cswap 이 보고한 usage_fetched_at 과는 별개 축.
    captured_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True)
    # cswap 이 보고한 계정 사용량 조회 시각(원문 usageFetchedAt).
    usage_fetched_at = Column(DateTime(timezone=True), nullable=True)
    account_email = Column(String(255), nullable=False, index=True)
    organization_uuid = Column(String(64), nullable=True)
    # 계정 축(D-8 패턴과 동일) — 시트 삭제 시 원장 행은 남고 축만 끊긴다(SET NULL).
    seat_id = Column(
        Uuid,
        ForeignKey("user_anthropic_credentials.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    window: Column[SeatQuotaWindow] = Column(
        Enum(SeatQuotaWindow, name="seat_quota_window"), nullable=False
    )
    # scoped 윈도우 전용 식별자(예: 모델/스코프 이름). five_hour/seven_day 는 NULL.
    scope_name = Column(String(128), nullable=True)
    pct = Column(Numeric(6, 3), nullable=False)
    resets_at = Column(DateTime(timezone=True), nullable=True)
    expected_pct = Column(Numeric(6, 3), nullable=True)
    ahead_of_pace = Column(Boolean, nullable=True)
    projected_exhaustion_at = Column(DateTime(timezone=True), nullable=True)
    will_last_to_reset = Column(Boolean, nullable=True)
    # 계정 원문 보존(디버깅/재처리용) — cswap 응답의 해당 계정 dict 그대로.
    raw = Column(JSONB, nullable=True)
