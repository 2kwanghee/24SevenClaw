"""운영 패널 화이트리스트 테이블 CRUD endpoint (CE-305 PR-4, superadmin 전용).

feature flag `feature_ops_panel` OFF 시 모든 endpoint 404(킬스위치).
코드로 정의된 화이트리스트(table_registry.REGISTRY) 테이블만 노출하며, 미등재
테이블은 존재 자체를 은닉(404)한다.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_ops_feature, require_superadmin
from app.models.user import User
from app.schemas.ops import TableInfo, TableRow, TableRowsPage, TableRowWrite, TableSchema
from app.services.ops import table_admin_service

router = APIRouter(
    prefix="/admin/ops",
    tags=["ops"],
    dependencies=[Depends(require_ops_feature), Depends(require_superadmin)],
)


@router.get("/tables", response_model=list[TableInfo])
async def list_tables(db: AsyncSession = Depends(get_db)) -> list[TableInfo]:
    """화이트리스트 테이블 목록(허용 연산 + 행 수)."""
    return await table_admin_service.list_tables(db)


@router.get("/tables/{table_key}/schema", response_model=TableSchema)
async def get_table_schema(table_key: str) -> TableSchema:
    """테이블 컬럼 디스크립터(동적 폼용). 미등재는 404."""
    return table_admin_service.get_schema(table_key)


@router.get("/tables/{table_key}/rows", response_model=TableRowsPage)
async def list_rows(
    table_key: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    q: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> TableRowsPage:
    """페이지네이션 조회(마스킹). 미등재는 404."""
    return await table_admin_service.list_rows(db, table_key, limit=limit, offset=offset, q=q)


@router.get("/tables/{table_key}/rows/{pk}", response_model=TableRow)
async def get_row(
    table_key: str,
    pk: str,
    db: AsyncSession = Depends(get_db),
) -> TableRow:
    """단건 조회(마스킹). 미등재/미존재는 404."""
    return await table_admin_service.get_row(db, table_key, pk)


@router.post("/tables/{table_key}/rows", status_code=201, response_model=TableRow)
async def create_row(
    table_key: str,
    payload: TableRowWrite,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_superadmin),
) -> TableRow:
    """행 생성. 미허용 연산 405, 임의 컬럼 400."""
    return await table_admin_service.create_row(db, table_key, payload.values, user.id)  # type: ignore[arg-type]


@router.put("/tables/{table_key}/rows/{pk}", response_model=TableRow)
async def update_row(
    table_key: str,
    pk: str,
    payload: TableRowWrite,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_superadmin),
) -> TableRow:
    """행 수정. PK/불변 컬럼 변경 400, 미존재 404."""
    return await table_admin_service.update_row(db, table_key, pk, payload.values, user.id)  # type: ignore[arg-type]


@router.delete("/tables/{table_key}/rows/{pk}", status_code=204)
async def delete_row(
    table_key: str,
    pk: str,
    confirm: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_superadmin),
) -> None:
    """행 삭제(confirm=true 필수). 미허용 연산 405, 미존재 404."""
    await table_admin_service.delete_row(db, table_key, pk, user.id, confirm=confirm)  # type: ignore[arg-type]
