from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db_indexes
from app.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure indexes
    try:
        await init_db_indexes()
    except Exception as e:
        print(f"Warning: Could not connect to DB on startup to initialize indexes: {e}")
    yield
    # Shutdown

app = FastAPI(
    title="Pipeline Triage API",
    version="1.0.0",
    description="Automated CI/CD build failure diagnosis, routing, and reporting backend.",
    lifespan=lifespan,
)

# CORS middleware
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
        "environment": settings.ENVIRONMENT
    }

# Additional routers will be mounted here as features are assembled (api/webhooks, api/issues, api/analytics, etc.)
