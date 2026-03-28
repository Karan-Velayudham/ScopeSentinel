import os
import structlog
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.http import models
from openai import AsyncOpenAI
from .ingest import _collection_name, _get_qdrant_client, _get_llm_client, EMBEDDING_MODEL

logger = structlog.get_logger(__name__)

async def search_memory(query: str, org_id: str | None = None, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Search the tenant's vector memory for relevant context.
    """
    collection = _collection_name(org_id)
    client = _get_qdrant_client()
    llm = _get_llm_client()
    
    try:
        # Check if collection exists
        collections = client.get_collections().collections
        if not any(c.name == collection for c in collections):
            return []

        # Embed query
        res = await llm.embeddings.create(input=[query], model=EMBEDDING_MODEL)
        vector = res.data[0].embedding
        
        # Search Qdrant
        hits = client.search(
            collection_name=collection,
            query_vector=vector,
            limit=limit,
            with_payload=True
        )
        
        results = []
        for hit in hits:
            results.append({
                "content": hit.payload.get("content"),
                "path": hit.payload.get("path"),
                "score": hit.score
            })
        
        return results
    except Exception as e:
        logger.error("knowledge.search_failed", query=query, error=str(e))
        return []
