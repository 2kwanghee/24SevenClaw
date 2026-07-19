from pydantic_settings import BaseSettings

# Agent 데몬 버전. register/heartbeat 페이로드의 agent_version 으로 보고된다.
AGENT_VERSION = "0.1.0"


class AgentSettings(BaseSettings):
    # Agent 식별
    agent_id: str = ""  # hub 라우팅용 라벨 (DB 컬럼 아님)
    agent_token: str = ""  # canonical 크리덴셜 (DB unique 컬럼과 매칭, 핸드셰이크 쿼리 인증)
    # NOTE(CE-300): agent_secret은 하위 호환을 위해 유지하나 핸드셰이크에서는 미사용.
    #   현재 인증은 쿼리 agent_id + agent_token 조합만 사용한다.
    agent_secret: str = ""
    license_key: str = ""

    # Cloud 연결
    cloud_ws_url: str = "wss://api.24sevenclaw.com"
    heartbeat_interval: int = 30  # 초

    # 로컬 저장소
    data_dir: str = "/data/clickeye"
    local_db_path: str = "/data/clickeye/agent.db"

    # Docker
    docker_socket: str = "unix:///var/run/docker.sock"

    model_config = {"env_file": ".env", "env_prefix": "CLICKEYE_"}


agent_settings = AgentSettings()
