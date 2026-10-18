"""Classification metrics, and the confidence floor the API ships.

Written out rather than pulled from scikit-learn for two reasons: the only
operations needed are counts over a confusion matrix, and the floor search is a
project-specific decision that has to be readable by whoever audits the model
before it tells a farmer to spray.

Macro averages throughout. A sample average would let `other_disease`, which is
36% of the corpus, carry a model that cannot find grey blight.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


class UnreachableTargetError(RuntimeError):
    """No usable confidence floor reaches the required accuracy."""


@dataclass(frozen=True)
class ClassMetrics:
    precision: float
    recall: float
    f1: float
    support: int


@dataclass(frozen=True)
class FloorResult:
    """The confidence floor to ship, and what it costs."""

    floor: float
    accepted: int
    total: int
    accepted_accuracy: float
    downgraded_pct: float


def confusion_matrix(
    y_true: np.ndarray, y_pred: np.ndarray, *, n_classes: int
) -> np.ndarray:
    """Rows are the true class, columns the predicted class."""
    if y_true.shape != y_pred.shape:
        raise ValueError(f"shape mismatch: {y_true.shape} vs {y_pred.shape}")
    cm = np.zeros((n_classes, n_classes), dtype=np.int64)
    np.add.at(cm, (y_true.astype(int), y_pred.astype(int)), 1)
    return cm


def per_class_metrics(cm: np.ndarray) -> list[ClassMetrics]:
    """Precision, recall, F1 and support for every class.

    A class that is never predicted and never found scores zero rather than
    NaN: a NaN would drop out of an average and hide the miss.
    """
    rows: list[ClassMetrics] = []
    for index in range(cm.shape[0]):
        true_positive = int(cm[index, index])
        predicted = int(cm[:, index].sum())
        actual = int(cm[index, :].sum())
        precision = true_positive / predicted if predicted else 0.0
        recall = true_positive / actual if actual else 0.0
        denominator = precision + recall
        f1 = 2 * precision * recall / denominator if denominator else 0.0
        rows.append(ClassMetrics(precision, recall, f1, actual))
    return rows


def macro_f1(cm: np.ndarray) -> float:
    """Unweighted mean F1 over every class present in the matrix."""
    rows = per_class_metrics(cm)
    return float(np.mean([row.f1 for row in rows])) if rows else 0.0


def choose_confidence_floor(
    probs: np.ndarray,
    labels: np.ndarray,
    *,
    target_accuracy: float,
    min_accepted_frac: float = 0.50,
) -> FloorResult:
    """The smallest floor at which accepted predictions reach the target.

    A prediction is accepted when its top probability is at or above the floor,
    and otherwise reported as `other_disease` with `low_confidence` set. The
    search runs on a two-decimal grid because the result is shipped as a config
    value, and it starts at chance level, below which a floor means nothing.

    `min_accepted_frac` exists because a high floor reaches any accuracy
    trivially by accepting almost nothing. A system that answers "I do not
    know" to most photographs has a perfect score and no users, so a floor that
    keeps less than half the predictions is not a solution.
    """
    if probs.ndim != 2:
        raise ValueError(f"probs must be 2-D, got shape {probs.shape}")
    if probs.shape[0] != labels.shape[0]:
        raise ValueError(
            f"row mismatch: {probs.shape[0]} probability rows, "
            f"{labels.shape[0]} labels"
        )

    total = probs.shape[0]
    top_prob = probs.max(axis=1)
    correct = probs.argmax(axis=1) == labels.astype(int)
    chance = math.ceil(100 / probs.shape[1]) / 100

    for step in range(int(round(chance * 100)), 100):
        floor = step / 100
        keep = top_prob >= floor
        accepted = int(keep.sum())
        if accepted / total < min_accepted_frac:
            break
        accuracy = float(correct[keep].mean()) if accepted else 0.0
        if accuracy >= target_accuracy:
            return FloorResult(
                floor=floor,
                accepted=accepted,
                total=total,
                accepted_accuracy=accuracy,
                downgraded_pct=100.0 * (total - accepted) / total,
            )

    raise UnreachableTargetError(
        f"no floor between {chance:.2f} and 0.99 reaches {target_accuracy:.2f} "
        f"accuracy while keeping at least {min_accepted_frac:.0%} of "
        f"{total} predictions"
    )
