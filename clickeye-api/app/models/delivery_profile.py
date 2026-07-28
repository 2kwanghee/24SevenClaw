"""딜리버리 프로파일 — 서비스 #2 가 생성한 제어면 YAML 의 **런타임 미러**(다프로젝트화 P0).

⚠️ 이 테이블은 정본(SSOT)이 아니다. 정본은 **서비스 #2(기획)가 프로젝트 성격에 맞춰
자동 생성·선택한 YAML** 이며(docs/multiproject-delivery.md §3, D-3 철회·D-14), 이 테이블은
그 YAML 을 수신·검증한 뒤 커널이 빠르게 읽도록 미러링한 캐시다. 따라서:

- 신뢰 근거는 소유권("사용자만 편집")이 아니라 **출처 인증** — `source_signature` 가
  서비스 #2 의 서비스 키 서명을, `schema_version` 이 계약 버전을 담는다.
- `source_yaml` 은 수신 원문 그대로다. 서명·해시 재검증은 파싱 결과(`policy`)가 아니라
  이 원문에 대해 수행한다.
- `provenance` 는 서비스 #2 가 "어느 템플릿에서 어떤 근거로 이 정책을 선택했는가"를
  남기는 자리다(기계 저작물의 주석은 사람용 설명이 아니라 출처 기록이다).

거버넌스 커널(`governance.core.evaluate`)은 `policy=` 로 정책을 주입받고, 주입되면
**서버 프로세스의 env 를 조회하지 않는다**(static). 즉 한 프로젝트의 토글이 다른 프로젝트
판정에 새어 들어가지 않는다. 프로파일이 없는 프로젝트는 기본 정책(env 재독, live)으로
폴백한다 — 오늘의 동작과 동일(회귀 0).

P0 범위: 보관·주입까지. YAML 수신·서명 검증·거부 콜백 배선은 P2(YAML 제어면 계약)에서.
"""

from sqlalchemy import JSON, Boolean, Column, ForeignKey, String, Text, Uuid, text

from app.database import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class DeliveryProfile(Base, UUIDPKMixin, TimestampMixin):
    """프로젝트별 딜리버리 티어 + 거버넌스 정책 미러(제어면 YAML 수신본)."""

    __tablename__ = "delivery_profiles"

    # 프로젝트당 1개 — 커널이 읽는 미러는 하나여야 하므로 unique 로 강제한다.
    project_id = Column(
        Uuid,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    # 딜리버리 티어: lite | standard | enterprise
    # (P0 은 값만 보관한다 — 티어별 기본 정책 파생은 P2 에서 다룬다.)
    tier = Column(String(20), nullable=False, default="lite", server_default=text("'lite'"))
    # governance.policy.Policy.from_dict() 입력 형태의 정책 JSON — YAML 파싱 결과.
    # 빈 객체({})면 기본 정책 값을 승계하되 static(env 미조회)으로 동작한다.
    policy = Column(JSON, nullable=False, default=dict)

    # ── 출처 인증(D-14) — 정본 YAML 의 수신 증거. P2 에서 검증 로직이 붙는다. ──
    # 제어면 YAML 스키마 계약 버전. 미수신(수동 생성) 프로파일은 NULL.
    schema_version = Column(String(20), nullable=True)
    # 서비스 #2 의 서비스 키 서명. NULL 이면 서명 미검증 프로파일 —
    # P2 이후 무인 경로에서는 서명 없는 프로파일을 신뢰하지 않는다(fail-closed).
    source_signature = Column(Text, nullable=True)
    # 수신한 YAML 원문. 서명·해시 재검증은 파싱 결과가 아니라 이 원문에 대해 한다.
    source_yaml = Column(Text, nullable=True)
    # 서비스 #2 의 선택 근거(템플릿 ID·선택 사유 등) — 기계 저작물의 출처 기록.
    provenance = Column(JSON, nullable=True)

    # ClickEye 내부 에이전트 쓰기 금지 표시(집행면 G-04 상당의 예고).
    # ⚠️ P0 에서는 **플래그만 둔다.** 이 값으로 쓰기를 차단하는 집행 로직은 아직 없다.
    locked = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    # 마지막 변경 주체(감사 보조). 기계 수신(인테이크)이면 NULL — 그 경우 출처는
    # source_signature 가 말한다. 사용자 삭제 시 이력만 끊고 행은 보존.
    updated_by = Column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
