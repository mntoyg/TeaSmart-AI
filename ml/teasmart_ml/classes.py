"""The canonical class taxonomy, and the map from each source's own labels.

Five trained classes, in class_id order. physical_burn is never one of them: it
is a verdict the lesion analyser reaches from image features, not something the
classifier learns, because no labelled burn photographs exist.

Every source dataset spells its labels differently and several carry diseases
the knowledge base does not cover. Those collapse into other_disease rather than
being dropped, so the system can say "an abnormality outside the three primary
diseases, have an agronomist look at it" instead of confidently naming the wrong
one.
"""

from collections.abc import Mapping
from types import MappingProxyType

CANONICAL_CLASSES: tuple[str, ...] = (
    "grey_blight",
    "brown_blight",
    "algal_spot",
    "healthy",
    "other_disease",
)


class UnmappedLabelError(KeyError):
    """Raised when a source label has no canonical class.

    Deliberately not a fallback to other_disease: an unknown label means a
    source changed under us, and absorbing it silently would hide that behind
    plausible-looking advice.
    """


SOURCE_LABEL_MAP: Mapping[str, str] = MappingProxyType(
    {
        "gray_blight": "grey_blight",
        "gray_light": "grey_blight",
        "Gray Blight": "grey_blight",
        "brown_blight": "brown_blight",
        "Brown Blight": "brown_blight",
        "algal_spot": "algal_spot",
        "algal_leaf": "algal_spot",
        "Algal Leaf Spot": "algal_spot",
        "healthy": "healthy",
        "Healthy": "healthy",
        "anthracnose": "other_disease",
        "Anthracnose": "other_disease",
        "bird_eye_spot": "other_disease",
        "red_spot": "other_disease",
        "red_leaf_spot": "other_disease",
        "Red Leaf Spot": "other_disease",
        "helopeltis": "other_disease",
        "Helopeltis": "other_disease",
        "white_spot": "other_disease",
    }
)


def to_canonical(label: str) -> str:
    try:
        return SOURCE_LABEL_MAP[label]
    except KeyError as exc:
        raise UnmappedLabelError(label) from exc
