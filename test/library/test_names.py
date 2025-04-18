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


@pytest.mark.parametrize(
    "py_file",
    [
        p
        for p in (_repo_root() / "src" / "faebryk" / "library").glob("**/*.py")
        if p.is_file()
    ],
    ids=lambda p: p.stem,
)
def test_class_name(py_file: Path):
    """Test that class names match their file names in the library directory."""
    classes = _extract_classes_from_file(py_file)
    for cls in classes:
        if cls.name.startswith("_"):
            continue
        assert cls.name == py_file.stem, f"Class name mismatch in {py_file}"
