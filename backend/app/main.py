"""FastAPI application factory for the TeaSmart AI backend."""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.kb import router as kb_router
from app.core.config import get_settings
from app.core.images import (
    CorruptImageError,
    ImageLoadError,
    ImageTooLargeError,
    UnsupportedImageError,
)
from app.services.expert import load_kb

Handler = Callable[[Request, Exception], Awaitable[JSONResponse]]

# Every rejection the upload door can make, with the status and the Thai line a
# field worker sees. Nothing from the exception itself reaches the client, so a
# rejected upload cannot leak an internal path or a traceback.
#
# ImageLoadError itself is registered last as a catch-all: Starlette resolves a
# handler by walking the exception's MRO, so the specific entries still win, and
# a rejection class added in a later stage answers 400 instead of 500.
_IMAGE_ERRORS: tuple[tuple[type[ImageLoadError], int, str, str], ...] = (
    (
        UnsupportedImageError,
        415,
        "unsupported image format",
        "ไฟล์ที่อัปโหลดไม่ใช่ภาพ JPEG, PNG หรือ WebP",
    ),
    (
        ImageTooLargeError,
        413,
        "image too large",
        "ไฟล์ภาพใหญ่เกินกำหนด กรุณาย่อขนาดภาพก่อนอัปโหลด",
    ),
    (
        CorruptImageError,
        400,
        "corrupt image",
        "ไฟล์ภาพเสียหายหรือไม่สมบูรณ์ กรุณาถ่ายใหม่",
    ),
    (
        ImageLoadError,
        400,
        "image rejected",
        "ไม่สามารถใช้ภาพนี้ได้ กรุณาถ่ายใหม่",
    ),
)


def _image_error_handler(status: int, detail: str, detail_th: str) -> Handler:
    async def handler(_request: Request, _exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status, content={"detail": detail, "detail_th": detail_th}
        )

    return handler


def create_app() -> FastAPI:
    settings = get_settings()

    # Load and validate the knowledge base here, not on the first request: a
    # malformed or missing file should stop the service from starting rather than
    # answer 500 to a worker standing in a field.
    load_kb(settings.kb_path)

    app = FastAPI(title=settings.app_name, version=settings.model_version)

    # Explicit allowlist only; a wildcard origin would expose the scan API.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    for error_type, status, detail, detail_th in _IMAGE_ERRORS:
        app.add_exception_handler(
            error_type, _image_error_handler(status, detail, detail_th)
        )

    app.include_router(kb_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "app": settings.app_name,
            "model_version": settings.model_version,
        }

    return app
