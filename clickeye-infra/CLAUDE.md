# Infra Agent — ClickEye Infrastructure Development Guide

> 이 파일은 clickeye-infra 모듈 개발 시 Claude Code가 참조하는 전담 가이드입니다.
> 레포 초기화 시 `clickeye-infra/CLAUDE.md`로 복사합니다.

## 역할
- 로컬 개발 환경 (Docker Compose)
- CI/CD 파이프라인 (GitHub Actions)
- 배포 설정 (Dockerfile, Nginx)
- 스크립트 (셋업, 마이그레이션, 코드젠)

## Directory Structure
```
docker/
├── docker-compose.yml              # 클라우드 로컬 dev (API + DB + Redis)
├── docker-compose.agent-test.yml   # Agent 테스트용
├── docker-compose.prod.yml         # 프로덕션
├── Dockerfile.api                  # FastAPI 이미지
├── Dockerfile.web                  # Next.js 이미지
├── Dockerfile.agent                # Agent 이미지
└── nginx/
    └── nginx.conf
managed/                            # Managed infrastructure configs
├── ...                             # 클라우드 배포 설정
scripts/
├── setup-dev.sh                    # 원컴맨드 로컬 셋업 (docker-compose up + migrations)
├── generate-api-client.sh          # OpenAPI → TS 클라이언트 생성
├── deploy.sh                       # 배포 스크립트
└── health-check.sh                 # 서비스 헬스 체크
```

## Docker Compose Rules

### 로컬 개발 환경
```yaml
# docker-compose.yml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: clickeye
      POSTGRES_USER: clickeye
      POSTGRES_PASSWORD: devpassword
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U clickeye"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]

volumes:
  pgdata:
```

### Dockerfile 작성 규칙
- **멀티스테이지 빌드**: 빌드/실행 분리
- **non-root 사용자**: 보안을 위해 root로 실행 금지
- **레이어 캐싱**: 의존성 설치 → 소스 복사 순서
- **.dockerignore**: 불필요한 파일 제외

```dockerfile
# Dockerfile.api 패턴
FROM python:3.12-slim AS builder
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen

FROM python:3.12-slim
WORKDIR /app
RUN useradd -m appuser
COPY --from=builder /app/.venv /app/.venv
COPY app/ ./app/
USER appuser
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## GitHub Actions CI/CD

### API CI 패턴
```yaml
# .github/workflows/ci.yml
name: API CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: test_clickeye
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports: ["5432:5432"]
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: uv sync
      - run: uv run ruff check .
      - run: uv run mypy app/
      - run: uv run pytest --cov=app --cov-report=xml
```

## Script Rules
- **Bash strict mode**: `set -euo pipefail`
- **헬스 체크 대기**: DB/Redis 준비될 때까지 대기 후 진행
- **멱등성**: 여러 번 실행해도 안전
- **에러 메시지**: 한국어로 사용자 친화적

```bash
#!/bin/bash
set -euo pipefail

echo "🔄 개발 환경을 시작합니다..."
docker compose up -d

echo "⏳ PostgreSQL 준비 대기 중..."
until docker compose exec -T db pg_isready -U clickeye; do
  sleep 1
done

echo "✅ 개발 환경이 준비되었습니다."
```

## Do NOT
- docker-compose.yml에 프로덕션 시크릿 하드코딩
- root 사용자로 컨테이너 실행
- 볼륨 없이 DB 컨테이너 실행 (데이터 유실)
- CI에서 --no-verify 플래그 사용
