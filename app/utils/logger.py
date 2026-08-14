"""Logging setup shared across the application."""

from __future__ import annotations

import logging
import sys
from functools import lru_cache

from app.utils.config import get_settings

_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


@lru_cache(maxsize=1)
def get_logger(name: str = "datapilot") -> logging.Logger:
    """Return a configured logger instance."""
    settings = get_settings()
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    level = getattr(logging, settings.log_level, logging.INFO)
    logger.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_FORMAT, datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(handler)
    logger.propagate = False
    return logger