# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import ast
from pathlib import Path

import pytest

from faebryk.libs.util import repo_root as _repo_root


def _extract_classes_from_file(filepath: Path):
    with open(filepath, "r", encoding="utf-8") as file:
        module = ast.parse(file.read())
    classes = [node for node in module.body if isinstance(node, ast.ClassDef)]
    return classes


def _is_module_import(name: str) -> bool:
    """Check if name is imported as a module (not a class) in _F.py."""
    with open(
        _repo_root() / "src" / "faebryk" / "library" / "_F.py", "r", encoding="utf-8"
    ) as file:
        tree = ast.parse(file.read())

    module_imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("faebryk.library.") and alias.asname:
                    module_name = alias.name.split(".")[-1]
                    module_imports.add(module_name)
    return name in module_imports


@pytest.mark.parametrize(
    "py_file",
    [
        p
        for p in (_repo_root() / "src" / "faebryk" / "library").glob("**/*.py")
        if p.is_file() and not p.stem.startswith("_") and not _is_module_import(p.stem)
    ],
    ids=lambda p: p.stem,
)
def test_class_name(py_file: Path):
    """Test that class names match their file names in the library directory."""
    classes = _extract_classes_from_file(py_file)
    assert py_file.stem in [cls.name for cls in classes], (
        f"Class name mismatch in {py_file}"
    )
