# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import importlib.util
import logging
import re
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable

import typer

from faebryk.libs.logging import FLOG_FMT, setup_basic_logging
from faebryk.libs.util import indented_container

logger = logging.getLogger(__name__)

FLOG_FMT.set(True)


class DiscoveryMode(str, Enum):
    manual = "manual"
    pytest = "pytest"


def discover_tests(
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


def _fixture_setup_project_config(tmp_path: Path):
    from atopile.config import ProjectConfig, ProjectPaths, config

    config.project = ProjectConfig.skeleton(
        entry="", paths=ProjectPaths(build=tmp_path / "build", root=tmp_path)
    )


@dataclass
class _PytestArgDef:
    names: list[str]
    values: list[tuple[Any, ...]]
    id_fn: Callable[[Any], str] | None

    def __post_init__(self):
        for vs in self.values:
            if len(vs) != len(self.names):
                raise ValueError(f"Expected {len(self.names)} values, got {len(vs)}")


def run_tests(matches: list[tuple[Path, Callable]]) -> None:
    """Run tests discovered via manual discovery."""
    import tempfile

    import typer

    setup_basic_logging()

    for filepath, test_func in matches:
        logger.info(f"Running {test_func.__name__}")

        with tempfile.TemporaryDirectory() as tmp_path_:
            tmp_path = Path(tmp_path_)

        # args: list[str] | None = None
        arg_def: _PytestArgDef | None = None

        # check if need to run fixtures
        print(indented_container(test_func.__dict__, recursive=True))
        if hasattr(test_func, "pytestmark"):
            for mark in test_func.pytestmark:
                if mark.name == "parametrize":
                    arg_def = _PytestArgDef(
                        names=[name.strip() for name in mark.args[0].split(",")],
                        values=list(mark.args[1]),
                        id_fn=mark.kwargs.get("ids"),
                    )
                if mark.name == "usefixtures":
                    if "setup_project_config" in mark.args:
                        _fixture_setup_project_config(tmp_path)
                    else:
                        raise ValueError(
                            f"Test {test_func.__name__} is using usefixtures. "
                            "Manual discovery does not support usefixtures."
                        )

        sys.argv = [test_func.__name__]

        def fn():
            if not arg_def:
                test_func()
                return
            for values in arg_def.values:
                kwargs = dict(zip(arg_def.names, values))
                # name = arg_def.id_fn(kwargs) if arg_def.id_fn else str(values)
                print(f"Running {test_func.__name__} with {kwargs}")
                test_func(**kwargs)

        typer.run(fn)


def run(
    test_name: str,
    filepaths: list[Path],
):
    test_files: list[Path] = []
    for filepath in filepaths:
        if not filepath.exists():
            raise ValueError(f"Filepath {filepath} does not exist")
        if not filepath.is_dir():
            test_files.append(filepath)
        else:
            test_files.extend(filepath.rglob("test_*.py"))

    matches = discover_tests(test_files, test_name)
    if not matches:
        raise ValueError(f"Test function '{test_name}' not found in {filepaths}")
    run_tests(matches)


def main(
    filepaths: list[Path] | None = None,
    test_name: str = typer.Option("-k", help="Test name pattern"),
):
    assert test_name
    if filepaths is None:
        filepaths = [Path("test"), Path("src")]
    run(test_name, filepaths)


if __name__ == "__main__":
    typer.run(main)
