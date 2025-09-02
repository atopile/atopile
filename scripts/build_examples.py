import ast
import importlib
import textwrap
from pathlib import Path
from textwrap import dedent

import faebryk.library._F as F
from atopile.datatypes import TypeRef
from atopile.front_end import Bob
from atopile.parse import parse_text_as_file
from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.core.trait import Trait
from faebryk.libs.library import L


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

def extract_usage_example_ast(file_path: str) -> tuple[str | None, str | None]:
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
        if not any(isinstance(t, ast.Name) and t.id == "usage_example" for t in node.targets):
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
    module_results = {}

    modules = [(name, module) for name, module in vars(F).items()
        if (
            isinstance(module, type)
        )
    ]

    for name, module in modules:
        module_name = getattr(module, "__module__", None)
        if module_name is None:
            continue
        mod = importlib.import_module(module_name)
        module_file = getattr(mod, "__file__", None)
        if module_file is None:
            continue
        try:
            example, language = extract_usage_example_ast(module_file)
            if example is None or language is None:
                if issubclass(module, Module):
                    module_results[name] = "Fail: modules must have usage examples"
                    print(f"Fail: {name} is a module without a usage example")
                    continue
                else:
                    continue
            tree = parse_text_as_file(dedent(example))
            node = bob.build_ast(tree, TypeRef(["UsageExample"]))
            assert isinstance(node, L.Module)
            print(f"Successfully built example for {module_file}")
            module_results[module_file] = "PASS"
        except* Exception as eg:
            print(f"Error building example for {module_file}:")
            for sub in eg.exceptions:
                print(f"  - {repr(sub)}")
            module_results[module_file] = "FAIL"

    # Count and print the number of passing examples out of total
    num_pass = sum(1 for result in module_results.values() if result == "PASS")
    total = len(module_results)
    print(f"Passing examples: {num_pass} / {total}")

    # r1 = bob.resolve_node_shortcut(node, "r1")
    # trait = r1.get_trait(F.has_usage_example)
    # print(trait._language)
    # print(dedent(trait._example))
