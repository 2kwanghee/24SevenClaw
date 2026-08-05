"""모든 SQLAlchemy 모델을 여기서 import — Alembic autogenerate용."""

from app.models.agent_connection import AgentConnection  # noqa: F401
from app.models.app_setting import AppSetting  # noqa: F401
from app.models.artifact import Artifact, ArtifactEvent  # noqa: F401
from app.models.central_contract import (  # noqa: F401
    CentralContract,
    ContractAuditLog,
    CustomerContractOverride,
)
from app.models.delivery_event import DeliveryEvent  # noqa: F401
from app.models.delivery_profile import DeliveryProfile  # noqa: F401
from app.models.intake import IntakeRequest, IntakeServiceKey  # noqa: F401
from app.models.license import License  # noqa: F401
from app.models.llm_usage_ledger import LlmUsageLedger  # noqa: F401
from app.models.managed_env_var import ManagedEnvVar  # noqa: F401
from app.models.maturity_assessment import MaturityAssessment  # noqa: F401
from app.models.orchestrator import OrchestratorSession, PhaseEvent, SubTask  # noqa: F401
from app.models.organization import Organization  # noqa: F401
from app.models.pipeline_run_event import PipelineRunEvent  # noqa: F401
from app.models.pm_composition import PMComposition  # noqa: F401
from app.models.pm_metrics import PMMetrics  # noqa: F401
from app.models.pm_profile import PMProfile  # noqa: F401
from app.models.pm_rating import PMRating  # noqa: F401
from app.models.pm_recommendation_log import PMRecommendationLog  # noqa: F401
from app.models.preset import Preset  # noqa: F401
from app.models.project import Project  # noqa: F401
from app.models.project_config import ProjectConfig  # noqa: F401
from app.models.project_linear_credentials import ProjectLinearCredentials  # noqa: F401
from app.models.prototype_catalog import PrototypeCatalogEntry, PrototypeTag  # noqa: F401
from app.models.quality_gate import QualityCheck, QualityGateEvent, QualityGateRun  # noqa: F401
from app.models.rbac import OrganizationMembership, RoleAuditLog  # noqa: F401
from app.models.registry import Agent, MCPServer, Skill  # noqa: F401
from app.models.review_pipeline import ReviewEvent, ReviewRound  # noqa: F401
from app.models.roi_standard import RoiStandard  # noqa: F401
from app.models.seat_quota_snapshot import SeatQuotaSnapshot  # noqa: F401
from app.models.ticket import Ticket, TicketEvent  # noqa: F401
from app.models.user import User  # noqa: F401

# llm_usage_ledger.seat_id 가 이 테이블을 FK 로 참조하는데 등록이 빠져 있었다 —
# 없으면 alembic autogenerate 가 NoReferencedTableError 로 죽는다(CE-363 작업 중 발견).
# 등록 누락 전수 점검은 CE-370.
from app.models.user_anthropic_credentials import (  # noqa: F401
    UserAnthropicCredentials,
)
from app.models.user_linear_credentials import UserLinearCredentials  # noqa: F401

__all__ = [
    "Agent",
    "AppSetting",
    "PrototypeCatalogEntry",
    "PrototypeTag",
    "AgentConnection",
    "Artifact",
    "ArtifactEvent",
    "CentralContract",
    "ContractAuditLog",
    "CustomerContractOverride",
    "DeliveryEvent",
    "DeliveryProfile",
    "IntakeRequest",
    "IntakeServiceKey",
    "License",
    "LlmUsageLedger",
    "PipelineRunEvent",
    "UserAnthropicCredentials",
    "ManagedEnvVar",
    "MaturityAssessment",
    "MCPServer",
    "OrchestratorSession",
    "Organization",
    "OrganizationMembership",
    "PMComposition",
    "PMMetrics",
    "PMProfile",
    "PMRating",
    "PMRecommendationLog",
    "PhaseEvent",
    "Preset",
    "Project",
    "ProjectConfig",
    "ProjectLinearCredentials",
    "QualityCheck",
    "QualityGateEvent",
    "QualityGateRun",
    "ReviewEvent",
    "ReviewRound",
    "RoiStandard",
    "RoleAuditLog",
    "SeatQuotaSnapshot",
    "Skill",
    "SubTask",
    "Ticket",
    "TicketEvent",
    "User",
    "UserLinearCredentials",
]
