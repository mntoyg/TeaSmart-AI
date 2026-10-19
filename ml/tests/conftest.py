"""Session-wide import order, which is load-bearing on Windows.

`import pyarrow` followed by `import onnx` fails in this environment:

    ImportError: DLL load failed while importing onnx_cpp2py_export:
    A dynamic link library (DLL) initialization routine failed.

The reverse order is fine. Both libraries bring their own copy of the protobuf
runtime, and whichever arrives second loses. Measured with:

    python -c "import pyarrow; import onnx"   # fails
    python -c "import onnx; import pyarrow"   # fine

Only the test suite needs both in one process: `prepare` uses pyarrow and
`export` uses onnx, and `teasmart_ml.cli` imports each lazily so neither
command pays for the other. Here, onnx goes first for the whole session, and
the failure this prevents is tests that pass alone and fail in the suite.
"""

try:
    import onnx  # noqa: F401
    import onnxruntime  # noqa: F401
except ImportError:  # pragma: no cover - the ONNX tests report this themselves
    pass
