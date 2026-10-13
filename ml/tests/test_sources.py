import pytest

from teasmart_ml.classes import CANONICAL_CLASSES, to_canonical
from teasmart_ml.datasets.sources import (
    SOURCES,
    SourceUnavailableError,
    download_source,
    enabled_sources,
    resolve_mendeley_download,
    validate_mendeley_url,
)


def test_only_the_three_credential_free_sources_are_enabled():
    assert set(enabled_sources()) == {"agml", "yunusserhat", "mendeley_mz598"}


def test_every_registry_label_is_mappable_to_a_canonical_class():
    # A label in the registry that to_canonical cannot resolve is a registry bug
    # that would otherwise surface only after a 900MB download.
    for source in SOURCES.values():
        for label in getattr(source, "label_names", ()):
            assert to_canonical(label) in CANONICAL_CLASSES


def test_resolve_mendeley_download_picks_the_url_for_the_named_file():
    payload = [
        {"filename": "data.yaml", "content_details": {"download_url": "https://x/yaml"}},
        {
            "filename": "Tea Leaf Diseases.zip",
            "content_details": {"download_url": "https://x/zip"},
        },
    ]
    url = resolve_mendeley_download(
        "mz598gxfw9", 1, "Tea Leaf Diseases.zip", fetch_json=lambda _: payload
    )
    assert url == "https://x/zip"


def test_resolve_mendeley_download_raises_when_the_api_returns_an_error():
    # The probe found sjmy6k24d6 answering {"error": 451}; that must be a clear
    # failure, not a crash deep inside a download loop.
    with pytest.raises(SourceUnavailableError):
        resolve_mendeley_download(
            "sjmy6k24d6", 3, "whatever.zip", fetch_json=lambda _: {"error": 451}
        )


def test_resolve_mendeley_download_raises_when_the_filename_is_absent():
    with pytest.raises(SourceUnavailableError):
        resolve_mendeley_download(
            "mz598gxfw9", 1, "absent.zip", fetch_json=lambda _: []
        )


def test_download_skips_a_file_that_is_already_present(tmp_path):
    existing = tmp_path / "agml" / "data" / "train-00000-of-00001.parquet"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"already here")

    def fail(*_args, **_kwargs):
        raise AssertionError("should not download an existing file")

    paths = download_source("agml", tmp_path, hf_download=fail)
    assert paths == (existing,)
    assert existing.read_bytes() == b"already here"


@pytest.mark.parametrize(
    "url",
    [
        "http://data.mendeley.com/public-files/x",
        "https://evil.example.com/public-files/x",
        "https://data.mendeley.com.evil.example.com/x",
        "file:///c:/windows/system32/drivers/etc/hosts",
        "ftp://data.mendeley.com/x",
    ],
)
def test_a_download_url_outside_mendeley_over_https_is_refused(url):
    # The download URL arrives inside an API response, so it is network data.
    # An unchecked URL handed to a fetcher that writes to disk is an arbitrary
    # download waiting to happen.
    with pytest.raises(SourceUnavailableError):
        validate_mendeley_url(url)


def test_a_genuine_mendeley_download_url_is_accepted():
    url = (
        "https://data.mendeley.com/public-files/datasets/mz598gxfw9/files/"
        "bc2642b5-a056-4466-857d-a00cdb8a375f/file_downloaded"
    )
    assert validate_mendeley_url(url) == url
