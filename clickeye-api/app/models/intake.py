"""인테이크 수주(외부 요구사항 접수) 모델 — Chunk A1.

외부 서비스가 API key 로 요구사항 정의서(structured/document/url)를 접수하면
IntakeRequest 로 저장하고, 검토(pending_review) → 승인 시 Project 로 승격한다.
"""

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)

from app.database import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class IntakeServiceKey(Base, UUIDPKMixin, TimestampMixin):
    """외부 서비스별 인테이크 API 키 (sha256 해시만 저장, 평문은 발급 시 1회 반환)."""

    __tablename__ = "intake_service_keys"

    name = Column(String(100), nullable=False)
    # 평문 키의 sha256 hexdigest — project.setup_token_hash 패턴과 동일.
    key_hash = Column(String(128), nullable=False, unique=True, index=True)
    # 키 소속 조직 — accept 시 생성되는 Project.organization_id 로 전파된다.
    organization_id = Column(
        Uuid, ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("true"))


class IntakeRequest(Base, UUIDPKMixin, TimestampMixin):
    """인테이크 수주 요청 — 게이트형(pending_review → accepted/rejected)."""

    __tablename__ = "intake_requests"
    # 멱등성: 동일 서비스 키가 같은 Idempotency-Key 를 재전송하면 기존 레코드를 반환.
    __table_args__ = (
        UniqueConstraint("service_key_id", "idempotency_key", name="uq_intake_idempotency"),
    )

    service_key_id = Column(
        Uuid,
        ForeignKey("intake_service_keys.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    idempotency_key = Column(String(200), nullable=True)
    # structured | document | url
    input_type = Column(String(20), nullable=False)
    title = Column(String(200), nullable=False)
    # 원본 페이로드(requirements/document/fetch_error 등) 보존.
    payload = Column(JSON, nullable=False, default=dict)
    # 정규화된 요구사항 텍스트 — accept 시 Project.requirements_text 로 전파.
    normalized_text = Column(Text, nullable=True)
    # A3-full: 로컬 metaprompt 배치(scripts/intake_refine.sh)가 정제한 구현 스펙.
    # 서버는 저장/조율만 한다(실행 플레인 분리 — LLM 호출은 로컬 배치 전용).
    refined_text = Column(Text, nullable=True)
    # pending | refined | skipped — 정제 배치 처리 상태. accept 는 refined_text 우선 사용.
    refine_status = Column(
        String(16),
        nullable=False,
        default="pending",
        server_default=text("'pending'"),
    )
    source_url = Column(String(1000), nullable=True)
    target = Column(JSON, nullable=True)
    priority = Column(String(20), nullable=True)
    # 상태 변경 푸시 대상(A1 은 저장만, 발송은 후속).
    callback_url = Column(String(1000), nullable=True)
    # CE-311 콜백 재시도 큐: none(콜백 없음) | pending(발송 대기/재시도 중) |
    # sent(발송 성공) | failed(최대 재시도 초과). accept/reject 시 pending 기록 후
    # 즉시 1회 시도, 실패 시 백오프(1m→5m→30m→2h→6h) 재시도 — at-least-once 계약.
    callback_status = Column(
        String(16),
        nullable=False,
        default="none",
        server_default=text("'none'"),
    )
    # 발송 시도 횟수(성공 포함). 최대 6회(초기 1 + 재시도 5) 초과 실패 시 failed.
    callback_attempts = Column(Integer, nullable=False, default=0, server_default=text("0"))
    # 다음 재시도 예정 시각 — 워커(60s 폴링)가 due 건만 재발송. sent/failed 면 NULL.
    callback_next_retry_at = Column(DateTime(timezone=True), nullable=True)
    # 마지막 발송 실패 사유(관측용, 2000자 절단).
    callback_last_error = Column(Text, nullable=True)
    # pending_review | accepted | rejected
    status = Column(
        String(20),
        nullable=False,
        default="pending_review",
        server_default=text("'pending_review'"),
        index=True,
    )
    # accept 시 생성된 프로젝트 연결.
    project_id = Column(
        Uuid, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True
    )
