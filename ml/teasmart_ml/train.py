"""Train the five-class leaf classifier.

Every choice here is dictated by one constraint: the only GPU available is a
4 GB RTX 3050 laptop card, and the demo is on 2026-11-21. MobileNetV3-Large at
224x224 with batch 32 and mixed precision fits in that memory with room for the
augmentation pipeline; anything heavier trains overnight or not at all. The same
architecture is what has to run in a browser on a phone afterwards, so the
constraint is also the product requirement.

Selection is on validation macro-F1, never on accuracy. `other_disease` is 36%
of the corpus, so accuracy rewards a model that answers `other_disease` and
never finds grey blight - which is the only answer a farmer can act on.
"""

from __future__ import annotations

import json
import math
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, WeightedRandomSampler
from torchvision.models import MobileNet_V3_Large_Weights, mobilenet_v3_large

from teasmart_ml.classes import CANONICAL_CLASSES
from teasmart_ml.dataset import ManifestDataset, class_counts, sample_weights
from teasmart_ml.metrics import confusion_matrix, macro_f1
from teasmart_ml.transforms import train_transform


@dataclass(frozen=True)
class TrainConfig:
    epochs: int = 30
    batch_size: int = 32
    lr: float = 3e-4
    weight_decay: float = 1e-4
    patience: int = 5
    device: str = "cuda"
    num_workers: int = 4
    pretrained: bool = True
    label_smoothing: float = 0.05
    amp: bool = True
    seed: int = 1337


@dataclass(frozen=True)
class EpochRow:
    epoch: int
    train_loss: float
    val_loss: float
    val_accuracy: float
    val_macro_f1: float


@dataclass(frozen=True)
class TrainResult:
    checkpoint: Path
    history: list[EpochRow] = field(default_factory=list)
    best_epoch: int = 0
    best_macro_f1: float = 0.0


class EarlyStopping:
    """Stop when validation macro-F1 has not improved for `patience` epochs.

    Holds the best score seen, not the last one, because the checkpoint written
    is the best epoch and the two have to agree.
    """

    def __init__(self, *, patience: int, min_delta: float = 0.0) -> None:
        self.patience = patience
        self.min_delta = min_delta
        self.best = -math.inf
        self.epochs_without_improvement = 0

    def update(self, score: float) -> bool:
        """Record an epoch's score. True when it is a new best."""
        if score > self.best + self.min_delta:
            self.best = score
            self.epochs_without_improvement = 0
            return True
        self.epochs_without_improvement += 1
        return False

    @property
    def should_stop(self) -> bool:
        return self.epochs_without_improvement >= self.patience


def build_model(n_classes: int, *, pretrained: bool = True) -> nn.Module:
    """MobileNetV3-Large with a fresh head, emitting raw logits.

    No softmax in the graph: spec section 8.4 says the output is logits, and a
    softmax baked in here would be applied twice in the browser and flatten
    every confidence the threshold depends on.
    """
    weights = MobileNet_V3_Large_Weights.IMAGENET1K_V1 if pretrained else None
    model = mobilenet_v3_large(weights=weights)
    in_features = model.classifier[3].in_features
    model.classifier[3] = nn.Linear(in_features, n_classes)
    return model


def _seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def _evaluate(
    model: nn.Module,
    loader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
) -> tuple[float, float, float]:
    """Mean loss, accuracy and macro-F1 over a loader."""
    model.eval()
    total_loss = 0.0
    seen = 0
    predictions: list[np.ndarray] = []
    targets: list[np.ndarray] = []
    with torch.no_grad():
        for images, labels in loader:
            images = images.to(device, non_blocking=True)
            labels = labels.to(device, non_blocking=True)
            logits = model(images)
            total_loss += float(criterion(logits, labels)) * labels.shape[0]
            seen += labels.shape[0]
            predictions.append(logits.argmax(dim=1).cpu().numpy())
            targets.append(labels.cpu().numpy())

    y_pred = np.concatenate(predictions)
    y_true = np.concatenate(targets)
    cm = confusion_matrix(y_true, y_pred, n_classes=len(CANONICAL_CLASSES))
    accuracy = float((y_pred == y_true).mean())
    return total_loss / max(seen, 1), accuracy, macro_f1(cm)


