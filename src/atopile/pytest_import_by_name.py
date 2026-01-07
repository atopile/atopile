"""
Pytest plugin: collect co-located tests in `src/` by importing modules by package name.

Why:
- This repo co-locates tests inside production modules under `src/`.
- Pytest's path-based collection can import the same file under a synthetic module name,
  while the application imports it by its package name (e.g. via `faebryk.library._F`).
- That can execute the same file twice under different names, triggering side-effectful
  type registration twice (FabLL's `Node.__init_subclass__`).

What we do:
- For `<repo>/src/{faebryk,atopile}/**/*.py` files that *look like* they contain tests,
  create a Module collector that imports by the real dotted module name.
- For `<repo>/src/...` files that don't look like they contain tests, we skip collection
  even if `python_files` is broad.
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path

import pytest

_TEST_HINT_RE = re.compile(r"(^|\n)\s*(def\s+test_|class\s+Test)", re.MULTILINE)

_ROOT: Path | None = None


def pytest_configure(config: pytest.Config) -> None:
    """
    Capture pytest's chosen repository root.

    Important: this plugin may be imported from site-packages (not from the repo),
    so deriving the repo root from `__file__` is unreliable.
    """
    global _ROOT
    _ROOT = Path(str(config.rootpath)).resolve()


def _module_name_for_src_file(path: Path) -> str | None:
    if path.is_dir():
        return None

    root = _ROOT or Path.cwd().resolve()
    src_root = root / "src"

    try:
        rel = path.resolve().relative_to(src_root)
    except Exception:
        return None

    if rel.parts[:1] not in {("faebryk",), ("atopile",)}:
        return None

    if rel.name == "__init__.py":
        rel = rel.parent
    else:
        rel = rel.with_suffix("")

    return ".".join(rel.parts)


def _file_looks_like_it_contains_tests(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False
    return _TEST_HINT_RE.search(text) is not None


class _ImportByNameModule(pytest.Module):
    _import_name: str

    @staticmethod
    def _import_by_name(import_name: str):
        # `faebryk.library` has a known import-order dependency: importing `_F` first
        # establishes a safe order (`_F` imports Literals before Expressions).
        if import_name.startswith("faebryk.library."):
            import faebryk.library._F as _unused  # noqa: F401

        return importlib.import_module(import_name)

    def _getobj(self):
        return self._import_by_name(self._import_name)


class _NoTestsModule(pytest.Module):
    """
    Module collector for `src/**.py` files that belong to our packages but don't contain
    tests.

    This is used from the `pytest_pycollect_makemodule` hook (which expects a `Module`),
    and crucially avoids importing the module at all.
    """

    def collect(self):
        return []


@pytest.hookimpl(tryfirst=True)
def pytest_pycollect_makemodule(module_path: Path, parent):
    """
    Override pytest's default per-file `Module` collector for in-package `src/**.py`.

    This hook is a **firstresult** hook (pytest expects a single Module back), so
    returning a collector here prevents the default path-based import that can create
    duplicate module identities.
    """
    modname = _module_name_for_src_file(module_path)
    if modname is None:
        return None

    if _file_looks_like_it_contains_tests(module_path):
        module = _ImportByNameModule.from_parent(parent, path=module_path)
        module._import_name = modname
        return module

    return _NoTestsModule.from_parent(parent, path=module_path)
