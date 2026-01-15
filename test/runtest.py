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
from rich.console import Console
from rich.traceback import Traceback

from faebryk.libs.logging import FLOG_FMT, setup_basic_logging
from faebryk.libs.util import indented_container

logger = logging.getLogger(__name__)

FLOG_FMT.set(True, force=True)


class DiscoveryMode(str, Enum):
    manual = "manual"
    pytest = "pytest"


def create_method_wrapper(cls, method_name):
    method = getattr(cls, method_name)

    def wrapper(**kwargs):
        instance = cls()
        if hasattr(instance, "setup_method"):
            instance.setup_method()
        try:
            getattr(instance, method_name)(**kwargs)
        finally:
            if hasattr(instance, "teardown_method"):
                instance.teardown_method()

    wrapper.__name__ = method_name
    wrapper.__qualname__ = f"{cls.__name__}.{method_name}"
    if hasattr(method, "pytestmark"):
        wrapper.pytestmark = method.pytestmark
    # Also copy dict for other attributes if needed
    wrapper.__dict__.update(method.__dict__)

    return wrapper


def discover_tests(
    filepaths: list[Path], test_pattern: str
) -> list[tuple[Path, Callable]]:
    """
    Manual test discovery by loading modules and finding matching functions.
    Note: This does NOT discover parametrized test variants.
    """
    matches = []
    import_errors = {}
    for fp in filepaths:
        if not re.search(test_pattern, fp.read_text(encoding="utf-8")):
            continue
        try:
            module_name = f"test_module_{fp.stem}"
            spec = importlib.util.spec_from_file_location(module_name, fp)
            if spec is None:
                continue
            module = importlib.util.module_from_spec(spec)
            if spec.loader is None:
                continue
            # Register module in sys.modules before exec to allow forward references
            # in dataclasses to resolve correctly
            sys.modules[module_name] = module
            # redirect_stderr and redirect_stdout to devnull
            # with redirect_stdout(open(os.devnull, "w")):
            #   with redirect_stderr(open(os.devnull, "w")):
            spec.loader.exec_module(module)
        except Exception:
            from rich import traceback

            # TODO suppress doesn't seem to work
            import_errors[fp] = traceback.Traceback(suppress=[__name__])
            continue
        for v in vars(module).values():
            if not hasattr(v, "__name__"):
                continue

            # Check if it's a class
            if isinstance(v, type):
                class_matches = re.search(test_pattern, v.__name__)

                # Iterate over methods
                for attr_name in dir(v):
                    if not attr_name.startswith("test_"):
                        continue

                    attr = getattr(v, attr_name)
                    if not callable(attr):
                        continue

                    # Check if method matches
                    method_matches = re.search(test_pattern, attr_name)

                    # Check if full name matches (Class::method)
                    full_name = f"{v.__name__}::{attr_name}"
                    full_name_matches = re.search(test_pattern, full_name)

                    if class_matches or method_matches or full_name_matches:
                        matches.append((fp, create_method_wrapper(v, attr_name)))

            elif callable(v):
                if re.search(test_pattern, v.__name__):
                    matches.append((fp, v))
    if not matches:
        for fp, tb in import_errors.items():
            from rich import print

            print(f"Error importing {fp}")
            print(tb)
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
        if len(self.names) == 1:
            self.values = [(vs,) for vs in self.values]
        for vs in self.values:
            if len(vs) != len(self.names):
                raise ValueError(
                    f"Expected {len(self.names)} values, got {len(vs)}: in {self}"
                )


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
        if test_func.__dict__:
            print(indented_container(test_func.__dict__, recursive=True))
        if hasattr(test_func, "pytestmark"):
            for mark in test_func.pytestmark:
                if mark.name == "parametrize":
                    from _pytest.mark import ParameterSet

                    raw_values = mark.args[1]
                    values = [
                        v.values if isinstance(v, ParameterSet) else v
                        for v in raw_values
                    ]
                    arg_def = _PytestArgDef(
                        names=[name.strip() for name in mark.args[0].split(",")],
                        values=values,
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
        # check if has argument called tmpdir
        if "tmpdir" in test_func.__code__.co_varnames:
            old_test_func = test_func

            def _(*args, **kwargs):
                with tempfile.TemporaryDirectory() as tmp_path_:
                    tmp_path = Path(tmp_path_)
                    old_test_func(*args, tmpdir=tmp_path, **kwargs)  # type: ignore

            test_func = _

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

        try:
            fn()
        except Exception:
            # Print Rich traceback with locals and suppressed internals
            console = Console(stderr=True)
            tb = Traceback.from_exception(
                *sys.exc_info(),
                show_locals=True,
                suppress=[typer, "click", __file__],
            )
            console.print(tb)
            raise SystemExit(1)


class TestNotFound(Exception):
    pass


class TestFileNotFound(TestNotFound):
    pass


class TestCaseNotFound(TestNotFound):
    pass


def run(
    test_name: str,
    filepaths: list[Path],
):
    test_files: list[Path] = []
    for filepath in filepaths:
        if not filepath.exists():
            raise TestFileNotFound(f"Filepath {filepath} does not exist")
        if not filepath.is_dir():
            test_files.append(filepath)
        else:
            test_files.extend(filepath.rglob("*.py"))

    matches = discover_tests(test_files, test_name)
    if not matches:
        raise TestCaseNotFound(f"Test function '{test_name}' not found in {filepaths}")
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
