"""Structured logging configuration using Loguru."""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger


def configure_logging(
    level: str = "INFO",
    log_file: Path | None = None,
) -> None:
    """Configure application-wide logging.

    Args:
        level: Minimum log level (DEBUG, INFO, WARNING, ERROR).
        log_file: Optional path to persist logs.
    """
    logger.remove()
    logger.add(
        sys.stderr,
        level=level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        colorize=True,
    )

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            log_file,
            level=level,
            rotation="10 MB",
            retention="30 days",
            encoding="utf-8",
        )


__all__ = ["configure_logging", "logger"]
