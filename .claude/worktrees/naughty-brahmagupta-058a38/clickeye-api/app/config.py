from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 앱
    app_name: str = "ClickEye API"
    debug: bool = False

    # DB
    database_url: str = "postgresql+asyncpg://sevenclaw:devpassword@localhost:5432/sevenclaw"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # JWT
    jwt_secret_key: str = "dev-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

    # CORS
    cors_origins: list[str] = ["http://localhost:3000"]
    cors_allow_methods: list[str] = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    cors_allow_headers: list[str] = [
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-Request-ID",
    ]

    # Rate Limiting
    rate_limit_default_requests: int = 100
    rate_limit_default_window: int = 60
    rate_limit_auth_requests: int = 10
    rate_limit_auth_window: int = 60

    # Anthropic (Solution Wizard v2)
    anthropic_api_key: str = ""
    anthropic_model_default: str = "claude-sonnet-4-6"
    anthropic_model_advanced: str = "claude-opus-4-7"
    prototype_generation_timeout: int = 60

    # Queued/Backlog 이슈 자동 Wait 복귀 타임아웃 (분)
    queue_stale_minutes: int = 60

    # 부트스트랩: 로컬 ZIP에 베이크되는 클라우드 API 공개 URL
    public_api_url: str = "http://localhost:8000"
    # setup_token TTL (일)
    setup_token_expire_days: int = 30

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
