"""The eval transform is half of a contract; the browser implements the other.

Spec section 8.4 fixes these five steps for both sides. Anything that changes
here changes what onnxruntime-web has to do, and a silent disagreement shows up
as a model that is accurate in Python and wrong on a phone.
"""

import numpy as np
import pytest
from PIL import Image

from teasmart_ml.transforms import (
    EVAL_SIZE,
    IMAGENET_MEAN,
    IMAGENET_STD,
    eval_array,
    eval_tensor,
    train_transform,
)


def test_eval_array_shape_and_dtype_match_the_onnx_input() -> None:
    out = eval_array(Image.new("RGB", (640, 480), (10, 20, 30)))
    assert out.shape == (3, *EVAL_SIZE)
    assert out.dtype == np.float32


def test_eval_array_normalises_each_channel_with_its_own_statistics() -> None:
    # A flat colour makes the arithmetic checkable by hand, and a channel-order
    # or mean/std mix-up cannot survive it.
    out = eval_array(Image.new("RGB", (64, 64), (255, 0, 128)))
    expected = [
        (1.0 - IMAGENET_MEAN[0]) / IMAGENET_STD[0],
        (0.0 - IMAGENET_MEAN[1]) / IMAGENET_STD[1],
        (128 / 255 - IMAGENET_MEAN[2]) / IMAGENET_STD[2],
    ]
    for channel, value in enumerate(expected):
        assert out[channel].mean() == pytest.approx(value, abs=1e-5)


def test_eval_array_stretches_instead_of_cropping() -> None:
    # preserve_aspect_ratio is false in the contract. A crop would discard a
    # lesion at the edge of a wide photograph, which is where damage often is.
    wide = Image.new("RGB", (400, 100), (0, 0, 0))
    wide.paste(Image.new("RGB", (40, 100), (255, 255, 255)), (360, 0))

    out = eval_array(wide)

    # The white strip is the last tenth of the width, wherever it ends up.
    assert out[0, :, -10:].mean() > out[0, :, :-20].mean()
    # Nothing was cropped away vertically either: the strip spans every row.
    assert out[0, 0, -1] == pytest.approx(out[0, -1, -1], abs=1e-5)


def test_eval_array_converts_a_non_rgb_image() -> None:
    out = eval_array(Image.new("L", (64, 64), 255))
    assert out.shape == (3, *EVAL_SIZE)
    # Greyscale in means equal values per channel BEFORE normalisation; after
    # it they differ, because each channel has its own mean and std.
    undone = [out[c].mean() * IMAGENET_STD[c] + IMAGENET_MEAN[c] for c in range(3)]
    assert undone == pytest.approx([1.0, 1.0, 1.0], abs=1e-5)


def test_eval_tensor_is_the_same_numbers_with_a_batch_dimension() -> None:
    image = Image.new("RGB", (120, 90), (40, 80, 160))
    tensor = eval_tensor(image)
    assert tuple(tensor.shape) == (1, 3, *EVAL_SIZE)
    assert np.allclose(tensor.numpy()[0], eval_array(image), atol=1e-6)


def test_train_transform_is_deterministic_under_a_fixed_seed() -> None:
    import torch

    image = Image.fromarray(
        np.random.default_rng(7).integers(0, 255, (256, 256, 3), dtype=np.uint8)
    )
    transform = train_transform()

    torch.manual_seed(0)
    first = transform(image)
    torch.manual_seed(0)
    second = transform(image)

    assert torch.allclose(first, second)
    assert tuple(first.shape) == (3, *EVAL_SIZE)


def test_train_transform_actually_augments() -> None:
    # An augmentation pipeline that returns the same tensor twice is not
    # augmenting, and the 4 GB card cannot afford a pipeline that does nothing.
    import torch

    image = Image.fromarray(
        np.random.default_rng(11).integers(0, 255, (256, 256, 3), dtype=np.uint8)
    )
    transform = train_transform()

    torch.manual_seed(1)
    first = transform(image)
    torch.manual_seed(2)
    second = transform(image)

    assert not torch.allclose(first, second)
