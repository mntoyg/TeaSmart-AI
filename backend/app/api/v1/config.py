"""Serve the numbers that exist on both sides of the wire.

The PWA duplicates two things out of necessity: the quality gate, because it is
cheap and has to work offline, and the classifier preprocessing, because
onnxruntime-web runs the model in the browser. Every constant those copies need
is served from here and cached alongside the knowledge base.

The alternative is a second copy of each number in TypeScript, which drifts the
first time one of them is retuned - and drifts silently, because nothing in
either codebase can see the other.
"""

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from app.core.config import Settings, get_settings
from app.services.expert import load_kb

router = APIRouter(prefix="/api/v1", tags=["config"])

# The class the lesion analyser reaches from image features. The classifier is
# never trained on it, so it is not part of the model output.
_RULE_BASED_CLASS = "physical_burn"

_IMAGENET_MEAN = (0.485, 0.456, 0.406)
_IMAGENET_STD = (0.229, 0.224, 0.225)


class Preprocessing(BaseModel):
    model_config = ConfigDict(frozen=True)

    size: tuple[int, int] = (224, 224)
    resize: str = "bilinear"
    preserve_aspect_ratio: bool = False
    scale: float = 255.0
    mean: tuple[float, float, float] = _IMAGENET_MEAN
    std: tuple[float, float, float] = _IMAGENET_STD
    layout: str = "NCHW"
    dtype: str = "float32"


class OnnxContract(BaseModel):
    model_config = ConfigDict(frozen=True)

    # fp32, not int8. Static int8 quantisation of MobileNetV3 moved a
    # probability by 0.248 against a contract bound of 0.05, measured on
    # 2026-10-19; see docs/EVIDENCE.md section 2.5. Top-1 still
    # agreed on all 50 parity images, which is why top-1 agreement is not the
    # acceptance test: the product thresholds on the probability, so a shift
    # that size moves predictions across min_confidence in both directions.
    file: str = "teasmart-v1.onnx"
    input: str = "input"
    output: str = "logits"
    output_is_logits: bool = True


class QualityThresholds(BaseModel):
    model_config = ConfigDict(frozen=True)

    blur_threshold: float
    exposure_min_mean: float
    exposure_max_mean: float
    clip_max_pct: float


class LeafGate(BaseModel):
    """The browser's own check that there is a plant in the photograph.

    Two numbers and no colour-space conversion, so a TypeScript port has
    nothing to get wrong. `frontend/src/test/fixtures/leaf-fraction.json`
    pins both against this implementation.
    """

    model_config = ConfigDict(frozen=True)

    veg_index_min: float
    min_fraction: float


class ClientConfig(BaseModel):
    model_config = ConfigDict(frozen=True, protected_namespaces=())

    model_version: str
    min_confidence: float
    class_order: list[str]
    preprocessing: Preprocessing
    onnx: OnnxContract
    quality: QualityThresholds
    leaf: LeafGate


def class_order(settings: Settings) -> list[str]:
    """Canonical class names in class_id order, from the knowledge base.

    Derived rather than listed again: a second copy could disagree with the
    records, and the records are what the advice is looked up by.
    """
    records = sorted(load_kb(settings.kb_path).values(), key=lambda r: r.class_id)
    return [r.canonical for r in records if r.canonical != _RULE_BASED_CLASS]


@router.get("/config", response_model=ClientConfig)
def read_config() -> ClientConfig:
    settings = get_settings()
    return ClientConfig(
        model_version=settings.model_version,
        min_confidence=settings.min_confidence,
        class_order=class_order(settings),
        preprocessing=Preprocessing(),
        onnx=OnnxContract(),
        quality=QualityThresholds(
            blur_threshold=settings.blur_threshold,
            exposure_min_mean=settings.exposure_min_mean,
            exposure_max_mean=settings.exposure_max_mean,
            clip_max_pct=settings.clip_max_pct,
        ),
        leaf=LeafGate(
            veg_index_min=settings.veg_index_min,
            min_fraction=settings.leaf_min_fraction,
        ),
    )
