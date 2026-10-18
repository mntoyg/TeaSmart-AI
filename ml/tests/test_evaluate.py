"""Evaluation, tested against a model whose answers are known in advance.

A stub model is used so the assertions are about the reporting, not about
whether twelve images taught anything. The numbers this module produces are the
only evidence anyone will have that the classifier is safe to show a farmer, so
they have to be right even in the cases that embarrass the model.
"""

import csv

import pytest
import torch
from torch import nn

from teasmart_ml.classes import CANONICAL_CLASSES
from teasmart_ml.dataset import ManifestDataset
from teasmart_ml.evaluate import evaluate_dataset, predict_probs, report_markdown
from tests.fixtures import write_leaf_photo


class _AlwaysClass(nn.Module):
    """Answers one class, confidently. The failure mode worth testing."""

    def __init__(self, index: int, logit: float = 9.0) -> None:
        super().__init__()
        self.index = index
        self.logit = logit

    def forward(self, images: torch.Tensor) -> torch.Tensor:
        out = torch.zeros(images.shape[0], len(CANONICAL_CLASSES))
        out[:, self.index] = self.logit
        return out


class _Scripted(nn.Module):
    """Returns a prepared answer per image, in dataset order.

    The loader is unshuffled for evaluation, so position is a reliable key and
    the test can decide exactly what the model gets right.
    """

    def __init__(self, answers: list[int], logit: float = 9.0) -> None:
        super().__init__()
        self.answers = answers
        self.logit = logit
        self.position = 0

    def forward(self, images: torch.Tensor) -> torch.Tensor:
        count = images.shape[0]
        chunk = self.answers[self.position : self.position + count]
        self.position += count
        out = torch.zeros(count, len(CANONICAL_CLASSES))
        for row, index in enumerate(chunk):
            out[row, index] = self.logit
        return out


def _corpus(tmp_path, plan):
    root = tmp_path / "interim"
    csv_path = tmp_path / "manifest.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["path", "canonical", "source", "phash", "width", "height", "split"]
        )
        for index, canonical in enumerate(plan):
            relative = f"agml/{canonical}/img-{index:04d}.jpg"
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            write_leaf_photo(path, seed=index)
            writer.writerow([relative, canonical, "agml", "0" * 16, 64, 64, "test"])
    return ManifestDataset(csv_path, root, split="test")


def test_predict_probs_returns_a_probability_row_per_image(tmp_path) -> None:
    dataset = _corpus(tmp_path, ["healthy", "grey_blight", "healthy"])

    probs, labels = predict_probs(
        _AlwaysClass(3), dataset, device="cpu", batch_size=2, num_workers=0
    )

    assert probs.shape == (3, len(CANONICAL_CLASSES))
    assert probs.sum(axis=1) == pytest.approx([1.0, 1.0, 1.0], abs=1e-5)
    assert labels.tolist() == [3, 0, 3]


def test_evaluate_dataset_exposes_a_class_the_model_never_finds(tmp_path) -> None:
    # The important failure: a model that answers healthy to everything scores
    # 50% accuracy here and must not look acceptable.
    dataset = _corpus(tmp_path, ["healthy", "grey_blight"])

    report = evaluate_dataset(
        _AlwaysClass(3), dataset, device="cpu", batch_size=2, num_workers=0
    )

    assert report.accuracy == pytest.approx(0.5)
    assert report.per_class[0].recall == pytest.approx(0.0)
    assert report.per_class[3].recall == pytest.approx(1.0)
    # Macro-F1 over five classes, only one of which scores at all.
    assert report.macro_f1 < 0.2


def test_evaluate_dataset_reports_the_confidence_floor_it_can_measure(
    tmp_path,
) -> None:
    dataset = _corpus(tmp_path, ["healthy"] * 4 + ["grey_blight"] * 4)

    report = evaluate_dataset(
        _Scripted([3, 3, 3, 3, 0, 0, 0, 0]),
        dataset,
        device="cpu",
        batch_size=4,
        num_workers=0,
        target_accuracy=0.9,
    )

    assert report.floor is not None
    assert report.floor.accepted == 8
    assert report.floor_error is None


def test_evaluate_dataset_records_why_no_floor_exists_instead_of_raising(
    tmp_path,
) -> None:
    # A model this bad has no usable threshold. The report still has to be
    # written, with the reason in it, or the run ends in a traceback and
    # nobody can see how bad it was.
    dataset = _corpus(tmp_path, ["healthy"] + ["grey_blight"] * 9)

    report = evaluate_dataset(
        _AlwaysClass(3), dataset, device="cpu", batch_size=4, num_workers=0
    )

    assert report.floor is None
    assert report.floor_error is not None
    assert "0.90" in report.floor_error


def test_report_markdown_names_every_class_and_the_floor(tmp_path) -> None:
    dataset = _corpus(tmp_path, ["healthy"] * 4 + ["grey_blight"] * 4)
    report = evaluate_dataset(
        _Scripted([3, 3, 3, 3, 0, 0, 0, 0]),
        dataset,
        device="cpu",
        batch_size=4,
        num_workers=0,
    )

    text = report_markdown(report, title="test split")

    for canonical in CANONICAL_CLASSES:
        assert canonical in text
    assert "macro-F1" in text
    assert "min_confidence" in text
