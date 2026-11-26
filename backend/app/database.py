import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import MongoClient
import pymongo
from app.config import settings

logger = logging.getLogger(__name__)

# Async client for FastAPI API endpoints
async_client: AsyncIOMotorClient | None = None
async_db: AsyncIOMotorDatabase | None = None

def get_async_db() -> AsyncIOMotorDatabase:
    global async_client, async_db
    if async_client is None:
        async_client = AsyncIOMotorClient(settings.MONGODB_URI)
        async_db = async_client[settings.DATABASE_NAME]
    return async_db

# Sync client for background workers (RQ)
def get_sync_db():
    client = MongoClient(settings.MONGODB_URI)
    return client[settings.DATABASE_NAME]

async def init_db_indexes():
    """
    Ensures safe uniqueness constraints according to the architecture proposal:
    1. Unique index on failures.event_key
    2. Partial unique index on issues.fingerprint where is_open is true
    """
    db = get_async_db()
    logger.info("Initializing MongoDB indexes...")

    # Unique index on failures.event_key
    await db.failures.create_index(
        [("event_key", pymongo.ASCENDING)],
        unique=True,
        name="unique_failure_event_key"
    )

    # Partial unique index on issues.fingerprint where is_open is true
    await db.issues.create_index(
        [("fingerprint", pymongo.ASCENDING)],
        unique=True,
        partialFilterExpression={"is_open": True},
        name="unique_open_issue_fingerprint"
    )

    # General indexes for performance
    await db.issues.create_index([("assignee", pymongo.ASCENDING)])
    await db.issues.create_index([("status", pymongo.ASCENDING)])
    await db.issues.create_index([("category", pymongo.ASCENDING)])
    await db.run_stats.create_index([("project", pymongo.ASCENDING), ("finished_at", pymongo.DESCENDING)])
    await db.patterns.create_index([("signature", pymongo.ASCENDING)], unique=True)
    await db.users.create_index([("email", pymongo.ASCENDING)], unique=True)
    await db.users.create_index([("git_emails", pymongo.ASCENDING)])

    logger.info("MongoDB indexes successfully created.")
