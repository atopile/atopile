#!/usr/bin/env python3

"""
This file generates faebryk/src/faebryk/library/__init__.py
"""

import ast
import logging
import re
from graphlib import TopologicalSorter
from itertools import groupby
from pathlib import Path
from typing import Iterable

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent.parent
LIBRARY_DIR = REPO_ROOT / "src" / "faebryk" / "library"
OUT = LIBRARY_DIR / "_F.py"


def try_(stmt: str, exc: str | type[Exception] | Iterable[type[Exception]]):
    if isinstance(exc, type):
        exc = exc.__name__
    if not isinstance(exc, str):
        exc = f"({', '.join(e.__name__ for e in exc)})"

    return (
        f"try:\n    {stmt}\nexcept {exc} as e:\n    print('{stmt.split(' ')[-1]}', e)"
    )


def extract_public_classes(module_path: Path) -> list[str]:
    """
    Parse a Python file and extract all public class names (not starting with _).
    Returns a list of class names defined at the top level of the module.
    """
    try:
        content = module_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(module_path))

        classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
                # Check if this is a top-level class (not nested)
                # We do this by checking if the parent is the Module node
                for parent_node in ast.walk(tree):
                    if isinstance(parent_node, ast.Module):
                        if node in parent_node.body:
                            classes.append(node.name)
                            break

        return sorted(set(classes))  # Remove duplicates and sort
    except Exception as e:
        logger.warning(f"Failed to parse {module_path}: {e}")
        return []


def topo_sort(modules_out: dict[str, tuple[Path, list[str]]]):
    """
    Sort modules topologically based on their dependencies.
    """

    def find_deps(module_path: Path) -> set[str]:
        f = module_path.read_text(encoding="utf-8")
        p = re.compile(r"[^a-zA-Z_0-9]F\.([a-zA-Z_][a-zA-Z_0-9]*)")
        return set(p.findall(f))

    if True:
        SRC_DIR = LIBRARY_DIR.parent.parent
        all_modules = [
            (p.stem, p) for p in SRC_DIR.rglob("*.py") if not p.stem.startswith("_")
        ]
    else:
        all_modules = [
            (module_name, module_path)
            for module_name, (module_path, _) in modules_out.items()
        ]

    topo_graph = [
        (module_name, find_deps(module_path))
        for module_name, module_path in all_modules
    ]

    # handles name collisions (of non-lib modules)
    topo_grouped = groupby(
        sorted(topo_graph, key=lambda item: item[0]), lambda item: item[0]
    )
    topo_merged = {
        name: {x for xs in group for x in xs[1]} for name, group in topo_grouped
    }

    # sort for deterministic order
    topo_graph = {
        k: sorted(v) for k, v in sorted(topo_merged.items(), key=lambda item: item[0])
    }
    order = list(TopologicalSorter(topo_graph).static_order())

    # TEST
    seen = set()
    for m in order:
        if m not in topo_graph:
            continue
        for sub in topo_graph[m]:
            if sub not in seen and sub in topo_graph:
                raise Exception(f"Collision: {sub} after {m}")
        seen.add(m)

    # Flatten modules_out into (module_name, class_name) tuples in topological order
    result: list[tuple[str, str]] = []
    for module_name in order:
        if module_name in modules_out:
            _, class_names = modules_out[module_name]
            for class_name in class_names:
                result.append((module_name, class_name))

    return result


def main():
    assert LIBRARY_DIR.exists()

    logger.info(f"Scanning {LIBRARY_DIR} for modules")

    module_files = [p for p in LIBRARY_DIR.glob("*.py") if not p.name.startswith("_")]

    logger.info(f"Found {len(module_files)} modules")

    modules_out: dict[str, tuple[Path, list[str]]] = {}

    # Extract classes from each module
    for module_path in module_files:
        module_name = module_path.stem
        classes = extract_public_classes(module_path)

        if not classes:
            logger.warning(f"No public classes found in {module_path}")
            continue

        # If a class with the same name as the module exists, use only that
        if module_name in classes:
            modules_out[module_name] = (module_path, [module_name])
        else:
            # Otherwise, import the module itself as a namespace
            # Use the special marker to signal module import
            marker = f"__{module_name}__AS_MODULE__"
            modules_out[module_name] = (module_path, [marker])
            logger.info(
                f"Module {module_name} has no matching class, "
                f"importing module as namespace"
            )

    modules_ordered = topo_sort(modules_out)

    # Generate import statements
    import_statements: list[str] = []
    for module, class_ in modules_ordered:
        # Check if this is a module import (marked with __NAME__AS_MODULE__)
        if class_.endswith("__AS_MODULE__"):
            # Import the module itself as a namespace
            # The marker format is "__ModuleName__AS_MODULE__"
            import_statements.append(f"import faebryk.library.{module} as {module}")
        else:
            # Import a specific class from the module
            import_statements.append(f"from faebryk.library.{module} import {class_}")

    OUT.write_text(
        "# This file is part of the faebryk project\n"
        "# SPDX-License-Identifier: MIT\n"
        "\n"
        '"""\n'
        "This file is autogenerated by tools/library/gen_F.py\n"
        "This is the __init__.py file of the library\n"
        "All modules are in ./<module>.py with name class <module>\n"
        "Export all <module> classes here\n"
        "Do it programmatically instead of specializing each manually\n"
        "This way we can add new modules without changing this file\n"
        '"""\n'
        "\n"
        "# Disable ruff warning for whole block\n"
        "# flake8: noqa: F401\n"
        "# flake8: noqa: I001\n"
        "# flake8: noqa: E501\n"
        "\n" + "\n".join(import_statements) + "\n"
        "\n"
        "__all__ = [\n"
        + "\n".join(f'"{module}",' for module, _ in modules_ordered)
        + "\n]"
        "\n",
        encoding="utf-8",
    )

    logger.info(f"Exported to {OUT}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
