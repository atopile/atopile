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

from faebryk.libs.util import indented_container

logger = logging.getLogger(__name__)


class DiscoveryMode(str, Enum):
    manual = "manual"
    pytest = "pytest"


def _find_class_fixtures(cls) -> dict[str, Callable]:
    """Find all @pytest.fixture decorated methods in the class hierarchy."""
    from _pytest.fixtures import FixtureFunctionDefinition

    fixtures = {}
    for klass in cls.__mro__:
        for name, attr in vars(klass).items():
            if isinstance(attr, FixtureFunctionDefinition):
                fixtures[name] = attr
    return fixtures


def create_method_wrapper(cls, method_name):
    method = getattr(cls, method_name)
    class_fixtures = _find_class_fixtures(cls)

    def wrapper(**kwargs):
        instance = cls()

        # Resolve class-level fixtures for parameters not already in kwargs
        import inspect

        sig = inspect.signature(method)
        for param_name in sig.parameters:
            if param_name == "self":
                continue
            if param_name in kwargs:
                continue
            if param_name in class_fixtures:
                # Call the underlying fixture function on the instance
                # Fixtures are wrapped in FixtureFunctionDefinition which can't
                # be called directly, so we access the original via __wrapped__
                fixture_def = getattr(instance, param_name)
                if hasattr(fixture_def, "__wrapped__"):
                    kwargs[param_name] = fixture_def.__wrapped__(instance)
                else:
                    kwargs[param_name] = fixture_def()

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


def _get_package_module_name(fp: Path) -> str | None:
    """
    If the file is under src/faebryk, src/atopile, or test/, return the proper
    package module name. Otherwise return None.
    """
    parts = fp.parts

    # Handle src/faebryk and src/atopile packages
    for pkg_name in ("faebryk", "atopile"):
        if "src" in parts and pkg_name in parts:
            src_idx = parts.index("src")
            pkg_idx = parts.index(pkg_name)
            # Make sure pkg is directly under src
            if pkg_idx == src_idx + 1:
                # Build module name from package onwards, excluding .py extension
                module_parts = list(parts[pkg_idx:])
                # Remove .py extension from last part
                module_parts[-1] = fp.stem
                return ".".join(module_parts)

    # Handle test/ directory - build module name from test/ onwards
    if "test" in parts:
        test_idx = parts.index("test")
        # Build module name from test onwards
        module_parts = list(parts[test_idx:])
        # Remove .py extension from last part
        module_parts[-1] = fp.stem
        return ".".join(module_parts)

    return None


def _strip_regex_anchors(pattern: str) -> str:
    """
    Strip regex anchors (^ and $) from a pattern.

    Used for preliminary file content search where anchors don't make sense.
    """
    # Remove leading ^ (possibly after whitespace or group start)
    pattern = re.sub(r"^\^", "", pattern)
    # Remove trailing $ (possibly before whitespace or group end)
    pattern = re.sub(r"\$$", "", pattern)
    return pattern


def discover_tests(
    filepaths: list[Path], test_pattern: str
) -> list[tuple[Path, Callable]]:
    """
    Manual test discovery by loading modules and finding matching functions.
    Note: This does NOT discover parametrized test variants.
    """
    from rich import print

    # Strip anchors for file content search (just a quick filter)
    file_search_pattern = _strip_regex_anchors(test_pattern)

    matches = []
    import_errors = {}
    for fp in filepaths:
        if not re.search(file_search_pattern, fp.read_text(encoding="utf-8")):
            continue
        try:
            # Check if file is in src/faebryk or src/atopile - load as package module
            package_module_name = _get_package_module_name(fp)
            if package_module_name:
                module = importlib.import_module(package_module_name)
            else:
                # Fall back to file-based loading for test files
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
            print(f"Error importing {fp}")
            print(tb)
    return matches


def _fixture_setup_project_config(tmp_path: Path):
    from atopile.config import ProjectConfig, ProjectPaths, config

    config.project = ProjectConfig.skeleton(
        entry="", paths=ProjectPaths(build=tmp_path / "build", root=tmp_path)
    )


def _idval_from_value(val: Any) -> str | None:
    """
    Generate a pytest-compatible ID string for a parameter value.

    This mimics pytest's _idval_from_value logic for generating test IDs.
    """
    if isinstance(val, str | bytes):
        # For strings/bytes, use ascii_escaped equivalent
        if isinstance(val, bytes):
            return val.decode("ascii", "backslashreplace")
        # For regular strings, escape non-printable chars
        return val.encode("unicode_escape").decode("ascii")
    elif val is None or isinstance(val, float | int | bool | complex):
        return str(val)
    elif isinstance(val, re.Pattern):
        return val.pattern.encode("unicode_escape").decode("ascii")
    elif hasattr(val, "__name__") and isinstance(val.__name__, str):
        # Name of a class, function, module, etc.
        return val.__name__
    # Check for enum after __name__ check (enums have __name__ but we want str())
    elif isinstance(val, Enum):
        return str(val)
    return None


