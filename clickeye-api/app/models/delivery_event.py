"""딜리버리 이벤트 — 무인 체인의 전이 이력 1급 기록 (다프로젝트화 P9, D-8·D-9).

인테이크의 상태 컬럼(status/refine_status/tickets_status)은 **현재 스냅샷**만 담는다.
이 테이블은 **전이 이력**(누가·언제·왜)을 담는다 — 사후 감사, 정지 원인 추적, 대시보드
타임라인의 원천이다. `PhaseEvent`(orchestrator) 관례를 미러한다.

기록 원칙:
- **실패 전이도 기록한다**(D-9) — verification_failed·callback_failed 가 없으면
  "그 시점에 무슨 일이 있었나"를 사후에 재구성할 수 없다.
- 기록은 순수 계측이다 — 이벤트 기록 실패가 전이(주 경로)를 절대 깨뜨리지 않는다
  (기록 훅 쪽 원칙, llm_usage_ledger 와 동일).
- append-only — 이벤트는 수정·삭제하지 않는다.

event_type 값 도메인(v1):
  received            수신(202)
  refined             정제 완료(로컬 배치 제출)
  refine_skipped      정제 skip(빈 출력)
  accepted            사람 수락(Project 생성)
  machine_accepted    기계 수락(D-12 — Project 생성)
  rejected            반려
  tickets_issued      티켓 전량 발급 확정(원장 기록)
  verification_passed 정합성 게이트 통과(verified 확정)
  verification_failed 정합성 게이트 실패(gate_failed)
  callback_sent       콜백 발송 성공
  callback_failed     콜백 최종 실패(재시도 소진)
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String, Text, Uuid

from app.database import Base


class DeliveryEvent(Base):
    __tablename__ = "delivery_events"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    intake_id = Column(
        Uuid,
        ForeignKey("intake_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # 수락 이후의 이벤트는 프로젝트에도 귀속된다(대시보드의 프로젝트 축 조회용).
    project_id = Column(
        Uuid, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type = Column(String(30), nullable=False, index=True)
    # machine(배치/서비스 #2) | human(검토 콘솔) | system(서버 내부 전이)
    actor_type = Column(String(20), nullable=False, default="system")
    actor_id = Column(Uuid, nullable=True)
    # 사람이 읽는 한 줄 경위 — 대시보드 타임라인의 본문.
    detail = Column(Text, nullable=True)
    # 구조화 부가정보(티켓 수·게이트 결과 요약 등) — 스키마 강제 없음(관측 전용).
    meta = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), index=True)
