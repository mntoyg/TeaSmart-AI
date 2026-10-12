import pytest

from app.core.config import get_settings
from app.services.expert import UnknownClassError, get_advice, load_kb


def test_kb_has_six_records_covering_every_canonical_class():
    kb = load_kb(get_settings().kb_path)
    assert len(kb) == 6
    assert {r.class_id for r in kb.values()} == {0, 1, 2, 3, 4, 5}


def test_grey_blight_advice_is_the_supplied_thai_text():
    kb = load_kb(get_settings().kb_path)
    record = get_advice("Tea Grey Blight", kb)
    assert record.pathogen == "Pestalotiopsis theae"
    assert record.disease_name_th == "โรคใบไหม้เทา"


def test_physical_burn_advice_prescribes_no_fungicide():
    kb = load_kb(get_settings().kb_path)
    record = get_advice("Physical Burn / Sun Scorch", kb)
    assert record.pathogen.startswith("ไม่มีเชื้อก่อโรค")
    assert "ไม่ต้องพ่นสาร" in record.immediate_action


def test_unknown_class_raises():
    kb = load_kb(get_settings().kb_path)
    with pytest.raises(UnknownClassError):
        get_advice("Nonexistent Blight", kb)
