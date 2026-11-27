import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import MongoClient
import pymongo
from passlib.hash import argon2
from app.config import settings
from app.security.crypto import encrypt_credential

logger = logging.getLogger(__name__)

async_client: AsyncIOMotorClient | None = None
async_db: AsyncIOMotorDatabase | None = None

def get_async_db() -> AsyncIOMotorDatabase:
    global async_client, async_db
    if async_client is None:
        async_client = AsyncIOMotorClient(settings.MONGODB_URI)
        async_db = async_client[settings.DATABASE_NAME]
    return async_db

def get_sync_db():
    client = MongoClient(settings.MONGODB_URI)
    return client[settings.DATABASE_NAME]

async def seed_initial_data():
    """Seeds default users, projects, adapters, and connectors if empty."""
    db = get_async_db()
    
    # 1. Seed Users
    dhilshan_email = "dhilshan@example.com"
    user_count = await db.users.count_documents({})
    if user_count == 0:
        logger.info("Seeding initial users and roles...")
        users = [
            {
                "name": "System Administrator",
                "email": "admin@example.com",
                "password_hash": argon2.hash("admin123"),
                "role": "admin",
                "git_emails": ["admin@example.com"]
            },
            {
                "name": "Ariwalagan Dhilshan",
                "email": dhilshan_email,
                "password_hash": argon2.hash("developer123"),
                "role": "developer",
                "git_emails": [dhilshan_email, "dhilshan2000@users.noreply.github.com"]
            },
            {
                "name": "DevOps On-Call Lead",
                "email": "devops-oncall@example.com",
                "password_hash": argon2.hash("devops123"),
                "role": "devops",
                "git_emails": ["devops-oncall@example.com", "infra@example.com"]
            },
            {
                "name": "Security Lead",
                "email": "security-lead@example.com",
                "password_hash": argon2.hash("security123"),
                "role": "security",
                "git_emails": ["security-lead@example.com", "secops@example.com"]
            }
        ]
        await db.users.insert_many(users)

    # 2. Seed Projects
    proj_count = await db.projects.count_documents({})
    if proj_count == 0:
        logger.info("Seeding initial sandbox projects...")
        projects = [
            {
                "name": "sandbox-gitlab",
                "platform": "gitlab",
                "repo_id": "Dhilshan2000/sandbox-gitlab",
                "default_owner": "developer@example.com",
                "adapter": "gitlab",
                "connectors": ["kanvaro", "email"]
            },
            {
                "name": "sandbox-github",
                "platform": "github",
                "repo_id": "Dhilshan2000/sandbox-github",
                "default_owner": dhilshan_email,
                "adapter": "github",
                "connectors": ["kanvaro", "email"]
            }
        ]
        await db.projects.insert_many(projects)

    # 3. Seed Adapter Settings
    adapter_count = await db.adapter_settings.count_documents({})
    if adapter_count == 0:
        logger.info("Seeding default adapter configurations...")
        gitlab_token = getattr(settings, "GITLAB_API_TOKEN", None)
        github_token = getattr(settings, "GITHUB_API_TOKEN", None)
        adapters = [
            {
                "key": "gitlab",
                "enabled": True,
                "config": {"api_url": "https://gitlab.com/api/v4", "webhook_secret": settings.GITLAB_WEBHOOK_SECRET},
                "encrypted_credentials": {"access_token": encrypt_credential(gitlab_token) if gitlab_token else ""}
            },
            {
                "key": "github",
                "enabled": True,
                "config": {"api_url": "https://api.github.com", "webhook_secret": settings.GITHUB_WEBHOOK_SECRET},
                "encrypted_credentials": {"access_token": encrypt_credential(github_token) if github_token else ""}
            }
        ]
        await db.adapter_settings.insert_many(adapters)

    # 4. Seed Connector Settings
    connector_count = await db.connector_settings.count_documents({})
    if connector_count == 0:
        logger.info("Seeding default connector configurations...")
        connectors = [
            {
                "type": "mcp",
                "name": "kanvaro",
                "enabled": True,
                "config": {
                    "server_url": settings.KANVARO_MCP_URL,
                    "bot_user": settings.KANVARO_BOT_USER,
                    "bot_password": settings.KANVARO_BOT_PASSWORD
                }
            },
            {
                "type": "email",
                "name": "mailpit",
                "enabled": True,
                "config": {
                    "smtp_host": settings.SMTP_HOST,
                    "smtp_port": settings.SMTP_PORT,
                    "from_email": settings.SMTP_FROM_EMAIL
                }
            },
            {
                "type": "rest",
                "name": "slack",
                "enabled": False,
                "config": {
                    "webhook_url": "https://hooks.slack.com/services/mock/token/xyz"
                }
            }
        ]
        await db.connector_settings.insert_many(connectors)

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
    await seed_initial_data()
