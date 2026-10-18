"""Evaluate a trained classifier and write the report that gets committed.

The report is the evidence. Nobody on the team will re-run the training to
check a claim three days before a demo, so the numbers that go into
`docs/eval/` have to be produced by this module and not by hand.

`other_disease` gets its own row for the same reason macro-F1 is the selection
metric: it is 36% of the corpus, and a model that hides behind it would look
fine on any aggregate.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader

from teasmart_ml.classes import CANONICAL_CLASSES
from teasmart_ml.dataset import ManifestDataset
from teasmart_ml.metrics import (
    ClassMetrics,
    FloorResult,
    UnreachableTargetError,
    choose_confidence_floor,
    confusion_matrix,
    macro_f1,
    per_class_metrics,
)

TARGET_ACCURACY = 0.90


@dataclass(frozen=True)
class EvaluationReport:
    n: int
    accuracy: float
    macro_f1: float
    confusion: np.ndarray
    per_class: list[ClassMetrics]
    floor: FloorResult | None
    floor_error: str | None


def predict_probs(
    model: nn.Module,
    dataset: ManifestDataset,
    *,
    device: str = "cuda",
    batch_size: int = 32,
    num_workers: int = 4,
) -> tuple[np.ndarray, np.ndarray]:
    """Softmax probabilities and true labels, in dataset order.

    Softmax is applied here rather than in the model because the ONNX graph
    emits raw logits by contract (spec 8.4), and the browser applies its own.
    """
    loader = DataLoader(
        dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers
    )
    torch_device = torch.device(device)
    model.to(torch_device)
    model.eval()

    probs: list[np.ndarray] = []
    labels: list[np.ndarray] = []
    with torch.no_grad():
        for images, targets in loader:
            logits = model(images.to(torch_device))
            probs.append(torch.softmax(logits.float(), dim=1).cpu().numpy())
            labels.append(targets.numpy())

    return np.concatenate(probs), np.concatenate(labels)


def evaluate_dataset(
    model: nn.Module,
    dataset: ManifestDataset,
    *,
    device: str = "cuda",
    batch_size: int = 32,
    num_workers: int = 4,
    target_accuracy: float = TARGET_ACCURACY,
) -> EvaluationReport:
    """Score a model on one split, including the confidence floor it implies."""
    probs, labels = predict_probs(
        model, dataset, device=device, batch_size=batch_size, num_workers=num_workers
    )
    predictions = probs.argmax(axis=1)
    cm = confusion_matrix(labels, predictions, n_classes=len(CANONICAL_CLASSES))

    floor: FloorResult | None = None
    floor_error: str | None = None
    try:
        floor = choose_confidence_floor(
            probs, labels, target_accuracy=target_accuracy
        )
    except UnreachableTargetError as error:
        # Recorded, not raised. A model with no usable threshold is a result,
        # and the report has to be written so that result is visible.
        floor_error = str(error)

    return EvaluationReport(
        n=int(labels.shape[0]),
        accuracy=float((predictions == labels).mean()),
        macro_f1=macro_f1(cm),
        confusion=cm,
        per_class=per_class_metrics(cm),
        floor=floor,
        floor_error=floor_error,
    )


def report_markdown(report: EvaluationReport, *, title: str) -> str:
    """The committed evidence, as markdown."""
    lines = [
        f"## {title}",
        "",
        f"- images: **{report.n}**",
        f"- accuracy: **{report.accuracy:.4f}**",
        f"- macro-F1: **{report.macro_f1:.4f}**",
        "",
        "| class | precision | recall | F1 | support |",
        "|---|---|---|---|---|",
    ]
    for canonical, row in zip(CANONICAL_CLASSES, report.per_class):
        lines.append(
            f"| `{canonical}` | {row.precision:.4f} | {row.recall:.4f} | "
            f"{row.f1:.4f} | {row.support} |"
        )

    lines += ["", "### Confusion matrix", "", "Rows are the true class."]
    header = " | ".join(f"`{name}`" for name in CANONICAL_CLASSES)
    lines += ["", f"| true \\ predicted | {header} |", "|---" * 6 + "|"]
    for canonical, row in zip(CANONICAL_CLASSES, report.confusion):
        cells = " | ".join(str(int(value)) for value in row)
        lines.append(f"| `{canonical}` | {cells} |")

    lines += ["", "### Confidence floor (`min_confidence`)", ""]
    if report.floor is not None:
        lines += [
            f"- **`min_confidence` = {report.floor.floor:.2f}**",
            f"- accepted predictions: {report.floor.accepted} of "
            f"{report.floor.total}",
            f"- accuracy among accepted: **{report.floor.accepted_accuracy:.4f}**",
            f"- downgraded to `other_disease`: "
            f"**{report.floor.downgraded_pct:.2f}%**",
            "",
            "The smallest floor at which accepted predictions reach the target "
            "accuracy. The downgrade percentage matters as much as the floor: a "
            "system that answers \"I do not know\" too often is not used.",
        ]
    else:
        lines += [
            "**No usable `min_confidence` exists for this model.**",
            "",
            f"> {report.floor_error}",
            "",
            "The provisional 0.60 in `Settings` stays until a model clears the "
            "bar. Nothing offline should be enabled on this basis.",
        ]
    return "\n".join(lines) + "\n"


def load_checkpoint(path: Path, *, pretrained: bool = False) -> nn.Module:
    """Rebuild the model from a training checkpoint.

    Asserts the stored class order, because a checkpoint whose columns mean
    something else than `CANONICAL_CLASSES` would score well and advise wrongly.
    """
    from teasmart_ml.train import build_model

    payload = torch.load(path, map_location="cpu", weights_only=True)
    stored = list(payload["class_order"])
    if stored != list(CANONICAL_CLASSES):
        raise ValueError(
            f"checkpoint class order {stored} does not match {list(CANONICAL_CLASSES)}"
        )
    model = build_model(len(CANONICAL_CLASSES), pretrained=pretrained)
    model.load_state_dict(payload["state_dict"])
    model.eval()
    return model
