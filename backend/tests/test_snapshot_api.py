"""The static snapshots must agree with the knowledge base in this repository.

`scripts/snapshot_api.py` freezes `GET /api/v1/config` and `GET /api/v1/kb`
into files, because the demo deployment is the frontend with no backend behind
it and both endpoints otherwise 404 - which stops the on-device model running
at all and leaves the result card with no Thai advice in it.

A snapshot is a copy, and a copy can go stale. The check that needs no network
is that it still agrees with `backend/app/kb/diseases.json`, which is the
source both the live endpoint and the snapshot derive from. If someone adds a
seventh disease and forgets to re-run the script, this says so.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "snapshot_api.py"
SNAPSHOT_DIR = REPO_ROOT / "frontend" / "public" / "api" / "v1"
KB_SOURCE = REPO_ROOT / "backend" / "app" / "kb" / "diseases.json"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("teasmart_snapshot_api", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None, SCRIPT_PATH
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def snapshot_api() -> ModuleType:
    return _load()


def _read(name: str):
    path = SNAPSHOT_DIR / name
    assert path.is_file(), (
        f"{path.relative_to(REPO_ROOT)} is missing. The built site serves it at "
        f"/api/v1/{name}; without it that request 404s on a static host. "
        "Regenerate with: python scripts/snapshot_api.py"
    )
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def config():
    return _read("config")


@pytest.fixture(scope="module")
def kb():
    return _read("kb")


@pytest.fixture(scope="module")
def kb_canonicals() -> set[str]:
    records = json.loads(KB_SOURCE.read_text(encoding="utf-8"))
    return {record["canonical"] for record in records}


def test_the_snapshots_pass_the_scripts_own_check(snapshot_api, config, kb) -> None:
    snapshot_api.check(config, kb)


def test_the_snapshot_kb_has_not_drifted_from_the_source(kb, kb_canonicals) -> None:
    assert {record["canonical"] for record in kb} == kb_canonicals, (
        "the committed kb snapshot and backend/app/kb/diseases.json no longer "
        "list the same classes. Regenerate: python scripts/snapshot_api.py"
    )


def test_every_class_the_model_emits_has_advice(config, kb_canonicals) -> None:
    missing = [name for name in config["class_order"] if name not in kb_canonicals]
    assert not missing, (
        f"the classifier can emit {missing} and the knowledge base has no "
        "record for it, so the result card would be empty."
    )


def test_check_rejects_a_class_with_no_advice(snapshot_api) -> None:
    config = {"class_order": ["grey_blight", "a_seventh_disease"], "min_confidence": 0.6}
    kb = [{"canonical": "grey_blight"}]
    with pytest.raises(ValueError, match="a_seventh_disease"):
        snapshot_api.check(config, kb)


def test_check_rejects_a_config_without_a_confidence_floor(snapshot_api) -> None:
    config = {"class_order": ["grey_blight"], "min_confidence": "0.6"}
    with pytest.raises(ValueError, match="min_confidence"):
        snapshot_api.check(config, [{"canonical": "grey_blight"}])


def test_check_rejects_an_empty_class_order(snapshot_api) -> None:
    with pytest.raises(ValueError, match="class_order"):
        snapshot_api.check({"class_order": [], "min_confidence": 0.6}, [])


def test_fetch_refuses_to_invent_a_snapshot(snapshot_api) -> None:
    """A snapshot taken from nothing would deploy a broken site silently."""
    with pytest.raises(RuntimeError, match="could not reach"):
        snapshot_api.fetch("http://127.0.0.1:9", "config", timeout=2.0)
