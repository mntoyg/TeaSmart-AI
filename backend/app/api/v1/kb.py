"""Serve the knowledge base so the PWA can cache it for offline use."""

from fastapi import APIRouter

from app.core.config import get_settings
from app.services.expert import DiseaseRecord, load_kb

router = APIRouter(prefix="/api/v1", tags=["knowledge-base"])


@router.get("/kb", response_model=list[DiseaseRecord])
def read_kb() -> list[DiseaseRecord]:
    kb = load_kb(get_settings().kb_path)
    return sorted(kb.values(), key=lambda record: record.class_id)
