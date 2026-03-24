# 24SevenClaw - Daily TODO

---

## Day 1 (2026-03-23) - 저장소 초기화

### 24SevenClaw-api (클라우드 백엔드)
- [ ] 프로젝트 디렉토리 생성 + git init
- [ ] uv init + 의존성 추가 (fastapi, sqlalchemy, alembic, pydantic, pytest, httpx, ruff)
- [ ] 디렉토리 구조 생성 (app/, tests/, alembic/)
- [ ] .gitignore, .env.example, pyproject.toml 설정

### 24SevenClaw-web (클라우드 프론트엔드)
- [ ] create-next-app (TypeScript, Tailwind, App Router, ESLint)
- [ ] shadcn/ui 초기화
- [ ] 기본 의존성 추가 (zustand, @tanstack/react-query, react-hook-form, zod, lucide-react)

### 24SevenClaw-agent (고객 서버 에이전트)
- [ ] 프로젝트 디렉토리 생성 + git init
- [ ] uv init + 의존성 추가 (websockets, docker, pydantic)
- [ ] 디렉토리 구조 생성 (agent/, tests/)
- [ ] .gitignore, .env.example 설정

### 24SevenClaw-infra
- [ ] docker-compose.yml (클라우드용: PostgreSQL 16 + Redis 7)
- [ ] docker-compose.agent.yml (고객 서버 에이전트 테스트용)
- [ ] setup-dev.sh 스크립트
- [ ] Dockerfile.api, Dockerfile.agent 작성

### 24SevenClaw-contracts
- [ ] package.json + @hey-api/openapi-ts
- [ ] 클라우드↔에이전트 통신 프로토콜 스키마 정의
- [ ] 생성 스크립트 (fetch-spec.sh, generate.sh)

### 공통
- [ ] 각 레포 .gitignore 확인
- [ ] docker-compose up으로 DB + Redis 실행 확인

---

## Day 2 - FastAPI 스켈레톤 + DB
- [ ] app/main.py, config.py, database.py
- [ ] health 엔드포인트
- [ ] Alembic 설정 + users 테이블 마이그레이션
- [ ] Docker에서 API + DB 연결 확인

## Day 3 - 인증 백엔드
- [ ] security.py (bcrypt, JWT)
- [ ] auth schemas + auth_service
- [ ] auth 엔드포인트 4개
- [ ] get_current_user 의존성
- [ ] test_auth.py

## Day 4 - Next.js 스켈레톤 + 인증 UI
- [ ] Auth.js v5 설정
- [ ] shadcn 컴포넌트 설치
- [ ] 로그인/회원가입 페이지
- [ ] 대시보드 레이아웃
- [ ] auth middleware

## Day 5 - CI/CD
- [ ] API CI (ruff, mypy, pytest)
- [ ] Web CI (lint, typecheck, build)
- [ ] Agent CI (ruff, mypy, pytest)
- [ ] Contracts CI
- [ ] 브랜치 보호 규칙

## Day 6 - DB 스키마 + Projects CRUD
- [ ] 전체 SQLAlchemy 모델 (licenses, agent_connections 포함)
- [ ] Alembic 마이그레이션
- [ ] Projects API + 서비스 + 테스트

## Day 7 - Contract 파이프라인 + 대시보드 UI
- [ ] OpenAPI 스펙 생성 + TS 클라이언트 생성
- [ ] TanStack Query + use-projects 훅
- [ ] 프로젝트 목록/생성 페이지

## Day 8 - Agent 기본 데몬 + 환경 강화
- [ ] Agent 데몬 기본 구조 (main.py, config.py, connection.py)
- [ ] Agent → Cloud WebSocket 연결 테스트
- [ ] 에러 핸들링, 로깅, Rate Limiting
- [ ] README, .env.example 완성
- [ ] E2E 테스트 + v0.1.0-phase0 태깅
