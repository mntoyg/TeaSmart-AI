"""Stage 6: the rule-based expert system.

The knowledge base is data, never code. It is read once, validated, and handed
out as immutable records; nothing mutates it at runtime.
"""

import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class UnknownClassError(KeyError):
    """Raised when a resolved class has no knowledge-base record."""


class DiseaseRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    class_id: int
    class_name: str
    disease_name_th: str
    pathogen: str
    symptoms: str
    immediate_action: str
    cultural_control: str
    chemical_treatment: str
    preventive_measures: str


@lru_cache
def load_kb(path: Path) -> dict[str, DiseaseRecord]:
    """Read and validate the knowledge base, keyed by class_name."""
    records = json.loads(Path(path).read_text(encoding="utf-8"))
    kb: dict[str, DiseaseRecord] = {}
    for raw in records:
        record = DiseaseRecord.model_validate(raw)
        if record.class_name in kb:
            raise KeyError(f"duplicate class_name in knowledge base: {record.class_name}")
        kb[record.class_name] = record
    return kb


def get_advice(class_name: str, kb: dict[str, DiseaseRecord]) -> DiseaseRecord:
    try:
        return kb[class_name]
    except KeyError as exc:
        raise UnknownClassError(class_name) from exc
