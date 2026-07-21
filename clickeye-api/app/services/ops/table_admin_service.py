"""화이트리스트 테이블 제네릭 CRUD 서비스 (CE-305 PR-4, superadmin 전용).

`table_registry.REGISTRY` (코드 정의, 런타임 불변)에 등재된 테이블/컬럼에 대해서만
동작한다. 미등재 테이블은 404(존재 은닉), 미허용 연산은 405, 임의(화이트리스트 밖)
컬럼 주입은 400 으로 거부한다. 모든 쓰기는 `ops_audit` 로 기록하며 값 자체는 남기지
않고(민감 데이터 유출 방지) 변경 컬럼명 요약만 마스킹 규칙과 함께 기록한다.

동적 컬럼 접근은 항상 디스크립터의 화이트리스트 컬럼으로 제한(getattr/setattr)하여
요청이 임의 ORM 속성을 주입하는 것을 차단한다.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy import String, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppError
from app.schemas.ops import (
    TableColumnSchema,
    TableInfo,
    TableRow,
    TableRowsPage,
    TableSchema,
)
from app.services.ops import ops_audit
from app.services.ops.table_registry import (
    REGISTRY,
    ColumnSpec,
    Op,
    TableDescriptor,
    get_descriptor,
)

_MASK = "***"
_DEFAULT_LIMIT = 50
_MAX_LIMIT = 200


# ---------------------------------------------------------------------------
# 디스크립터 resolve + 연산 가드
# ---------------------------------------------------------------------------


def _resolve(table_key: str) -> TableDescriptor:
    """화이트리스트 테이블 resolve. 미등재는 404(존재 은닉)."""
    descriptor = get_descriptor(table_key)
    if descriptor is None:
        raise AppError("OPS_TABLE_NOT_FOUND", "Not Found", 404)
    return descriptor


def _require_op(descriptor: TableDescriptor, op: Op) -> None:
    """허용 연산 가드. 화이트리스트 테이블이지만 미허용 연산이면 405."""
    if not descriptor.allows(op):
        raise AppError(
            "OPS_TABLE_OP_NOT_ALLOWED",
            f"'{descriptor.key}' 테이블은 '{op}' 연산을 지원하지 않습니다.",
            405,
        )


# ---------------------------------------------------------------------------
# 직렬화 / 마스킹
# ---------------------------------------------------------------------------


def _serialize(value: Any) -> Any:
    """DB 값을 JSON 직렬화 가능한 형태로 변환."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, Enum):
        return value.value
    return value


def _row_to_dict(descriptor: TableDescriptor, row: object) -> dict[str, Any]:
    """행을 화이트리스트 컬럼만 담은 dict 로 변환(민감 컬럼 마스킹)."""
    out: dict[str, Any] = {}
    for spec in descriptor.columns:
        raw = getattr(row, spec.name, None)
        if spec.sensitive:
            out[spec.name] = _MASK if raw is not None else None
        else:
            out[spec.name] = _serialize(raw)
    return out


def _envelope(descriptor: TableDescriptor, row: object) -> TableRow:
    """행을 마스킹된 값 dict + 테이블/PK 메타로 감싼 단건 응답 엔벌로프로 변환."""
    values = _row_to_dict(descriptor, row)
    pk_val = values.get(descriptor.pk_column)
    return TableRow(table=descriptor.key, pk=str(pk_val), values=values)


# ---------------------------------------------------------------------------
# 값 검증 / 강제 변환
# ---------------------------------------------------------------------------


def _coerce_pk(descriptor: TableDescriptor, pk_raw: str) -> Any:
    """경로 파라미터 pk 문자열을 pk 컬럼 타입으로 변환."""
    if descriptor.pk_spec.type == "uuid":
        try:
            return UUID(pk_raw)
        except (ValueError, AttributeError) as exc:
            raise AppError("OPS_TABLE_PK_INVALID", "유효하지 않은 식별자입니다.", 400) from exc
    return pk_raw


