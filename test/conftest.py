import logging
import os
from pathlib import Path


def pytest_configure(config):
    worker_id = os.environ.get("PYTEST_XDIST_WORKER")
    if worker_id is not None:
        logging.basicConfig(
            format=config.getini("log_file_format"),
            filename=Path("artifacts") / f"tests_{worker_id}.log",
            level=config.getini("log_file_level"),
        )
