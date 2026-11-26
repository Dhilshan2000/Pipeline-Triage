import logging
from typing import Optional
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from app.config import settings

logger = logging.getLogger(__name__)

COLLECTION_NAME = "knowledge_base"
VECTOR_DIM = 384

def get_qdrant_client() -> Optional[QdrantClient]:
    try:
        client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
            timeout=5.0
        )
        return client
    except Exception as e:
        logger.warning(f"Could not connect to Qdrant at {settings.QDRANT_URL}: {e}")
        return None

def init_qdrant_collection():
    """Initializes Qdrant collection for hybrid RAG search."""
    client = get_qdrant_client()
    if not client:
        return

    try:
        collections = client.get_collections().collections
        exists = any(c.name == COLLECTION_NAME for c in collections)
        if not exists:
            logger.info(f"Creating Qdrant collection: {COLLECTION_NAME}")
            client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=qmodels.VectorParams(
                    size=VECTOR_DIM,
                    distance=qmodels.Distance.COSINE
                )
            )
    except Exception as e:
        logger.warning(f"Failed to initialize Qdrant collection: {e}")
