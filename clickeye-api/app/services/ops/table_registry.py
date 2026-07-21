"""운영 패널 화이트리스트 테이블 레지스트리 (CE-305 PR-4, superadmin 전용).

**보안 핵심 — 코드로만 정의, 런타임 불변**:
- 조회/편집 가능한 테이블·컬럼은 이 모듈의 `REGISTRY` (module-level frozen dataclass)로만
  정의된다. 요청/DB/환경변수로 테이블·컬럼 화이트리스트를 바꿀 수 없다(권한상승 방지).
- 여기에 **없는** 테이블은 존재 자체를 은닉(404). 민감 테이블(users, organization_memberships,
  role_audit_logs, central_contracts, *_credentials, licenses, RBAC, managed_env_vars 등)은
  절대 등재하지 않는다.
- 컬럼 접근은 항상 이 디스크립터의 화이트리스트 컬럼으로 제한한다(임의 컬럼 주입 차단).

편집 권한 의미:
- `required`  : create(POST) payload 에 반드시 존재해야 하는 컬럼.
- `editable`  : update(PUT) 로 수정 가능한 컬럼. PK/created_at/updated_at/updated_by 등
                자동·불변 컬럼은 False.
- create 시 설정 가능한 컬럼 = (`required` 또는 `editable`) 인 컬럼.
- update 시 설정 가능한 컬럼 = `editable` 인 컬럼. 그 외 컬럼을 payload 에 담으면 거부.
- `sensitive` : 조회(list/get) 및 감사 로그에서 값을 마스킹(***). 초기 3개 테이블엔 민감
                컬럼이 없으나(설정성 데이터), 마스킹 경로는 제네릭하게 지원한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal

from app.database import Base
from app.models.app_setting import AppSetting
from app.models.preset import Preset
from app.models.roi_standard import RoiStandard

# 컬럼 논리 타입. 검증/직렬화 분기에 사용.
ColumnType = Literal["str", "int", "float", "bool", "uuid", "datetime", "json", "enum"]

# 허용 연산.
Op = Literal["read", "create", "update", "delete"]


@dataclass(frozen=True)
class ColumnSpec:
    """화이트리스트 컬럼 1개의 디스크립터."""

    name: str
    type: ColumnType
    required: bool = False
    editable: bool = True
    sensitive: bool = False
    max_length: int | None = None
    enum: tuple[str, ...] | None = None

    @property
    def creatable(self) -> bool:
        """create payload 에서 설정 가능한 컬럼인지 (natural PK 포함)."""
        return self.required or self.editable


@dataclass(frozen=True)
class TableDescriptor:
    """화이트리스트 테이블 1개의 디스크립터."""

    key: str
    label: str
    model: type[Base]
    pk_column: str
    columns: tuple[ColumnSpec, ...]
    allowed_ops: frozenset[Op]
    columns_by_name: MappingProxyType[str, ColumnSpec] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        mapping = {c.name: c for c in self.columns}
        object.__setattr__(self, "columns_by_name", MappingProxyType(mapping))

    def column(self, name: str) -> ColumnSpec | None:
        return self.columns_by_name.get(name)

    @property
    def pk_spec(self) -> ColumnSpec:
        spec = self.columns_by_name.get(self.pk_column)
        if spec is None:  # pragma: no cover - 레지스트리 정의 오류 방지용 가드
            raise ValueError(f"pk_column '{self.pk_column}' not in columns of '{self.key}'")
        return spec

    def allows(self, op: Op) -> bool:
        return op in self.allowed_ops


# ---------------------------------------------------------------------------
# 화이트리스트 정의 (코드 SSOT, 런타임 불변)
# ---------------------------------------------------------------------------

_APP_SETTINGS = TableDescriptor(
    key="app_settings",
    label="앱 설정",
    model=AppSetting,
    pk_column="key",
    columns=(
        ColumnSpec("key", "str", required=True, editable=False, max_length=100),
        ColumnSpec("value", "json", required=True, editable=True),
        ColumnSpec("description", "str", required=False, editable=True),
        ColumnSpec("updated_by", "uuid", editable=False),
        ColumnSpec("updated_at", "datetime", editable=False),
    ),
    allowed_ops=frozenset({"read", "create", "update", "delete"}),
)

_ROI_STANDARDS = TableDescriptor(
    key="roi_standards",
    label="ROI 표준 파라미터",
    model=RoiStandard,
    pk_column="id",
    columns=(
        ColumnSpec("id", "uuid", required=False, editable=False),
        ColumnSpec(
            "category",
            "enum",
            required=True,
            editable=True,
            enum=("role_rate", "solution_effort", "complexity_multiplier"),
        ),
        ColumnSpec("key", "str", required=True, editable=True, max_length=64),
        ColumnSpec("label", "str", required=True, editable=True, max_length=100),
        ColumnSpec("description", "str", required=False, editable=True),
        ColumnSpec("value_numeric", "float", required=False, editable=True),
        ColumnSpec("value_json", "json", required=False, editable=True),
        ColumnSpec("unit", "str", required=True, editable=True, max_length=32),
        ColumnSpec("display_order", "int", required=False, editable=True),
        ColumnSpec("is_active", "bool", required=False, editable=True),
        ColumnSpec("updated_by", "uuid", editable=False),
        ColumnSpec("created_at", "datetime", editable=False),
        ColumnSpec("updated_at", "datetime", editable=False),
    ),
    allowed_ops=frozenset({"read", "create", "update", "delete"}),
)

# presets 는 카탈로그 시드성 데이터 → read/update 만 허용(create/delete 금지, allowed_ops 강제).
_PRESETS = TableDescriptor(
    key="presets",
    label="솔루션 프리셋",
    model=Preset,
    pk_column="id",
    columns=(
        ColumnSpec("id", "uuid", required=False, editable=False),
        ColumnSpec("name", "str", required=True, editable=True, max_length=200),
        ColumnSpec("slug", "str", required=True, editable=True, max_length=200),
        ColumnSpec(
            "maturity_level",
            "enum",
            required=True,
            editable=True,
            enum=("starter", "intermediate", "advanced"),
        ),
        ColumnSpec("solution_types", "json", required=False, editable=True),
        ColumnSpec("default_agents", "json", required=False, editable=True),
        ColumnSpec("default_skills", "json", required=False, editable=True),
        ColumnSpec("default_pipelines", "json", required=False, editable=True),
        ColumnSpec("description", "str", required=False, editable=True),
        # is_system 은 시스템 시드 플래그 — 편집 금지(보호).
        ColumnSpec("is_system", "bool", editable=False),
        ColumnSpec("is_active", "bool", required=False, editable=True),
        ColumnSpec("created_at", "datetime", editable=False),
        ColumnSpec("updated_at", "datetime", editable=False),
    ),
    allowed_ops=frozenset({"read", "update"}),
)


REGISTRY: MappingProxyType[str, TableDescriptor] = MappingProxyType(
    {d.key: d for d in (_APP_SETTINGS, _ROI_STANDARDS, _PRESETS)}
)


def get_descriptor(table_key: str) -> TableDescriptor | None:
    """화이트리스트 테이블 디스크립터 조회. 미등재 → None(호출처에서 404 은닉)."""
    return REGISTRY.get(table_key)
