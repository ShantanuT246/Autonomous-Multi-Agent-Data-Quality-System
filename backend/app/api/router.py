from fastapi import APIRouter
from backend.app.api.datasets import router as datasets_router
from backend.app.api.runs import router as runs_router

api_router = APIRouter(prefix="/api")
api_router.include_router(datasets_router)
api_router.include_router(runs_router)
