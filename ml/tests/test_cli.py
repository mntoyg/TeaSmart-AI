from teasmart_ml.classes import CANONICAL_CLASSES
from teasmart_ml.cli import prepare
from tests.fixtures import seed_fake_source_for


def test_prepare_is_idempotent(tmp_path):
    # A second run must not re-download a complete archive or double the corpus:
    # the first run costs 900MB and twenty minutes.
    calls = []

    def downloader(source_id, raw_root, **kwargs):
        calls.append(source_id)
        return seed_fake_source_for(source_id, raw_root, **kwargs)

    first = prepare(
        tmp_path / "raw", tmp_path / "interim", tmp_path / "m.csv", downloader=downloader
    )
    first_csv = (tmp_path / "m.csv").read_text(encoding="utf-8")
    second = prepare(
        tmp_path / "raw", tmp_path / "interim", tmp_path / "m.csv", downloader=downloader
    )
    second_csv = (tmp_path / "m.csv").read_text(encoding="utf-8")

    assert first == second
    assert first_csv == second_csv
    assert calls == ["agml", "yunusserhat", "mendeley_mz598"] * 2


def test_prepare_reports_counts_per_class_and_split(tmp_path):
    summary = prepare(
        tmp_path / "raw",
        tmp_path / "interim",
        tmp_path / "m.csv",
        downloader=seed_fake_source_for,
    )
    assert set(summary) <= set(CANONICAL_CLASSES)
    assert all(set(splits) == {"train", "val", "test"} for splits in summary.values())
    assert all(sum(splits.values()) >= 3 for splits in summary.values())
