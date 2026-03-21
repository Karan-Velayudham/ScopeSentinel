import os
import asyncio
import structlog
from pathlib import Path
from qdrant_client import QdrantClient
from qdrant_client.http import models
from openai import AsyncOpenAI

logger = structlog.get_logger(__name__)

COLLECTION_NAME = "codebase"
EMBEDDING_MODEL = "text-embedding-3-small"

def _get_qdrant_client():
    host = os.environ.get("QDRANT_HOST", "qdrant")
    port = int(os.environ.get("QDRANT_PORT", "6333"))
    return QdrantClient(host=host, port=port)

def _get_llm_client():
    api_key = os.environ.get("LITELLM_MASTER_KEY", "sk-1234")
    base_url = os.environ.get("LITELLM_URL", "http://litellm:4000")
    return AsyncOpenAI(api_key=api_key, base_url=base_url)

async def init_collection():
    client = _get_qdrant_client()
    collections = client.get_collections().collections
    exists = any(c.name == COLLECTION_NAME for c in collections)
    
    if not exists:
        logger.info("ingest.creating_collection", name=COLLECTION_NAME)
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(size=1536, distance=models.Distance.COSINE),
        )

async def ingest_file(file_path: Path, repo_id: str):
    """Chunk and index a single file."""
    client = _get_qdrant_client()
    llm = _get_llm_client()
    
    try:
        content = file_path.read_text(encoding="utf-8")
        if not content.strip():
            return

        # Simple chunking by line count for now
        lines = content.splitlines()
        chunks = []
        for i in range(0, len(lines), 50):
            chunk = "\n".join(lines[i:i+50])
            chunks.append(chunk)

        if not chunks:
            return

        # Embed chunks
        logger.info("ingest.embedding_file", path=str(file_path), chunks=len(chunks))
        res = await llm.embeddings.create(input=chunks, model=EMBEDDING_MODEL)
        
        points = []
        for i, emb in enumerate(res.data):
            points.append(models.PointStruct(
                id=str(Path(file_path).relative_to(Path.cwd())) + f"_{i}",
                vector=emb.embedding,
                payload={
                    "path": str(file_path),
                    "content": chunks[i],
                    "repo_id": repo_id
                }
            ))
        
        client.upsert(collection_name=COLLECTION_NAME, points=points)
    except Exception as e:
        logger.error("ingest.file_failed", path=str(file_path), error=str(e))

async def ingest_directory(directory: Path, repo_id: str):
    ignore_dirs = {".git", "__pycache__", "node_modules", "venv", ".venv", "dist", "build"}
    ignore_exts = {".pyc", ".pyo", ".pyd", ".so", ".dll", ".exe", ".bin", ".jpg", ".png", ".gif", ".pdf"}

    tasks = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for file in files:
            path = Path(root) / file
            if path.suffix in ignore_exts:
                continue
            tasks.append(ingest_file(path, repo_id))
    
    if tasks:
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    # Example usage: python ingest.py /app/workspace/REPO_ID REPO_ID
    import sys
    if len(sys.argv) < 3:
        print("Usage: python ingest.py <dir> <repo_id>")
        sys.exit(1)
    
    asyncio.run(init_collection())
    asyncio.run(ingest_directory(Path(sys.argv[1]), sys.argv[2]))
