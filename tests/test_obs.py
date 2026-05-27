"""Tests for mindpalace.obs (operational logging — AC15)."""
import logging

from mindpalace.obs import configure_logging, get_logger


def test_configure_logging_writes_to_file(tmp_path):
    """T21 (RED, AC15): configure_logging(log_file) routes records to a file."""
    log_file = tmp_path / "mindpalace.log"
    configure_logging(str(log_file))

    get_logger("mindpalace.test").info("hello-marker latency_ms=1.23")

    logging.getLogger("mindpalace").handlers[0].flush()
    contents = log_file.read_text()
    assert "hello-marker" in contents
    assert "latency_ms=1.23" in contents


def test_configure_logging_is_idempotent(tmp_path):
    """T21 (RED, AC15): repeated configure_logging calls don't stack handlers
    (which would duplicate every line)."""
    log_file = tmp_path / "mindpalace.log"
    configure_logging(str(log_file))
    configure_logging(str(log_file))

    root = logging.getLogger("mindpalace")
    # Exactly one file handler for the given target, no duplicates.
    file_handlers = [h for h in root.handlers if isinstance(h, logging.FileHandler)]
    assert len(file_handlers) == 1
