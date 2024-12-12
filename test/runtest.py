# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import importlib.util
import logging
import re
from pathlib import Path

import typer

from faebryk.libs.logging import setup_basic_logging

logger = logging.getLogger(__name__)


def main(
    filepath: Path = typer.Argument(Path("test")),
    test_name: str = typer.Option(".*", "-k", help="Test name pattern (regex)"),
):
    if not filepath.exists():
        raise ValueError(f"Filepath {filepath} does not exist")
    if not filepath.is_dir():
        filepaths = [filepath]
    else:
        assert filepath.is_dir()
        filepaths = list(filepath.rglob("test_*.py"))

    matches = []
    for fp in filepaths:
        spec = importlib.util.spec_from_file_location("test_module", fp)
        if spec is None:
            continue
        module = importlib.util.module_from_spec(spec)
        if spec.loader is None:
            continue
        spec.loader.exec_module(module)
        for v in vars(module).values():
            if not hasattr(v, "__name__"):
                continue
            if not re.match(test_name, v.__name__):
                continue
            matches.append(v)

    if not matches:
        raise ValueError(f"Test function '{test_name}' not found in {filepaths}")

    setup_basic_logging(force_fmt=True)
    for test_func in matches:
        if len(matches) > 1:
            logger.info(f"Running {test_func.__name__}")
        test_func()


if __name__ == "__main__":
    typer.run(main)
