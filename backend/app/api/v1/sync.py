"""POST /api/v1/sync/batch - replay the queue a phone built while offline.

Each queued scan already has a classifier-only result computed in the browser.
The server redoes it in full, which fills in the lesion analysis and the
severity the browser cannot compute.

Three things here are load-bearing, and all three come from
docs/DESIGN.md section 8.2:

**Items and files are matched by `scan_id`, never by position.** An off-by-one
would attach a diagnosis to the wrong photograph, and a worker would treat the
wrong plot. A mismatch in either direction fails the whole request rather than
guessing.

**One unusable frame must not fail the batch.** A queue built over a morning
will contain a blurred shot. That one becomes an entry in `failed` with its
Thai message; the rest are analysed. Every `scan_id` sent comes back in exactly
one of the two arrays, which is what the client checks before it marks anything
as sent.

**`local_prediction` is recorded, never used.** It is what the phone guessed,
kept so the two can be compared later. The answer is always the server's.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.api.v1.scan import (
    QualityRejected,
    ScanResult,
    analyse,
    get_result_cache,
    get_runner,
)
from app.core.config import Settings, get_settings
from app.core.images import (
    CorruptImageError,
    ImageLoadError,
    ImageTooLargeError,
    UnsupportedImageError,
)
from app.services.classify import Runner
from app.services.idempotency import ResultCache

router = APIRouter(prefix="/api/v1", tags=["sync"])

_ENVELOPE_TH = "ข้อมูลคิวไม่ถูกต้อง กรุณาลองซิงก์ใหม่"

# Mapped to the same statuses POST /api/v1/scan returns for the same causes, so
# a client sees one vocabulary whichever path a scan took. MRO order: the
# catch-all base last.
_IMAGE_ERRORS: tuple[tuple[type[Exception], int], ...] = (
    (UnsupportedImageError, 415),
    (ImageTooLargeError, 413),
    (CorruptImageError, 400),
    (ImageLoadError, 400),
)


class FailedItem(BaseModel):
    scan_id: str
    status: int
    detail: str
    detail_th: str


class BatchResponse(BaseModel):
    results: list[ScanResult]
    failed: list[FailedItem]


class EnvelopeError(Exception):
    """The request as a whole is unusable, so nothing in it is analysed."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


def _parse_items(raw: str, settings: Settings) -> list[dict]:
    """Validate the items envelope, or refuse the request.

    Refused rather than repaired: every field here either identifies a
    photograph or records what the phone thought, and guessing at either is
    worse than making the client send it again.
    """
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as error:
        raise EnvelopeError(f"items is not valid JSON: {error}") from error

    if not isinstance(parsed, list) or not parsed:
        raise EnvelopeError("items must be a non-empty JSON array")
    if len(parsed) > settings.max_batch_items:
        raise EnvelopeError(
            f"{len(parsed)} items exceeds max_batch_items "
            f"{settings.max_batch_items}; send the queue in several requests"
        )

    seen: set[str] = set()
    for index, item in enumerate(parsed):
        if not isinstance(item, dict):
            raise EnvelopeError(f"items[{index}] is not an object")
        scan_id = item.get("scan_id")
        if not isinstance(scan_id, str) or not scan_id:
            raise EnvelopeError(f"items[{index}] has no scan_id")
        if scan_id in seen:
            raise EnvelopeError(f"items contains {scan_id} more than once")
        seen.add(scan_id)
    return parsed


def _status_for(error: Exception) -> int | None:
    for kind, status in _IMAGE_ERRORS:
        if isinstance(error, kind):
            return status
    return None


@router.post("/sync/batch", response_model=BatchResponse)
async def sync_batch(
    items: str = Form(...),
    images: list[UploadFile] = File(...),
    settings: Settings = Depends(get_settings),
    runner: Runner = Depends(get_runner),
    cache: ResultCache = Depends(get_result_cache),
) -> BatchResponse | JSONResponse:
    try:
        parsed = _parse_items(items, settings)
    except EnvelopeError as error:
        return JSONResponse(
            status_code=422,
            content={"detail": error.detail, "detail_th": _ENVELOPE_TH},
        )

    # The filename IS the scan_id. Read with a cap per file and a running total
    # for the request, so an oversized queue is refused rather than buffered.
    payloads: dict[str, bytes] = {}
    total = 0
    for upload in images:
        name = upload.filename or ""
        if not name:
            return JSONResponse(
                status_code=422,
                content={
                    "detail": "an image part has no filename, so no scan_id",
                    "detail_th": _ENVELOPE_TH,
                },
            )
        if name in payloads:
            return JSONResponse(
                status_code=422,
                content={
                    "detail": f"two image parts are named {name}",
                    "detail_th": _ENVELOPE_TH,
                },
            )
        payload = await upload.read(settings.max_upload_bytes + 1)
        total += len(payload)
        if total > settings.max_batch_bytes:
            return JSONResponse(
                status_code=422,
                content={
                    "detail": (
                        f"request body exceeds max_batch_bytes "
                        f"{settings.max_batch_bytes}"
                    ),
                    "detail_th": _ENVELOPE_TH,
                },
            )
        payloads[name] = payload

    claimed = {item["scan_id"] for item in parsed}
    supplied = set(payloads)
    if claimed != supplied:
        # Both directions are an envelope error. Analysing the intersection
        # would hand the client a response it is right to reject, and it would
        # mean some queued photograph was silently dropped.
        missing = sorted(claimed - supplied)
        extra = sorted(supplied - claimed)
        parts = []
        if missing:
            parts.append(f"no image for {', '.join(missing)}")
        if extra:
            parts.append(f"no item for {', '.join(extra)}")
        return JSONResponse(
            status_code=422,
            content={"detail": "; ".join(parts), "detail_th": _ENVELOPE_TH},
        )

    results: list[ScanResult] = []
    failed: list[FailedItem] = []

    for item in parsed:
        scan_id = item["scan_id"]
        captured_at = item.get("captured_at")
        captured_at = captured_at if isinstance(captured_at, str) else None

        stored = cache.get(scan_id)
        if stored is not None:
            results.append(ScanResult(**{**stored, "replayed": True}))
            continue

        try:
            result = analyse(
                payloads[scan_id],
                scan_id=scan_id,
                captured_at=captured_at,
                settings=settings,
                runner=runner,
            )
        except QualityRejected as rejection:
            failed.append(
                FailedItem(
                    scan_id=scan_id,
                    status=422,
                    detail=rejection.detail,
                    detail_th=rejection.detail_th,
                )
            )
            continue
        except Exception as error:  # noqa: BLE001 - mapped below or re-raised
            status = _status_for(error)
            if status is None:
                raise
            failed.append(
                FailedItem(
                    scan_id=scan_id,
                    status=status,
                    detail=str(error),
                    detail_th="ไฟล์ภาพนี้ใช้ไม่ได้ กรุณาถ่ายใหม่",
                )
            )
            continue

        cache.put(result.scan_id, result.model_dump())
        results.append(result)

    return BatchResponse(results=results, failed=failed)
