"""Command line for the ML package.

    python -m teasmart_ml.cli prepare
    python -m teasmart_ml.cli train
    python -m teasmart_ml.cli evaluate --split test
    python -m teasmart_ml.cli export
    python -m teasmart_ml.cli fixtures

Paths default to data/ beside the repository root rather than the process cwd,
so the command behaves the same wherever it is run from.
"""

import argparse
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - typing only
    from teasmart_ml.datasets.ingest import IngestReport


_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW = _REPO_ROOT / "data" / "raw"
DEFAULT_INTERIM = _REPO_ROOT / "data" / "interim"
DEFAULT_MANIFEST = _REPO_ROOT / "data" / "processed" / "manifest.csv"
DEFAULT_ARTIFACTS = _REPO_ROOT / "data" / "artifacts"


def _report_line(report: "IngestReport") -> str:
    return (
        f"{report.source_id:16} {report.written:6} written  "
        f"{report.skipped_corrupt:5} corrupt  "
        f"{report.skipped_unlabelled:5} unlabelled  "
        f"{report.skipped_ambiguous:5} ambiguous"
    )


def prepare(
    raw_root: Path,
    interim_root: Path,
    out_csv: Path,
    *,
    seed: int = 42,
    downloader: Callable[..., tuple[Path, ...]] | None = None,
) -> Mapping[str, Mapping[str, int]]:
    """Run the whole pipeline and return counts per class per split.

    Safe to re-run: the downloader skips files already on disk and each ingest
    clears its own output folder, so a second run reproduces the first rather
    than doubling it.
    """
    # Imported here, not at module level. `import pyarrow` poisons a later
    # `import onnx` on Windows - both ship a protobuf runtime and the second
    # one in loses - so the export command must be able to run in a process
    # that never touches the dataset pipeline. See tests/conftest.py.
    from teasmart_ml.datasets.ingest import (
        ingest_parquet_source,
        ingest_yolo_zip_source,
    )
    from teasmart_ml.datasets.manifest import (
        build_manifest,
        summarise,
        write_manifest,
    )
    from teasmart_ml.datasets.sources import (
        SOURCES,
        HFParquetSource,
        download_source,
        enabled_sources,
    )

    downloader = downloader or download_source

    for source_id in enabled_sources():
        source = SOURCES[source_id]
        paths = downloader(source_id, raw_root)
        if isinstance(source, HFParquetSource):
            report = ingest_parquet_source(source, paths, interim_root)
        else:
            report = ingest_yolo_zip_source(source, paths[0], interim_root)
        print(_report_line(report))

    manifest = build_manifest(interim_root, seed=seed)
    write_manifest(manifest.rows, out_csv)
    print(
        f"manifest         {len(manifest.rows):6} rows     "
        f"{manifest.collapsed_duplicates:5} duplicates collapsed  "
        f"{manifest.conflicting_groups:5} class conflicts dropped"
    )

    summary = summarise(manifest.rows)
    for canonical, splits in summary.items():
        counts = "  ".join(f"{split} {count:5}" for split, count in splits.items())
        print(f"  {canonical:16} {counts}")
    return summary


def _evenly_spaced(total: int, count: int) -> list[int]:
    """Deterministic sample indices spread across a dataset.

    Spread rather than random so the parity set is the same on every machine
    and the same before and after a re-export: a parity number measured on a
    different 50 images is not comparable to the last one.
    """
    if total <= count:
        return list(range(total))
    step = total / count
    return [min(total - 1, int(index * step)) for index in range(count)]


def _evaluate_command(args) -> int:
    from teasmart_ml.dataset import ManifestDataset
    from teasmart_ml.evaluate import evaluate_dataset, load_checkpoint, report_markdown

    model = load_checkpoint(args.checkpoint)
    dataset = ManifestDataset(args.manifest, args.interim, split=args.split)
    report = evaluate_dataset(
        model,
        dataset,
        device=args.device,
        num_workers=args.num_workers,
    )
    text = report_markdown(report, title=f"{args.split} split")
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(text)

    print(
        f"{args.split}: n {report.n}  accuracy {report.accuracy:.4f}  "
        f"macro_f1 {report.macro_f1:.4f}"
    )
    if report.floor is not None:
        print(
            f"min_confidence {report.floor.floor:.2f}  "
            f"accepted_accuracy {report.floor.accepted_accuracy:.4f}  "
            f"downgraded {report.floor.downgraded_pct:.2f}%"
        )
    else:
        print(f"no usable min_confidence: {report.floor_error}")
    return 0