def _idval(val: Any, argname: str, idx: int, idfn: Callable | None = None) -> str:
    """
    Generate a pytest-compatible ID for a parameter value.

    Falls back to argname+idx if the value type is not supported.
    """
    # Try user-provided id function first
    if idfn is not None:
        try:
            id_result = idfn(val)
            if id_result is not None:
                id_from_fn = _idval_from_value(id_result)
                if id_from_fn is not None:
                    return id_from_fn
        except Exception:
            pass

    # Try to get ID from value
    id_from_value = _idval_from_value(val)
    if id_from_value is not None:
        return id_from_value

    # Fallback to argname + index
    return f"{argname}{idx}"


def _make_unique_ids(ids: list[str]) -> list[str]:
    """
    Make IDs unique by appending suffixes to duplicates.

    This mimics pytest's duplicate handling logic.
    """
    from collections import Counter

    id_counts = Counter(ids)
    id_suffixes: dict[str, int] = {id_: 0 for id_ in id_counts}
    resolved_ids = list(ids)

    for index, id_ in enumerate(ids):
        if id_counts[id_] > 1:
            suffix = ""
            if id_ and id_[-1].isdigit():
                suffix = "_"
            new_id = f"{id_}{suffix}{id_suffixes[id_]}"
            # Ensure uniqueness
            while new_id in set(resolved_ids[:index]):
                id_suffixes[id_] += 1
                new_id = f"{id_}{suffix}{id_suffixes[id_]}"
            resolved_ids[index] = new_id
            id_suffixes[id_] += 1

    return resolved_ids


@dataclass
class _PytestArgDef:
    names: list[str]
    values: list[tuple[Any, ...]]
    id_fn: Callable[[Any], str] | None
    # Explicit IDs from pytest.param(..., id="...") or parametrize(..., ids=[...])
    explicit_ids: list[str | None] | None = None

    def __post_init__(self):
        if len(self.names) == 1:
            self.values = [(vs,) for vs in self.values]
        for vs in self.values:
            if len(vs) != len(self.names):
                raise ValueError(
                    f"Expected {len(self.names)} values, got {len(vs)}: in {self}"
                )

    def get_ids(self) -> list[str]:
        """
        Generate pytest-compatible IDs for all parameter sets.

        Returns a list of unique ID strings matching pytest's behavior.
        """
        raw_ids: list[str] = []

        for idx, values in enumerate(self.values):
            # Check for explicit ID first
            if self.explicit_ids and idx < len(self.explicit_ids):
                explicit_id = self.explicit_ids[idx]
                if explicit_id is not None:
                    raw_ids.append(explicit_id)
                    continue

            # Generate ID from values (joined by "-" for multiple params)
            param_ids = [
                _idval(val, argname, idx, self.id_fn)
                for val, argname in zip(values, self.names, strict=True)
            ]
            raw_ids.append("-".join(param_ids))

        return _make_unique_ids(raw_ids)


def _print_test_header(
    filepath: Path, test_name: str, args: str | None = None, width: int = 80
) -> None:
    """Print a formatted header before running a test."""
    print()
    print("=" * width)
    print(f"File:      {filepath}")
    print(f"Test:      {test_name}")
    if args is not None:
        print(f"Arguments: [{args}]")
    print("-" * width)


