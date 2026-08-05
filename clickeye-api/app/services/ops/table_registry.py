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
- `creatable` : create(POST) payload 로 설정 가능한 컬럼(SSOT). 자동생성 PK(id)·
                created_at/updated_at/updated_by·보호 플래그(is_system) 는 False.
                사용자 제공 natural PK(app_settings.key) 는 editable=False 여도 True.
                프론트 생성 폼은 이 플래그로 전송 컬럼을 결정한다.
- update 시 설정 가능한 컬럼 = `editable` 인 컬럼. 그 외 컬럼을 payload 에 담으면 거부.
- `sensitive` : 조회(list/get) 및 감사 로그에서 값을 마스킹(***). 설정성 3개 테이블엔 민감
                컬럼이 없으나, 마스킹 경로는 제네릭하게 지원한다.

딜리버리 데이터 테이블(projects·intake_requests·pipeline_run_events·llm_usage_ledger)은
운영자가 "프로젝트를 구현하면서 발생한 데이터"를 진단·관측하기 위한 **읽기 전용** 등재다
(`allowed_ops={"read"}`, 전 컬럼 editable=False·creatable=False). 원장을 편집·삭제하면
안 되므로 create/update/delete 를 열지 않는다. 민감 테이블(users·*_credentials·RBAC·
managed_env_vars·central_contracts)은 여전히 미등재이며, 이 테이블들의 민감 컬럼(예:
setup_token_hash·requirements_text)도 등재에서 제외한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal

from app.database import Base
from app.models.app_setting import AppSetting
from app.models.intake import IntakeRequest
from app.models.llm_usage_ledger import LlmUsageLedger
from app.models.pipeline_run_event import PipelineRunEvent
from app.models.preset import Preset
from app.models.project import Project
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
    # create(POST) payload 에서 설정 가능한 컬럼인지 (SSOT). 자동생성 PK(id)·
    # created_at/updated_at/updated_by·보호 플래그(is_system) 는 False. 사용자 제공
    # natural PK(app_settings.key) 는 editable=False 여도 creatable=True.
    # 기본 True — editable/required 컬럼은 모두 create 가능하므로 자동/불변 컬럼에만
    # 명시적으로 False 를 지정한다.
    creatable: bool = True
    sensitive: bool = False
    max_length: int | None = None
    enum: tuple[str, ...] | None = None


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
        # key 는 사용자 제공 natural PK — editable=False 이나 create 시 반드시 제공(creatable).
        ColumnSpec("key", "str", required=True, editable=False, max_length=100),
        ColumnSpec("value", "json", required=True, editable=True),
        ColumnSpec("description", "str", required=False, editable=True),
        ColumnSpec("updated_by", "uuid", editable=False, creatable=False),
        ColumnSpec("updated_at", "datetime", editable=False, creatable=False),
    ),
    allowed_ops=frozenset({"read", "create", "update", "delete"}),
)

_ROI_STANDARDS = TableDescriptor(
    key="roi_standards",
    label="ROI 표준 파라미터",
    model=RoiStandard,
    pk_column="id",
    columns=(
        # id 는 서버 자동생성 PK — create payload 로 받지 않음(creatable=False).
        ColumnSpec("id", "uuid", required=False, editable=False, creatable=False),
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
        ColumnSpec("updated_by", "uuid", editable=False, creatable=False),
        ColumnSpec("created_at", "datetime", editable=False, creatable=False),
        ColumnSpec("updated_at", "datetime", editable=False, creatable=False),
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
        # id 는 서버 자동생성 PK — create 미지원 테이블이지만 일관성 위해 creatable=False.
        ColumnSpec("id", "uuid", required=False, editable=False, creatable=False),
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
        # is_system 은 시스템 시드 플래그 — 편집/생성 금지(보호).
        ColumnSpec("is_system", "bool", editable=False, creatable=False),
        ColumnSpec("is_active", "bool", required=False, editable=True),
        ColumnSpec("created_at", "datetime", editable=False, creatable=False),
        ColumnSpec("updated_at", "datetime", editable=False, creatable=False),
    ),
    allowed_ops=frozenset({"read", "update"}),
)


# ---------------------------------------------------------------------------
# 딜리버리 데이터 테이블 (읽기 전용 — 운영자 진단/관측용, CE-376)
# ---------------------------------------------------------------------------
# 원장/이력 테이블은 편집·삭제하면 안 된다. 아래 4개는 allowed_ops={"read"} 로만 열고,
# 전 컬럼을 editable=False·creatable=False 로 고정한다. 이 헬퍼가 그 규약을 강제한다.


