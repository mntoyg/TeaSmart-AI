"""Training wiring, tested on a corpus small enough to run on the CPU.

The point is not that the model learns here - twelve images teach nothing. It is
that the loop saves the right checkpoint, stops when validation stops improving,
and reports the epoch it actually chose, so that a real run on the 4 GB card is
not the first time any of that is exercised.
"""

import csv

import pytest
import torch

from teasmart_ml.classes import CANONICAL_CLASSES
from teasmart_ml.train import EarlyStopping, TrainConfig, build_model, train
from tests.fixtures import write_leaf_photo


def _corpus(tmp_path) -> tuple[object, object]:
    root = tmp_path / "interim"
    csv_path = tmp_path / "manifest.csv"
    plan = [("grey_blight", "train")] * 4 + [("healthy", "train")] * 4
    plan += [("grey_blight", "val"), ("healthy", "val")]
    plan += [("grey_blight", "test"), ("healthy", "test")]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["path", "canonical", "source", "phash", "width", "height", "split"]
        )
        for index, (canonical, split) in enumerate(plan):
            relative = f"agml/{canonical}/img-{index:04d}.jpg"
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            write_leaf_photo(path, seed=index)
            writer.writerow([relative, canonical, "agml", "0" * 16, 64, 64, split])
    return csv_path, root


def test_build_model_has_one_output_per_canonical_class() -> None:
    model = build_model(len(CANONICAL_CLASSES), pretrained=False)
    out = model(torch.zeros(2, 3, 224, 224))
    assert tuple(out.shape) == (2, len(CANONICAL_CLASSES))


def test_build_model_emits_logits_not_probabilities() -> None:
    # The ONNX contract says raw logits. A softmax baked into the graph would
    # make the browser apply it twice and flatten every confidence.
    model = build_model(len(CANONICAL_CLASSES), pretrained=False)
    out = model(torch.randn(4, 3, 224, 224))
    assert not torch.allclose(out.sum(dim=1), torch.ones(4), atol=1e-3)


def test_early_stopping_keeps_the_best_score_not_the_last() -> None:
    stopper = EarlyStopping(patience=2)
    assert stopper.update(0.50) is True  # improved
    assert stopper.update(0.40) is False
    assert stopper.should_stop is False
    assert stopper.update(0.45) is False
    assert stopper.should_stop is True
    assert stopper.best == pytest.approx(0.50)


def test_early_stopping_resets_its_patience_on_an_improvement() -> None:
    stopper = EarlyStopping(patience=2)
    stopper.update(0.50)
    stopper.update(0.40)
    assert stopper.update(0.60) is True
    assert stopper.should_stop is False
    assert stopper.best == pytest.approx(0.60)


def test_train_writes_a_checkpoint_and_a_history(tmp_path) -> None:
    csv_path, root = _corpus(tmp_path)
    out_dir = tmp_path / "artifacts"

    result = train(
        csv_path,
        root,
        out_dir,
        TrainConfig(
            epochs=2,
            batch_size=2,
            device="cpu",
            num_workers=0,
            pretrained=False,
            patience=5,
        ),
    )

    assert result.checkpoint.exists()
    assert len(result.history) == 2
    assert result.best_epoch in (1, 2)
    # The checkpoint is the best epoch, not whatever the loop finished with.
    assert result.best_macro_f1 == pytest.approx(
        max(row.val_macro_f1 for row in result.history)
    )
    state = torch.load(result.checkpoint, map_location="cpu", weights_only=True)
    assert state["class_order"] == list(CANONICAL_CLASSES)


def test_train_stops_early_when_validation_stops_improving(tmp_path) -> None:
    csv_path, root = _corpus(tmp_path)
    result = train(
        csv_path,
        root,
        tmp_path / "artifacts",
        TrainConfig(
            epochs=10,
            batch_size=2,
            device="cpu",
            num_workers=0,
            pretrained=False,
            patience=1,
        ),
    )
    # Ten epochs were allowed; patience 1 on a twelve-image corpus must cut it
    # short, or the patience argument is not wired to anything.
    assert len(result.history) < 10
