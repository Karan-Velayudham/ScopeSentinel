from fastapi import APIRouter
from pydantic import BaseModel
from typing import List

router = APIRouter(prefix="/api/models", tags=["models"])

class ModelOption(BaseModel):
    value: str
    label: str

@router.get("/", response_model=List[ModelOption])
async def get_supported_models():
    """Return a list of supported models for agents and workflows."""
    return [
        {"value": "claude-sonnet-4-6", "label": "Claude Sonnet 4.6"},
        {"value": "claude-opus-4-6", "label": "Claude Opus 4.6"},
        {"value": "gpt-4o", "label": "GPT-4o"},
        {"value": "gemini-3.1-pro", "label": "Gemini 3.1 Pro"},
    ]
