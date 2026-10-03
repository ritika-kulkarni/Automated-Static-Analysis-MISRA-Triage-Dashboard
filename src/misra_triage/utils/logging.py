"""Structured console logging helpers."""

from __future__ import annotations

import logging
import sys

from rich.logging import RichHandler


def setup_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    if root.handlers:
        for handler in list(root.handlers):
            root.removeHandler(handler)
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, markup=True, show_path=False)],
        force=True,
    )
    # Keep third-party noise down in CI logs.
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def configure_stream_fallback() -> None:
    """Ensure stderr exists even in constrained runners."""
    if sys.stderr is None:  # pragma: no cover
        sys.stderr = sys.__stderr__
