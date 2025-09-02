import ast
import importlib
from pathlib import Path
from textwrap import dedent

import pytest

import faebryk.library._F as F
from atopile.datatypes import TypeRef
from atopile.front_end import Bob
from atopile.parse import parse_text_as_file
from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.core.trait import Trait
from faebryk.libs.library import L

# Without any way to mark which modules are not exposed to user,
# we need to explicity skip them
skip_list = [
    "DIP",
    "Footprint",
    "KicadFootprint",
    "Net",
    "PCB",
    "Pad",
    "QFN",
    "SMDTwoPin",
    "SOIC",
    "Symbol",
]


def _extract_usage_example_ast(file_path: str) -> tuple[str | None, str | None]:
    """
    Parse the usage example trait implementation and return (example, language).
    """
    example = None
    language = None

    LIBRARY_PATH = Path(F.__file__).parent
    abs_file_path = LIBRARY_PATH / f"{file_path}"

    content = abs_file_path.read_text()
    tree = ast.parse(content)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(t, ast.Name) and t.id == "usage_example" for t in node.targets
        ):
            continue
        if not isinstance(node.value, ast.Call):
            continue
        if not isinstance(node.value.keywords, list):
            continue
        if len(node.value.keywords) != 2:
            continue
        if isinstance(node.value.keywords[0].value, ast.Constant):
            example = str(node.value.keywords[0].value.value)
        if isinstance(node.value.keywords[1].value, ast.Attribute):
            language = str(node.value.keywords[1].value.attr)

    return example, language


@pytest.mark.skipif(F is None, reason="Library not loaded")
@pytest.mark.parametrize(
    "name, module",
    [(name, module) for name, module in vars(F).items() if (isinstance(module, type))],
)
def test_usage_examples(name: str, module):
    """Test that all usage examples compile to graphs"""
    bob = Bob()

    if name in skip_list:
        pytest.skip(f"{name} is not exposed to user, does not need usage example")

    module_name = getattr(module, "__module__", None)
    if module_name is None:
        pytest.fail(f"Module {name} has no module name")
    mod = importlib.import_module(module_name)
    module_file = getattr(mod, "__file__", None)

    if module_file is None:
        pytest.fail(f"Module {name} has no file")

    example, language = _extract_usage_example_ast(module_file)

    if example is None:
        if issubclass(module, Module):
            pytest.fail(f"{name} is a module without a usage example")
        if issubclass(module, ModuleInterface):
            pytest.skip(f"{name} is a module interface without a usage example")
        if issubclass(module, Trait):
            pytest.skip(f"{name} is a trait without a usage example")
        pytest.skip(f"{name} has no usage example")

    if language != F.has_usage_example.Language.ato.value:
        pytest.skip(f"{name} has no usage example in ato language")

    tree = parse_text_as_file(dedent(example))
    node = bob.build_ast(tree, TypeRef(["UsageExample"]))
    assert isinstance(node, L.Module)
