"""The ONNX export is the contract the browser loads; its shape is not optional.

Spec section 8.4 names the file, the input, the output and the fact that the
output is raw logits. A graph that disagrees on any of those produces a PWA that
is confidently wrong, which is the one failure this product cannot have.
"""

import numpy as np
import pytest
import torch
from torch import nn

from teasmart_ml.classes import CANONICAL_CLASSES
from teasmart_ml.export_onnx import (
    INPUT_NAME,
    OUTPUT_NAME,
    ParityResult,
    export_fp32,
    measure_parity,
)


class _Tiny(nn.Module):
    """A real graph, small enough to export in a test."""

    def __init__(self) -> None:
        super().__init__()
        self.body = nn.Sequential(
            nn.Conv2d(3, 4, 3, stride=2, padding=1),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Linear(4, len(CANONICAL_CLASSES)),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.body(x)


def test_export_names_the_input_and_output_from_the_contract(tmp_path) -> None:
    import onnxruntime as ort

    path = export_fp32(_Tiny(), tmp_path / "m.onnx")
    session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])

    assert [i.name for i in session.get_inputs()] == [INPUT_NAME]
    assert [o.name for o in session.get_outputs()] == [OUTPUT_NAME]
    assert session.get_inputs()[0].shape == [1, 3, 224, 224]
    assert session.get_outputs()[0].shape == [1, len(CANONICAL_CLASSES)]


def test_exported_graph_emits_logits_not_probabilities(tmp_path) -> None:
    import onnxruntime as ort

    path = export_fp32(_Tiny(), tmp_path / "m.onnx")
    session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    rng = np.random.default_rng(3)
    batch = rng.standard_normal((1, 3, 224, 224), dtype=np.float32)

    out = session.run([OUTPUT_NAME], {INPUT_NAME: batch})[0]

    # Probabilities would sum to one. These must not.
    assert not np.isclose(out.sum(), 1.0, atol=1e-3)


def test_measure_parity_agrees_with_itself(tmp_path) -> None:
    model = _Tiny().eval()
    path = export_fp32(model, tmp_path / "m.onnx")
    rng = np.random.default_rng(5)
    batch = [rng.standard_normal((3, 224, 224)).astype(np.float32) for _ in range(4)]

    result = measure_parity(model, path, batch)

    assert isinstance(result, ParityResult)
    assert result.top1_agreement == pytest.approx(1.0)
    assert result.max_prob_delta < 1e-4
    assert result.n == 4


def test_measure_parity_catches_a_graph_that_is_not_the_model(tmp_path) -> None:
    # The check has to be able to fail, or it is decoration. Exporting one
    # model and comparing against another must show up as disagreement.
    exported = _Tiny().eval()
    other = _Tiny().eval()
    path = export_fp32(exported, tmp_path / "m.onnx")
    rng = np.random.default_rng(9)
    batch = [rng.standard_normal((3, 224, 224)).astype(np.float32) for _ in range(4)]

    result = measure_parity(other, path, batch)

    assert result.max_prob_delta > 0.01
