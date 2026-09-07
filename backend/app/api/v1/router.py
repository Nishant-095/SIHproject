from fastapi import APIRouter

from app.api.v1.collection_runs import router as collection_runs_router
from app.api.v1.exports import router as exports_router
from app.api.v1.historical import router as historical_router
from app.api.v1.index import router as index_router
from app.api.v1.observations import router as observations_router
from app.api.v1.quality import router as quality_router
from app.api.v1.routes import router as routes_router
from app.api.v1.source_health import admin_router as source_admin_router
from app.api.v1.source_health import router as source_health_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(routes_router)
api_router.include_router(observations_router)
api_router.include_router(collection_runs_router)
api_router.include_router(source_health_router)
api_router.include_router(source_admin_router)
api_router.include_router(index_router)
api_router.include_router(quality_router)
api_router.include_router(exports_router)
api_router.include_router(historical_router)
