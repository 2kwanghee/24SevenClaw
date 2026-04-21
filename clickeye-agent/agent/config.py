from pydantic_settings import BaseSettings


class AgentSettings(BaseSettings):
    # Agent 식별
    agent_id: str = ""
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
