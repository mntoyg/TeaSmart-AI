"""Export the trained classifier to ONNX for onnxruntime-web, and prove parity.

Names and shapes come from spec section 8.4 and are not a local choice: the PWA
loads this file by name and reads `logits` by name. Batch stays fixed at 1
because the browser classifies one photograph at a time and a fixed shape is
one less thing for onnxruntime-web to negotiate.

Quantisation is attempted, not assumed. MobileNetV3 is a hard case for int8 -
depthwise convolutions and hard-swish both lose resolution - so the int8 graph
is measured against the Python pipeline and kept only if it stays inside the
contract's 0.05 probability bound. A 21 MB download that gives the right answer
beats a 6 MB one that does not.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from torch import nn

INPUT_NAME = "input"
OUTPUT_NAME = "logits"
OPSET = 17
PARITY_PROB_BOUND = 0.05


@dataclass(frozen=True)
class ParityResult:
    n: int
    top1_agreement: float
    max_prob_delta: float

    @property
    def passed(self) -> bool:
        return self.top1_agreement == 1.0 and self.max_prob_delta <= PARITY_PROB_BOUND


def export_fp32(model: nn.Module, out_path: Path) -> Path:
    """Write the float32 graph. Input `input`, output `logits`, batch 1."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    model = model.eval().cpu()
    dummy = torch.zeros(1, 3, 224, 224)
    torch.onnx.export(
        model,
        dummy,
        str(out_path),
        input_names=[INPUT_NAME],
        output_names=[OUTPUT_NAME],
        opset_version=OPSET,
        do_constant_folding=True,
        dynamo=False,
    )
    return out_path


def quantize_int8(
    fp32_path: Path, out_path: Path, calibration: Sequence[np.ndarray]
) -> Path:
    """Static int8 quantisation, calibrated on real preprocessed images.

    Static rather than dynamic because this is a convolutional network: dynamic
    quantisation leaves the convolutions in float and saves almost nothing.
    Calibration uses images from the validation split, preprocessed exactly as
    inference will preprocess them.
    """
    from onnxruntime.quantization import CalibrationDataReader, QuantType
    from onnxruntime.quantization import quantize_static
    from onnxruntime.quantization.shape_inference import quant_pre_process

    class _Reader(CalibrationDataReader):
        def __init__(self, arrays: Sequence[np.ndarray]) -> None:
            self._rows = iter(
                [{INPUT_NAME: array.reshape(1, 3, 224, 224)} for array in arrays]
            )

        def get_next(self):  # noqa: ANN201 - signature fixed by onnxruntime
            return next(self._rows, None)

    out_path = Path(out_path)
    prepared = out_path.with_suffix(".prepared.onnx")
    quant_pre_process(str(fp32_path), str(prepared), skip_symbolic_shape=True)
    quantize_static(
        str(prepared),
        str(out_path),
        _Reader(calibration),
        activation_type=QuantType.QUInt8,
        weight_type=QuantType.QInt8,
        per_channel=True,
    )
    prepared.unlink(missing_ok=True)
    return out_path


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max(axis=-1, keepdims=True)
    exponentiated = np.exp(shifted)
    return exponentiated / exponentiated.sum(axis=-1, keepdims=True)


def measure_parity(
    model: nn.Module, onnx_path: Path, images: Iterable[np.ndarray]
) -> ParityResult:
    """Compare the ONNX graph with the Python model on preprocessed images.

    Both sides get the identical CHW float32 array, so any difference is the
    graph and not the preprocessing. Top-1 has to agree on every image;
    quantisation is allowed to move probabilities but not decisions.
    """
    import onnxruntime as ort

    session = ort.InferenceSession(
        str(onnx_path), providers=["CPUExecutionProvider"]
    )
    model = model.eval().cpu()

    agreements = 0
    count = 0
    worst = 0.0
    with torch.no_grad():
        for array in images:
            batch = np.ascontiguousarray(
                array.reshape(1, 3, 224, 224), dtype=np.float32
            )
            onnx_probs = _softmax(
                session.run([OUTPUT_NAME], {INPUT_NAME: batch})[0]
            )[0]
            torch_probs = (
                torch.softmax(model(torch.from_numpy(batch)).float(), dim=1)
                .numpy()[0]
            )
            worst = max(worst, float(np.abs(onnx_probs - torch_probs).max()))
            agreements += int(onnx_probs.argmax() == torch_probs.argmax())
            count += 1

    return ParityResult(
        n=count,
        top1_agreement=agreements / count if count else 0.0,
        max_prob_delta=worst,
    )
