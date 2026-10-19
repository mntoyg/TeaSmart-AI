"""Metrics are computed here rather than imported, so they are testable.

The numbers in docs/eval decide whether this model is allowed near a tea farm.
A metric nobody can check is worse than no metric.
"""

import numpy as np
import pytest

from teasmart_ml.metrics import (
    UnreachableTargetError,
    choose_confidence_floor,
    confusion_matrix,
    macro_f1,
    per_class_metrics,
)


def test_confusion_matrix_counts_true_rows_against_predicted_columns() -> None:
    cm = confusion_matrix(
        np.array([0, 0, 1, 2]), np.array([0, 1, 1, 0]), n_classes=3
    )
    assert cm.tolist() == [
        [1, 1, 0],
        [0, 1, 0],
        [1, 0, 0],
    ]


def test_per_class_metrics_against_hand_computed_values() -> None:
    # class 0: 1 of 2 predicted correct, 1 of 2 actual found
    # class 1: 1 of 2 predicted correct, 1 of 1 actual found
    # class 2: never predicted, 1 actual missed
    cm = confusion_matrix(
        np.array([0, 0, 1, 2]), np.array([0, 1, 1, 0]), n_classes=3
    )
    rows = per_class_metrics(cm)

    assert [r.support for r in rows] == [2, 1, 1]
    assert rows[0].precision == pytest.approx(0.5)
    assert rows[0].recall == pytest.approx(0.5)
    assert rows[0].f1 == pytest.approx(0.5)
    assert rows[1].precision == pytest.approx(0.5)
    assert rows[1].recall == pytest.approx(1.0)
    assert rows[1].f1 == pytest.approx(2 / 3)
    # Never predicted and never found: zero, not a NaN that hides the miss.
    assert rows[2].precision == pytest.approx(0.0)
    assert rows[2].recall == pytest.approx(0.0)
    assert rows[2].f1 == pytest.approx(0.0)


def test_macro_f1_averages_over_classes_not_over_samples() -> None:
    # A rare class predicted perfectly and a common class predicted badly must
    # not be hidden by the common one. other_disease is 36% of the corpus.
    y_true = np.array([0] * 90 + [1] * 10)
    y_pred = np.array([0] * 90 + [0] * 10)
    cm = confusion_matrix(y_true, y_pred, n_classes=2)

    # 90% of samples are right, but one of two classes is never found.
    assert macro_f1(cm) == pytest.approx(0.5 * (0.9473684210526315 + 0.0))


def test_macro_f1_is_one_when_every_prediction_is_right() -> None:
    labels = np.array([0, 1, 2, 3, 4])
    cm = confusion_matrix(labels, labels, n_classes=5)
    assert macro_f1(cm) == pytest.approx(1.0)


def _probs(top: list[float], n_classes: int = 5) -> np.ndarray:
    """Probability rows whose maximum is `top`, in column 0."""
    rest = [(1.0 - t) / (n_classes - 1) for t in top]
    return np.array([[t] + [r] * (n_classes - 1) for t, r in zip(top, rest, strict=False)])


def test_confidence_floor_is_the_smallest_grid_value_reaching_the_target() -> None:
    # Confident rows are right, unconfident rows are wrong. Accepting
    # everything gives 0.90; accepting down to 0.62 gives 18/19 = 0.947, still
    # short of 0.95. The first floor that clears it is 0.63.
    probs = _probs([0.95] * 18 + [0.62, 0.60])
    labels = np.array([0] * 18 + [1, 1])

    result = choose_confidence_floor(probs, labels, target_accuracy=0.95)

    assert result.floor == pytest.approx(0.63)
    assert result.accepted == 18
    assert result.accepted_accuracy == pytest.approx(1.0)
    assert result.downgraded_pct == pytest.approx(10.0)


def test_confidence_floor_reports_the_cheapest_floor_not_the_safest() -> None:
    # Every row is right, so chance-level confidence already meets the target
    # and no prediction should be thrown away.
    probs = _probs([0.30] * 10)
    result = choose_confidence_floor(
        np.asarray(probs), np.zeros(10, dtype=int), target_accuracy=0.90
    )

    assert result.floor == pytest.approx(0.20)
    assert result.downgraded_pct == pytest.approx(0.0)


def test_confidence_floor_refuses_a_floor_that_accepts_almost_nothing() -> None:
    # One lucky confident row would reach 1.00 accuracy at a high floor while
    # discarding 95% of the predictions. That is not a usable threshold: a system
    # that answers "I do not know" nineteen times out of twenty is not used.
    probs = _probs([0.99] + [0.80] * 19)
    labels = np.array([0] + [1] * 19)

    with pytest.raises(UnreachableTargetError) as excinfo:
        choose_confidence_floor(probs, labels, target_accuracy=0.90)

    assert "0.90" in str(excinfo.value)


def test_confidence_floor_rejects_a_label_probability_shape_mismatch() -> None:
    with pytest.raises(ValueError):
        choose_confidence_floor(_probs([0.9, 0.9]), np.array([0]), target_accuracy=0.9)
