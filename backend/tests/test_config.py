import json
import re
from pathlib import Path

from app.core.config import Settings


def test_settings_defaults_match_the_values_the_spec_pins():
    # These are Global Constraints: the whole pipeline hangs off them, so a typo
    # here has to break a test rather than quietly change how a frame is judged.
    settings = Settings(_env_file=None)
    assert settings.app_name == "TeaSmart AI"
    assert settings.model_version == "teasmart-v1"
    assert settings.cors_origins == ["http://localhost:5173"]
    assert settings.max_upload_bytes == 8388608
    assert settings.max_image_pixels == 40000000
    # Measured 2026-10-19 over 400 corpus images, not guessed: 80 rejected
    # 52.8% of real photographs as blurry. docs/EVIDENCE.md section 4.
    assert settings.blur_threshold == 15.0
    assert settings.exposure_min_mean == 40.0
    assert settings.exposure_max_mean == 235.0
    assert settings.clip_max_pct == 0.10
    assert settings.min_confidence == 0.60


def test_kb_path_default_is_absolute_so_it_resolves_from_any_cwd():
    settings = Settings(_env_file=None)
    assert settings.kb_path.is_absolute()
    assert settings.kb_path.name == "diseases.json"


def test_settings_match_transport_and_quality_values_in_the_api_spec():
    settings = Settings(_env_file=None)
    spec = Path(__file__).resolve().parents[2] / "docs" / "DESIGN.md"
    document = spec.read_text(encoding="utf-8")

    for field in ("max_upload_bytes", "max_image_pixels", "max_batch_items", "max_batch_bytes"):
        match = re.search(rf"`{field}`\s+(\d+)", document)
        assert match is not None, f"{field} is missing from docs/DESIGN.md"
        assert getattr(settings, field) == int(match.group(1)), field

    cache_size = re.search(r"`Settings\.idempotency_cache_size`,\s*(\d+)", document)
    assert cache_size is not None, "idempotency_cache_size is missing from docs/DESIGN.md"
    assert settings.idempotency_cache_size == int(cache_size.group(1))

    section = document.split("### 8.5", 1)[1].split("## 9.", 1)[0]
    sample = re.search(r"```json\s*([\s\S]*?)```", section)
    assert sample is not None, "config JSON sample is missing from section 8.5"
    published = json.loads(sample.group(1))
    quality = published["quality"]
    for field in ("blur_threshold", "exposure_min_mean", "exposure_max_mean", "clip_max_pct"):
        assert getattr(settings, field) == quality[field], field

    # The leaf gate, for the same reason: the browser reads these two numbers
    # and `min_fraction` was measured over the whole corpus. A value that
    # drifts from the document is a value nobody re-measured.
    leaf = published["leaf"]
    assert settings.veg_index_min == leaf["veg_index_min"]
    assert settings.leaf_min_fraction == leaf["min_fraction"]
