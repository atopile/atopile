# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import pytest

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.core import Namespace

try:
    from faebryk.library import _F as F
except ImportError:
    F = None

IGNORE_MODULES = ["NumberDomain"]


def test_load_library():
    """Verify that the faebryk library can be loaded successfully."""
    assert F is not None, "Failed to load library"


@pytest.mark.skipif(F is None, reason="Library not loaded")
@pytest.mark.parametrize(
    "name, module",
    [
        (name, module)
        for name, module in list(vars(F).items())
        if F is not None
        and not name.startswith("_")
        and not getattr(module, "_is_once_wrapper", False)
        and isinstance(module, type)
    ],
)
def test_symbol_types(name: str, module: fabll.Node):
    """Verify that all exported library symbols are valid Node or Namespace types."""
    # All symbols must be Node or Namespace class types
    assert isinstance(module, type) and issubclass(module, (fabll.Node, Namespace)), (
        f"Module [{name}] is not a Node or Namespace class type but [{type(module)}]"
    )


_discovery_tg = fbrk.TypeGraph.create(g=graph.GraphView.create())


def _is_trait(node_type_bound: fabll.TypeNodeBoundTG) -> bool:
    return node_type_bound.try_get_type_trait(fabll.ImplementsTrait) is not None


@pytest.mark.skipif(F is None, reason="Library not loaded")
@pytest.mark.parametrize(
    "name, module",
    [
        (name, module)
        for name, module in list(vars(F).items())
        if F is not None
        if (
            not name.startswith("_")
            and isinstance(module, type)
            and issubclass(module, fabll.Node)
            and not _is_trait(module.bind_typegraph(tg=_discovery_tg))
            and name not in IGNORE_MODULES
        )
    ],
)
def test_instantiate_libary_modules(name: str, module: type[fabll.Node]):
    """Verify that library modules can be successfully instantiated.

    This test attempts to instantiate all library modules that:
    - Are not Traits
    - Do not have a MakeChild or setup method (and thus don't require
      arguments for instantiation)
    """
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)
    try:
        print(module.__name__)
        instance = module.bind_typegraph(tg=tg).create_instance(g=g)
        assert not _is_trait(module.bind_typegraph(tg=tg)), (
            f"Module {module.__name__} is a trait"
        )
        assert instance.try_get_trait(fabll.is_module) or instance.try_get_trait(
            fabll.is_interface
        ), f"Module {module.__name__} is not a module or interface"

    except TypeError:
        pytest.xfail(f"{module.__name__} needs arguments to be instantiated")
    except Exception as e:
        pytest.fail(f"Failed to instantiate module {module.__name__}: {e}")


if __name__ == "__main__":
    test_instantiate_libary_modules("Resistor", F.Resistor)