def _export_command(args) -> int:
    import json

    import numpy as np
    from PIL import Image

    from teasmart_ml.dataset import ManifestDataset
    from teasmart_ml.evaluate import load_checkpoint
    from teasmart_ml.export_onnx import (
        PARITY_PROB_BOUND,
        export_fp32,
        measure_parity,
        quantize_int8,
    )
    from teasmart_ml.transforms import eval_array

    def arrays(dataset: ManifestDataset, indices: list[int]) -> list[np.ndarray]:
        out = []
        for index in indices:
            with Image.open(dataset.paths[index]) as image:
                image.load()
                out.append(eval_array(image))
        return out

    model = load_checkpoint(args.checkpoint)
    val_set = ManifestDataset(args.manifest, args.interim, split="val")
    test_set = ManifestDataset(args.manifest, args.interim, split="test")

    args.out_dir.mkdir(parents=True, exist_ok=True)
    fp32_path = args.out_dir / "teasmart-v1.onnx"
    int8_path = args.out_dir / "teasmart-v1-int8.onnx"

    export_fp32(model, fp32_path)
    print(f"fp32 {fp32_path}  {fp32_path.stat().st_size / 1e6:.1f} MB")

    parity_images = arrays(
        test_set, _evenly_spaced(len(test_set), args.parity_images)
    )
    fp32_parity = measure_parity(model, fp32_path, parity_images)
    print(
        f"fp32 parity: n {fp32_parity.n}  top1 {fp32_parity.top1_agreement:.4f}  "
        f"max_prob_delta {fp32_parity.max_prob_delta:.5f}"
    )

    calibration = arrays(
        val_set, _evenly_spaced(len(val_set), args.calibration_images)
    )
    quantize_int8(fp32_path, int8_path, calibration)
    print(f"int8 {int8_path}  {int8_path.stat().st_size / 1e6:.1f} MB")

    int8_parity = measure_parity(model, int8_path, parity_images)
    print(
        f"int8 parity: n {int8_parity.n}  top1 {int8_parity.top1_agreement:.4f}  "
        f"max_prob_delta {int8_parity.max_prob_delta:.5f}"
    )

    summary = {
        "bound": PARITY_PROB_BOUND,
        "parity_images": fp32_parity.n,
        "fp32": {
            "size_bytes": fp32_path.stat().st_size,
            "top1_agreement": fp32_parity.top1_agreement,
            "max_prob_delta": fp32_parity.max_prob_delta,
            "passed": fp32_parity.passed,
        },
        "int8": {
            "size_bytes": int8_path.stat().st_size,
            "top1_agreement": int8_parity.top1_agreement,
            "max_prob_delta": int8_parity.max_prob_delta,
            "passed": int8_parity.passed,
        },
    }
    (args.out_dir / "parity.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    if not int8_parity.passed:
        # Not a failure of the export: a measured fact about MobileNetV3 in
        # int8. The caller decides which file to ship, and the number is on
        # record either way.
        print(
            "int8 is OUTSIDE the contract bound of "
            f"{PARITY_PROB_BOUND}. Ship the fp32 graph and say so.",
            flush=True,
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="teasmart_ml.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("prepare", help="build the training manifest")
    run.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    run.add_argument("--interim", type=Path, default=DEFAULT_INTERIM)
    run.add_argument("--out", type=Path, default=DEFAULT_MANIFEST)
    run.add_argument("--seed", type=int, default=42)
    fit = sub.add_parser("train", help="train the five-class classifier")
    fit.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    fit.add_argument("--interim", type=Path, default=DEFAULT_INTERIM)
    fit.add_argument("--out", type=Path, default=DEFAULT_ARTIFACTS)
    fit.add_argument("--epochs", type=int, default=30)
    fit.add_argument("--batch-size", type=int, default=32)
    fit.add_argument("--lr", type=float, default=3e-4)
    fit.add_argument("--patience", type=int, default=5)
    fit.add_argument("--device", default="cuda")
    fit.add_argument("--num-workers", type=int, default=4)

    report = sub.add_parser("evaluate", help="score a checkpoint and write a report")
    report.add_argument("--checkpoint", type=Path, default=DEFAULT_ARTIFACTS / "teasmart-v1.pt")
    report.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    report.add_argument("--interim", type=Path, default=DEFAULT_INTERIM)
    report.add_argument("--split", default="val", choices=["train", "val", "test"])
    report.add_argument("--out", type=Path, default=None)
    report.add_argument("--device", default="cuda")
    report.add_argument("--num-workers", type=int, default=4)

    export = sub.add_parser("export", help="export ONNX for the browser")
    export.add_argument("--checkpoint", type=Path, default=DEFAULT_ARTIFACTS / "teasmart-v1.pt")
    export.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    export.add_argument("--interim", type=Path, default=DEFAULT_INTERIM)
    export.add_argument(
        "--out-dir",
        type=Path,
        default=_REPO_ROOT / "frontend" / "public" / "models",
    )
    export.add_argument("--calibration-images", type=int, default=200)
    export.add_argument("--parity-images", type=int, default=50)

    fixtures = sub.add_parser(
        "fixtures", help="write the browser preprocessing parity fixtures"
    )
    fixtures.add_argument(
        "--out",
        type=Path,
        default=_REPO_ROOT / "frontend" / "src" / "test" / "fixtures" / "preprocess",
    )

    args = parser.parse_args(argv)

    if args.command == "fixtures":
        from teasmart_ml.parity import FIXTURE_CASES, write_fixtures

        manifest = write_fixtures(args.out)
        print(f"wrote {len(FIXTURE_CASES)} cases and {manifest.name} to {args.out}")
        return 0

    if args.command == "prepare":
        prepare(args.raw, args.interim, args.out, seed=args.seed)
        return 0

    # Imported here: torch costs several seconds to load and `prepare` has no
    # reason to pay for it.
    if args.command == "evaluate":
        return _evaluate_command(args)
    if args.command == "export":
        return _export_command(args)

    from teasmart_ml.train import TrainConfig, train

    result = train(
        args.manifest,
        args.interim,
        args.out,
        TrainConfig(
            epochs=args.epochs,
            batch_size=args.batch_size,
            lr=args.lr,
            patience=args.patience,
            device=args.device,
            num_workers=args.num_workers,
        ),
    )
    if args.command == "train":
        print(
            f"best epoch {result.best_epoch}  "
            f"val_macro_f1 {result.best_macro_f1:.4f}  "
            f"checkpoint {result.checkpoint}"
        )
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
