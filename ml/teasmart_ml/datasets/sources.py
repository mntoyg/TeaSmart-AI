"""Where the training images come from, and how to fetch them.

Only the sources that need no credentials are enabled. The rest stay in the
registry so enabling them later is a flag, not an archaeology exercise.

Every network call is injected as a parameter. That is what lets the whole
registry be tested offline, and it is the reason a registry mistake surfaces in
a 0.2 second test run rather than after 900MB of download.
"""

import json
import shutil
import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from urllib.parse import urlparse

_MENDELEY_FILES = (
    "https://data.mendeley.com/public-api/datasets/{dataset_id}/files"
    "?folder_id=root&version={version}"
)


class SourceUnavailableError(RuntimeError):
    """A source cannot be fetched: withdrawn, geo-blocked, or re-uploaded."""


class LabelDriftError(RuntimeError):
    """A source's embedded label order disagrees with the registry.

    Raised during ingest, declared here because the registry is what it
    disagrees with.
    """


@dataclass(frozen=True)
class HFParquetSource:
    source_id: str
    repo_id: str
    files: tuple[str, ...]
    label_names: tuple[str, ...]
    enabled: bool = True


@dataclass(frozen=True)
class MendeleyZipSource:
    source_id: str
    dataset_id: str
    version: int
    filename: str
    enabled: bool = True


# Probed 2026-10-13. Label orders are each source's own ClassLabel order and are
# verified against the file's embedded metadata at ingest time.
SOURCES: Mapping[str, HFParquetSource | MendeleyZipSource] = MappingProxyType(
    {
        "agml": HFParquetSource(
            source_id="agml",
            repo_id="Project-AgML/tea_leaf_disease_classification",
            files=("data/train-00000-of-00001.parquet",),
            label_names=(
                "algal_spot",
                "brown_blight",
                "gray_blight",
                "healthy",
                "helopeltis",
                "red_spot",
            ),
        ),
        "yunusserhat": HFParquetSource(
            source_id="yunusserhat",
            repo_id="yunusserhat/tea_sickness_dataset",
            files=(
                "data/train-00000-of-00002.parquet",
                "data/train-00001-of-00002.parquet",
                "data/validation-00000-of-00001.parquet",
                "data/test-00000-of-00001.parquet",
            ),
            label_names=(
                "Anthracnose",
                "algal_leaf",
                "bird_eye_spot",
                "brown_blight",
                "gray_light",
                "healthy",
                "red_leaf_spot",
                "white_spot",
            ),
        ),
        "mendeley_mz598": MendeleyZipSource(
            source_id="mendeley_mz598",
            dataset_id="mz598gxfw9",
            version=1,
            filename="Tea Leaf Diseases.zip",
        ),
        # Extra volume, deferred: 3.07GB and a .rar needing an external unpacker.
        "mendeley_d2xy": MendeleyZipSource(
            source_id="mendeley_d2xy",
            dataset_id="d2xybhfw59",
            version=1,
            filename="Tea Leaf Dataset.zip",
            enabled=False,
        ),
        "mendeley_94fz": MendeleyZipSource(
            source_id="mendeley_94fz",
            dataset_id="94fzcdz8gz",
            version=1,
            filename="Tea Leaf Dataset.rar",
            enabled=False,
        ),
    }
)


def enabled_sources() -> tuple[str, ...]:
    return tuple(sid for sid, source in SOURCES.items() if source.enabled)


# Mendeley's edge refuses urllib3 outright: curl gets 200 from the public API
# even when sent the python-requests User-Agent, so the discriminator is the TLS
# or HTTP fingerprint, not a header we can set. Shelling out to curl is the
# cheapest thing that actually works, and curl ships with Windows 10+, macOS and
# every Linux this will run on.
_CURL_TIMEOUT_SECONDS = "900"
_MENDELEY_HOST = "data.mendeley.com"


def validate_mendeley_url(url: str) -> str:
    """Refuse any URL that is not HTTPS on Mendeley's own host.

    The download URL arrives inside an API response, so it is data from the
    network. Handing an unchecked URL to a fetcher that writes to disk is how a
    surprising response turns into an arbitrary download.
    """
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != _MENDELEY_HOST:
        raise SourceUnavailableError(f"refusing to fetch a non-Mendeley URL: {url!r}")
    return url


def _curl(url: str, dest: Path | None) -> bytes:
    command = [
        "curl",
        "-sSL",
        "--fail",
        "--max-time",
        _CURL_TIMEOUT_SECONDS,
        validate_mendeley_url(url),
    ]
    if dest is not None:
        command += ["-o", str(dest)]
    try:
        completed = subprocess.run(command, check=True, capture_output=True)
    except FileNotFoundError as exc:
        raise SourceUnavailableError("curl is not installed; it is required for Mendeley sources") from exc
    except subprocess.CalledProcessError as exc:
        raise SourceUnavailableError(f"curl failed for {url!r}: {exc.stderr.decode(errors='replace')[:200]}") from exc
    return completed.stdout


def _fetch_json(url: str):
    return json.loads(_curl(url, dest=None))


def _fetch_file(url: str, dest: Path) -> None:
    _curl(url, dest=dest)


def _hf_download(repo_id: str, filename: str, dest: Path) -> None:
    from huggingface_hub import hf_hub_download

    cached = hf_hub_download(repo_id=repo_id, filename=filename, repo_type="dataset")
    shutil.copyfile(cached, dest)


def resolve_mendeley_download(
    dataset_id: str,
    version: int,
    filename: str,
    *,
    fetch_json: Callable[[str], object] = _fetch_json,
) -> str:
    """Look the file's download URL up at call time.

    The per-file id is not pinned in the registry on purpose: it changes if the
    owner re-uploads, and a pinned id would turn that into a silent 404 halfway
    through a prepare run.
    """
    payload = fetch_json(
        _MENDELEY_FILES.format(dataset_id=dataset_id, version=version)
    )
    if not isinstance(payload, list):
        raise SourceUnavailableError(
            f"Mendeley dataset {dataset_id} v{version} is unavailable: {payload}"
        )
    for entry in payload:
        if entry.get("filename") == filename:
            url = entry.get("content_details", {}).get("download_url")
            if url:
                return url
    raise SourceUnavailableError(
        f"{filename!r} is not in Mendeley dataset {dataset_id} v{version}"
    )


def download_source(
    source_id: str,
    raw_root: Path,
    *,
    fetch_json: Callable[[str], object] = _fetch_json,
    fetch_file: Callable[[str, Path], None] = _fetch_file,
    hf_download: Callable[..., None] = _hf_download,
) -> tuple[Path, ...]:
    """Fetch a source into raw_root/<source_id>/, skipping what is already there."""
    source = SOURCES[source_id]
    target_dir = Path(raw_root) / source_id

    if isinstance(source, HFParquetSource):
        paths = []
        for relative in source.files:
            dest = target_dir / relative
            if not dest.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                hf_download(repo_id=source.repo_id, filename=relative, dest=dest)
            paths.append(dest)
        return tuple(paths)

    dest = target_dir / source.filename
    if not dest.exists():
        url = resolve_mendeley_download(
            source.dataset_id, source.version, source.filename, fetch_json=fetch_json
        )
        dest.parent.mkdir(parents=True, exist_ok=True)
        fetch_file(url, dest)
    return (dest,)
