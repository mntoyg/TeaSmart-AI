"""FastAPI application factory for the TeaSmart AI backend."""

from collections.abc import Callable

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

# Every rejection the upload door can make, with the status and the Thai line a
# field worker sees. Nothing from the exception itself reaches the client, so no
# internal path or traceback leaks through a rejected upload.
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
)


def _image_error_handler(status: int, detail: str, detail_th: str) -> Callable:
    async def handler(_request: Request, _exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=status, content={"detail": detail, "detail_th": detail_th}
        )

    return handler


def create_app() -> FastAPI:
    settings = get_settings()
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
