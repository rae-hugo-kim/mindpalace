"""Operational logging for mindpalace (AC15).

A single ``mindpalace`` parent logger; modules log under ``mindpalace.*``
and rely on propagation. ``configure_logging`` attaches one handler
(file if a path is given, else stderr) and is idempotent so repeated
calls from the CLI commands don't stack duplicate handlers.

Logged signals (seed AC15): import results (counts + masking applied),
embedding-failure counter, and search latency.
"""
from __future__ import annotations

import logging

_ROOT_NAME = "mindpalace"
_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def get_logger(name: str) -> logging.Logger:
    """Return a logger under the ``mindpalace`` namespace."""
    return logging.getLogger(name)


def configure_logging(log_file: str | None = None, level: int = logging.INFO) -> None:
    """Attach a single handler to the ``mindpalace`` logger.

    If ``log_file`` is given, records go to that file; otherwise to
    stderr. Idempotent for a given target: a second call with the same
    file path does not add a duplicate handler (which would double every
    line). A different file path replaces the previous file handler.
    """
    root = logging.getLogger(_ROOT_NAME)
    root.setLevel(level)

    if log_file is not None:
        for h in list(root.handlers):
            if isinstance(h, logging.FileHandler):
                if getattr(h, "baseFilename", None) == _abspath(log_file):
                    return  # already configured for this exact file
                root.removeHandler(h)
                h.close()
        handler: logging.Handler = logging.FileHandler(log_file, encoding="utf-8")
    else:
        if any(
            isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
            for h in root.handlers
        ):
            return
        handler = logging.StreamHandler()

    handler.setFormatter(logging.Formatter(_FORMAT))
    root.addHandler(handler)


def _abspath(path: str) -> str:
    import os

    return os.path.abspath(path)