def _validate_value(spec: ColumnSpec, value: Any) -> Any:
    """쓰기 값 타입/형식 검증 + 필요한 강제 변환. 실패 시 AppError(400)."""
    if value is None:
        if spec.required:
            raise AppError("OPS_TABLE_VALUE_INVALID", f"'{spec.name}' 는 필수 값입니다.", 400)
        return None

    if spec.type == "str":
        if not isinstance(value, str):
            raise AppError("OPS_TABLE_VALUE_INVALID", f"'{spec.name}' 는 문자열이어야 합니다.", 400)
        if spec.max_length is not None and len(value) > spec.max_length:
            raise AppError(
                "OPS_TABLE_VALUE_INVALID",
                f"'{spec.name}' 는 최대 {spec.max_length}자를 초과할 수 없습니다.",
                400,
            )
        return value

    if spec.type == "enum":
        if not isinstance(value, str) or (spec.enum is not None and value not in spec.enum):
            allowed = ", ".join(spec.enum or ())
            raise AppError(
                "OPS_TABLE_VALUE_INVALID",
                f"'{spec.name}' 는 다음 중 하나여야 합니다: {allowed}",
                400,
            )
        return value

    if spec.type == "int":
        if isinstance(value, bool) or not isinstance(value, int):
            raise AppError("OPS_TABLE_VALUE_INVALID", f"'{spec.name}' 는 정수여야 합니다.", 400)
        return value

    if spec.type == "float":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise AppError("OPS_TABLE_VALUE_INVALID", f"'{spec.name}' 는 숫자여야 합니다.", 400)
        return float(value)

    if spec.type == "bool":
        if not isinstance(value, bool):
            raise AppError(
                "OPS_TABLE_VALUE_INVALID", f"'{spec.name}' 는 boolean 이어야 합니다.", 400
            )
        return value

    if spec.type == "uuid":
        try:
            return UUID(str(value))
        except (ValueError, AttributeError) as exc:
            raise AppError(
                "OPS_TABLE_VALUE_INVALID", f"'{spec.name}' 는 UUID 여야 합니다.", 400
            ) from exc

    # json — 스칼라/리스트/딕트 모두 허용(구조 검증은 도메인 밖).
    return value


def _collect_write_values(
    descriptor: TableDescriptor,
    values: dict[str, Any],
    *,
    for_create: bool,
) -> dict[str, Any]:
    """payload 를 화이트리스트 컬럼으로 필터링·검증한다.

    - 디스크립터에 없는 컬럼 → 400 (임의 컬럼 주입 차단).
    - create: creatable(required|editable) 아닌 컬럼(예: id/updated_at auto) → 400.
    - update: editable 아닌 컬럼(PK·created_at 등 불변) → 400.
    - create: required 컬럼 누락 → 400.
    """
    coerced: dict[str, Any] = {}
    for key, raw in values.items():
        spec = descriptor.column(key)
        if spec is None:
            raise AppError(
                "OPS_TABLE_COLUMN_UNKNOWN",
                f"'{key}' 는 관리 대상 컬럼이 아닙니다.",
                400,
            )
        if for_create and not spec.creatable:
            raise AppError(
                "OPS_TABLE_COLUMN_NOT_WRITABLE",
                f"'{key}' 는 생성 시 설정할 수 없는 컬럼입니다.",
                400,
            )
        if not for_create and not spec.editable:
            raise AppError(
                "OPS_TABLE_COLUMN_IMMUTABLE",
                f"'{key}' 는 수정할 수 없는 컬럼입니다(PK/자동 컬럼).",
                400,
            )
        coerced[key] = _validate_value(spec, raw)

    if for_create:
        for spec in descriptor.columns:
            if spec.required and spec.name not in coerced:
                raise AppError(
                    "OPS_TABLE_VALUE_INVALID",
                    f"'{spec.name}' 는 필수 값입니다.",
                    400,
                )
    return coerced


def _has_sensitive(descriptor: TableDescriptor, keys: list[str]) -> bool:
    return any((s := descriptor.column(k)) is not None and s.sensitive for k in keys)


