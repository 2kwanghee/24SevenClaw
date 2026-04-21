# API Agent — ClickEye Backend Development Guide

> 이 파일은 24SevenClaw-api 모듈 개발 시 Claude Code가 참조하는 전담 가이드입니다.
> 레포 초기화 시 `24SevenClaw-api/CLAUDE.md`로 복사합니다.

## Tech Stack
- **Framework**: FastAPI 0.115+
- **Language**: Python 3.12+ (type hints 필수)
- **ORM**: SQLAlchemy 2.0 async
- **Migration**: Alembic (async)
- **Validation**: Pydantic v2
- **Auth**: JWT (python-jose + passlib[bcrypt])
- **Testing**: pytest + httpx (AsyncClient)
- **Linting**: ruff
- **Type Check**: mypy (strict)
- **Package Manager**: uv

## Directory Structure
```
app/
├── main.py                 # FastAPI app factory
├── config.py               # Pydantic BaseSettings
├── database.py             # async engine + session
├── dependencies.py         # DI (get_db, get_current_user)
├── api/
│   └── v1/
│       ├── router.py       # v1 라우터 집합
│       ├── auth.py         # 인증 엔드포인트
│       ├── projects.py     # 프로젝트 CRUD
│       ├── registry.py     # 레지스트리 프록시
│       ├── configurations.py
│       └── health.py
├── models/                 # SQLAlchemy 모델
├── schemas/                # Pydantic 스키마 (요청/응답)
├── services/               # 비즈니스 로직
├── core/
│   ├── security.py         # JWT, 패스워드 해싱
│   ├── exceptions.py       # 커스텀 예외
│   └── middleware.py       # CORS, 요청ID, Rate Limiting
└── utils/
    ├── pagination.py
    └── cache.py
```

## Coding Rules

### FastAPI 엔드포인트
```python
# 라우터 파일 패턴
from fastapi import APIRouter, Depends, HTTPException, status
from app.dependencies import get_current_user, get_db
from app.schemas.project import ProjectCreate, ProjectResponse
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])

@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    service = ProjectService(db)
    return await service.create(user_id=user.id, data=data)
```

### SQLAlchemy 모델
```python
# models/project.py
from sqlalchemy import Column, String, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID, primary_key=True, server_default=text("gen_random_uuid()"))
    owner_id = Column(UUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    slug = Column(String(200), nullable=False)
    settings = Column(JSONB, server_default=text("'{}'"))
```

### Pydantic 스키마
```python
# schemas/project.py
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None

class ProjectResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
```

### 서비스 레이어
- **비즈니스 로직은 services/에**: 엔드포인트는 얇게, 서비스가 두껍게
- **DB 세션은 주입**: `__init__(self, db: AsyncSession)`
- **예외는 서비스에서**: `HTTPException`은 라우터에서만, 서비스는 커스텀 예외

```python
# services/project_service.py
class ProjectService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: UUID, data: ProjectCreate) -> Project:
        slug = slugify(data.name)
        project = Project(owner_id=user_id, name=data.name, slug=slug)
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        return project
```

### DB 마이그레이션 (Alembic)
- 모델 변경 → `alembic revision --autogenerate -m "설명"`
- 마이그레이션 적용 → `alembic upgrade head`
- **절대 수동으로 DB 스키마 변경 금지**
- 마이그레이션 메시지는 한국어

### WebSocket Hub (Agent 통신)
- `app/ws/hub.py`: Agent WebSocket 연결 관리
- `app/ws/handlers.py`: 메시지 타입별 핸들러
- 프로토콜: `docs/agent-protocol.md` 참조
- Redis Pub/Sub로 다중 인스턴스 지원

### 에러 핸들링
```python
# core/exceptions.py
class AppException(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code

# 사용
raise AppException("PROJECT_NOT_FOUND", "프로젝트를 찾을 수 없습니다", 404)
```

## Testing
```python
# tests/test_projects.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_project(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/projects",
        json={"name": "테스트 프로젝트"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    assert response.json()["name"] == "테스트 프로젝트"
```

- **conftest.py**: 테스트 DB, 클라이언트, 인증 fixture 정의
- 각 엔드포인트 최소 3개 테스트 (성공, 인증 실패, 유효성 검사 실패)

## OpenAPI 스펙 생성
- FastAPI가 자동 생성하는 `/openapi.json` 활용
- `openapi_export.py`: 스크립트로 JSON 파일 내보내기
- 변경 시 contracts 레포에 동기화

## Do NOT
- 엔드포인트에 비즈니스 로직 작성 (서비스 레이어 사용)
- sync DB 호출 사용 (반드시 async)
- `*` import 사용
- 하드코딩된 설정값 (config.py 사용)
- 마이그레이션 파일 수동 편집
- print 디버깅 커밋 (structlog 사용)
