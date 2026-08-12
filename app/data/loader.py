"""Load data from CSV/JSON/Excel/Parquet into a pandas DataFrame."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from app.utils.logger import get_logger

logger = get_logger(__name__)

SUPPORTED_EXTENSIONS = {".csv", ".json", ".jsonl", ".xlsx", ".xls", ".parquet"}


def _read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def _read_json(path: Path) -> pd.DataFrame:
    return pd.read_json(path)


def _read_jsonl(path: Path) -> pd.DataFrame:
    return pd.read_json(path, lines=True)


def _read_excel(path: Path) -> pd.DataFrame:
    return pd.read_excel(path)


def _read_parquet(path: Path) -> pd.DataFrame:
    return pd.read_parquet(path)


_READERS = {
    ".csv": _read_csv,
    ".json": _read_json,
    ".jsonl": _read_jsonl,
    ".xlsx": _read_excel,
    ".xls": _read_excel,
    ".parquet": _read_parquet,
}


def load_dataframe(source: str | Path) -> pd.DataFrame:
    """Load a supported file into a DataFrame.

    Args:
        source: Path to a CSV/JSON/JSONL/Excel/Parquet file.

    Returns:
        The freshly loaded DataFrame (independent copy of the source).

    Raises:
        FileNotFoundError: if the file does not exist.
        ValueError: if the file extension is unsupported or reading fails.
    """
    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    ext = path.suffix.lower()
    if ext not in _READERS:
        raise ValueError(
            f"Unsupported file type '{ext}'. Supported: "
            f"{', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    logger.info("Loading %s (%s)", path.name, ext.lstrip("."))
    try:
        return _READERS[ext](path).copy()
    except Exception as exc:
        logger.error("Failed to read %s: %s", path.name, exc)
        raise ValueError(f"Could not parse file '{path.name}': {exc}") from exc


def load_dataframe_from_bytes(
    filename: str, content: bytes, **reader_kwargs: Any
) -> pd.DataFrame:
    """Load an uploaded file's bytes into a DataFrame.

    Args:
        filename: Original name of the uploaded file (used for the extension).
        content: Raw file bytes.
        **reader_kwargs: Extra kwargs forwarded to the pandas reader.

    Returns:
        The parsed DataFrame.
    """
    ext = Path(filename).suffix.lower()
    if ext not in _READERS:
        raise ValueError(
            f"Unsupported file type '{ext}'. Supported: "
            f"{', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    import io

    logger.info("Loading uploaded file %s", filename)
    try:
        if ext == ".csv":
            return pd.read_csv(io.BytesIO(content), **reader_kwargs)
        if ext == ".json":
            return pd.read_json(io.BytesIO(content), **reader_kwargs)
        if ext == ".jsonl":
            return pd.read_json(io.BytesIO(content), lines=True, **reader_kwargs)
        if ext == ".parquet":
            return pd.read_parquet(io.BytesIO(content), **reader_kwargs)
        return pd.read_excel(io.BytesIO(content), **reader_kwargs)
    except Exception as exc:
        logger.error("Failed to read uploaded file %s: %s", filename, exc)
        raise ValueError(f"Could not parse file '{filename}': {exc}") from exc