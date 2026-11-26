from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db_indexes
from app.config import settings
from app.rag.qdrant_client import init_qdrant_collection
from app.rag.knowledge_base import knowledge_base

# Import API Routers
from app.api.webhooks import router as webhooks_router
from app.api.auth import router as auth_router
from app.api.issues import router as issues_router
from app.api.analytics import router as analytics_router
from app.api.settings import router as settings_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB indexes
    try:
        await init_db_indexes()
    except Exception as e:
        print(f"Warning: Could not connect to MongoDB on startup: {e}")

    # Initialize Qdrant Collection & Seed Knowledge Chunks
    try:
        init_qdrant_collection()
        knowledge_base.seed_knowledge()
    except Exception as e:
        print(f"Warning: Could not initialize Qdrant knowledge base: {e}")

    yield

app = FastAPI(
    title="Pipeline Triage API",
    version="1.0.0",
    description="Automated CI/CD build failure diagnosis, routing, and reporting backend.",
    lifespan=lifespan,
)

# CORS middleware for Next.js web app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "pipeline-triage-backend",
        "llm_provider": settings.LLM_PROVIDER,
        "llm_model": settings.LLM_MODEL,
        "environment": settings.ENVIRONMENT
    }

# Mount routers
app.include_router(webhooks_router)
app.include_router(auth_router)
app.include_router(issues_router)
app.include_router(analytics_router)
app.include_router(settings_router)