def run_tests(
    matches: list[tuple[Path, Callable]], arg_filter: str | None = None
) -> None:
    """
    Run tests discovered via manual discovery.

    Args:
        matches: List of (filepath, test_function) tuples
        arg_filter: Optional argument string filter (e.g., "arg1-arg2" from "test_foo[arg1-arg2]")
                   If provided, only parametrized variants matching this filter will run.
    """
    import tempfile

    import typer

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
                    values: list[tuple[Any, ...]] = []
                    explicit_ids: list[str | None] = []

                    for v in raw_values:
                        if isinstance(v, ParameterSet):
                            values.append(v.values)
                            explicit_ids.append(v.id)
                        else:
                            values.append(v)
                            explicit_ids.append(None)

                    # Also check for ids kwarg (can be list or callable)
                    ids_kwarg = mark.kwargs.get("ids")
                    id_fn: Callable | None = None
                    if callable(ids_kwarg):
                        id_fn = ids_kwarg
                    elif isinstance(ids_kwarg, list):
                        # Merge with explicit_ids (explicit takes precedence)
                        for i, id_val in enumerate(ids_kwarg):
                            if i < len(explicit_ids) and explicit_ids[i] is None:
                                explicit_ids[i] = str(id_val) if id_val is not None else None

                    arg_def = _PytestArgDef(
                        names=[name.strip() for name in mark.args[0].split(",")],
                        values=values,
                        id_fn=id_fn,
                        explicit_ids=explicit_ids if any(x is not None for x in explicit_ids) else None,
                    )
                if mark.name == "usefixtures":
                    if "setup_project_config" in mark.args:
                        _fixture_setup_project_config(tmp_path)
                    else:
                        raise ValueError(
                            f"Test {test_func.__name__} is using usefixtures. "
                            "Manual discovery does not support usefixtures."
                        )
        # check if has argument called tmpdir or tmp_path
        varnames = test_func.__code__.co_varnames
        needs_tmpdir = "tmpdir" in varnames
        needs_tmp_path = "tmp_path" in varnames
        if needs_tmpdir or needs_tmp_path:
            old_test_func = test_func

            def _(*args, **kwargs):
                with tempfile.TemporaryDirectory() as tmp_path_str:
                    tmp_path_obj = Path(tmp_path_str)
                    if needs_tmpdir:
                        kwargs["tmpdir"] = tmp_path_obj
                    if needs_tmp_path:
                        kwargs["tmp_path"] = tmp_path_obj
                    old_test_func(*args, **kwargs)

            test_func = _

        sys.argv = [test_func.__name__]

        def fn():
            if not arg_def:
                if arg_filter is not None:
                    logger.warning(
                        f"Test {test_func.__name__} is not parametrized but "
                        f"arg filter '[{arg_filter}]' was specified"
                    )
                _print_test_header(filepath, test_func.__name__)
                test_func()
                return

            # Get pytest-compatible IDs for all parameter sets
            param_ids = arg_def.get_ids()

            # Compile arg_filter as regex if provided
            arg_pattern: re.Pattern | None = None
            if arg_filter is not None:
                try:
                    arg_pattern = re.compile(arg_filter)
                except re.error as e:
                    raise ValueError(
                        f"Invalid regex pattern in arg filter '[{arg_filter}]': {e}"
                    ) from e

            # Filter to matching parameter sets
            runs_executed = 0
            for idx, (values, param_id) in enumerate(zip(arg_def.values, param_ids)):
                # If arg_filter is specified, only run matching variants (regex search)
                if arg_pattern is not None and not arg_pattern.search(param_id):
                    continue

                kwargs = dict(zip(arg_def.names, values))
                _print_test_header(filepath, test_func.__name__, param_id)
                test_func(**kwargs)
                runs_executed += 1

            if arg_filter is not None and runs_executed == 0:
                available_ids = ", ".join(param_ids[:5])
                if len(param_ids) > 5:
                    available_ids += f", ... ({len(param_ids)} total)"
                raise TestCaseNotFound(
                    f"No parametrized variant matching regex '[{arg_filter}]' found for "
                    f"{test_func.__name__}. Available: {available_ids}"
                )

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


def _parse_test_name_with_args(test_name: str) -> tuple[str, str | None]:
    """
    Parse a test name that may include an argument string.

    Formats supported:
    - "test_foo" -> ("test_foo", None)
    - "test_foo[arg1-arg2]" -> ("test_foo", "arg1-arg2")
    - "TestClass::test_method[arg]" -> ("TestClass::test_method", "arg")

    Returns (test_pattern, arg_filter) where arg_filter is None if no brackets present.
    """
    # Match pattern: name[args] where args can contain nested brackets
    # We need to find the outermost [...] at the end
    if not test_name.endswith("]"):
        return test_name, None

    # Find matching opening bracket
    depth = 0
    for i in range(len(test_name) - 1, -1, -1):
        if test_name[i] == "]":
            depth += 1
        elif test_name[i] == "[":
            depth -= 1
            if depth == 0:
                # Found the matching opening bracket
                base_name = test_name[:i]
                arg_string = test_name[i + 1 : -1]  # Extract content between brackets
                return base_name, arg_string

    # No matching bracket found, treat as regular name
    return test_name, None


def run(
    test_name: str,
    filepaths: list[Path],
):
    # Parse test_name[argstring] format
    test_pattern, arg_filter = _parse_test_name_with_args(test_name)

    test_files: list[Path] = []
    for filepath in filepaths:
        if not filepath.exists():
            raise TestFileNotFound(f"Filepath {filepath} does not exist")
        if not filepath.is_dir():
            test_files.append(filepath)
        else:
            test_files.extend(filepath.rglob("*.py"))

    matches = discover_tests(test_files, test_pattern)
    if not matches:
        raise TestCaseNotFound(f"Test function '{test_pattern}' not found in {filepaths}")
    run_tests(matches, arg_filter=arg_filter)


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
