"""ClickEye Agent 데몬 엔트리포인트"""

import asyncio
import signal

import structlog

from agent.config import agent_settings
from agent.connection import CloudConnection
from agent.dispatcher import Dispatcher
from agent.handlers.config_handler import ConfigHandler
from agent.handlers.docker_handler import DockerHandler
from agent.handlers.env_handler import EnvHandler
from agent.handlers.runner_handler import RunnerHandler
from agent.local_store import LocalStore
from agent.reporter import Reporter

logger = structlog.get_logger()


async def main() -> None:
    logger.info(
        "ClickEye Agent 시작",
        agent_id=agent_settings.agent_id,
        cloud_url=agent_settings.cloud_ws_url,
    )

    # 로컬 저장소 초기화
    local_store = LocalStore(db_path=agent_settings.local_db_path)
    await local_store.init()

    # 디스패처 초기화
    dispatcher = Dispatcher()

    # 클라우드 연결
    connection = CloudConnection(config=agent_settings, dispatcher=dispatcher)
    reporter = Reporter(connection=connection)

    # 핸들러 등록
    docker_handler = DockerHandler(
        config=agent_settings, reporter=reporter, local_store=local_store
    )
    env_handler = EnvHandler(
        config=agent_settings, reporter=reporter, local_store=local_store
    )
    config_handler = ConfigHandler(
        config=agent_settings, reporter=reporter, local_store=local_store
    )
    runner_handler = RunnerHandler(
        config=agent_settings, reporter=reporter, local_store=local_store
    )

    dispatcher.register("command.setup_env", env_handler)
    dispatcher.register("command.build", docker_handler)
    dispatcher.register("command.run", docker_handler)
    dispatcher.register("command.stop", docker_handler)
    dispatcher.register("command.destroy_env", docker_handler)
    # 항목 I: 위치 무관 Runner 태스크 실행(RunnerTaskPayload, CE-301).
    dispatcher.register("command.run_task", runner_handler)
    dispatcher.register("config.update", config_handler)

    # 항목 F: capabilities 는 실제 등록된 핸들러에서 도출한다(진실 공급원).
    #   "command." 접두어를 제거해 ["setup_env","build",...,"config.update"] 형태로 보고.
    capabilities = [t.removeprefix("command.") for t in dispatcher.handlers]

    # 연결(및 재연결) 성공 직후 agent.register 를 1회 전송하도록 훅 배선.
    async def _on_connect() -> None:
        await reporter.send_register(capabilities)

    connection.on_connect = _on_connect

    # 종료 시그널 처리
    stop_event = asyncio.Event()

    def handle_shutdown(sig: signal.Signals) -> None:
        logger.info("종료 시그널 수신", signal=sig.name)
        stop_event.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, handle_shutdown, sig)

    # 하트비트 + 메시지 수신 동시 실행
    try:
        await asyncio.gather(
            connection.listen(stop_event),
            reporter.heartbeat_loop(stop_event),
        )
    except Exception:
        logger.exception("Agent 오류 발생")
    finally:
        await local_store.close()
        logger.info("ClickEye Agent 종료")


if __name__ == "__main__":
    asyncio.run(main())
