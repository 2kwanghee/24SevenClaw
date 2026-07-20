import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.api.v1.router import api_v1_router
from app.config import settings
from app.core.exceptions import AppError, app_exception_handler, unhandled_exception_handler
from app.core.logging import setup_logging
from app.core.middleware import RequestIDMiddleware
from app.core.rate_limit import RateLimitMiddleware
from app.redis import close_redis, init_redis
from app.ws.router import router as ws_router

_bg_logger = logging.getLogger("queue_monitor")

# Todo/Backlog 상태 — 타임아웃 대상
_STALE_STATES = {"Todo", "Backlog"}
# 5분마다 체크
_CHECK_INTERVAL = 300


async def _reset_stale_queued_issues() -> None:
    """Todo/Backlog 상태에서 일정 시간 이상 정체된 이슈를 Backlog로 되돌린다."""
    from app.core.crypto import decrypt
    from app.database import async_session
    from app.models.orchestrator import OrchestratorSession, SubTask
    from app.models.project_linear_credentials import ProjectLinearCredentials
    from app.models.user_linear_credentials import UserLinearCredentials
    from app.services.linear_service import (
        fetch_issue_states,
        get_initial_state_id,
        update_issue_state_id,
    )

    cutoff = datetime.now(UTC) - timedelta(minutes=settings.queue_stale_minutes)

    async with async_session() as db:
        result = await db.execute(
            select(SubTask).where(
                SubTask.linear_state.in_(list(_STALE_STATES)),
                SubTask.linear_issue_id.is_not(None),
                SubTask.updated_at < cutoff,
            )
        )
        stale = result.scalars().all()

    if not stale:
        return

    _bg_logger.info("정체 이슈 %d건 발견 (기준: %d분)", len(stale), settings.queue_stale_minutes)

    for subtask in stale:
        try:
            async with async_session() as db:
                # 세션 → 프로젝트 자격증명 조회
                sess_result = await db.execute(
                    select(OrchestratorSession).where(OrchestratorSession.id == subtask.session_id)
                )
                session = sess_result.scalar_one_or_none()
                if session is None:
                    continue

                proj_creds_result = await db.execute(
                    select(ProjectLinearCredentials).where(
                        ProjectLinearCredentials.project_id == session.project_id
                    )
                )
                proj_creds = proj_creds_result.scalar_one_or_none()

                if proj_creds is not None:
                    api_key = decrypt(str(proj_creds.encrypted_api_key))
                    team_id = str(proj_creds.team_id)
                else:
                    user_creds_result = await db.execute(
                        select(UserLinearCredentials).where(
                            UserLinearCredentials.user_id == session.created_by
                        )
                    )
                    user_creds = user_creds_result.scalar_one_or_none()
                    if user_creds is None:
                        _bg_logger.warning("자격증명 없음: subtask=%s", subtask.id)
                        continue
                    api_key = decrypt(str(user_creds.encrypted_api_key))
                    team_id = str(user_creds.team_id)

                # Linear 실제 상태 먼저 확인 — 이미 전진했으면 DB만 갱신하고 복귀하지 않음
                # UUID(linear_issue_id)로 조회 → {identifier: state} 맵 반환
                real_states = fetch_issue_states(api_key, team_id, [str(subtask.linear_issue_id)])
                real_state = real_states.get(str(subtask.linear_identifier))

                if real_state and real_state not in _STALE_STATES:
                    subtask_fresh = await db.get(SubTask, subtask.id)
                    if subtask_fresh:
                        subtask_fresh.linear_state = real_state  # type: ignore[assignment]  # TODO: 타입 정합
                        subtask_fresh.updated_at = datetime.now(UTC)  # type: ignore[assignment]  # TODO: 타입 정합
                        await db.commit()
                    _bg_logger.info(
                        "DB 동기화 (파이프라인 전진): %s (%s → %s)",
                        subtask.linear_identifier,
                        subtask.linear_state,
                        real_state,
                    )
                    continue

                wait_state_id = get_initial_state_id(api_key, team_id)
                if not wait_state_id:
                    continue

                ok = update_issue_state_id(api_key, str(subtask.linear_issue_id), wait_state_id)
                if ok:
                    subtask_fresh = await db.get(SubTask, subtask.id)
                    if subtask_fresh:
                        subtask_fresh.linear_state = "Backlog"  # type: ignore[assignment]  # TODO: 타입 정합
                        subtask_fresh.updated_at = datetime.now(UTC)  # type: ignore[assignment]  # TODO: 타입 정합
                        await db.commit()
                    _bg_logger.info(
                        "자동 복귀: %s (%s → Backlog)",
                        subtask.linear_identifier,
                        subtask.linear_state,
                    )
        except Exception as exc:
            _bg_logger.error("자동 복귀 오류 subtask=%s: %s", subtask.id, exc)


async def _queue_monitor_loop() -> None:
    await asyncio.sleep(60)  # 서버 기동 후 1분 대기
    while True:
        try:
            await _reset_stale_queued_issues()
        except Exception as exc:
            _bg_logger.error("queue_monitor 오류: %s", exc)
        await asyncio.sleep(_CHECK_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # 시작 시 초기화
    setup_logging()
    await init_redis()
    monitor_task = asyncio.create_task(_queue_monitor_loop())
    # 프리셋 시드 자동 로드 (최초 기동 시에만 삽입, 이미 존재하면 건너뜀)
    await _seed_presets_on_startup()
    yield
    # 종료 시 정리
    monitor_task.cancel()
    await close_redis()


async def _seed_presets_on_startup() -> None:
    from app.database import async_session
    from app.services.preset_service import PresetService

    try:
        async with async_session() as db:
            service = PresetService(db)
            count = await service.seed_presets()
            if count:
                logging.getLogger("startup").info("프리셋 시드 %d개 삽입 완료", count)
    except Exception:
        logging.getLogger("startup").exception("프리셋 시드 로드 실패 (무시하고 계속)")


def create_app() -> FastAPI:
    app = FastAPI(
        title="ClickEye API",
        description="AI 에이전트 개발 오케스트레이션 플랫폼",
        version="0.1.0",
        lifespan=lifespan,
    )

    # 미들웨어 (역순으로 실행됨 — 아래가 먼저)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )

    # 예외 핸들러
    app.add_exception_handler(AppError, app_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # 라우터
    app.include_router(api_v1_router, prefix="/api/v1")
    app.include_router(ws_router)

    return app


app = create_app()
