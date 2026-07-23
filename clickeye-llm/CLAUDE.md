# LLM Agent — ClickEye 지식축적형 sLLM 개발 가이드

> 이 파일은 clickeye-llm 모듈 개발 시 Claude Code가 참조하는 전담 가이드입니다.

## 역할
딜리버리 지식을 **증분 축적(RAG)** 하고, 진행상황 체크 + KB Q&A를 제공하는 신규 서비스.
- **스위처블 모델**: LLM/임베딩 백엔드를 config(`OLLAMA_BASE_URL`/`LLM_MODEL`/`EMBED_MODEL`)로만 교체 — 코드 변경 없음.
- **로컬(고객 구독)이 엔진**: 호스트에서 도는 Ollama를 컨테이너에서 참조(`host.docker.internal:11434`).
- **Qdrant 네임스페이스 격리**: KB를 딜리버리(조직) 네임스페이스로 분리(자격 격리 원칙 일관).
- **토글 뒤 격리**: 전부 `docker compose --profile llm` 프로파일 뒤 → OFF 시 미기동(기존 스택 회귀 0).

## Tech Stack
- **Framework**: FastAPI 0.115+
- **Language**: Python 3.12+ (type hints 필수)
- **Validation / Config**: Pydantic v2 / pydantic-settings
- **LLM/임베딩**: Ollama (httpx, 스위처블)
- **Vector DB**: Qdrant (qdrant-client)
- **Logging**: structlog
- **Package Manager**: uv
- **Port**: 8100

## Directory Structure
```
app/
├── main.py       # FastAPI 앱 팩토리(create_app), /health
├── config.py     # pydantic-settings Settings (★모델 스위처블★)
└── clients/      # (Chunk2) ollama.py / qdrant.py
```

## 실행
```bash
# 로컬 직접 실행 (OLLAMA_BASE_URL=http://localhost:11434 권장)
uv run uvicorn app.main:app --host 0.0.0.0 --port 8100

# Docker (프로파일 llm)
cd clickeye-infra/docker && docker compose --profile llm up -d qdrant clickeye-llm
curl http://localhost:8100/health   # → {"status":"ok","model":...,"embed_model":...}
```

## P1~P3 로드맵
- **P1 (진행 중)**
  - **Chunk1 (이번)**: 인프라 + FastAPI 뼈대 + config 스위처 + Dockerfile.llm + compose(profile llm) + `/health`.
  - **Chunk2**: ollama/qdrant 클라이언트 + ingest(임베딩·upsert, 딜리버리 네임스페이스) + chat(RAG) + progress. `nomic-embed-text` pull.
  - **Chunk3**: clickeye-api LLM 프록시 라우터 + web 딜리버리 콘솔 챗 패널.
- **P2**: 피드백 루프(응답 품질 개선 사이클).
  - **P2-MVP (완료)**: 수집·저장·노출 — `/chat` 응답에 `chat_id`, `POST /feedback`(👍/👎+코멘트),
    `GET /feedback/{delivery_id}?rating=&limit=`. 저장은 Qdrant `clickeye_feedback` 컬렉션
    (size=1 더미 벡터, payload 전체 저장, delivery_id 격리 필터 강제).
  - **prompt-evolve 소비 계약**: 오프라인 배치(`scripts/prompt-evolve-loop.sh` → prompt-evolver)가
    `GET /feedback/{delivery_id}` 로 항목(query·answer·rating·comment·sources·model·created_at)을
    끌어가 챔피언 프롬프트 평가 입력으로 사용한다. rating=down 이 실패 피드백, 당시 model 로
    모델별 성적을 분리한다. 자동 파라미터 튜닝은 P2-후속.
- **P3**: LoRA 미세조정.

> sLLM 답변 품질은 초기엔 낮을 수 있음(모델 스위칭·KB 성장으로 개선) — 완벽 전제 아님.

## Do NOT
- 하드코딩된 모델명/URL (반드시 config.py 사용 — 스위처블 원칙)
- root 사용자로 컨테이너 실행 (non-root)
- 기존 compose 서비스/네트워크/프로파일 변경 (추가만, 회귀 0)
- KB 네임스페이스 혼용 (딜리버리 단위 격리 유지)