def train(
    manifest_path: Path,
    interim_root: Path,
    out_dir: Path,
    config: TrainConfig | None = None,
) -> TrainResult:
    """Fit the classifier and write the best epoch to `out_dir`."""
    config = config or TrainConfig()
    _seed_everything(config.seed)

    device = torch.device(config.device)
    use_amp = config.amp and device.type == "cuda"

    train_set = ManifestDataset(
        manifest_path, interim_root, split="train", transform=train_transform()
    )
    val_set = ManifestDataset(manifest_path, interim_root, split="val")

    # Class-balanced sampling, with an epoch defined as one pass worth of
    # draws. Replacement is on by design: the rare classes have to repeat.
    generator = torch.Generator().manual_seed(config.seed)
    sampler = WeightedRandomSampler(
        weights=sample_weights(train_set),
        num_samples=len(train_set),
        replacement=True,
        generator=generator,
    )
    train_loader = DataLoader(
        train_set,
        batch_size=config.batch_size,
        sampler=sampler,
        num_workers=config.num_workers,
        pin_memory=device.type == "cuda",
        drop_last=False,
    )
    val_loader = DataLoader(
        val_set,
        batch_size=config.batch_size,
        shuffle=False,
        num_workers=config.num_workers,
        pin_memory=device.type == "cuda",
    )

    model = build_model(len(CANONICAL_CLASSES), pretrained=config.pretrained)
    model.to(device)
    criterion = nn.CrossEntropyLoss(label_smoothing=config.label_smoothing)
    optimiser = torch.optim.AdamW(
        model.parameters(), lr=config.lr, weight_decay=config.weight_decay
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimiser, T_max=max(config.epochs, 1)
    )
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    checkpoint = out_dir / "teasmart-v1.pt"

    stopper = EarlyStopping(patience=config.patience)
    history: list[EpochRow] = []
    best_epoch = 0

    for epoch in range(1, config.epochs + 1):
        model.train()
        running = 0.0
        seen = 0
        for images, labels in train_loader:
            images = images.to(device, non_blocking=True)
            labels = labels.to(device, non_blocking=True)
            optimiser.zero_grad(set_to_none=True)
            with torch.amp.autocast("cuda", enabled=use_amp):
                loss = criterion(model(images), labels)
            scaler.scale(loss).backward()
            scaler.step(optimiser)
            scaler.update()
            running += float(loss) * labels.shape[0]
            seen += labels.shape[0]

        scheduler.step()
        val_loss, val_accuracy, val_f1 = _evaluate(model, val_loader, criterion, device)
        history.append(
            EpochRow(
                epoch=epoch,
                train_loss=running / max(seen, 1),
                val_loss=val_loss,
                val_accuracy=val_accuracy,
                val_macro_f1=val_f1,
            )
        )
        print(
            f"epoch {epoch:>2}  train_loss {running / max(seen, 1):.4f}  "
            f"val_loss {val_loss:.4f}  val_acc {val_accuracy:.4f}  "
            f"val_macro_f1 {val_f1:.4f}",
            flush=True,
        )

        if stopper.update(val_f1):
            best_epoch = epoch
            torch.save(
                {
                    "state_dict": model.state_dict(),
                    "class_order": list(CANONICAL_CLASSES),
                    "epoch": epoch,
                    "val_macro_f1": val_f1,
                    "config": asdict(config),
                },
                checkpoint,
            )
        if stopper.should_stop:
            print(
                f"stopping: no improvement for {config.patience} epochs "
                f"(best {stopper.best:.4f} at epoch {best_epoch})",
                flush=True,
            )
            break

    (out_dir / "history.json").write_text(
        json.dumps(
            {
                "config": asdict(config),
                "train_class_counts": class_counts(train_set),
                "history": [asdict(row) for row in history],
                "best_epoch": best_epoch,
                "best_val_macro_f1": stopper.best,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    return TrainResult(
        checkpoint=checkpoint,
        history=history,
        best_epoch=best_epoch,
        best_macro_f1=stopper.best,
    )
