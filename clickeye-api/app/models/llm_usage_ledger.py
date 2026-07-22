"""LLM 사용량/비용 원장 모델 (CE-299).

모든 in-API AI 호출을 얇은 게이트웨이가 통과시키며, 호출 1건당 이 테이블에
토큰/비용 1행을 기록한다. 프로바이더(anthropic/openai)와 키 출처(구독시트 vs
조직키)를 구분해 회계한다. 구독시트 호출은 비용을 산정하지 않으므로 cost=NULL.
"""

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Integer,
    Numeric,
    String,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class LlmProvider(StrEnum):
    anthropic = "anthropic"
    openai = "openai"


class LlmKeySource(StrEnum):
    # 구독시트: ANTHROPIC_API_KEY 미설정/OAuth 세션 → 비용 미산정
    subscription_seat = "subscription_seat"
    # 조직키: 조직 소유 API 키 → 토큰 단가로 비용 산정
    org_api_key = "org_api_key"


class LlmUsageStatus(StrEnum):
    success = "success"
    error = "error"


class LlmUsageLedger(Base):
    __tablename__ = "llm_usage_ledger"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True)
    # 파이프라인 태스크/프로젝트 상관관계 (nullable — in-API 호출은 프로젝트 없이 발생 가능)
    project_id = Column(Uuid, nullable=True, index=True)
    task_id = Column(String(128), nullable=True)  # Runner 프로토콜 상관관계
    provider: Column[LlmProvider] = Column(Enum(LlmProvider, name="llm_provider"), nullable=False)
    key_source: Column[LlmKeySource] = Column(
        Enum(LlmKeySource, name="llm_key_source"), nullable=False
    )
    model = Column(String(64), nullable=False)
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    # 구독시트는 비용=NULL, 조직키만 단가로 산정
    cost = Column(Numeric(14, 6), nullable=True)
    request_kind = Column(String(64), nullable=False)  # 예: wizard_preview
    meta = Column(JSONB, nullable=True)
    status: Column[LlmUsageStatus] = Column(
        Enum(LlmUsageStatus, name="llm_usage_status"),
        nullable=False,
        default=LlmUsageStatus.success,
    )
