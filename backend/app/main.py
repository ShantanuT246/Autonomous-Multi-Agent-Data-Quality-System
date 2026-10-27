import os
import sys
from pathlib import Path

# Ensure project root is in sys.path regardless of execution directory
project_root = str(Path(__file__).resolve().parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api.router import api_router
from backend.app.config import settings
from backend.app.db.mongo import close_db_connections, init_db_indexes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("autonomous_data_quality")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize database collections and indexes
    logger.info("Initializing Autonomous Multi-Agent Data Quality System...")
    init_db_indexes()
    yield
    # Shutdown: clean up client connection pools
    logger.info("Shutting down database connections...")
    close_db_connections()


app = FastAPI(
    title="Autonomous Multi-Agent Data Quality API",
    description="Backend API for Autonomous Multi-Agent Data Quality and Cleaning System.",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for frontend integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API endpoints
app.include_router(api_router)


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "healthy", "environment": settings.ENVIRONMENT}


# Mount Single Page Application frontend
from fastapi.staticfiles import StaticFiles
from pathlib import Path

frontend_dir = Path("frontend")
if not frontend_dir.exists():
    frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"

if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)

