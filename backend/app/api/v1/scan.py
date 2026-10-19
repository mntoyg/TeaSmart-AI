"""POST /api/v1/scan - the whole pipeline, one image in, one answer out.

Stage order is the contract's: quality, segment, classify, lesion, severity,
advice. Each stage is a pure function taking what it needs as an argument, so
this module is the only place that knows the order.

Two decisions worth naming:

**The verdict overrides the advice, not the prediction.** When the lesion
analyser says the damage is physical, the classifier's answer is still
reported - a worker and a reviewer should both be able to see what the model
thought - but the advice served is the burn record, which prescribes no
fungicide. Rewriting the prediction would hide the disagreement.

**The image is downscaled immediately after decode.** An 8 MiB upload can be a
40 MP image and 235 MB of RAM, which was open decision 1 against the only
untrusted door in the system. Every stage either works in ratios or resizes to
224x224, so capping at 4 MP costs nothing and closes the amplification.
"""

from __future__ import annotations

import time
import uuid
from functools import lru_cache

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from app.core.config import Settings, get_settings
from app.core.images import ImageTooLargeError, decode_image
from app.services.classify import Runner, classify, load_session
from app.services.expert import get_advice, load_kb
from app.services.lesion import analyse_lesion
from app.services.quality import assess_quality
from app.services.segment import segment_leaf
from app.services.severity import assess_severity

router = APIRouter(prefix="/api/v1", tags=["scan"])

# The server does every stage, so it says so. The browser cannot segment and
# reports `classifier_only`; the result card has to state which it got.
ANALYSIS_MODE = "full"
BURN_CLASS = "physical_burn"


class ClassScoreOut(BaseModel):
    class_name: str
    confidence: float


class QualityOut(BaseModel):
    passed: bool
    blur_score: float
    exposure_mean: float
    clipped_low_pct: float
    clipped_high_pct: float


class PredictionOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    class_id: int
    class_name: str
    confidence: float
    top_k: list[ClassScoreOut]
    low_confidence: bool


class FeaturesOut(BaseModel):
    edge_sharpness: float
    ring_score: float
    acervuli_score: float
    edge_affinity: float
    colour_zonation: float


class BurnAnalysisOut(BaseModel):
    verdict: str
    burn_likelihood: float
    features: FeaturesOut


class SeverityOut(BaseModel):
    affected_pct: float
    level: str


class AdviceOut(BaseModel):
    canonical: str
    disease_name_th: str
    immediate_action: str
    cultural_control: str
    chemical_treatment: str
    preventive_measures: str


class ScanResult(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    scan_id: str
    captured_at: str | None
    quality: QualityOut
    prediction: PredictionOut
    burn_analysis: BurnAnalysisOut
    severity: SeverityOut
    advice: AdviceOut
    analysis_mode: str
    model_version: str
    processing_ms: int


@lru_cache(maxsize=1)
def _cached_runner(model_path: str) -> Runner:
    return load_session(model_path)


def get_runner(settings: Settings = Depends(get_settings)) -> Runner:
    """The ONNX runner, loaded once per process.

    A dependency rather than a module global so tests can inject fixed logits
    without a 16.8 MB model load, and so a path change takes effect.
    """
    return _cached_runner(str(settings.model_path))


def downscale_for_analysis(rgb: np.ndarray, settings: Settings) -> np.ndarray:
    """Cap the working resolution. See the module docstring."""
    height, width = rgb.shape[:2]
    pixels = height * width
    if pixels <= settings.max_analysis_pixels:
        return rgb

    scale = (settings.max_analysis_pixels / pixels) ** 0.5
    return cv2.resize(
        rgb,
        (max(int(width * scale), 1), max(int(height * scale), 1)),
        interpolation=cv2.INTER_AREA,
    )


async def _read_capped(upload: UploadFile, settings: Settings) -> bytes:
    """Read the upload, refusing anything over the cap.

    Reads one byte past the limit rather than the whole body, so an oversized
    upload is rejected without being held in memory.
    """
    payload = await upload.read(settings.max_upload_bytes + 1)
    if len(payload) > settings.max_upload_bytes:
        raise ImageTooLargeError(
            f"upload exceeds {settings.max_upload_bytes} bytes"
        )
    return payload


@router.post("/scan", response_model=ScanResult)
async def scan(
    image: UploadFile = File(...),
    scan_id: str | None = Form(default=None),
    captured_at: str | None = Form(default=None),
    settings: Settings = Depends(get_settings),
    runner: Runner = Depends(get_runner),
) -> ScanResult | JSONResponse:
    started = time.perf_counter()

    payload = await _read_capped(image, settings)
    decoded = decode_image(
        payload,
        max_bytes=settings.max_upload_bytes,
        max_pixels=settings.max_image_pixels,
    )
    rgb = downscale_for_analysis(decoded, settings)

    quality = assess_quality(
        rgb,
        blur_threshold=settings.blur_threshold,
        exposure_min_mean=settings.exposure_min_mean,
        exposure_max_mean=settings.exposure_max_mean,
        clip_max_pct=settings.clip_max_pct,
    )
    if not quality.passed:
        # Not an error page. The Thai message says what to change, and the UI
        # offers an immediate retake.
        return JSONResponse(
            status_code=422,
            content={
                "detail": quality.reason,
                "detail_th": quality.reason_th,
                "quality": QualityOut(
                    passed=quality.passed,
                    blur_score=quality.blur_score,
                    exposure_mean=quality.exposure_mean,
                    clipped_low_pct=quality.clipped_low_pct,
                    clipped_high_pct=quality.clipped_high_pct,
                ).model_dump(),
            },
        )

    leaf = segment_leaf(rgb, settings)
    prediction = classify(leaf.crop, runner, settings)
    lesion = analyse_lesion(rgb, leaf, settings)
    severity = assess_severity(lesion.lesion_area_px, lesion.leaf_area_px, settings)

    resolved = (
        BURN_CLASS if lesion.verdict == BURN_CLASS else prediction.class_name
    )
    advice = get_advice(resolved, load_kb(settings.kb_path))

    return ScanResult(
        scan_id=scan_id or str(uuid.uuid4()),
        captured_at=captured_at,
        quality=QualityOut(
            passed=quality.passed,
            blur_score=quality.blur_score,
            exposure_mean=quality.exposure_mean,
            clipped_low_pct=quality.clipped_low_pct,
            clipped_high_pct=quality.clipped_high_pct,
        ),
        prediction=PredictionOut(
            class_id=prediction.class_id,
            class_name=prediction.class_name,
            confidence=prediction.confidence,
            top_k=[
                ClassScoreOut(class_name=entry.class_name, confidence=entry.confidence)
                for entry in prediction.top_k
            ],
            low_confidence=prediction.low_confidence,
        ),
        burn_analysis=BurnAnalysisOut(
            verdict=lesion.verdict,
            burn_likelihood=lesion.burn_likelihood,
            features=FeaturesOut(**lesion.features.as_dict()),
        ),
        severity=SeverityOut(
            affected_pct=severity.affected_pct, level=severity.level
        ),
        advice=AdviceOut(
            canonical=advice.canonical,
            disease_name_th=advice.disease_name_th,
            immediate_action=advice.immediate_action,
            cultural_control=advice.cultural_control,
            chemical_treatment=advice.chemical_treatment,
            preventive_measures=advice.preventive_measures,
        ),
        analysis_mode=ANALYSIS_MODE,
        model_version=settings.model_version,
        processing_ms=int((time.perf_counter() - started) * 1000),
    )
