"""Prepare the training corpus: download, normalise, deduplicate, split.

    python -m teasmart_ml.cli prepare

Paths default to data/ beside the repository root rather than the process cwd,
so the command behaves the same wherever it is run from.
"""

import argparse
from collections.abc import Callable, Mapping
from pathlib import Path

from teasmart_ml.datasets.ingest import (
    IngestReport,
    ingest_parquet_source,
    ingest_yolo_zip_source,
)
from teasmart_ml.datasets.manifest import build_manifest, summarise, write_manifest
from teasmart_ml.datasets.sources import (
    SOURCES,
    HFParquetSource,
    download_source,
    enabled_sources,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW = _REPO_ROOT / "data" / "raw"
DEFAULT_INTERIM = _REPO_ROOT / "data" / "interim"
DEFAULT_MANIFEST = _REPO_ROOT / "data" / "processed" / "manifest.csv"


def _report_line(report: IngestReport) -> str:
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
    downloader: Callable[..., tuple[Path, ...]] = download_source,
) -> Mapping[str, Mapping[str, int]]:
    """Run the whole pipeline and return counts per class per split.

    Safe to re-run: the downloader skips files already on disk and each ingest
    clears its own output folder, so a second run reproduces the first rather
    than doubling it.
    """
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="teasmart_ml.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("prepare", help="build the training manifest")
    run.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    run.add_argument("--interim", type=Path, default=DEFAULT_INTERIM)
    run.add_argument("--out", type=Path, default=DEFAULT_MANIFEST)
    run.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    prepare(args.raw, args.interim, args.out, seed=args.seed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
