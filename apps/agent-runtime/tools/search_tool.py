import os
import structlog
from qdrant_client import QdrantClient
from qdrant_client.http import models
from openai import AsyncOpenAI

logger = structlog.get_logger(__name__)

_DEFAULT_COLLECTION = "codebase"
EMBEDDING_MODEL = "text-embedding-3-small"


def _collection_name(org_id: str | None) -> str:
    if org_id:
        return f"org_{org_id}_knowledge"
    return _DEFAULT_COLLECTION

def _get_qdrant_client():
    host = os.environ.get("QDRANT_HOST", "qdrant")
    port = int(os.environ.get("QDRANT_PORT", "6333"))
    return QdrantClient(host=host, port=port)

def _get_llm_client():
    api_key = os.environ.get("LITELLM_MASTER_KEY", "sk-1234")
    base_url = os.environ.get("LITELLM_URL", "http://litellm:4000")
    return AsyncOpenAI(api_key=api_key, base_url=base_url)

async def search_codebase(query: str, repo_id: str = None, top_k: int = 5, org_id: str | None = None):
    """
    Perform semantic search over the indexed codebase.
    Uses the tenant-specific Qdrant collection when org_id is provided.
    """
    collection = _collection_name(org_id)
    client = _get_qdrant_client()
    llm = _get_llm_client()
    
    try:
        # Embed query
        res = await llm.embeddings.create(input=[query], model=EMBEDDING_MODEL)
        vector = res.data[0].embedding
        
        # Search Qdrant in the tenant-scoped collection
        search_result = client.search(
            collection_name=collection,
            query_vector=vector,
            query_filter=models.Filter(
                must=[models.FieldCondition(key="repo_id", match=models.MatchValue(value=repo_id))]
            ) if repo_id else None,
            limit=top_k
        )
        
        formatted_results = []
        for r in search_result:
            formatted_results.append(
                f"--- File: {r.payload.get('path')} ---\n{r.payload.get('content')}\n"
            )
        
        return "\n".join(formatted_results) if formatted_results else "No relevant code found."
    except Exception as e:
        logger.error("search.failed", query=query, error=str(e))
        return f"Search failed: {e}"
