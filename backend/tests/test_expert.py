import pytest

from app.core.config import get_settings
from app.services.expert import UnknownClassError, get_advice, load_kb


def test_kb_has_six_records_covering_every_canonical_class():
    kb = load_kb(get_settings().kb_path)
    assert len(kb) == 6
    assert {r.class_id for r in kb.values()} == {0, 1, 2, 3, 4, 5}


def test_kb_is_keyed_by_the_canonical_class_names_the_spec_defines():
    # Stage 3 emits these names and stage 6 is a pure lookup, so the key has to
    # be the canonical name, not the English display name.
    kb = load_kb(get_settings().kb_path)
    assert set(kb) == {
        "grey_blight",
        "brown_blight",
        "algal_spot",
        "healthy",
        "other_disease",
        "physical_burn",
    }


def test_grey_blight_advice_is_the_supplied_thai_text():
    kb = load_kb(get_settings().kb_path)
    record = get_advice("grey_blight", kb)
    assert record.class_name == "Tea Grey Blight"
    assert record.pathogen == "Pestalotiopsis theae"
    assert record.disease_name_th == "โรคใบไหม้เทา"


def test_physical_burn_advice_prescribes_no_fungicide():
    kb = load_kb(get_settings().kb_path)
    record = get_advice("physical_burn", kb)
    assert record.pathogen.startswith("ไม่มีเชื้อก่อโรค")
    assert "ไม่ต้องพ่นสาร" in record.immediate_action


def test_unknown_class_raises():
    kb = load_kb(get_settings().kb_path)
    with pytest.raises(UnknownClassError):
        get_advice("Nonexistent Blight", kb)


def test_the_knowledge_base_cannot_be_mutated_at_runtime():
    # One cached mapping is shared process-wide, and the PWA caches whatever this
    # serves for offline use. A single stray write would poison the advice a
    # worker reads until the service restarts.
    kb = load_kb(get_settings().kb_path)
    with pytest.raises(TypeError):
        kb["grey_blight"] = kb["healthy"]
    with pytest.raises(TypeError):
        del kb["healthy"]
