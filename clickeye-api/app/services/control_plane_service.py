"""제어면 YAML 수신 서비스 (다프로젝트화 P2) — 서비스 #2 → DeliveryProfile 미러.

3-서비스 체인에서 서비스 #2(기획)가 프로젝트 성격에 맞춰 자동 생성한 제어면 YAML 을
수신·검증하고 `DeliveryProfile` 에 미러링한다(docs/multiproject-delivery.md §3).

계층 분담:
- YAML 텍스트 → dict 파싱: **여기(PyYAML)**. 커널은 YAML 을 모른다.
- dict → 검증: `governance.control.ControlPlane.from_dict()`(stdlib 커널, fail-closed).
- 저장: `DeliveryProfile` — P0 에서 만든 출처 인증 컬럼을 그대로 사용(마이그레이션 0).

저장 전략 — **원문이 미러의 정본이다**:
- `source_yaml` = 수신 원문 전체. 전체 제어면(retry_limits·gates·git·…)은 필요 시
  원문을 재검증(`load_control_plane`)해 얻는다 — 구조화 사본을 이중 저장하면 드리프트한다.
- `policy` = 판정면이 소비하는 hot 경로만 구조화 저장(`ControlPlane.policy_raw` —
  지정분만. 전체 Policy 를 저장하면 미지정 필드가 명시로 굳는다).
- `source_signature` = `sha256:<hex>` 콘텐츠 해시(D-14 v1 무결성 — 원문과 재대조 가능).

거부(fail-closed): YAML 파싱 실패·스키마 위반은 전부 `AppError("CONTROL_PLANE_INVALID",
..., 422)` — 라우터가 이를 서비스 #2 콜백에 실을 수 있는 거부 사유로 반환한다.
조용히 기본값으로 떨어지지 않는다.
"""

from __future__ import annotations

from uuid import UUID

import yaml
from governance.control import ControlPlane, ControlPlaneError, content_signature
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.models.delivery_profile import DeliveryProfile
from app.models.project import Project


def parse_control_yaml(control_yaml: str) -> ControlPlane:
    """YAML 원문 → 검증된 ControlPlane. 파싱·스키마 오류는 AppError(422)로 승격.

    yaml.safe_load 만 사용한다 — 임의 객체 역직렬화(full_load)는 기계 수신 경로에서 금지.
    """
    if not control_yaml or not control_yaml.strip():
        raise AppError("CONTROL_PLANE_INVALID", "control_yaml: 비어 있음", 422)
    try:
        data = yaml.safe_load(control_yaml)
    except yaml.YAMLError as e:
        raise AppError("CONTROL_PLANE_INVALID", f"YAML 파싱 실패: {e}", 422) from e
    try:
        return ControlPlane.from_dict(data)
    except ControlPlaneError as e:
        raise AppError("CONTROL_PLANE_INVALID", str(e), 422) from e


class ControlPlaneService:
    """제어면 수신·미러 비즈니스 로직."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def submit(
        self,
        *,
        project_id: UUID,
        control_yaml: str,
        updated_by: UUID | None = None,
    ) -> tuple[DeliveryProfile, ControlPlane]:
        """검증 후 DeliveryProfile 미러를 upsert 한다(프로젝트당 1행).

        `updated_by` 는 사람 경유 제출일 때만. 기계(서비스 #2) 수신이면 None —
        그 경우 출처는 source_signature 가 말한다(모델 도크스트링 참조).
        """
        # 검증이 저장보다 먼저다 — 불량 YAML 은 프로젝트 존재 여부와 무관하게 422.
        plane = parse_control_yaml(control_yaml)

        project = (
            await self.db.execute(select(Project).where(Project.id == project_id))
        ).scalar_one_or_none()
        if project is None:
            raise AppError("PROJECT_NOT_FOUND", "프로젝트를 찾을 수 없습니다.", 404)

        profile = (
            await self.db.execute(
                select(DeliveryProfile).where(DeliveryProfile.project_id == project_id)
            )
        ).scalar_one_or_none()
        if profile is None:
            profile = DeliveryProfile(project_id=project_id)
            self.db.add(profile)

        # 모델이 레거시 Column 선언(Mapped 미사용)이라 인스턴스 대입에 ignore 가 필요하다
        # — 런타임 동작은 정상이며 intake_service 등 기존 서비스와 동일한 패턴이다.
        profile.tier = plane.tier  # type: ignore[assignment]
        profile.policy = dict(plane.policy_raw)  # type: ignore[assignment]  # 지정분만 — 미러 오염 방지
        profile.schema_version = plane.schema_version  # type: ignore[assignment]
        profile.source_signature = content_signature(  # type: ignore[assignment]
            control_yaml.encode("utf-8")
        )
        profile.source_yaml = control_yaml  # type: ignore[assignment]
        profile.provenance = dict(plane.provenance) or None  # type: ignore[assignment]
        profile.updated_by = updated_by  # type: ignore[assignment]

        await self.db.commit()
        await self.db.refresh(profile)
        return profile, plane

    async def load_control_plane(self, project_id: UUID) -> ControlPlane | None:
        """저장된 원문(source_yaml)을 재검증해 전체 제어면을 복원한다.

        원문이 정본이므로 구조화 사본을 따로 저장하지 않는다. 재검증 실패는 저장 이후
        계약 버전이 강화됐다는 뜻 — 조용히 기본값으로 떨어지지 않고 422 로 드러낸다.
        """
        profile = (
            await self.db.execute(
                select(DeliveryProfile).where(DeliveryProfile.project_id == project_id)
            )
        ).scalar_one_or_none()
        if profile is None or not profile.source_yaml:
            return None
        return parse_control_yaml(str(profile.source_yaml))
