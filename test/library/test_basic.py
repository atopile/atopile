# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import unittest

from faebryk.core.core import Namespace
from faebryk.core.node import Node


class TestBasicLibrary(unittest.TestCase):
    def test_load_library(self):
        import faebryk.library._F  # noqa: F401

    def test_symbol_types(self):
        import faebryk.library._F as F

        symbols = {
            k: v
            for k, v in vars(F).items()
            if not k.startswith("_")
            and (not isinstance(v, type) or not issubclass(v, (Node, Namespace)))
            and not type(v).__name__ == "_once"
        }
        self.assertFalse(symbols, f"Found unexpected symbols: {symbols}")

    def test_imports(self):
        import faebryk.library._F as F
        from faebryk.core.trait import Trait, TraitImpl

        # get all symbols in F
        symbols = {
            k: v
            for k, v in vars(F).items()
            if not k.startswith("_")
            and isinstance(v, type)
            and issubclass(v, Node)
            # check if constructor has no args
            and v.__init__.__code__.co_argcount == 1
            # no trait base
            and (not issubclass(v, Trait) or issubclass(v, TraitImpl))
        }

        for k, v in symbols.items():
            try:
                v()
            except Exception as e:
                self.fail(f"Failed to instantiate {k}: {e}")


if __name__ == "__main__":
    unittest.main()
