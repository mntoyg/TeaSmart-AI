"""Read the manifest into a torch Dataset.

Two facts about the manifest that nothing else records:

- `path` is relative to the interim root, not to the repository, and it is
  written with Windows separators.
- `canonical` is a name, not an index. The index comes from
  `CANONICAL_CLASSES`, which is the same order the API serves as `class_order`
  and the same order the ONNX output columns are in. Deriving it from the file
  would make the order depend on which rows happen to appear first.
"""

from __future__ import annotations

import csv
from collections.abc import Callable
from pathlib import Path

import torch
from PIL import Image
from torch.utils.data import Dataset

from teasmart_ml.classes import CANONICAL_CLASSES
from teasmart_ml.transforms import eval_array


class SplitMissingError(RuntimeError):
    """The requested split has no rows in the manifest."""


class ManifestDataset(Dataset):
    """Images of one split, labelled by canonical class index."""

    def __init__(
        self,
        manifest_path: Path,
        interim_root: Path,
        *,
        split: str,
        transform: Callable[[Image.Image], torch.Tensor] | None = None,
    ) -> None:
        self.classes = list(CANONICAL_CLASSES)
        self.interim_root = Path(interim_root)
        self.transform = transform
        self.paths: list[Path] = []
        self.labels: list[int] = []

        index_of = {name: index for index, name in enumerate(CANONICAL_CLASSES)}
        with Path(manifest_path).open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                if row["split"] != split:
                    continue
                canonical = row["canonical"]
                if canonical not in index_of:
                    raise KeyError(f"manifest row has unknown class {canonical!r}")
                self.paths.append(self.interim_root / Path(row["path"].replace("\\", "/")))
                self.labels.append(index_of[canonical])

        if not self.paths:
            raise SplitMissingError(
                f"split {split!r} has no rows in {manifest_path}. Rebuild the "
                f"corpus with: python -m teasmart_ml.cli prepare"
            )

    def __len__(self) -> int:
        return len(self.paths)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, int]:
        with Image.open(self.paths[index]) as image:
            image.load()
            if self.transform is not None:
                return self.transform(image), self.labels[index]
            return torch.from_numpy(eval_array(image)), self.labels[index]


def class_counts(dataset: ManifestDataset) -> list[int]:
    """How many images each canonical class has in this split."""
    counts = [0] * len(CANONICAL_CLASSES)
    for label in dataset.labels:
        counts[label] += 1
    return counts


def class_weights(dataset: ManifestDataset) -> list[float]:
    """Inverse-frequency sampling weight per class.

    `other_disease` is 36% of the corpus. Uniform sampling would let the model
    answer `other_disease` and keep a respectable accuracy while never finding
    grey blight, which is the only answer a farmer can act on.

    An absent class gets weight 0 rather than an infinity, so a split that is
    missing a class fails on the metrics rather than on a NaN loss.
    """
    counts = class_counts(dataset)
    return [1.0 / count if count else 0.0 for count in counts]


def sample_weights(dataset: ManifestDataset) -> list[float]:
    """Per-image weights for `WeightedRandomSampler`."""
    weights = class_weights(dataset)
    return [weights[label] for label in dataset.labels]
