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
    # 운영(Ops) 패널 저버짓 — superadmin 전용이라 낮게 유지.
    rate_limit_ops_requests: int = 30
    rate_limit_ops_window: int = 60

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
    # 운영(Ops) 패널 (CE-305, superadmin 전용 인프라 조회/관리).
    # 기본 False — OFF 시 전 ops endpoint 404 (킬스위치, 무침습 롤아웃).
    feature_ops_panel: bool = False
    # read-only docker 소켓 프록시 내부 URL (POST=0, GET 전용).
    docker_proxy_url: str = "http://dockerproxy:2375"
    # 관리형 env 파일 마운트 경로 (env CRUD PR 에서 사용).
    managed_env_path: str = "/app/managed/api.env"
    # 포트 프로브 대상 목록. 형식: "host:port" 또는 "service=host:port". JSON 배열로 주입.
    ops_port_targets: list[str] = []
    # 관리형 서비스명 목록 (env 렌더/재생성 안내 대상). JSON 배열로 주입.
    ops_managed_services: list[str] = []

    # 프론트엔드 URL (redirect 대상)
    frontend_url: str = "http://localhost:3000"

    # clickeye-llm (지식축적형 sLLM, profile llm, 포트 8100) 프록시 대상 URL.
    # 기본값은 docker compose 서비스명(api·clickeye-llm 이 default 네트워크 공유).
    # 로컬 uvicorn 직접 실행 시 env 로 override: CLICKEYE_LLM_URL=http://localhost:8100
    clickeye_llm_url: str = "http://clickeye-llm:8100"

    # clickeye-llm KB 자동 인제스트 (P1.5). 기본 off — off 면 enqueue_ingest 가 즉시
    # no-op(회귀 0). on 시 산출물/거버넌스/오케스트레이션/리뷰 이벤트를 fire-and-forget
    # 으로 POST {clickeye_llm_url}/ingest 전송. delivery_id = str(project_id).
    feature_llm_autoingest: bool = False

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

    # 인테이크 수주 API (Chunk A1). 기본 off — OFF 시 전 /intake endpoint 404
    # (킬스위치, 회귀 0). on 시 외부 서비스가 X-ClickEye-Service-Key 로 요구사항을 접수.
    feature_intake: bool = False

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
