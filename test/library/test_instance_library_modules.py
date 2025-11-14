# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import pytest

import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.core.core import Namespace

try:
    from faebryk.library import _F as F
except ImportError:
    F = None


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
            and not issubclass(module, fabll.ImplementsTrait)
        )
    ],
)
def test_instantiate_library_modules(name: str, module: type[fabll.Node]):
    """Verify that library modules can be successfully instantiated.

    This test attempts to instantiate all library modules that:
    - Are not Traits
    - Do not have a MakeChild or setup method (and thus don't require
      arguments for instantiation)
    """
    try:
        _ = module.MakeChild()
    except TypeError:
        pytest.xfail(f"{module.__name__} needs arguments to be instantiated")
    except Exception as e:
        pytest.fail(f"Failed to instantiate module {module.__name__}: {e}")
