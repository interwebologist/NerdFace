# Remove Compression Module, Tests & CLI References

## Goal
Remove the `compression/` package, all compression tests, and all references to compression in `cli.py` to create a clean slate before implementing a new compression system.

## Files to Delete
- `compression/__init__.py`
- `compression/context_compressor.py`
- `compression/auxiliary_client.py`
- `compression/model_metadata.py`
- `compression/__pycache__/` (if exists)
- `tests/test_compressor.py`
- `tests/test_compression_edge_cases.py`
- `tests/test_model_metadata.py`
- `test_compression.py` (root-level, tests `compression.py` module)
- `compression.py` (root-level, standalone `Compression` class)
- `__pycache__/test_compression.cpython-313-pytest-9.0.3.pyc` (stale cache)

## Files to Modify

### `cli.py`
1. **Remove import** (line 13): `from compression.context_compressor import ContextCompressor`
2. **Remove compression block** (lines 177-186): The entire `if os.getenv("COMRESSION_SIZE")` / `if os.getenv("ENABLE_COMPRESSION")` block that calls `compressor.compress()`

## Files to Check (no action needed if not found)
- `agent.py` — verify no compression imports (confirmed: none exist)
- `pyproject.toml` — check for compression-related dependencies (none expected)
- `uv.lock` — no action needed

## Verification
- `python -c "import cli"` succeeds without compression imports
- `python -c "import agent"` succeeds
- No references to `compression` remain in `cli.py`
- No compression test files remain in `tests/` or root
