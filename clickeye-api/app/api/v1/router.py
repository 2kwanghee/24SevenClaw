from fastapi import APIRouter

from app.api.v1.admin_recommendations import router as admin_recommendations_router
from app.api.v1.anthropic_credentials import router as anthropic_credentials_router
from app.api.v1.app_settings_admin import router as app_settings_admin_router
from app.api.v1.artifacts import router as artifacts_router
from app.api.v1.auth import router as auth_router
from app.api.v1.catalog import router as catalog_router
from app.api.v1.contracts import project_contracts_router
from app.api.v1.contracts import router as contracts_router
from app.api.v1.contracts import sync_router as contracts_sync_router
from app.api.v1.control_tower import router as control_tower_router
from app.api.v1.github_app import router as github_app_router
from app.api.v1.health import router as health_router
from app.api.v1.integrations import router as integrations_router
from app.api.v1.linear_credentials import router as linear_credentials_router
from app.api.v1.maturity import router as maturity_router
from app.api.v1.modernize import router as modernize_router
from app.api.v1.orchestrator import router as orchestrator_router
from app.api.v1.organizations import router as organizations_router
from app.api.v1.pm_profiles import router as pm_profiles_router
from app.api.v1.presets import router as presets_router
from app.api.v1.projects import router as projects_router
from app.api.v1.prototype_catalog import router as prototype_catalog_router
from app.api.v1.prototype_catalog_admin import router as prototype_catalog_admin_router
from app.api.v1.prototype_sessions import router as prototype_sessions_router
from app.api.v1.quality_gate import router as quality_gate_router
from app.api.v1.rbac import router as rbac_router
from app.api.v1.recommend import router as recommend_router
from app.api.v1.registry_admin import router as registry_admin_router
from app.api.v1.reports import router as reports_router
from app.api.v1.review_pipeline import router as review_pipeline_router
from app.api.v1.roi import router as roi_router
from app.api.v1.roi_admin import router as roi_admin_router
from app.api.v1.setup_bootstrap import router as setup_bootstrap_router
from app.api.v1.system_features import router as system_features_router
from app.api.v1.wizard_preview import router as wizard_preview_router

api_v1_router = APIRouter()
api_v1_router.include_router(admin_recommendations_router)
api_v1_router.include_router(app_settings_admin_router)
api_v1_router.include_router(registry_admin_router)
api_v1_router.include_router(prototype_catalog_admin_router)
api_v1_router.include_router(prototype_catalog_router)
api_v1_router.include_router(health_router, tags=["health"])
api_v1_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_v1_router.include_router(catalog_router)
api_v1_router.include_router(projects_router)
api_v1_router.include_router(artifacts_router)
api_v1_router.include_router(orchestrator_router)
api_v1_router.include_router(organizations_router)
api_v1_router.include_router(maturity_router)
api_v1_router.include_router(presets_router)
api_v1_router.include_router(rbac_router)
api_v1_router.include_router(quality_gate_router)
api_v1_router.include_router(recommend_router)
api_v1_router.include_router(reports_router)
api_v1_router.include_router(review_pipeline_router)
api_v1_router.include_router(prototype_sessions_router)
api_v1_router.include_router(pm_profiles_router)
api_v1_router.include_router(contracts_router)
api_v1_router.include_router(project_contracts_router)
api_v1_router.include_router(contracts_sync_router)
api_v1_router.include_router(anthropic_credentials_router)
api_v1_router.include_router(linear_credentials_router)
api_v1_router.include_router(integrations_router)
api_v1_router.include_router(github_app_router)
api_v1_router.include_router(modernize_router)
api_v1_router.include_router(control_tower_router)
api_v1_router.include_router(roi_router)
api_v1_router.include_router(roi_admin_router)
api_v1_router.include_router(setup_bootstrap_router)
api_v1_router.include_router(system_features_router)
api_v1_router.include_router(wizard_preview_router)
