# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import unittest
from typing import Sequence

from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.core.node import Node
from faebryk.libs.library import L


class TestUtil(unittest.TestCase):
    def test_trees(self):
        class N(Module):
            mif: ModuleInterface

            @L.rt_field
            def n(self):
                if self._depth == 0:
                    # TODO does this work?
                    return []
                return N(self._depth - 1)

            def __init__(self, depth: int):
                super().__init__()
                self._depth = depth

        level_count = 5
        n = N(level_count)

        def assertEqual(n1: Sequence[Node], n2: Sequence[Node]):
            n1s = list(sorted(n1, key=id))
            n2s = list(sorted(n2, key=id))
            self.assertEqual(n1s, n2s)

        tree = n.get_tree(types=(Module, ModuleInterface))
        levels = list(tree.iter_by_depth())
        print(tree)
        for i, le in enumerate(levels):
            print(i, le)
        self.assertEqual(len(levels), level_count + 2)
        assertEqual(levels[0], [n])
        n_i = n
        for i in range(1, level_count + 1):
            assertEqual(levels[i], [n_i.n, n_i.mif])
            n_i = n_i.n
        assertEqual(levels[level_count + 1], [n_i.mif])
