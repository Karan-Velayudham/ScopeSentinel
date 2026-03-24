import os
import json
import io
import structlog
from minio import Minio

logger = structlog.get_logger(__name__)

def get_minio_client() -> Minio:
    url = os.getenv("MINIO_URL", "minio:9000")
    if url.startswith("http://"):
        url = url[7:]
    elif url.startswith("https://"):
        url = url[8:]
    
    access_key = os.getenv("MINIO_ACCESS_KEY", "admin")
    secret_key = os.getenv("MINIO_SECRET_KEY", "adminpassword")
    
    return Minio(
        url,
        access_key=access_key,
        secret_key=secret_key,
        secure=False
    )

def save_step_io_sync(run_id: str, step_name: str, payload: dict, is_input: bool):
    """Saves input or output payload to MinIO synchronously"""
    try:
        client = get_minio_client()
        bucket_name = "step-io-capture"
        
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)

        file_name = f"{run_id}/{step_name}_{'input' if is_input else 'output'}.json"
        data = json.dumps(payload, indent=2).encode('utf-8')
        
        client.put_object(
            bucket_name,
            file_name,
            io.BytesIO(data),
            length=len(data),
            content_type="application/json"
        )
        logger.info("minio.io_saved", run_id=run_id, step_name=step_name, is_input=is_input)
    except Exception as e:
        logger.warning("minio.io_save_failed", error=str(e), run_id=run_id)
