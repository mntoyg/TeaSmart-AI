import pytest
from fastapi.testclient import TestClient

from app.core.images import (
    CorruptImageError,
    ImageLoadError,
    ImageTooLargeError,
    UnsupportedImageError,
)
from app.main import create_app

_LEAKY_MESSAGE = "boom at D:/secret/path/app/core/images.py"

_KINDS = {
    "unsupported": UnsupportedImageError,
    "too_large": ImageTooLargeError,
    "corrupt": CorruptImageError,
    "base": ImageLoadError,
}


@pytest.fixture
def probe_client() -> TestClient:
    """An app with a route that raises each rejection, so the handlers are exercised.

    The scan endpoint that will raise these for real arrives on D5; the status
    codes and Thai strings are already the contract the PWA is written against,
    so they are pinned now.
    """
    app = create_app()

    @app.get("/_probe/{kind}")
    def probe(kind: str) -> None:
        raise _KINDS[kind](_LEAKY_MESSAGE)

    return TestClient(app)


@pytest.mark.parametrize(
    ("kind", "status", "detail", "detail_th"),
    [
        (
            "unsupported",
            415,
            "unsupported image format",
            "ไฟล์ที่อัปโหลดไม่ใช่ภาพ JPEG, PNG หรือ WebP",
        ),
        (
            "too_large",
            413,
            "image too large",
            "ไฟล์ภาพใหญ่เกินกำหนด กรุณาย่อขนาดภาพก่อนอัปโหลด",
        ),
        (
            "corrupt",
            400,
            "corrupt image",
            "ไฟล์ภาพเสียหายหรือไม่สมบูรณ์ กรุณาถ่ายใหม่",
        ),
    ],
)
def test_each_rejection_answers_with_its_status_and_thai_message(
    probe_client, kind, status, detail, detail_th
):
    response = probe_client.get(f"/_probe/{kind}")
    assert response.status_code == status
    assert response.json() == {"detail": detail, "detail_th": detail_th}


def test_a_bare_image_load_error_is_a_client_error_not_an_unhandled_500(probe_client):
    # Every later stage adds rejection classes under ImageLoadError. Without a
    # fallback, each new one would answer 500 with nothing to warn its author.
    response = probe_client.get("/_probe/base")
    assert response.status_code == 400
    assert set(response.json()) == {"detail", "detail_th"}


@pytest.mark.parametrize("kind", list(_KINDS))
def test_a_rejection_never_leaks_the_exception_message(probe_client, kind):
    response = probe_client.get(f"/_probe/{kind}")
    assert "secret" not in response.text
