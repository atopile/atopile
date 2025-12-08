# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import importlib.util
import logging
import re
import subprocess
import sys
from enum import Enum
from pathlib import Path
from typing import Callable

import typer

from faebryk.libs.logging import FLOG_FMT, setup_basic_logging

logger = logging.getLogger(__name__)

FLOG_FMT.set(True)


class DiscoveryMode(str, Enum):
    manual = "manual"
    pytest = "pytest"


def discover_tests_manual(
    filepaths: list[Path], test_pattern: str
) -> list[tuple[Path, Callable]]:
    """
    Manual test discovery by loading modules and finding matching functions.
    Note: This does NOT discover parametrized test variants.
    """
    matches = []
    for fp in filepaths:
        spec = importlib.util.spec_from_file_location("test_module", fp)
        if spec is None:
            continue
        module = importlib.util.module_from_spec(spec)
        if spec.loader is None:
            continue
        try:
            spec.loader.exec_module(module)
        except Exception:
            continue
        for v in vars(module).values():
            if not hasattr(v, "__name__"):
                continue
            if not re.match(test_pattern, v.__name__):
                continue
            matches.append((fp, v))
    return matches


def discover_tests_pytest(
    filepaths: list[Path], test_pattern: str
) -> list[tuple[Path, str]]:
    """
    Pytest-based test discovery using pytest's collection mechanism.
    This properly discovers parametrized test variants.

    Returns list of (filepath, node_id) tuples where node_id is the full pytest
    node identifier including parametrization (e.g. "test_file.py::test_func[param1]")
    """
    # Build pytest collect command
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "--collect-only",
        "-q",
        # Filter by test name pattern (pytest uses -k for keyword expressions)
        "-k",
        test_pattern,
    ]
    # Add file paths
    cmd.extend(str(fp) for fp in filepaths)

    result = subprocess.run(cmd, capture_output=True, text=True)

    # Parse output - each line that contains :: is a test node ID
    # Format: path/to/test_file.py::TestClass::test_method[param]
    # or:     path/to/test_file.py::test_function[param]
    matches = []
    for line in result.stdout.strip().split("\n"):
        line = line.strip()
        if "::" in line and not line.startswith("<"):
            # Extract the file path from the node ID
            file_part = line.split("::")[0]
            filepath = Path(file_part)
            matches.append((filepath, line))

    return matches


def run_tests_manual(matches: list[tuple[Path, Callable]]) -> None:
    """Run tests discovered via manual discovery."""
    setup_basic_logging()

    for filepath, test_func in matches:
        if len(matches) > 1:
            logger.info(f"Running {test_func.__name__}")
        test_func()


def run_tests_pytest(matches: list[tuple[Path, str]]) -> None:
    """Run tests discovered via pytest discovery."""
    import pytest

    setup_basic_logging()

    for filepath, node_id in matches:
        if len(matches) > 1:
            logger.info(f"Running {node_id}")
        # Run the specific test using pytest with its full node ID
        # -s to not capture output, -v for verbose
        pytest.main(
            [
                "-s",
                "-o",
                "addopts=''",
                "--log-cli-level=INFO",
                "-v",
                node_id,
            ]
        )


def main(
    filepath: Path = typer.Argument(Path("test")),
    test_name: str = typer.Option(
        ".*", "-k", help="Test name pattern (regex for manual, keyword expr for pytest)"
    ),
    discovery: DiscoveryMode = typer.Option(
        DiscoveryMode.manual,
        "--discovery",
        "-d",
        help="Test discovery mode: 'manual' (original, no parametrized tests) or "
        "'pytest' (includes parametrized tests)",
    ),
):
    if not filepath.exists():
        raise ValueError(f"Filepath {filepath} does not exist")
    if not filepath.is_dir():
        filepaths = [filepath]
    else:
        assert filepath.is_dir()
        filepaths = list(filepath.rglob("test_*.py"))

    if discovery == DiscoveryMode.manual:
        matches = discover_tests_manual(filepaths, test_name)
        if not matches:
            raise ValueError(f"Test function '{test_name}' not found in {filepaths}")
        run_tests_manual(matches)
    else:
        matches = discover_tests_pytest(filepaths, test_name)
        if not matches:
            raise ValueError(f"Test '{test_name}' not found in {filepaths}")
        run_tests_pytest(matches)


if __name__ == "__main__":
    typer.run(main)
