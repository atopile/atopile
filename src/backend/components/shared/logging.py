from __future__ import annotations

import logging

_DEFAULT_FORMAT = "%(asctime)s %(levelname)s %(name)s event=%(message)s"


def configure_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    if root.handlers:
        root.setLevel(level)
        return
    logging.basicConfig(level=level, format=_DEFAULT_FORMAT)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def test_get_logger_returns_named_logger() -> None:
    logger = get_logger("backend.components.fetch")
    assert logger.name == "backend.components.fetch"
