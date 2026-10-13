import pytest

from teasmart_ml.datasets.ingest import ingest_parquet_source, ingest_yolo_zip_source
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
