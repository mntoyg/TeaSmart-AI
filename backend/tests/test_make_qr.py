"""A QR code committed to the README must point somewhere a stranger can reach.

The mistake this guards against was nearly made on 2026-10-20: a QR of
`https://192.168.0.32:5173`, the development machine's address on one wifi
network. On the author's phone it works, so it looks finished. A judge scanning
it from the room gets a connection error, which is worse than no QR at all -
they conclude the app is broken rather than that the link was local.

So the script classifies the host before it writes, and refuses a local or
private address unless told explicitly that a local QR is what is wanted.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "make_qr.py"

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("teasmart_make_qr", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None, SCRIPT_PATH
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def make_qr() -> ModuleType:
    return _load()


@pytest.mark.parametrize(
    "url",
    [
        "https://192.168.0.32:5173/scan",
        "http://192.168.0.32:5173",
        "https://10.0.0.5/",
        "https://172.16.4.9/",
        "http://localhost:5173/scan",
        "http://127.0.0.1:5173",
        "https://teasmart.local/",
        "https://machine.localhost/",
    ],
)
def test_local_and_private_hosts_are_not_reachable_by_a_stranger(
    make_qr, url: str
) -> None:
    assert make_qr.is_publicly_reachable(url) is False


@pytest.mark.parametrize(
    "url",
    [
        "https://teasmart.pages.dev/scan",
        "https://mntoyg.github.io/TeaSmart-AI/",
        "https://example.com",
    ],
)
def test_public_hosts_are_reachable(make_qr, url: str) -> None:
    assert make_qr.is_publicly_reachable(url) is True


@pytest.mark.parametrize("url", ["ftp://example.com", "example.com", "", "javascript:0"])
def test_rejects_anything_that_is_not_http(make_qr, url: str) -> None:
    with pytest.raises(ValueError, match="http"):
        make_qr.check_url(url)


def test_a_private_url_is_refused_by_default(make_qr, tmp_path: Path) -> None:
    out = tmp_path / "qr.png"
    with pytest.raises(ValueError, match="allow-local"):
        make_qr.write_qr("https://192.168.0.32:5173/scan", out)
    assert not out.exists(), "nothing may be written when the URL is refused"


def test_a_private_url_is_written_when_explicitly_allowed(
    make_qr, tmp_path: Path
) -> None:
    out = tmp_path / "qr.png"
    make_qr.write_qr("https://192.168.0.32:5173/scan", out, allow_local=True)
    assert out.read_bytes()[:8] == PNG_MAGIC
    assert out.stat().st_size > 200


def test_a_public_url_needs_no_flag(make_qr, tmp_path: Path) -> None:
    out = tmp_path / "nested" / "qr.png"
    make_qr.write_qr("https://teasmart.pages.dev/scan", out)
    assert out.read_bytes()[:8] == PNG_MAGIC


def test_the_url_is_actually_encoded_into_the_image(make_qr, tmp_path: Path) -> None:
    """Two URLs must not produce the same image.

    Decoding the PNG back to a string would be the direct check, but it needs a
    QR reader this project does not have a reason to depend on. This is the
    property that can be checked without one, and it is the one that fails if
    the script ever writes a fixed image or ignores its argument - which is the
    realistic defect, not a subtly wrong payload.
    """
    first = make_qr.write_qr("https://teasmart.pages.dev/scan", tmp_path / "a.png")
    second = make_qr.write_qr("https://teasmart.pages.dev/other", tmp_path / "b.png")
    assert first.read_bytes() != second.read_bytes()
