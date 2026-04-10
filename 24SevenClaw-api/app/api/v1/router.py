from fastapi import APIRouter

from app.api.v1.artifacts import router as artifacts_router
from app.api.v1.auth import router as auth_router
from app.api.v1.catalog import router as catalog_router
from app.api.v1.health import router as health_router
from app.api.v1.organizations import router as organizations_router
from app.api.v1.projects import router as projects_router
from app.api.v1.recommend import router as recommend_router

api_v1_router = APIRouter()
api_v1_router.include_router(health_router, tags=["health"])
api_v1_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_v1_router.include_router(catalog_router)
api_v1_router.include_router(projects_router)
api_v1_router.include_router(artifacts_router)
api_v1_router.include_router(organizations_router)
api_v1_router.include_router(recommend_router)
