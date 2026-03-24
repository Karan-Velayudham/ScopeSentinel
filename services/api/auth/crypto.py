import os
from cryptography.fernet import Fernet
import structlog

logger = structlog.get_logger(__name__)

def get_fernet() -> Fernet:
    key_str = os.environ.get("OAUTH_ENCRYPTION_KEY")
    if not key_str:
        # Default symmetric key for local development to avoid missing env var issues.
        # MUST be overridden in production securely.
        key_str = "xK2f5h-QW_8UjL1M4y-7nT3vP0b_rE5s9tO-aZ1cKwE="
    return Fernet(key_str.encode())

def encrypt_token(token: str) -> str:
    if not token:
        return ""
    try:
        f = get_fernet()
        return f.encrypt(token.encode()).decode()
    except Exception as e:
        logger.error("crypto.encrypt_failed", error=str(e))
        raise

def decrypt_token(encrypted_token: str) -> str:
    if not encrypted_token:
        return ""
    try:
        f = get_fernet()
        return f.decrypt(encrypted_token.encode()).decode()
    except Exception as e:
        logger.error("crypto.decrypt_failed", error=str(e))
        raise
