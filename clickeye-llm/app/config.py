from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 앱
    app_name: str = "ClickEye LLM"
    debug: bool = False
    log_level: str = "INFO"

    # ── ★모델 스위처블★ ──
    # LLM/임베딩 백엔드는 전부 config 로 주입 → 코드 변경 없이 모델 교체(회귀 0).
    # 로컬(고객 구독)이 엔진: 호스트에서 도는 ollama 를 컨테이너에서 참조한다.
    #   WSL/Linux 에서 컨테이너 → 호스트 접근은 host.docker.internal(compose extra_hosts) 사용.
    ollama_base_url: str = "http://host.docker.internal:11434"
    # 생성 모델(소형 sLLM). phi3:mini 기본 — 더 큰 모델로 교체 가능.
    llm_model: str = "phi3:mini"
    # 임베딩 모델. Qdrant 에 upsert 할 벡터 생성용.
    embed_model: str = "nomic-embed-text"

    # ── 벡터 DB (Qdrant) ──
    # 딜리버리(조직) 네임스페이스로 KB 격리(자격 격리 원칙 일관).
    # 단일 컬렉션 + payload.delivery_id 필터로 교차 딜리버리 유출을 코드에서 강제한다.
    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = "clickeye_kb"
    # 피드백 컬렉션(P2-MVP) — KB 와 분리 저장, 동일한 delivery_id 격리 필터 강제.
    qdrant_feedback_collection: str = "clickeye_feedback"

    # ── RAG 프롬프트 (P2-full: 프롬프트 진화 대상) ──
    # 챗 시스템 프롬프트 챔피언 파일. 존재하면 파일 로드(mtime 캐시 — 스왑 시 재기동
    # 없이 반영), 없으면 rag.py 내장 기본값 폴백. 상대 경로 = 프로세스 CWD 기준
    # (컨테이너 WORKDIR=/app, 로컬 uv run = clickeye-llm/ — 양쪽 모두 prompts/ 해석).
    rag_prompt_path: str = "prompts/rag_system.champion.md"

    # ── RAG 파라미터 ──
    # 청킹: 문단 우선, 길이 초과 시 분할(간단 전략). 임베딩 모델 컨텍스트에 맞춰 보수적.
    chunk_size: int = 800  # 문자 기준 최대 청크 길이
    chunk_overlap: int = 100  # 청크 간 겹침(문맥 보존)
    top_k: int = 4  # 검색 기본 반환 개수

    # ── HTTP 타임아웃(초) ──
    # CPU 추론(임베딩/생성)은 느릴 수 있어 넉넉히. 스위처블 모델별로 조정.
    ollama_timeout: float = 120.0

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