def _audit(
    db: AsyncSession,
    descriptor: TableDescriptor,
    *,
    op: str,
    pk: Any,
    changed: list[str],
    actor_id: UUID,
) -> None:
    """쓰기 감사 기록. 값은 남기지 않고 변경 컬럼명 요약만 기록(마스킹 규칙 적용)."""
    summary = ",".join(sorted(changed)) if changed else op
    db.add(
        ops_audit.build_ops_audit(
            actor_id=actor_id,
            action=f"ops.table.{op}",
            resource=f"table:{descriptor.key}:{pk}",
            key=descriptor.key,
            old_value=None,
            new_value=summary,
            is_secret=_has_sensitive(descriptor, changed),
        )
    )


# ---------------------------------------------------------------------------
# 메타 (테이블 목록 / 스키마)
# ---------------------------------------------------------------------------


async def list_tables(db: AsyncSession) -> list[TableInfo]:
    """화이트리스트 테이블 목록 + 행 수."""
    items: list[TableInfo] = []
    for descriptor in REGISTRY.values():
        try:
            total = await db.scalar(select(func.count()).select_from(descriptor.model))
            row_count = int(total) if total is not None else None
        except Exception:  # noqa: BLE001 - 집계 실패는 치명적이지 않음(None 처리)
            row_count = None
        items.append(
            TableInfo(
                key=descriptor.key,
                label=descriptor.label,
                ops=sorted(descriptor.allowed_ops),
                row_count=row_count,
            )
        )
    return items


def get_schema(table_key: str) -> TableSchema:
    """테이블 컬럼 디스크립터(동적 폼용). 미등재는 404."""
    descriptor = _resolve(table_key)
    return TableSchema(
        key=descriptor.key,
        label=descriptor.label,
        pk_column=descriptor.pk_column,
        allowed_ops=sorted(descriptor.allowed_ops),
        columns=[
            TableColumnSchema(
                name=s.name,
                type=s.type,
                required=s.required,
                editable=s.editable,
                sensitive=s.sensitive,
                max_length=s.max_length,
                enum=list(s.enum) if s.enum is not None else None,
            )
            for s in descriptor.columns
        ],
    )


# ---------------------------------------------------------------------------
# 조회 (list / get)
# ---------------------------------------------------------------------------


async def list_rows(
    db: AsyncSession,
    table_key: str,
    *,
    limit: int = _DEFAULT_LIMIT,
    offset: int = 0,
    q: str | None = None,
) -> TableRowsPage:
    """페이지네이션 조회(마스킹 적용)."""
    descriptor = _resolve(table_key)
    _require_op(descriptor, "read")

    limit = max(1, min(limit, _MAX_LIMIT))
    offset = max(0, offset)
    model = descriptor.model
    pk_attr = getattr(model, descriptor.pk_column)

    where_clause = None
    if q:
        # W1: 네이티브 PG enum(roi_standards.category 등)에 ILIKE 를 직접 걸면
        # `operator does not exist: roi_category ~~* text` 500 이 난다. String 으로
        # 캐스트하면 SQLite/PG 양쪽에서 안전하게 substring 검색된다(실제 PG 경로는
        # PR-6 pg 마커 테스트로 커버). W2: sensitive 컬럼은 값이 마스킹(***)되므로
        # q substring 프로빙으로 값을 역추적할 수 없도록 검색 대상에서 제외한다.
        conditions = [
            cast(getattr(model, s.name), String).ilike(f"%{q}%")
            for s in descriptor.columns
            if s.type in ("str", "enum") and not s.sensitive
        ]
        if conditions:
            where_clause = or_(*conditions)

    count_stmt = select(func.count()).select_from(model)
    rows_stmt = select(model).order_by(pk_attr).offset(offset).limit(limit)
    if where_clause is not None:
        count_stmt = count_stmt.where(where_clause)
        rows_stmt = rows_stmt.where(where_clause)

    total = await db.scalar(count_stmt)
    result = await db.execute(rows_stmt)
    rows = [_row_to_dict(descriptor, row) for row in result.scalars().all()]

    return TableRowsPage(
        total=int(total) if total is not None else 0,
        limit=limit,
        offset=offset,
        rows=rows,
    )


