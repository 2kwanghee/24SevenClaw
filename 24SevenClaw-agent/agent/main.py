"""24SevenClaw Agent 데몬 엔트리포인트"""

import asyncio
import signal

import structlog

from agent.config import agent_settings
from agent.connection import CloudConnection
from agent.dispatcher import Dispatcher
from agent.handlers.contract_handler import ContractHandler
from agent.handlers.docker_handler import DockerHandler
from agent.handlers.env_handler import EnvHandler
from agent.reporter import Reporter

logger = structlog.get_logger()


async def main() -> None:
    logger.info(
        "24SevenClaw Agent 시작",
        agent_id=agent_settings.agent_id,
        cloud_url=agent_settings.cloud_ws_url,
    )

    # 디스패처 초기화
    dispatcher = Dispatcher()

    # 클라우드 연결
    connection = CloudConnection(config=agent_settings, dispatcher=dispatcher)
    reporter = Reporter(connection=connection)

    # 핸들러 등록
    docker_handler = DockerHandler(
        config=agent_settings, reporter=reporter, local_store=None
    )
    env_handler = EnvHandler(
        config=agent_settings, reporter=reporter, local_store=None
    )
    contract_handler = ContractHandler(
        config=agent_settings, reporter=reporter, local_store=None
    )

    dispatcher.register("command.setup_env", env_handler)
    dispatcher.register("contract.sync", contract_handler)
    dispatcher.register("command.build", docker_handler)
    dispatcher.register("command.run", docker_handler)
    dispatcher.register("command.stop", docker_handler)
    dispatcher.register("command.destroy_env", docker_handler)

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
        logger.info("24SevenClaw Agent 종료")


if __name__ == "__main__":
    asyncio.run(main())
