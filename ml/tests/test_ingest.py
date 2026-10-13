import pytest

from teasmart_ml.datasets.ingest import (
    InterimRootError,
    ingest_parquet_source,
    ingest_yolo_zip_source,
)
from teasmart_ml.datasets.sources import SOURCES, LabelDriftError
from tests.fixtures import green_jpeg, green_png, make_parquet, make_yolo_zip

AGML = SOURCES["agml"]
MZ598 = SOURCES["mendeley_mz598"]
MZ598_NAMES = (
    "Algal Leaf Spot",
    "Brown Blight",
    "Gray Blight",
    "Healthy",
    "Helopeltis",
    "Red Leaf Spot",
)


def test_parquet_rows_land_in_their_canonical_class_folder(tmp_path):
    parquet = make_parquet(
        rows=[(green_png(), 2), (green_png(), 3), (green_png(), 4)],
        label_names=AGML.label_names,
        path=tmp_path / "t.parquet",
    )
    report = ingest_parquet_source(AGML, [parquet], tmp_path / "interim")
    assert report.written == 3
    assert report.per_class == {"grey_blight": 1, "healthy": 1, "other_disease": 1}
    assert (tmp_path / "interim" / "agml" / "grey_blight").is_dir()


def test_a_parquet_whose_embedded_labels_disagree_with_the_registry_raises(tmp_path):
    # If upstream reorders its ClassLabel, every label in that source is wrong
    # together and nothing downstream could tell.
    parquet = make_parquet(
        rows=[(green_png(), 0)],
        label_names=("healthy",) + AGML.label_names[1:],
        path=tmp_path / "t.parquet",
    )
    with pytest.raises(LabelDriftError):
        ingest_parquet_source(AGML, [parquet], tmp_path / "interim")


def test_a_parquet_without_embedded_labels_raises_rather_than_trusting_the_registry(tmp_path):
    import pyarrow.parquet as pq

    parquet = make_parquet(
        rows=[(green_png(), 0)], label_names=AGML.label_names, path=tmp_path / "t.parquet"
    )
    table = pq.read_table(parquet).replace_schema_metadata({})
    pq.write_table(table, parquet)
    with pytest.raises(LabelDriftError):
        ingest_parquet_source(AGML, [parquet], tmp_path / "interim")


def test_a_corrupt_parquet_image_is_skipped_and_counted_not_fatal(tmp_path):
    parquet = make_parquet(
        rows=[(green_png(), 3), (b"not an image at all", 3), (green_png(), 3)],
        label_names=AGML.label_names,
        path=tmp_path / "t.parquet",
    )
    report = ingest_parquet_source(AGML, [parquet], tmp_path / "interim")
    assert report.written == 2
    assert report.skipped_corrupt == 1


def test_yolo_images_take_their_class_from_the_label_file(tmp_path):
    archive = make_yolo_zip(
        entries=[("a", green_jpeg(), (2,)), ("b", green_jpeg(), (3, 3))],
        names=MZ598_NAMES,
        path=tmp_path / "t.zip",
    )
    report = ingest_yolo_zip_source(MZ598, archive, tmp_path / "interim")
    assert report.per_class == {"grey_blight": 1, "healthy": 1}
    assert report.written == 2


def test_a_data_yaml_whose_names_disagree_with_the_registry_raises(tmp_path):
    archive = make_yolo_zip(
        entries=[("a", green_jpeg(), (0,))],
        names=("Healthy",) + MZ598_NAMES[1:],
        path=tmp_path / "t.zip",
    )
    with pytest.raises(LabelDriftError):
        ingest_yolo_zip_source(MZ598, archive, tmp_path / "interim")


def test_an_image_annotated_with_two_different_classes_is_skipped_as_ambiguous(tmp_path):
    # A leaf carrying boxes of two diseases has no single classification target,
    # and picking one would invent a label the annotator never gave.
    archive = make_yolo_zip(
        entries=[("mixed", green_jpeg(), (2, 3))], names=MZ598_NAMES, path=tmp_path / "t.zip"
    )
    report = ingest_yolo_zip_source(MZ598, archive, tmp_path / "interim")
    assert report.written == 0
    assert report.skipped_ambiguous == 1


