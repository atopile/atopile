import argparse
import ast
import subprocess
import sys
import textwrap
from pathlib import Path
from textwrap import dedent

import faebryk.library._F as F
from atopile.datatypes import TypeRef
from faebryk.libs.library import L
from atopile.front_end import Bob, _has_ato_cmp_attrs
from atopile.parse import parse_text_as_file
from atopile.mcp.tools.library import _get_library_nodes
from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface



def extract_usage_example_runtime(module_name: str) -> tuple[str, str]:
    """
    Instantiate a library module, get its has_usage_example trait,
    and return (example, language).
    """
    try:
        module_cls = getattr(F, module_name)
    except AttributeError as exc:
        raise SystemExit(
            f"Module '{module_name}' not found in faebryk.library._F"
        ) from exc

    # Instantiate module to construct fields/traits
    module_obj = module_cls()

    # Get the usage example trait implementation
    trait = module_obj.get_trait(F.has_usage_example)

    # Access stored example text and language (private attrs by convention)
    example = getattr(trait, "_example", None)
    language = getattr(trait, "_language", None)
    if not example or not language:
        raise SystemExit(
            f"Module '{module_name}' does not provide a usage example"
        )

    return textwrap.dedent(example).strip("\n"), str(language)

def extract_usage_example_ast(file_path: str) -> tuple[str, str]:
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

def get_all_file_paths() -> list[str]:
    filepaths = []
    for m in F.__dict__.values():
        if isinstance(m, type):
            module_name = getattr(m, "__module__", None)
            if module_name is not None:
                import importlib
                mod = importlib.import_module(module_name)
                module_file = getattr(mod, "__file__", None)
                filepaths.append(module_file)
    return filepaths

if __name__ == "__main__":
    bob = Bob()

    module_filepaths = get_all_file_paths()

    for module_filepath in module_filepaths:
        try:
            example, language = extract_usage_example_ast(module_filepath)
            if example == "None" or language == "None":
                continue
            tree = parse_text_as_file(dedent(example))
            node = bob.build_ast(tree, TypeRef(["UsageExample"]))
            assert isinstance(node, L.Module)
            print(f"Successfully built example for {module_filepath}")
        except* Exception as eg:
            print(f"Error building example for {module_filepath}:")
            for sub in eg.exceptions:
                print(f"  - {repr(sub)}")


    # r1 = bob.resolve_node_shortcut(node, "r1")
    # trait = r1.get_trait(F.has_usage_example)
    # print(trait._language)
    # print(dedent(trait._example))
