"""The manifest is the only description of the corpus; reading it wrong is silent.

Two things here are easy to get wrong and impossible to notice later: the class
index order, which must match the order the API serves and the ONNX output
columns, and the fact that manifest paths are relative to the interim root.
"""

import csv

import numpy as np
import pytest

from teasmart_ml.classes import CANONICAL_CLASSES
from teasmart_ml.dataset import (
    ManifestDataset,
    SplitMissingError,
    class_counts,
    class_weights,
)
from tests.fixtures import write_leaf_photo


def _manifest(tmp_path, rows):
    root = tmp_path / "interim"
    csv_path = tmp_path / "manifest.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["path", "canonical", "source", "phash", "width", "height", "split"]
        )
        for index, (canonical, split) in enumerate(rows):
            relative = f"agml/{canonical}/img-{index:04d}.jpg"
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            write_leaf_photo(path, seed=index)
            writer.writerow(
                [relative.replace("/", "\\"), canonical, "agml", "0" * 16, 64, 64, split]
            )
    return csv_path, root


def test_class_index_follows_the_canonical_order_not_the_file_order(tmp_path) -> None:
    # healthy appears first in the file but is index 3 in the contract.
    csv_path, root = _manifest(
        tmp_path, [("healthy", "train"), ("grey_blight", "train")]
    )
    dataset = ManifestDataset(csv_path, root, split="train")

    assert dataset.classes == list(CANONICAL_CLASSES)
    assert dataset.labels == [CANONICAL_CLASSES.index("healthy"), 0]


def test_dataset_loads_only_the_requested_split(tmp_path) -> None:
    csv_path, root = _manifest(
        tmp_path,
        [("healthy", "train"), ("healthy", "val"), ("grey_blight", "test")],
    )
    assert len(ManifestDataset(csv_path, root, split="train")) == 1
    assert len(ManifestDataset(csv_path, root, split="val")) == 1
    assert len(ManifestDataset(csv_path, root, split="test")) == 1


def test_dataset_refuses_an_empty_split_instead_of_training_on_nothing(
    tmp_path,
) -> None:
    csv_path, root = _manifest(tmp_path, [("healthy", "train")])
    with pytest.raises(SplitMissingError):
        ManifestDataset(csv_path, root, split="val")


def test_dataset_resolves_paths_against_the_interim_root(tmp_path) -> None:
    csv_path, root = _manifest(tmp_path, [("healthy", "train")])
    dataset = ManifestDataset(csv_path, root, split="train")

    image, label = dataset[0]

    assert tuple(image.shape) == (3, 224, 224)
    assert label == CANONICAL_CLASSES.index("healthy")


def test_class_weights_are_inverse_frequency_so_the_rare_class_is_seen(
    tmp_path,
) -> None:
    # other_disease is 36% of the real corpus. Without this the model learns to
    # answer other_disease and still scores well on accuracy.
    csw = [("other_disease", "train")] * 8 + [("grey_blight", "train")] * 2
    csv_path, root = _manifest(tmp_path, csw)
    dataset = ManifestDataset(csv_path, root, split="train")

    counts = class_counts(dataset)
    assert counts[CANONICAL_CLASSES.index("other_disease")] == 8
    assert counts[CANONICAL_CLASSES.index("grey_blight")] == 2

    weights = class_weights(dataset)
    # A grey blight sample must be drawn four times as often as an
    # other_disease one, and absent classes must not produce an infinity.
    rare = CANONICAL_CLASSES.index("grey_blight")
    common = CANONICAL_CLASSES.index("other_disease")
    assert weights[rare] / weights[common] == pytest.approx(4.0)
    # brown_blight is absent from this split: weight 0, not an infinity.
    assert weights[CANONICAL_CLASSES.index("brown_blight")] == 0.0
    assert np.isfinite(np.asarray(weights)).all()
