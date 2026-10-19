"""Stage 3, and the preprocessing it shares with two other implementations.

The server, the browser and the training pipeline each preprocess an image, and
all three have to agree or the same leaf gets different answers depending on
where it was analysed. `frontend/src/test/fixtures/preprocess/` holds the
definition - PIL output for sources both languages can generate - and this suite
checks the server against it, exactly as the Vitest suite checks the browser.

Stage 3 takes a runner - a callable from a preprocessed tensor to logits -
rather than an onnxruntime session, so these tests inject fixed logits and say
something about the wiring rather than about the model. It is the same shape the
browser worker uses, and it keeps onnxruntime out of everything except
`load_session`.
"""

import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from app.core.config import get_settings
from app.services.classify import (
    ModelUnavailableError,
    Prediction,
    classify,
    load_session,
    preprocess,
)


def runner(logits: list[float]):
    """A stand-in for the ONNX graph, returning the logits a test wants."""

    def run(tensor: np.ndarray) -> np.ndarray:
        assert tensor.shape == (1, 3, 224, 224), tensor.shape
        return np.array([logits], dtype=np.float32)

    return run

FIXTURES = Path(__file__).resolve().parents[2] / "frontend/src/test/fixtures/preprocess"


def _hash_byte(seed: int, y: int, x: int, c: int, generator: dict) -> int:
    mask = 0xFFFFFFFF
    value = (
        seed
        ^ (x * generator["hash_x"] & mask)
        ^ (y * generator["hash_y"] & mask)
        ^ (c * generator["hash_c"] & mask)
    ) & mask
    value = (value ^ (value >> 15)) * generator["mix_1"] & mask
    value = (value ^ (value >> 13)) * generator["mix_2"] & mask
    return ((value ^ (value >> 16)) & mask) >> 24


def _source(case: dict, generator: dict) -> Image.Image:
    width, height = case["source"]["width"], case["source"]["height"]
    seed, pattern = case["source"]["seed"], case["source"]["pattern"]
    mask = 0xFFFFFFFF

    if pattern == "noise":
        y = np.arange(height, dtype=np.uint64).reshape(height, 1, 1)
        x = np.arange(width, dtype=np.uint64).reshape(1, width, 1)
        c = np.arange(3, dtype=np.uint64).reshape(1, 1, 3)
        value = (
            np.uint64(seed)
            ^ (x * np.uint64(generator["hash_x"]) & np.uint64(mask))
            ^ (y * np.uint64(generator["hash_y"]) & np.uint64(mask))
            ^ (c * np.uint64(generator["hash_c"]) & np.uint64(mask))
        ) & np.uint64(mask)
        value = (value ^ (value >> np.uint64(15))) * np.uint64(generator["mix_1"]) & np.uint64(mask)
        value = (value ^ (value >> np.uint64(13))) * np.uint64(generator["mix_2"]) & np.uint64(mask)
        array = ((value ^ (value >> np.uint64(16))) >> np.uint64(24)).astype(np.uint8)
    elif pattern == "gradient":
        red = (np.arange(width) * 255 // max(width - 1, 1)).astype(np.uint16)
        green = (np.arange(height) * 255 // max(height - 1, 1)).astype(np.uint16)
        red = np.broadcast_to(red[None, :], (height, width))
        green = np.broadcast_to(green[:, None], (height, width))
        blue = (red + green) // 2
        array = np.stack([red, green, blue], axis=-1).astype(np.uint8)
    else:  # blocks
        blocks = np.array(
            [[[_hash_byte(seed, by, bx, c, generator) for c in range(3)] for bx in range(8)]
             for by in range(8)],
            dtype=np.uint8,
        )
        rows = np.arange(height) * 8 // height
        cols = np.arange(width) * 8 // width
        array = blocks[rows[:, None], cols[None, :]]
    return Image.fromarray(array, mode="RGB")


@pytest.mark.skipif(not FIXTURES.exists(), reason="fixtures live on the frontend side")
def test_server_preprocessing_matches_the_shared_fixtures() -> None:
    manifest = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
    generator = manifest["generator"]
    tolerance = manifest["tolerance"]
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(3, 1, 1)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(3, 1, 1)

    assert manifest["cases"], "fixture manifest is empty"
    size = manifest["size"][0]
    for case in manifest["cases"]:
        # Raw RGB bytes, not an image file: the Vitest suite reads these too,
        # and a PNG decoder would be a dependency added to the frontend for the
        # sake of a test fixture.
        raw = (FIXTURES / case["expected"]).read_bytes()
        assert len(raw) == size * size * 3, case["name"]
        expected = (
            np.frombuffer(raw, dtype=np.uint8)
            .reshape(size, size, 3)
            .astype(np.float32)
        )

        # preprocess returns the normalised NCHW tensor; undo the normalisation
        # so the comparison is against the fixture's uint8 scale.
        produced = preprocess(np.asarray(_source(case, generator)))[0]
        undone = (produced * std + mean) * 255.0

        difference = np.abs(undone.transpose(1, 2, 0) - expected)
        assert difference.max() <= tolerance["max"], case["name"]
        assert difference.mean() <= tolerance["mean"], case["name"]


def test_preprocess_emits_the_shape_the_contract_fixes() -> None:
    out = preprocess(np.zeros((480, 640, 3), dtype=np.uint8))
    assert out.shape == (1, 3, 224, 224)
    assert out.dtype == np.float32


def test_classify_applies_the_confidence_floor() -> None:
    settings = get_settings()
    # Logits chosen so the top softmax probability lands under the floor.
    run = runner([0.30, 0.25, 0.20, 0.15, 0.10])

    result = classify(np.zeros((224, 224, 3), dtype=np.uint8), run, settings)

    assert isinstance(result, Prediction)
    assert result.low_confidence is True
    assert result.class_name == "other_disease"
    assert result.confidence < settings.min_confidence


def test_classify_keeps_a_confident_answer() -> None:
    run = runner([9.0, 0.0, 0.0, 0.0, 0.0])

    result = classify(np.zeros((224, 224, 3), dtype=np.uint8), run, get_settings())

    assert result.class_name == "grey_blight"
    assert result.class_id == 0
    assert result.low_confidence is False
    assert result.confidence > 0.99


def test_classify_reports_top_k_in_descending_order() -> None:
    run = runner([1.0, 3.0, 2.0, 0.0, 0.5])

    result = classify(np.zeros((224, 224, 3), dtype=np.uint8), run, get_settings())

    names = [entry.class_name for entry in result.top_k]
    assert names[:3] == ["brown_blight", "algal_spot", "grey_blight"]
    confidences = [entry.confidence for entry in result.top_k]
    assert confidences == sorted(confidences, reverse=True)
    assert sum(confidences) <= 1.0 + 1e-6


def test_load_session_says_so_when_the_model_is_missing(tmp_path) -> None:
    # The demo machine will hit this the first time it is cloned without the
    # model, and a clear error beats an onnxruntime stack trace.
    with pytest.raises(ModelUnavailableError) as excinfo:
        load_session(tmp_path / "absent.onnx")

    assert "absent.onnx" in str(excinfo.value)
