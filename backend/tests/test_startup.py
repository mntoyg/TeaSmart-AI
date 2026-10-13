import pytest

from app.core.config import get_settings
from app.main import create_app
from app.services.expert import load_kb


def test_the_knowledge_base_is_loaded_at_startup_not_on_the_first_request():
    load_kb.cache_clear()
    create_app()
    assert load_kb.cache_info().currsize == 1


def test_a_missing_knowledge_base_stops_the_service_from_starting(tmp_path, monkeypatch):
    # Better a service that refuses to boot than one that answers 500 to a worker
    # standing in a field.
    monkeypatch.setenv("TEASMART_KB_PATH", str(tmp_path / "absent.json"))
    get_settings.cache_clear()
    load_kb.cache_clear()
    try:
        with pytest.raises(FileNotFoundError):
            create_app()
    finally:
        get_settings.cache_clear()
        load_kb.cache_clear()
