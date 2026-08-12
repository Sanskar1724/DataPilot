"""Persistence: SQLite, Parquet, local files."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

from app.utils.config import get_settings
from app.utils.helpers import ensure_dir
from app.utils.logger import get_logger

logger = get_logger(__name__)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def save_parquet(df: pd.DataFrame, name: str, directory: str = "processed") -> Path:
    """Write a DataFrame to a Parquet file inside the data directory."""
    out_dir = ensure_dir(DATA_DIR / directory)
    path = out_dir / f"{name}.parquet"
    df.to_parquet(path, index=False)
    logger.info("Saved %s rows to %s", len(df), path)
    return path


def save_csv(df: pd.DataFrame, name: str, directory: str = "processed") -> Path:
    """Write a DataFrame to a CSV file inside the data directory (utf-8)."""
    out_dir = ensure_dir(DATA_DIR / directory)
    path = out_dir / f"{name}.csv"
    df.to_csv(path, index=False, encoding="utf-8")
    logger.info("Saved %s rows to %s", len(df), path)
    return path


def load_processed(name: str, directory: str = "processed") -> pd.DataFrame:
    """Load a previously processed dataset (Parquet preferred)."""
    out_dir = ensure_dir(DATA_DIR / directory)
    parquet = out_dir / f"{name}.parquet"
    if parquet.exists():
        return pd.read_parquet(parquet)
    csv = out_dir / f"{name}.csv"
    if csv.exists():
        return pd.read_csv(csv)
    raise FileNotFoundError(f"No processed dataset found named '{name}'")


def connect_sqlite(path: str | Path | None = None) -> sqlite3.Connection:
    """Open a SQLite connection (defaults to database inside data dir)."""
    settings = get_settings()
    db_path = (
        Path(path)
        if path is not None
        else ensure_dir(DATA_DIR / "db") / "datapilot.db"
    )
    _ = settings  # placeholder: future config-driven path
    logger.info("Opening SQLite database at %s", db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def register_pipeline_run(conn: sqlite3.Connection, name: str, payload: dict) -> int:
    """Insert a pipeline-run record and return its row id."""
    with conn:
        cur = conn.execute(
            "CREATE TABLE IF NOT EXISTS pipeline_runs ("
            " id INTEGER PRIMARY KEY AUTOINCREMENT,"
            " name TEXT NOT NULL,"
            " created_at TEXT DEFAULT CURRENT_TIMESTAMP,"
            " payload TEXT NOT NULL)"
        )
        cur.execute(
            "INSERT INTO pipeline_runs (name, payload) VALUES (?, ?)",
            (name, __import__("json").dumps(payload, default=str)),
        )
        conn.commit()
        run_id = cur.lastrowid
    logger.info("Registered pipeline run #%s '%s'", run_id, name)
    return int(run_id)