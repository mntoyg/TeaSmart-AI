"""Copy the shared ONNX graph into backend/model for the API service build.

The graph is committed once, under frontend/public/models, so the browser and
the server stay on the same file. A host that packages only backend/ cannot
see that path at runtime, so the build copies it into the gitignored model
directory and active_model_path prefers the copy when it is present.
"""

from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
SOURCE = BACKEND.parent / "frontend" / "public" / "models" / "teasmart-v1.onnx"
TARGET = BACKEND / "model" / "teasmart-v1.onnx"


def main() -> None:
    if not SOURCE.is_file():
        raise SystemExit(f"shared model missing at {SOURCE}")
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    if TARGET.is_file() and TARGET.stat().st_size == SOURCE.stat().st_size:
        return
    TARGET.write_bytes(SOURCE.read_bytes())


if __name__ == "__main__":
    main()