def test_an_image_with_a_missing_or_empty_label_file_is_skipped_as_unlabelled(tmp_path):
    archive = make_yolo_zip(
        entries=[("none", green_jpeg(), None), ("empty", green_jpeg(), ())],
        names=MZ598_NAMES,
        path=tmp_path / "t.zip",
    )
    report = ingest_yolo_zip_source(MZ598, archive, tmp_path / "interim")
    assert report.written == 0
    assert report.skipped_unlabelled == 2


def test_an_archive_member_path_cannot_write_outside_the_interim_root(tmp_path):
    # Filenames are generated, never taken from the archive, so a traversal
    # member has nowhere to land. This asserts that property rather than
    # trusting it.
    archive = make_yolo_zip(
        entries=[("../../escaped", green_jpeg(), (3,))],
        names=MZ598_NAMES,
        path=tmp_path / "evil.zip",
    )
    interim = tmp_path / "interim"
    ingest_yolo_zip_source(MZ598, archive, interim)
    written = [p for p in tmp_path.rglob("*.jpg") if p.is_file()]
    assert written
    assert all(interim in p.parents for p in written)


def test_label_files_are_matched_within_their_own_split_directory(tmp_path):
    # Matching by bare stem across the whole archive attaches one split's boxes
    # to another split's image. The real archive happens to be safe because
    # Roboflow appends a hash to every filename, but the two disabled Mendeley
    # archives are one flag away from being ingested.
    archive = make_yolo_zip(
        entries=[
            ("0001", green_jpeg(seed=1), (2,), "train"),
            ("0001", green_jpeg(seed=2), (3,), "valid"),
        ],
        names=MZ598_NAMES,
        path=tmp_path / "t.zip",
    )
    report = ingest_yolo_zip_source(MZ598, archive, tmp_path / "interim")
    assert report.written == 2
    assert report.per_class == {"grey_blight": 1, "healthy": 1}


def test_a_parquet_label_outside_the_class_list_is_skipped_not_wrapped(tmp_path):
    # HuggingFace writes -1 for "no label", and Python would index that as the
    # LAST class: white_spot, which maps to other_disease, with nothing to show
    # anything went wrong.
    parquet = make_parquet(
        rows=[(green_png(), -1), (green_png(), 99), (green_png(), 3)],
        label_names=AGML.label_names,
        path=tmp_path / "t.parquet",
    )
    report = ingest_parquet_source(AGML, [parquet], tmp_path / "interim")
    assert report.written == 1
    assert report.skipped_unlabelled == 2
    assert report.per_class == {"healthy": 1}


def test_a_decompression_bomb_in_an_archive_is_skipped_not_fatal(tmp_path, monkeypatch):
    # DecompressionBombError descends from Exception, not OSError, so it escaped
    # the skip-and-count path and would have killed a 900MB ingest outright.
    from PIL import Image

    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 100)
    archive = make_yolo_zip(
        entries=[("bomb", green_jpeg(size=(64, 64)), (3,)), ("ok", green_jpeg(size=(8, 8)), (3,))],
        names=MZ598_NAMES,
        path=tmp_path / "t.zip",
    )
    report = ingest_yolo_zip_source(MZ598, archive, tmp_path / "interim")
    assert report.skipped_corrupt == 1
    assert report.written == 1


def test_ingesting_into_a_populated_directory_without_the_marker_is_refused(tmp_path):
    # _reset removes a whole source folder. A mistyped --interim pointing at a
    # directory that happens to hold an agml/ folder would destroy it silently.
    interim = tmp_path / "somewhere-else"
    (interim / "agml").mkdir(parents=True)
    (interim / "important.txt").write_text("not ours", encoding="utf-8")
    parquet = make_parquet(
        rows=[(green_png(), 3)], label_names=AGML.label_names, path=tmp_path / "t.parquet"
    )
    with pytest.raises(InterimRootError):
        ingest_parquet_source(AGML, [parquet], interim)
    assert (interim / "important.txt").exists()
