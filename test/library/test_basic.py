# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import inspect

import pytest

from faebryk.core.core import Namespace
from faebryk.core.node import Node
from faebryk.core.trait import Trait, TraitImpl
from faebryk.libs.library import L

try:
    import faebryk.library._F as F
except ImportError:
    F = None


def test_load_library():
    assert F is not None, "Failed to load library"


@pytest.mark.skipif(F is None, reason="Library not loaded")
@pytest.mark.parametrize("name, module", list(vars(F).items()))
def test_symbol_types(name: str, module):
    # private symbols get a pass
    if name.startswith("_"):
        return

    # skip once wrappers
    # allow once wrappers for type generators
    if getattr(module, "_is_once_wrapper", False):
        return

    # otherwise, only allow Node or Namespace class objects
    assert isinstance(module, type) and issubclass(module, (Node, Namespace))


@pytest.mark.skipif(F is None, reason="Library not loaded")
@pytest.mark.parametrize(
    "name, module",
    [
        (name, module)
        for name, module in vars(F).items()
        if not (
            name.startswith("_")
            or not isinstance(module, type)
            or not issubclass(module, Node)
            or (issubclass(module, Trait) and not issubclass(module, TraitImpl))
        )
    ],
)
def test_init_args(name: str, module):
    """Make sure we can instantiate all classes without error"""

    # check if constructor has no args & no varargs
    init_signature = inspect.signature(module.__init__)
    if len(init_signature.parameters) > 1 or any(
        param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
        for param in init_signature.parameters.values()
    ):
        pytest.skip("Skipped module with init args because we can't instantiate it")

    try:
        module()
    except L.AbstractclassError:
        pytest.skip("Skipped abstract class")
