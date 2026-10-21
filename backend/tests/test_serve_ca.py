"""The root-CA server must never be able to serve the CA private key.

`scripts/serve_ca.py` exists so a handset can download the mkcert root
certificate and trust it, which is what turns the dev server's LAN address into
a secure context. The certificate next to it in `CAROOT` is `rootCA-key.pem`,
the key that signs for every name on the machine. Handing that out over the LAN
would be the worst thing in this repository.

So the invariant is stated as a property of the handler rather than of its path
handling: whatever is requested, the only bytes that can leave are the
certificate's. The handler ignores the request path entirely, and these tests
pin that by asking for the key by name, by traversal, and by absolute path.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "serve_ca.py"

CERT_BODY = b"-----BEGIN CERTIFICATE-----\npublic\n-----END CERTIFICATE-----\n"
KEY_BODY = b"-----BEGIN PRIVATE KEY-----\nSECRET\n-----END PRIVATE KEY-----\n"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("teasmart_serve_ca", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None, SCRIPT_PATH
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def serve_ca() -> ModuleType:
    return _load()


@pytest.fixture
def caroot(tmp_path: Path) -> Path:
    (tmp_path / "rootCA.pem").write_bytes(CERT_BODY)
    (tmp_path / "rootCA-key.pem").write_bytes(KEY_BODY)
    return tmp_path


def test_reads_the_certificate_and_not_the_key(serve_ca, caroot: Path) -> None:
    assert serve_ca.read_root_certificate(caroot) == CERT_BODY


@pytest.mark.parametrize(
    "requested",
    [
        "/rootCA.pem",
        "/rootCA-key.pem",
        "/",
        "/../rootCA-key.pem",
        "/%2e%2e/rootCA-key.pem",
        "/..%5crootCA-key.pem",
        "//rootCA-key.pem",
        "/rootCA-key.pem?x=1",
        "/C:/Users/anyone/AppData/Local/mkcert/rootCA-key.pem",
        "/anything/at/all",
    ],
)
def test_no_request_path_can_reach_the_key(serve_ca, caroot: Path, requested) -> None:
    """The path is not consulted, so there is no path that leaks the key."""
    body = serve_ca.response_body(requested, serve_ca.read_root_certificate(caroot))
    assert body == CERT_BODY
    assert b"SECRET" not in body
    assert b"PRIVATE KEY" not in body


def test_refuses_to_start_when_the_certificate_is_absent(
    serve_ca, tmp_path: Path
) -> None:
    with pytest.raises(FileNotFoundError, match="rootCA.pem"):
        serve_ca.read_root_certificate(tmp_path)


def test_refuses_a_private_key_served_as_the_certificate(
    serve_ca, tmp_path: Path
) -> None:
    """A CAROOT whose rootCA.pem holds a key is a mistake worth stopping on."""
    (tmp_path / "rootCA.pem").write_bytes(KEY_BODY)
    with pytest.raises(ValueError, match="private key"):
        serve_ca.read_root_certificate(tmp_path)


def test_content_type_makes_ios_offer_to_install_it(serve_ca) -> None:
    """Safari installs a certificate only when it is told what it is."""
    assert serve_ca.CONTENT_TYPE == "application/x-x509-ca-cert"


def test_mkcert_is_resolved_to_a_full_path_before_running_it(
    serve_ca, monkeypatch, tmp_path: Path
) -> None:
    """Running `mkcert` by bare name runs whatever PATH points at first.

    PATH is per-user and writable, so a file named mkcert.exe earlier on it
    would be executed instead. Resolving the name first makes what runs
    explicit, and makes "not installed" a different answer from "ran something".
    """
    fake = tmp_path / "mkcert.exe"
    fake.write_text("", encoding="utf-8")
    seen: list[list[str]] = []

    monkeypatch.setattr(serve_ca.shutil, "which", lambda name: str(fake))

    def record(argv, **kwargs):
        seen.append(argv)
        raise OSError("not actually running it")

    monkeypatch.setattr(serve_ca.subprocess, "run", record)
    serve_ca.mkcert_caroot()

    assert seen, "mkcert was never invoked"
    assert seen[0][0] == str(fake), seen[0]
    assert Path(seen[0][0]).is_absolute(), seen[0]


def test_missing_mkcert_is_reported_rather_than_guessed(
    serve_ca, monkeypatch
) -> None:
    monkeypatch.setattr(serve_ca.shutil, "which", lambda name: None)
    assert serve_ca.mkcert_caroot() is None


def test_the_default_bind_is_one_interface_not_all_of_them(serve_ca) -> None:
    """The handset needs to reach it; the VPN and every other adapter do not."""
    assert serve_ca.DEFAULT_BIND != "0.0.0.0"
    assert serve_ca.DEFAULT_BIND not in {"::", ""}
