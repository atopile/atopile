# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import inspect

import pytest

from faebryk.core.core import Namespace
from faebryk.core.node import Node
from faebryk.core.trait import Trait
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
            or (issubclass(module, Trait))
        )
    ],
)
@pytest.mark.timeout(60)  # TODO lower
def test_init_args(name: str, module):
    """Make sure we can instantiate all classes without error"""

    # handle post_init_decorator
    init = (
        module.__init__
        if not hasattr(module, "__original_init__")
        else module.__original_init__
    )
    init_signature = inspect.signature(init)
    args = [p for p in init_signature.parameters.values() if p.name != "self"]

    # check if constructor has no non-default args
    if any(
        p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
        and p.default is inspect.Parameter.empty
        for p in args
    ):
        pytest.skip(
            f"Skipped module with init args because we can't instantiate it: {args}"
        )

    try:
        module()
    except L.AbstractclassError:
        pytest.skip("Skipped abstract class")
