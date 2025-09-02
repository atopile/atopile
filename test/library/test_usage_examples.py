import ast
import importlib
import textwrap
from pathlib import Path
from textwrap import dedent

import pytest

import faebryk.library._F as F
from atopile.datatypes import TypeRef
from atopile.front_end import Bob
from atopile.parse import parse_text_as_file
from faebryk.core.node import Node
from faebryk.core.trait import Trait
from faebryk.libs.library import L


def _extract_usage_example_ast(file_path: str) -> tuple[str, str]:
    """
    Parse the usage example trait implementation and return (example, language).
    """
    LIBRARY_PATH = Path(F.__file__).parent
    file_path = LIBRARY_PATH / f"{file_path}"

    content = file_path.read_text()
    tree = ast.parse(content)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if target.id == "usage_example":
                        example = node.value.keywords[0].value.value
                        language = node.value.keywords[1].value.attr
                        return example, language
    return "None", "None"

@pytest.mark.skipif(F is None, reason="Library not loaded")
@pytest.mark.parametrize(
    "name, module",
    [
        (name, module)
        for name, module in vars(F).items()
        if (
            isinstance(module, type)
        )
    ],
)
# @pytest.mark.timeout(60)  # TODO lower
def test_usage_examples(name: str, module):
    """Test that all usage examples compile to graphs"""
    bob = Bob()

    mod = importlib.import_module(module)
    module_file = getattr(mod, "__file__", None)

    if module_file is not None:
        example, language = _extract_usage_example_ast(module_file)
        tree = parse_text_as_file(dedent(example))
        node = bob.build_ast(tree, TypeRef(["UsageExample"]))
        assert isinstance(node, L.Module)
