# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import unittest

from faebryk.core.core import Module, ModuleInterface
from faebryk.core.util import get_node_tree, iter_tree_by_depth


class TestUtil(unittest.TestCase):
    def test_trees(self):
        class N(Module):
            def __init__(self, depth: int):
                super().__init__()

                class _IFs(Module.IFS()):
                    mif = ModuleInterface()

                self.IFs = _IFs(self)

                if depth == 0:
                    return

                class _NODES(Module.NODES()):
                    n = N(depth - 1)

                self.NODEs = _NODES(self)

        level_count = 5
        n = N(level_count)

        tree = get_node_tree(n)
        levels = list(iter_tree_by_depth(tree))
        print(tree)
        for i, le in enumerate(levels):
            print(i, le)
        self.assertEqual(len(levels), level_count + 2)
        self.assertEqual(levels[0], [n])
        n_i = n
        for i in range(1, level_count + 1):
            self.assertEqual(levels[i], [n_i.NODEs.n, n_i.IFs.mif])
            n_i = n_i.NODEs.n
        self.assertEqual(levels[level_count + 1], [n_i.IFs.mif])


if __name__ == "__main__":
    unittest.main()
