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
    assert settings.blur_threshold == 80.0
    assert settings.exposure_min_mean == 40.0
    assert settings.exposure_max_mean == 215.0
    assert settings.clip_max_pct == 0.10


def test_kb_path_default_is_absolute_so_it_resolves_from_any_cwd():
    settings = Settings(_env_file=None)
    assert settings.kb_path.is_absolute()
    assert settings.kb_path.name == "diseases.json"
