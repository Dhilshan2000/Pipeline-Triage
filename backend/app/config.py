from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    APP_SECRET_KEY: str = "dev_secret_key_change_in_production"
    FERNET_MASTER_KEY: str = "o41k56sYJg3i49Vb7B3m0XwF8YnZ1Q2w3E4r5T6y7U8="

    # Databases
    MONGODB_URI: str = "mongodb://root:example_password@mongo:27017/pipeline_triage?authSource=admin"
    DATABASE_NAME: str = "pipeline_triage"
    REDIS_URL: str = "redis://redis:6379/0"
    QDRANT_URL: str = "http://qdrant:6333"
    QDRANT_API_KEY: Optional[str] = None

    # Claude LLM Settings (Locked exclusively to Claude / Anthropic)
    LLM_PROVIDER: str = "anthropic"
    LLM_MODEL: str = "claude-sonnet-5"
    ANTHROPIC_API_KEY: Optional[str] = None
    LLM_TIMEOUT_SECONDS: int = 45

    # Embeddings & Reranker
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"
    RERANKER_MODEL: str = "BAAI/bge-reranker-base"

    # Tracing
    LANGFUSE_PUBLIC_KEY: Optional[str] = None
    LANGFUSE_SECRET_KEY: Optional[str] = None
    LANGFUSE_HOST: str = "https://cloud.langfuse.com"

    # SMTP / Mailpit
    SMTP_HOST: str = "mailpit"
    SMTP_PORT: int = 1025
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: str = "pipeline-triage@example.com"

    # External APIs
    SONARQUBE_URL: str = "http://host.docker.internal:9000"
    SONARQUBE_TRIAGE_BOT_TOKEN: Optional[str] = None
    GITLAB_WEBHOOK_SECRET: Optional[str] = "gitlab_shared_webhook_secret_123"
    GITHUB_WEBHOOK_SECRET: Optional[str] = "github_shared_webhook_secret_456"
    GITLAB_API_TOKEN: Optional[str] = None
    GITHUB_API_TOKEN: Optional[str] = None

    # Kanvaro Mock MCP Server
    KANVARO_MCP_URL: str = "http://mock-kanvaro:8080/sse"
    KANVARO_BOT_USER: str = "triage-bot"
    KANVARO_BOT_PASSWORD: str = "mock_kanvaro_secure_pass"

    # Web App URLs
    NEXT_PUBLIC_API_URL: str = "http://localhost:8000"
    NEXTAUTH_URL: str = "http://localhost:3000"

    model_config = {"env_file": ".env", "extra": "ignore"}

settings = Settings()
