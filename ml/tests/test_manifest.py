from collections import Counter, defaultdict

from teasmart_ml.datasets.manifest import build_manifest, summarise, write_manifest
from tests.fixtures import build_interim, distinct, write_leaf_photo


def test_duplicates_are_collapsed_before_the_split(tmp_path):
    root = build_interim(tmp_path, {"healthy": [("a", 512), ("a", 256), ("b", 512)]})
    rows = build_manifest(root).rows
    assert len(rows) == 2
    assert {row.width for row in rows} == {512}


def test_each_class_is_split_seventy_fifteen_fifteen(tmp_path):
    root = build_interim(
        tmp_path, {"healthy": distinct(100), "grey_blight": distinct(100)}
    )
    rows = build_manifest(root).rows
    for canonical in ("healthy", "grey_blight"):
        counts = Counter(row.split for row in rows if row.canonical == canonical)
        assert counts == {"train": 70, "val": 15, "test": 15}


def test_no_perceptual_hash_appears_in_two_splits(tmp_path):
    root = build_interim(tmp_path, {"healthy": distinct(40)})
    rows = build_manifest(root).rows
    by_hash = defaultdict(set)
    for row in rows:
        by_hash[row.phash].add(row.split)
    assert all(len(splits) == 1 for splits in by_hash.values())


def test_the_split_is_deterministic_for_a_given_seed(tmp_path):
    root = build_interim(tmp_path, {"healthy": distinct(30)})
    first = {(row.path, row.split) for row in build_manifest(root, seed=42).rows}
    assert first == {(row.path, row.split) for row in build_manifest(root, seed=42).rows}
    assert first != {(row.path, row.split) for row in build_manifest(root, seed=7).rows}


def test_a_class_with_three_images_still_gets_one_in_every_split(tmp_path):
    # 70/15/15 of three rounds validation and test to zero. An empty test split
    # would silently drop that class from every metric we report.
    root = build_interim(tmp_path, {"other_disease": distinct(3)})
    assert Counter(row.split for row in build_manifest(root).rows) == {
        "train": 1,
        "val": 1,
        "test": 1,
    }


def test_a_class_with_one_image_puts_it_in_train(tmp_path):
    root = build_interim(tmp_path, {"other_disease": distinct(1)})
    assert [row.split for row in build_manifest(root).rows] == ["train"]


def test_the_manifest_csv_carries_the_agreed_header(tmp_path):
    rows = build_manifest(build_interim(tmp_path, {"healthy": distinct(4)})).rows
    out = tmp_path / "manifest.csv"
    write_manifest(rows, out)
    assert out.read_text(encoding="utf-8").splitlines()[0] == (
        "path,canonical,source,phash,width,height,split"
    )


def test_summarise_reports_every_split_for_every_class(tmp_path):
    root = build_interim(tmp_path, {"healthy": distinct(10), "algal_spot": distinct(10)})
    summary = summarise(build_manifest(root).rows)
    assert set(summary) == {"healthy", "algal_spot"}
    assert all(set(splits) == {"train", "val", "test"} for splits in summary.values())


def test_the_same_photo_labelled_two_different_classes_is_dropped_as_a_conflict(tmp_path):
    # One photograph carrying two different labels across sources cannot be
    # resolved by picking the one that sorts first: that trains the model on a
    # label a human never agreed with. Drop the group and report it.
    root = tmp_path / "interim"
    for canonical in ("healthy", "grey_blight"):
        dest = root / "fake" / canonical / "shared.jpg"
        dest.parent.mkdir(parents=True, exist_ok=True)
        write_leaf_photo(dest, seed=11)
    manifest = build_manifest(root)
    assert manifest.rows == ()
    assert manifest.conflicting_groups == 1


def test_collapsed_duplicates_are_counted(tmp_path):
    root = build_interim(tmp_path, {"healthy": [("a", 512), ("a", 256), ("b", 512)]})
    assert build_manifest(root).collapsed_duplicates == 1
