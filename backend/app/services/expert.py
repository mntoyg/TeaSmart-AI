"""Stage 6: the rule-based expert system.

The knowledge base is data, never code. It is read once at startup, validated,
and handed out as an immutable mapping of immutable records: one mapping is
shared process-wide, and the PWA caches whatever this serves for offline use, so
a single stray write would poison the advice a worker reads until restart.

Records are keyed by their canonical class name (the snake_case name stage 3
emits), not by the English display name, because stage 6 is a pure lookup from
the class the classifier resolved.
"""

import json
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType

from pydantic import BaseModel, ConfigDict


class UnknownClassError(KeyError):
    """Raised when a resolved class has no knowledge-base record."""


class DiseaseRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    class_id: int
    canonical: str
    class_name: str
    disease_name_th: str
    pathogen: str
    symptoms: str
    immediate_action: str
    cultural_control: str
    chemical_treatment: str
    preventive_measures: str


@lru_cache
def load_kb(path: Path) -> Mapping[str, DiseaseRecord]:
    """Read and validate the knowledge base, keyed by canonical class name."""
    records = json.loads(Path(path).read_text(encoding="utf-8"))
    kb: dict[str, DiseaseRecord] = {}
    for raw in records:
        record = DiseaseRecord.model_validate(raw)
        if record.canonical in kb:
            raise KeyError(f"duplicate canonical class in knowledge base: {record.canonical}")
        kb[record.canonical] = record
    return MappingProxyType(kb)


def get_advice(canonical: str, kb: Mapping[str, DiseaseRecord]) -> DiseaseRecord:
    try:
        return kb[canonical]
    except KeyError as exc:
        raise UnknownClassError(canonical) from exc