async def get_row(db: AsyncSession, table_key: str, pk_raw: str) -> TableRow:
    """단건 조회(마스킹). 미존재는 404."""
    descriptor = _resolve(table_key)
    _require_op(descriptor, "read")
    pk = _coerce_pk(descriptor, pk_raw)
    row = await db.get(descriptor.model, pk)
    if row is None:
        raise AppError("OPS_TABLE_ROW_NOT_FOUND", "행을 찾을 수 없습니다.", 404)
    return _envelope(descriptor, row)


# ---------------------------------------------------------------------------
# 쓰기 (create / update / delete)
# ---------------------------------------------------------------------------


async def create_row(
    db: AsyncSession, table_key: str, values: dict[str, Any], actor_id: UUID
) -> TableRow:
    """행 생성(editable/required 컬럼만). 미허용 연산 405, 임의 컬럼 400."""
    descriptor = _resolve(table_key)
    _require_op(descriptor, "create")
    coerced = _collect_write_values(descriptor, values, for_create=True)

    # updated_by 자동 세팅(해당 컬럼이 화이트리스트에 있고 payload 미포함 시).
    if descriptor.column("updated_by") is not None:
        coerced.setdefault("updated_by", actor_id)

    row = descriptor.model(**coerced)
    db.add(row)
    await db.flush()
    pk = getattr(row, descriptor.pk_column)
    _audit(
        db,
        descriptor,
        op="create",
        pk=pk,
        changed=list(coerced.keys()),
        actor_id=actor_id,
    )
    await db.commit()
    await db.refresh(row)
    return _envelope(descriptor, row)


async def update_row(
    db: AsyncSession,
    table_key: str,
    pk_raw: str,
    values: dict[str, Any],
    actor_id: UUID,
) -> TableRow:
    """행 수정(editable 컬럼만). PK/불변 컬럼 변경 시 400, 미존재 404."""
    descriptor = _resolve(table_key)
    _require_op(descriptor, "update")
    pk = _coerce_pk(descriptor, pk_raw)
    row = await db.get(descriptor.model, pk)
    if row is None:
        raise AppError("OPS_TABLE_ROW_NOT_FOUND", "행을 찾을 수 없습니다.", 404)

    coerced = _collect_write_values(descriptor, values, for_create=False)
    for key, val in coerced.items():
        setattr(row, key, val)
    if coerced and descriptor.column("updated_by") is not None:
        setattr(row, "updated_by", actor_id)  # noqa: B010 - 화이트리스트 컬럼 동적 세팅

    _audit(
        db,
        descriptor,
        op="update",
        pk=pk,
        changed=list(coerced.keys()),
        actor_id=actor_id,
    )
    await db.commit()
    await db.refresh(row)
    return _envelope(descriptor, row)


async def delete_row(
    db: AsyncSession,
    table_key: str,
    pk_raw: str,
    actor_id: UUID,
    *,
    confirm: bool,
) -> None:
    """행 삭제. confirm=False 시 400, 미존재 404."""
    descriptor = _resolve(table_key)
    _require_op(descriptor, "delete")
    if not confirm:
        raise AppError(
            "OPS_TABLE_DELETE_UNCONFIRMED",
            "삭제를 확정하려면 confirm=true 가 필요합니다.",
            400,
        )
    pk = _coerce_pk(descriptor, pk_raw)
    row = await db.get(descriptor.model, pk)
    if row is None:
        raise AppError("OPS_TABLE_ROW_NOT_FOUND", "행을 찾을 수 없습니다.", 404)

    await db.delete(row)
    _audit(db, descriptor, op="delete", pk=pk, changed=[], actor_id=actor_id)
    await db.commit()
