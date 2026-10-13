import json
from pathlib import Path

import pytest

from teasmart_ml.classes import CANONICAL_CLASSES, UnmappedLabelError, to_canonical

_KB_PATH = (
    Path(__file__).resolve().parents[2] / "backend" / "app" / "kb" / "diseases.json"
)


def test_the_five_canonical_classes_are_in_class_id_order():
    assert CANONICAL_CLASSES == (
        "grey_blight",
        "brown_blight",
        "algal_spot",
        "healthy",
        "other_disease",
    )


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("gray_blight", "grey_blight"),
        ("gray_light", "grey_blight"),
        ("Gray Blight", "grey_blight"),
        ("brown_blight", "brown_blight"),
        ("Brown Blight", "brown_blight"),
        ("algal_spot", "algal_spot"),
        ("algal_leaf", "algal_spot"),
        ("Algal Leaf Spot", "algal_spot"),
        ("healthy", "healthy"),
        ("Healthy", "healthy"),
        ("anthracnose", "other_disease"),
        ("bird_eye_spot", "other_disease"),
        ("red_spot", "other_disease"),
        ("red_leaf_spot", "other_disease"),
        ("Red Leaf Spot", "other_disease"),
        ("helopeltis", "other_disease"),
        ("Helopeltis", "other_disease"),
        ("white_spot", "other_disease"),
    ],
)
def test_every_source_label_maps_to_its_canonical_class(label, expected):
    assert to_canonical(label) == expected


def test_an_unmapped_label_raises_instead_of_becoming_other_disease():
    # A silent fallback would absorb an upstream relabelling and keep answering
    # confidently with advice derived from the wrong class.
    with pytest.raises(UnmappedLabelError):
        to_canonical("tea_mosquito_bug")


def test_the_canonical_classes_match_the_backend_knowledge_base():
    # Stage 6 looks advice up by these names. If the two drift apart, the
    # classifier emits a class the expert system cannot answer.
    kb = json.loads(_KB_PATH.read_text(encoding="utf-8"))
    kb_trainable = {record["canonical"] for record in kb} - {"physical_burn"}
    assert kb_trainable == set(CANONICAL_CLASSES)
