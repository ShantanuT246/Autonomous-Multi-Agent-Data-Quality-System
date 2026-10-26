import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import MongoClient
from pymongo.database import Database
from backend.app.config import settings

logger = logging.getLogger(__name__)

_async_client: Optional[AsyncIOMotorClient] = None
_sync_client: Optional[MongoClient] = None


def get_sync_client() -> MongoClient:
    global _sync_client
    if _sync_client is None:
        _sync_client = MongoClient(
            settings.MONGODB_URI,
            serverSelectionTimeoutMS=3000,
            connectTimeoutMS=3000,
        )
    return _sync_client


def get_sync_db() -> Database:
    client = get_sync_client()
    return client[settings.MONGODB_DB_NAME]


def get_async_client() -> AsyncIOMotorClient:
    global _async_client
    if _async_client is None:
        _async_client = AsyncIOMotorClient(
            settings.MONGODB_URI,
            serverSelectionTimeoutMS=3000,
            connectTimeoutMS=3000,
        )
    return _async_client


def get_async_db() -> AsyncIOMotorDatabase:
    client = get_async_client()
    return client[settings.MONGODB_DB_NAME]


def init_db_indexes():
    """Create indexes for performance and query optimization on startup."""
    try:
        db = get_sync_db()
        db.datasets.create_index("dataset_id", unique=True)
        db.runs.create_index("run_id", unique=True)
        db.runs.create_index("created_at")
        db.agent_states.create_index([("run_id", 1), ("step_order", 1)])
        db.cleaning_logs.create_index("run_id")
        db.llm_calls.create_index("run_id")
        db.reports.create_index("run_id", unique=True)
        logger.info("MongoDB indexes verified/created successfully.")
    except Exception as e:
        logger.warning(f"Could not connect or initialize MongoDB indexes: {e}")


def close_db_connections():
    global _async_client, _sync_client
    if _async_client is not None:
        _async_client.close()
        _async_client = None
    if _sync_client is not None:
        _sync_client.close()
        _sync_client = None
    logger.info("MongoDB client connections closed.")
