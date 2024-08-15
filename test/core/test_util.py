# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import unittest
from enum import StrEnum
from typing import Iterable

from faebryk.core.core import Module, ModuleInterface, Node, Parameter
from faebryk.core.util import get_children, get_node_tree, iter_tree_by_depth


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

        def assertEqual(n1: list[Node], n2: list[Node]):
            n1s = list(sorted(n1, key=id))
            n2s = list(sorted(n2, key=id))
            self.assertEqual(n1s, n2s)

        tree = get_node_tree(n)
        levels = list(iter_tree_by_depth(tree))
        print(tree)
        for i, le in enumerate(levels):
            print(i, le)
        self.assertEqual(len(levels), level_count + 2)
        assertEqual(levels[0], [n])
        n_i = n
        for i in range(1, level_count + 1):
            assertEqual(levels[i], [n_i.NODEs.n, n_i.IFs.mif])
            n_i = n_i.NODEs.n
        assertEqual(levels[level_count + 1], [n_i.IFs.mif])

    def test_children(self):
        # TODO this is a really annoying to debug test

        class E(StrEnum):
            I_ = "IF"
            N = "NODE"
            P = "PARAM"

        EI = E.I_
        EN = E.N
        EP = E.P

        def moduleFromTree(
            t: dict[E, dict | type] | type, root_type: E
        ) -> type[Module]:
            root_type_t = {
                EN: Module,
                EI: ModuleInterface,
                EP: Parameter,
            }[root_type]

            class _(root_type_t):
                inner_tree = t

                def __init__(self):
                    super().__init__()

                    if isinstance(t, dict):
                        for k, vs in t.items():
                            assert isinstance(vs, list)
                            name = f"{k}s"
                            for i, v in enumerate(vs):
                                setattr(
                                    getattr(self, name), f"i{i}", moduleFromTree(v, k)()
                                )

            return _

        def assertEqual(n1: Iterable[Node], n2: list):
            t = list(sorted([n.inner_tree for n in n1], key=id))
            t2 = list(sorted(n2, key=id))
            from pprint import pformat

            if t != t2:
                print("Compare", "-" * 40)
                for x in t:
                    print(f"{id(x)} \n{pformat(x, indent=4)}")
                print("=" * 20)
                for x in t2:
                    print(f"{id(x)} \n{pformat(x, indent=4)}")
                print("~" * 40)
                for x1, x2 in zip(t, t2):
                    print(
                        f"{x1==x2:>5}| "
                        f"{id(x1):<20} {pformat(x1, indent=4).splitlines()[0]:<80}"
                        " -- "
                        f"{id(x2):<20} {pformat(x2, indent=4).splitlines()[0]}"
                    )
            self.assertEqual(t, t2)

        tree = {
            EI: [
                ModuleInterface,
                {
                    EN: [Module, Module],
                    EI: [ModuleInterface],
                },
            ],
            EN: [
                {
                    EN: [Module, Module],
                    EI: [ModuleInterface],
                    EP: [
                        {
                            EP: [Parameter],
                        }
                    ],
                },
                {
                    EN: [Module, Module],
                    EI: [ModuleInterface],
                },
                {
                    EN: [Module, Module],
                    EI: [ModuleInterface],
                },
            ],
            EP: [],
        }

        def visit_tree(t, keys=None, typ=EN):
            if not keys or typ in keys:
                yield t

            if isinstance(t, dict):
                for k, vs in t.items():
                    for v in vs:
                        yield from visit_tree(v, keys=keys, typ=k)
            else:
                assert isinstance(t, type)

        mod = moduleFromTree(tree, EN)()

        direct_children_top = get_children(mod, direct_only=True, types=Module)
        assertEqual(direct_children_top, tree[EN])

        direct_children_top_all_types = get_children(mod, direct_only=True)
        assertEqual(direct_children_top_all_types, tree[EN] + tree[EI] + tree[EP])

        all_children_top = get_children(mod, direct_only=False, include_root=True)
        assertEqual(all_children_top, list(visit_tree(tree)))

        all_children_top_typed = get_children(
            mod, direct_only=False, types=Module, include_root=True
        )
        assertEqual(all_children_top_typed, list(visit_tree(tree, [EN])))

        direct_children_middle = get_children(mod.NODEs.i0, direct_only=True)
        assertEqual(
            direct_children_middle, tree[EN][0][EN] + tree[EN][0][EI] + tree[EN][0][EP]
        )

        all_children_middle = get_children(
            mod.NODEs.i0, direct_only=False, include_root=True
        )
        assertEqual(
            all_children_middle,
            list(visit_tree(tree[EN][0])),
        )


if __name__ == "__main__":
    unittest.main()
