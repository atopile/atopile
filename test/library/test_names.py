# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import ast
import unittest
from pathlib import Path

from faebryk.libs.util import repo_root as _repo_root


def _extract_classes_from_file(filepath: Path):
    with open(filepath, "r") as file:
        module = ast.parse(file.read())
    classes = [node for node in module.body if isinstance(node, ast.ClassDef)]
    return classes


class TestClassNames(unittest.TestCase):
    def test_class_name(self):
        root_dir = _repo_root()
        source_directory = root_dir / Path("src/faebryk/library/")

        for py_file in source_directory.glob("**/*.py"):
            classes = _extract_classes_from_file(py_file)
            for cls in classes:
                file_name = py_file.stem
                class_name = cls.name
                if class_name.startswith("_"):
                    continue
                self.assertEqual(class_name, file_name, f"In {py_file}")
