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
    # 경량 티어(분류/추출 등) — LLM 게이트웨이 라우팅 정책이 참조. 미설정이면 default 로 폴백.
    anthropic_model_light: str = "claude-haiku-4-5"
    prototype_generation_timeout: int = 60

    # OpenAI (Anthropic 키 무효/크레딧 부족/미설정 시 LLM 폴백)
    openai_api_key: str = ""
    openai_model_default: str = "gpt-4o"

    # Queued/Backlog 이슈 자동 Wait 복귀 타임아웃 (분)
    queue_stale_minutes: int = 60

    # 부트스트랩: 로컬 ZIP에 베이크되는 클라우드 API 공개 URL
    public_api_url: str = "http://localhost:8000"
    # setup_token TTL (일)
    setup_token_expire_days: int = 30

    # PM 추천 v2 (Jaccard 유사도 + 차원별 점수) 활성화 여부
    pm_reco_v2_enabled: bool = False

    # Feature flags
    # ClickEye Modernize (기존 코드 현대화 파이프라인, MVP-2-A).
    # 기본 False — 화이트리스트 베타 사용자만 노출. 신규 라우트/모델은 이 flag 가 True 일 때만 활성.
    feature_modernize_enabled: bool = False

    # GitHub App (Modernize 의 repo 연결용 — feature_modernize_enabled 와 별개로 미설정 가능)
    # 모든 값 비어있으면 github_app_service.is_configured() 가 False — 관련 endpoint 503.
    # 등록 가이드: docs/modernize-github-app-setup.md
    github_app_id: int = 0
    # PEM 형식 RSA private key (개행 포함). 환경변수에 통째로 또는 \\n 으로 인코딩.
    github_app_private_key: str = ""
    # user-to-server OAuth (사용자 식별 검증)
    github_app_client_id: str = ""
    github_app_client_secret: str = ""
    # webhook 서명 검증 시크릿 (HMAC-SHA256)
    github_app_webhook_secret: str = ""
    # App slug — install URL 구성용 (예: "clickeye-modernize-dev")
    github_app_slug: str = ""

    # 프론트엔드 URL (OAuth callback 후 redirect 대상)
    frontend_url: str = "http://localhost:3000"

    # 거버넌스 게이트 HTTP 노출용 머신 토큰. None/빈값이면 dev 개방(인증 없음),
    # 설정 시 POST /governance/evaluate 는 X-Governance-Token 헤더 일치를 요구.
    governance_service_token: str | None = None

    # 트리아지(항목 G) 예산 한도/경고 임계. 문서·기본값 제공용 필드다. 실제 판정은 커널
    # (governance.core.assess_budget)이 동일 이름의 FLOWOPS_GOVERNANCE_TRIAGE_BUDGET_*
    # 환경변수를 직접 읽어 수행한다(SSOT). 0 이하면 해당 축 비활성(회귀 0, 기본 off).
    # 운영에서는 .env 에 FLOWOPS_GOVERNANCE_TRIAGE=on 및 아래 임계를 env 로 설정.
    governance_triage_budget_cost_limit: float = 0.0
    governance_triage_budget_cost_warn: float = 0.0
    governance_triage_budget_token_limit: float = 0.0
    governance_triage_budget_token_warn: float = 0.0

    # LLM 게이트웨이 (CE-299, "로깅만"). 기본 off — flag on 시에만 대표 호출처를
    # 게이트웨이 경유로 라우팅해 usage 를 원장에 기록. off 면 기존 경로 그대로(회귀 0).
    feature_llm_gateway: bool = False
    llm_gateway_max_concurrency: int = 8  # 전역 동시성 세마포어 상한
    # 가격맵 외부화(P2). 빈값이면 번들 기본 파일(app/data/llm_pricing.json) 사용.
    # 테스트/운영에서 대체 파일 경로 주입 가능.
    llm_pricing_path: str = ""
    # 모델 라우팅 정책(P2): complexity 가 이 임계 이상이면 advanced(opus) 티어로 격상.
    llm_route_complexity_threshold: float = 0.7

    # Temporal 오케스트레이션 (CE-296, P0 토대). 기본 off — 토글 on 시에만 워커가
    # Temporal 서버에 연결한다. off 면 워커 프로세스가 즉시 종료(회귀 0). 실 워크플로
    # 글루는 P1. host 기본값은 docker compose 서비스명(로컬 직접 실행 시 localhost:7233).
    feature_temporal: bool = False
    temporal_host: str = "temporal:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "clickeye-default"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