def _ro(
    name: str,
    type: ColumnType,
    *,
    sensitive: bool = False,
    enum: tuple[str, ...] | None = None,
) -> ColumnSpec:
    """읽기 전용 컬럼 스펙(편집·생성 금지)."""
    return ColumnSpec(name, type, editable=False, creatable=False, sensitive=sensitive, enum=enum)


# projects — 딜리버리 프로젝트 식별·상태·상관축. settings JSONB 는 설정 blob 이라 목록
# 가독성을 위해 제외, requirements_text·setup_token_hash 는 고객 원문/토큰이라 제외.
_PROJECTS = TableDescriptor(
    key="projects",
    label="프로젝트",
    model=Project,
    pk_column="id",
    columns=(
        _ro("id", "uuid"),
        _ro("name", "str"),
        _ro("status", "str"),
        _ro("project_type", "str"),
        _ro("bootstrap_status", "str"),
        _ro("organization_id", "uuid"),
        _ro("created_at", "datetime"),
        _ro("updated_at", "datetime"),
    ),
    allowed_ops=frozenset({"read"}),
)

# intake_requests — 외부 요구사항 접수 원장. payload·normalized_text·refined_text 는
# 고객 요구사항 원문이지만 운영자가 내용을 봐야 진단이 되므로 마스킹하지 않는다(팀리드 판단).
# service_key_id 는 FK(값은 해시가 아님), callback_url 은 외부 엔드포인트라 등재 가능.
_INTAKE_REQUESTS = TableDescriptor(
    key="intake_requests",
    label="인테이크 요청",
    model=IntakeRequest,
    pk_column="id",
    columns=(
        _ro("id", "uuid"),
        _ro("service_key_id", "uuid"),
        _ro("input_type", "str"),
        _ro("title", "str"),
        _ro("status", "str"),
        _ro("refine_status", "str"),
        _ro("tickets_status", "str"),
        _ro("normalized_text", "str"),
        _ro("refined_text", "str"),
        _ro("payload", "json"),
        _ro("callback_url", "str"),
        _ro("project_id", "uuid"),
        _ro("created_at", "datetime"),
        _ro("updated_at", "datetime"),
    ),
    allowed_ops=frozenset({"read"}),
)

# pipeline_run_events — 파이프라인 단계 이벤트 이력. data JSONB 는 단계 결과(duration/
# outcome/verdict 등) 원형이라 진단에 유용. 토큰은 이 테이블이 갖지 않는다(llm_usage_ledger).
_PIPELINE_RUN_EVENTS = TableDescriptor(
    key="pipeline_run_events",
    label="파이프라인 실행 이벤트",
    model=PipelineRunEvent,
    pk_column="id",
    columns=(
        _ro("id", "uuid"),
        _ro("run_id", "str"),
        _ro("issue_key", "str"),
        _ro("event", "str"),
        _ro("project_id", "uuid"),
        _ro("workspace_key", "str"),
        _ro("data", "json"),
        _ro("occurred_at", "datetime"),
        _ro("created_at", "datetime"),
    ),
    allowed_ops=frozenset({"read"}),
)

# llm_usage_ledger — 토큰/비용 원장. project_id·task_id·seat_id·model 축과 토큰/비용 수치만
# 등재한다. meta JSONB 는 세션 정보를 담을 수 있어 제외(관측에 불필요), session_id(멱등 키)도
# 제외. seat_id 는 시트 FK(값은 크레덴셜이 아닌 UUID) — 계정별 소비 모니터링 축(D-8).
_LLM_USAGE_LEDGER = TableDescriptor(
    key="llm_usage_ledger",
    label="LLM 사용량 원장",
    model=LlmUsageLedger,
    pk_column="id",
    columns=(
        _ro("id", "uuid"),
        _ro("created_at", "datetime"),
        _ro("project_id", "uuid"),
        _ro("task_id", "str"),
        _ro("seat_id", "uuid"),
        _ro("provider", "str"),
        _ro("key_source", "str"),
        _ro("model", "str"),
        _ro("request_kind", "str"),
        _ro("input_tokens", "int"),
        _ro("output_tokens", "int"),
        _ro("cost", "float"),
        _ro("status", "str"),
    ),
    allowed_ops=frozenset({"read"}),
)


REGISTRY: MappingProxyType[str, TableDescriptor] = MappingProxyType(
    {
        d.key: d
        for d in (
            _APP_SETTINGS,
            _ROI_STANDARDS,
            _PRESETS,
            _PROJECTS,
            _INTAKE_REQUESTS,
            _PIPELINE_RUN_EVENTS,
            _LLM_USAGE_LEDGER,
        )
    }
)


def get_descriptor(table_key: str) -> TableDescriptor | None:
    """화이트리스트 테이블 디스크립터 조회. 미등재 → None(호출처에서 404 은닉)."""
    return REGISTRY.get(table_key)
