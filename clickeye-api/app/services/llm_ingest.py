"""clickeye-llm KB 자동 인제스트 헬퍼 (P1.5).

딜리버리 진행 이벤트(산출물/거버넌스/오케스트레이션/리뷰)를 clickeye-llm(profile llm,
:8100) POST /ingest 로 비동기·비차단(fire-and-forget) 전송한다.

불변식:
- 토글 FEATURE_LLM_AUTOINGEST 기본 off → enqueue_ingest 즉시 return(회귀 0).
- 어떤 예외도 호출자(이벤트 원 요청)에게 전파하지 않는다 — warning 로그만.
- delivery_id = str(project_id) (KB 네임스페이스 격리).
- 동일 source_id 재전송 시 clickeye-llm 이 선삭제 후 재삽입(증분 갱신) — 이벤트별
  source_id 는 "최신 상태 1문서" 계약으로 설계한다.
"""

import asyncio
import logging
from typing import TYPE_CHECKING, Any
from uuid import UUID

import httpx
from sqlalchemy import select

from app.config import settings

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# 인제스트 문서 텍스트 상한(문자). 초과분 절단 — 청크 품질/전송량 보호.
MAX_TEXT_LEN = 4000
# 인제스트 HTTP 타임아웃(초). fire-and-forget 이라 원 요청 지연에는 무관.
INGEST_TIMEOUT = 10.0

# fire-and-forget 태스크의 강한 참조 유지(GC 로 인한 조기 소멸 방지).
_background_tasks: set[asyncio.Task[None]] = set()


async def _post_ingest(
    delivery_id: str,
    source_id: str,
    text: str,
    metadata: dict[str, Any] | None,
) -> None:
    """실제 전송 코루틴. 실패는 warning 로그만 남기고 삼킨다."""
    try:
        async with httpx.AsyncClient(timeout=INGEST_TIMEOUT) as client:
            resp = await client.post(
                f"{settings.clickeye_llm_url.rstrip('/')}/ingest",
                json={
                    "delivery_id": delivery_id,
                    "documents": [
                        {
                            "source_id": source_id,
                            "text": text,
                            "metadata": metadata or {},
                        }
                    ],
                },
            )
            resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001 — 인제스트 실패는 원 요청에 절대 전파 금지
        logger.warning(
            "clickeye-llm 인제스트 실패(무시): delivery_id=%s source_id=%s err=%s",
            delivery_id,
            source_id,
            exc,
        )


async def resolve_project_by_team(db: "AsyncSession", team_id: str) -> UUID | None:
    """Linear team_id → project_id 역매핑 (P1.6, 파이프라인/웹훅 머신 인제스트용).

    project_linear_credentials 에서 team_id 매칭을 조회해 **정확히 1건일 때만**
    project_id 를 반환한다. 0건(미연동)·복수건(여러 프로젝트가 같은 팀 공유)이면
    None + warning — 잘못된 KB 네임스페이스 오염을 막는 결정적 규칙.
    """
    from app.models.project_linear_credentials import (  # noqa: PLC0415 — 순환 import 회피
        ProjectLinearCredentials,
    )

    rows = (
        await db.execute(
            select(ProjectLinearCredentials.project_id).where(
                ProjectLinearCredentials.team_id == team_id
            )
        )
    ).scalars().all()
    if len(rows) == 1:
        return rows[0]
    logger.warning(
        "team→project 역매핑 실패(스킵): team_id=%s 매칭 %d건 (정확히 1건일 때만 인제스트)",
        team_id,
        len(rows),
    )
    return None


def enqueue_ingest_ns(
    delivery_id: str,
    source_id: str,
    text: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    """임의 네임스페이스(delivery_id 문자열)로 KB 인제스트를 fire-and-forget 예약한다.

    프로젝트 네임스페이스(str(project_id))·조직 네임스페이스(f"org:{org_id}") 등
    격리 키를 자유롭게 지정할 수 있는 하위 계층. 어떤 경우에도 예외를 던지지 않는다.

    - 토글 off / URL 미설정 / 빈 텍스트 → 조용히 no-op.
    - 실행 중 이벤트 루프가 없으면(sync 컨텍스트) 비차단 원칙상 스킵(warning).
    """
    try:
        if not settings.feature_llm_autoingest or not settings.clickeye_llm_url:
            return
        normalized = (text or "").strip()
        if not normalized:
            return
        normalized = normalized[:MAX_TEXT_LEN]

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.warning("이벤트 루프 없음 — 인제스트 스킵: source_id=%s", source_id)
            return

        task = loop.create_task(
            _post_ingest(delivery_id, source_id, normalized, metadata)
        )
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
    except Exception as exc:  # noqa: BLE001 — 예약 실패도 호출자에게 전파 금지
        logger.warning("인제스트 예약 실패(무시): source_id=%s err=%s", source_id, exc)


def enqueue_ingest(
    project_id: UUID,
    source_id: str,
    text: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    """프로젝트(딜리버리) 네임스페이스 KB 인제스트. delivery_id = str(project_id).

    enqueue_ingest_ns 로 위임하는 편의 래퍼(기존 호출자 계약 불변).
    """
    enqueue_ingest_ns(str(project_id), source_id, text, metadata)
