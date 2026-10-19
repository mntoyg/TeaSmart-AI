"""POST /api/v1/scan, the endpoint the whole product hangs off.

The frontend's `parseScan` rejects a response that is missing any of
`burn_analysis`, `severity`, `advice` or `analysis_mode`, and refuses one whose
`class_id` does not index the class order it holds. So these tests check the
response against the contract in docs/DESIGN.md section 8.1 field by field -
a shape mistake here renders as "ผลวิเคราะห์ไม่ครบถ้วน" on a phone and nothing else.

The ONNX graph is injected, so the suite says something about the wiring and
runs in milliseconds. One test loads the real model to prove the default path
resolves, because a demo machine that cannot find it has no product.
"""

import io

import cv2
import numpy as np
import pytest
from PIL import Image

from app.api.v1.scan import get_runner
from app.core.config import get_settings

LEAF_GREEN = (54, 122, 58)
SOIL = (92, 74, 62)


def _leaf_png(diseased: bool = True, size: int = 360) -> bytes:
    frame = np.full((size, size, 3), SOIL, dtype=np.uint8)
    cv2.ellipse(frame, (size // 2, size // 2), (140, 95), 0, 0, 360, LEAF_GREEN, -1)
    if diseased:
        for radius, colour in ((34, (92, 74, 40)), (22, (150, 128, 86))):
            cv2.circle(frame, (180, 180), radius, colour, -1)
        cv2.circle(frame, (180, 180), 35, (46, 34, 24), thickness=2)
    # Texture, or stage 1 rejects it as blurry and never reaches the rest of
    # the pipeline. A flat synthetic frame has a genuinely low Laplacian
    # variance - 53 against a threshold of 80, measured - so the gate is right
    # and the fixture was wrong. Real foliage has grain everywhere.
    rng = np.random.default_rng(17)
    grain = rng.integers(-16, 17, frame.shape, dtype=np.int16)
    frame = np.clip(frame.astype(np.int16) + grain, 0, 255).astype(np.uint8)

    buffer = io.BytesIO()
    Image.fromarray(frame).save(buffer, format="PNG")
    return buffer.getvalue()


def _blurry_png() -> bytes:
    frame = np.full((320, 320, 3), SOIL, dtype=np.uint8)
    cv2.ellipse(frame, (160, 160), (120, 80), 0, 0, 360, LEAF_GREEN, -1)
    frame = cv2.GaussianBlur(frame, (61, 61), 0)
    buffer = io.BytesIO()
    Image.fromarray(frame).save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def fake_model(app):
    """Override the ONNX runner with fixed logits."""

    def install(logits: list[float]):
        def runner(tensor: np.ndarray) -> np.ndarray:
            return np.array([logits], dtype=np.float32)

        app.dependency_overrides[get_runner] = lambda: runner
        return runner

    yield install
    app.dependency_overrides.pop(get_runner, None)


def test_a_scan_returns_every_field_the_frontend_parses(client, fake_model) -> None:
    fake_model([9.0, 0.0, 0.0, 0.0, 0.0])

    response = client.post(
        "/api/v1/scan", files={"image": ("leaf.png", _leaf_png(), "image/png")}
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {
        "scan_id",
        "captured_at",
        "quality",
        "prediction",
        "burn_analysis",
        "severity",
        "advice",
        "analysis_mode",
        "model_version",
        "processing_ms",
        "replayed",
    }
    assert set(body["quality"]) == {
        "passed",
        "blur_score",
        "exposure_mean",
        "clipped_low_pct",
        "clipped_high_pct",
    }
    assert set(body["prediction"]) == {
        "class_id",
        "class_name",
        "confidence",
        "top_k",
        "low_confidence",
    }
    assert set(body["burn_analysis"]) == {"verdict", "burn_likelihood", "features"}
    assert set(body["burn_analysis"]["features"]) == {
        "edge_sharpness",
        "ring_score",
        "acervuli_score",
        "edge_affinity",
        "colour_zonation",
    }
    assert set(body["severity"]) == {"affected_pct", "level"}
    assert body["analysis_mode"] == "full"
    assert body["model_version"] == get_settings().model_version
    assert body["processing_ms"] >= 0
    assert body["replayed"] is False


def test_the_multipart_field_is_named_image(client, fake_model) -> None:
    # The contract names it `image`. Anything else is a 422 from FastAPI, and
    # the frontend would have no idea why.
    fake_model([9.0, 0.0, 0.0, 0.0, 0.0])
    response = client.post(
        "/api/v1/scan", files={"photo": ("leaf.png", _leaf_png(), "image/png")}
    )
    assert response.status_code == 422


def test_class_id_indexes_the_class_order_the_frontend_holds(client, fake_model) -> None:
    # parseScan rejects the response outright when these disagree.
    from app.services.classify import CLASS_ORDER

    fake_model([0.0, 9.0, 0.0, 0.0, 0.0])
    body = client.post(
        "/api/v1/scan", files={"image": ("leaf.png", _leaf_png(), "image/png")}
    ).json()

    assert CLASS_ORDER[body["prediction"]["class_id"]] == body["prediction"]["class_name"]
    assert body["prediction"]["class_name"] == "brown_blight"


def test_advice_comes_from_the_knowledge_base_in_thai(client, fake_model) -> None:
    fake_model([9.0, 0.0, 0.0, 0.0, 0.0])
    body = client.post(
        "/api/v1/scan", files={"image": ("leaf.png", _leaf_png(), "image/png")}
    ).json()

    advice = body["advice"]
    assert advice["canonical"] == "grey_blight"
    assert advice["disease_name_th"] == "โรคใบไหม้เทา"
    for field in ("immediate_action", "cultural_control", "chemical_treatment",
                  "preventive_measures"):
        assert advice[field], field


def test_a_low_confidence_answer_is_downgraded_not_guessed(client, fake_model) -> None:
    fake_model([0.30, 0.25, 0.20, 0.15, 0.10])
    body = client.post(
        "/api/v1/scan", files={"image": ("leaf.png", _leaf_png(), "image/png")}
    ).json()

    assert body["prediction"]["low_confidence"] is True
    assert body["prediction"]["class_name"] == "other_disease"
    assert body["advice"]["canonical"] == "other_disease"


def test_a_burn_verdict_overrides_the_advice_and_forbids_fungicide(
    client, fake_model, monkeypatch
) -> None:
    """The feature the product exists for, end to end.

    The classifier says grey blight; the lesion analyser says the damage is
    physical. The advice that reaches the worker must be the burn record, and
    it must not tell them to spray.
    """
    from app.api.v1 import scan as scan_module
    from app.services.lesion import LesionAnalysis, LesionFeatures

    def burnt(rgb, leaf, settings):
        return LesionAnalysis(
            verdict="physical_burn",
            burn_likelihood=0.88,
            features=LesionFeatures(0.1, 0.0, 0.0, 0.95, 0.2),
            lesion_mask=np.zeros(rgb.shape[:2], dtype=bool),
            lesion_area_px=1200,
            leaf_area_px=40000,
            insufficient_lesion=False,
        )

    monkeypatch.setattr(scan_module, "analyse_lesion", burnt)
    fake_model([9.0, 0.0, 0.0, 0.0, 0.0])

    body = client.post(
        "/api/v1/scan", files={"image": ("leaf.png", _leaf_png(), "image/png")}
    ).json()

    assert body["burn_analysis"]["verdict"] == "physical_burn"
    assert body["prediction"]["class_name"] == "grey_blight"  # unchanged, reported
    assert body["advice"]["canonical"] == "physical_burn"
    treatment = body["advice"]["chemical_treatment"]
    assert "ไม่" in treatment, treatment


def test_a_blurry_frame_is_422_with_a_thai_instruction(client, fake_model) -> None:
    fake_model([9.0, 0.0, 0.0, 0.0, 0.0])

    response = client.post(
        "/api/v1/scan", files={"image": ("blur.png", _blurry_png(), "image/png")}
    )

    assert response.status_code == 422
    body = response.json()
    assert set(body) == {"detail", "detail_th", "quality"}
    assert body["detail_th"] == "ภาพเบลอ กรุณาถ่ายใหม่ให้ชัดขึ้น"
    assert body["quality"]["passed"] is False
    assert body["quality"]["blur_score"] < get_settings().blur_threshold


def test_a_client_scan_id_is_echoed_and_a_missing_one_is_generated(
    client, fake_model
) -> None:
    # scan_id is the idempotency key and the join between a queued image and
    # its result, so the server must not invent a second one.
    import uuid

    fake_model([9.0, 0.0, 0.0, 0.0, 0.0])
    supplied = str(uuid.uuid4())

    echoed = client.post(
        "/api/v1/scan",
        files={"image": ("leaf.png", _leaf_png(), "image/png")},
        data={"scan_id": supplied, "captured_at": "2026-10-19T09:12:04+07:00"},
    ).json()
    assert echoed["scan_id"] == supplied
    assert echoed["captured_at"] == "2026-10-19T09:12:04+07:00"

    generated = client.post(
        "/api/v1/scan", files={"image": ("leaf.png", _leaf_png(), "image/png")}
    ).json()
    uuid.UUID(generated["scan_id"])
    assert generated["captured_at"] is None


def test_an_oversized_upload_is_refused_before_it_is_decoded(client, fake_model) -> None:
    fake_model([9.0, 0.0, 0.0, 0.0, 0.0])
    oversized = b"\x89PNG\r\n\x1a\n" + b"\x00" * (get_settings().max_upload_bytes + 1)

    response = client.post(
        "/api/v1/scan", files={"image": ("big.png", oversized, "image/png")}
    )

    assert response.status_code == 413
    assert set(response.json()) == {"detail", "detail_th"}


def test_a_non_image_is_refused(client, fake_model) -> None:
    fake_model([9.0, 0.0, 0.0, 0.0, 0.0])
    response = client.post(
        "/api/v1/scan", files={"image": ("notes.txt", b"not an image", "text/plain")}
    )
    assert response.status_code == 415


def test_the_real_model_loads_from_the_default_path() -> None:
    """No injection here on purpose.

    If this fails on a fresh clone the model was not exported, and every scan
    would 503. Better to find that in the suite than on a demo stage.
    """
    from app.services.classify import load_session

    settings = get_settings()
    if not settings.model_path.is_file():
        pytest.skip(f"model not exported at {settings.model_path}")

    runner = load_session(settings.model_path)
    logits = runner(np.zeros((1, 3, 224, 224), dtype=np.float32))

    assert logits.shape == (1, 5)
    assert np.isfinite(logits).all()
