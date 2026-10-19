"""Stage 3: the five-class classifier.

The server runs the same ONNX graph the browser runs, rather than a PyTorch
model, for one reason: there is then no second implementation to diverge. torch
would also put 2.5 GB of CUDA wheels into an API service that does one forward
pass per request.

Preprocessing is defined by `docs/DESIGN.md` section 8.4 and pinned by the
fixtures in `frontend/src/test/fixtures/preprocess/`, which this module is
tested against alongside the browser. PIL resizing is the definition because
the model was trained on it.

`classify` takes a runner - a callable from tensor to logits - not a session.
That keeps onnxruntime behind `load_session`, lets the tests inject logits, and
mirrors the shape the browser worker already uses.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from app.core.config import Settings

Runner = Callable[[np.ndarray], np.ndarray]

INPUT_SIZE = (224, 224)
INPUT_NAME = "input"
OUTPUT_NAME = "logits"
_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(3, 1, 1)
_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(3, 1, 1)

# The order the ONNX output columns are in, which is the knowledge base in
# class_id order with physical_burn left out - the classifier is never trained
# on it, because no burn photographs exist. Stage 4 is what reaches that class.
CLASS_ORDER = (
    "grey_blight",
    "brown_blight",
    "algal_spot",
    "healthy",
    "other_disease",
)
LOW_CONFIDENCE_CLASS = "other_disease"


class ModelUnavailableError(RuntimeError):
    """The ONNX graph is missing or will not load."""


@dataclass(frozen=True)
class ClassScore:
    class_name: str
    confidence: float


@dataclass(frozen=True)
class Prediction:
    class_id: int
    class_name: str
    confidence: float
    low_confidence: bool
    top_k: tuple[ClassScore, ...]


def preprocess(rgb: np.ndarray) -> np.ndarray:
    """The five contract steps, as an NCHW batch of one.

    Takes the bare RGB array `app.core.images` produces, so nothing upstream
    has to know about PIL.
    """
    image = Image.fromarray(np.ascontiguousarray(rgb), mode="RGB")
    resized = image.resize(INPUT_SIZE, resample=Image.BILINEAR)
    array = np.asarray(resized, dtype=np.float32) / 255.0
    chw = (array.transpose(2, 0, 1) - _MEAN) / _STD
    return np.ascontiguousarray(chw[None, ...], dtype=np.float32)


def load_session(model_path: Path) -> Runner:
    """Open the ONNX graph and return a runner over it.

    Checked eagerly and reported clearly: a fresh clone without the model is a
    situation the demo machine will meet, and "model not found at <path>" is
    more use than an onnxruntime stack trace.
    """
    model_path = Path(model_path)
    if not model_path.is_file():
        raise ModelUnavailableError(
            f"ONNX model not found at {model_path}. Export it with: "
            f"cd ml && .venv/Scripts/python.exe -m teasmart_ml.cli export"
        )

    try:
        import onnxruntime as ort

        session = ort.InferenceSession(
            str(model_path), providers=["CPUExecutionProvider"]
        )
    except Exception as error:  # pragma: no cover - environment dependent
        raise ModelUnavailableError(f"could not load {model_path}: {error}") from error

    names = {output.name for output in session.get_outputs()}
    if OUTPUT_NAME not in names:
        raise ModelUnavailableError(
            f"{model_path} has outputs {sorted(names)}, expected {OUTPUT_NAME!r}"
        )

    def run(tensor: np.ndarray) -> np.ndarray:
        return session.run([OUTPUT_NAME], {INPUT_NAME: tensor})[0]

    return run


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max()
    exponentiated = np.exp(shifted)
    return exponentiated / exponentiated.sum()


def classify(rgb: np.ndarray, runner: Runner, settings: Settings) -> Prediction:
    """Classify one image, applying the measured confidence floor.

    Below the floor the answer becomes `other_disease` with the flag set. That
    is not a cosmetic downgrade: naming the wrong disease sends a farmer to buy
    the wrong fungicide, while `other_disease` advice says to consult rather
    than to spray.
    """
    logits = np.asarray(runner(preprocess(rgb)), dtype=np.float32).reshape(-1)
    if logits.shape[0] != len(CLASS_ORDER):
        raise ModelUnavailableError(
            f"model produced {logits.shape[0]} logits, expected {len(CLASS_ORDER)}"
        )

    probabilities = _softmax(logits)
    order = np.argsort(probabilities)[::-1]
    top_k = tuple(
        ClassScore(CLASS_ORDER[index], float(probabilities[index]))
        for index in order[:3]
    )

    best = int(order[0])
    confidence = float(probabilities[best])
    low_confidence = confidence < settings.min_confidence
    class_name = LOW_CONFIDENCE_CLASS if low_confidence else CLASS_ORDER[best]

    return Prediction(
        class_id=CLASS_ORDER.index(class_name),
        class_name=class_name,
        confidence=confidence,
        low_confidence=low_confidence,
        top_k=top_k,
    )
