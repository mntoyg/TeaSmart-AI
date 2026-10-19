"""Image preprocessing, fixed by spec section 8.4.

The eval path is a contract: the browser runs the same five steps in
JavaScript, and the parity test before D7 compares them. It is implemented here
with PIL and numpy rather than torchvision so that every step is visible and
reproducible by whoever writes the other side - a `Resize` with an implicit
antialias default is exactly the kind of difference nobody finds until the
phone disagrees with the server.

The train path may do whatever helps; it never has to match anything.
"""

from __future__ import annotations

import numpy as np
import torch
from PIL import Image
from torchvision import transforms as T

EVAL_SIZE = (224, 224)
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)

_MEAN = np.array(IMAGENET_MEAN, dtype=np.float32).reshape(3, 1, 1)
_STD = np.array(IMAGENET_STD, dtype=np.float32).reshape(3, 1, 1)


def eval_array(image: Image.Image) -> np.ndarray:
    """The five contract steps, as a CHW float32 array.

    1. decode to RGB uint8
    2. resize to 224x224, bilinear, aspect ratio not preserved
    3. divide by 255
    4. normalise per channel with ImageNet statistics
    5. transpose to CHW float32
    """
    if image.mode != "RGB":
        image = image.convert("RGB")
    resized = image.resize(EVAL_SIZE, resample=Image.BILINEAR)
    array = np.asarray(resized, dtype=np.float32) / 255.0
    return np.ascontiguousarray((array.transpose(2, 0, 1) - _MEAN) / _STD)


def eval_tensor(image: Image.Image) -> torch.Tensor:
    """`eval_array` with the batch dimension the ONNX graph expects."""
    return torch.from_numpy(eval_array(image)).unsqueeze(0)


def train_transform() -> T.Compose:
    """Augmentation for training only.

    Geometry is free: a leaf has no canonical orientation, and a drone frame
    has no up. Colour is not - brown blight against grey blight is a colour
    difference, so brightness and contrast move a little and hue barely at all.
    """
    return T.Compose(
        [
            T.RandomResizedCrop(EVAL_SIZE, scale=(0.7, 1.0), ratio=(0.8, 1.25)),
            T.RandomHorizontalFlip(),
            T.RandomVerticalFlip(),
            T.RandomRotation(20),
            T.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.1, hue=0.02),
            T.ToTensor(),
            T.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ]
    )
