# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import unittest
from abc import abstractmethod
from typing import cast

from faebryk.core.core import LinkDirect, LinkParent, LinkSibling, TraitImpl


class TestTraits(unittest.TestCase):
    def test_equality(self):
        from faebryk.core.core import Trait

        class _trait1(Trait):
            pass

        class _trait1_1(_trait1):
            pass

        class _trait2(Trait):
            pass

        class impl1(_trait1.impl()):
            pass

        class impl1_1(impl1):
            pass

        class impl1_1_1(impl1_1):
            pass

        class impl1_2(impl1):
            pass

        class impl_1_1(_trait1_1.impl()):
            pass

        class impl2(_trait2.impl()):
            pass

        a = impl1()

        # different inst
        self.assertNotEqual(impl1(), impl1())
        # same inst
        self.assertEqual(a, a)
        # same class
        self.assertEqual(impl1, impl1)
        # class & parent/child class
        self.assertNotEqual(impl1_1, impl1)
        # class & parallel class
        self.assertNotEqual(impl2, impl1)

        def assertCmpTrue(one, two):
            self.assertTrue(one.cmp(two)[0])

        def assertCmpFalse(one, two):
            self.assertFalse(one.cmp(two)[0])

        # inst & class
        assertCmpTrue(impl1(), impl1())
        assertCmpTrue(impl1_1(), impl1_1())
        # inst & parent class
        assertCmpTrue(impl1_1(), impl1())
        # inst & child class
        assertCmpTrue(impl1(), impl1_1())
        # inst & parallel class
        assertCmpFalse(impl2(), impl1())
        assertCmpFalse(impl2(), impl1_1())
        # inst & double child class
        assertCmpTrue(impl1_1_1(), impl1())
        # inst & double parent class
        assertCmpTrue(impl1(), impl1_1_1())
        # inst & sister class
        assertCmpTrue(impl1_2(), impl1_1())
        # inst & nephew class
        assertCmpTrue(impl1_2(), impl1_1_1())

        # Trait inheritance
        assertCmpTrue(impl1(), impl_1_1())
        assertCmpTrue(impl_1_1(), impl1())

    def test_obj_traits(self):
        from faebryk.core.core import FaebrykLibObject, Trait

        obj = FaebrykLibObject()

        class trait1(Trait):
            @abstractmethod
            def do(self) -> int:
                raise NotImplementedError

        class trait1impl(trait1.impl()):
            def do(self) -> int:
                return 1

        class cfgtrait1(trait1impl):
            def __init__(self, cfg) -> None:
                super().__init__()
                self.cfg = cfg

            def do(self) -> int:
                return self.cfg

        class trait2(trait1):
            pass

        class impl2(trait2.impl()):
            pass

        # Test failure on getting non existent
        self.assertFalse(obj.has_trait(trait1))
        self.assertRaises(AssertionError, lambda: obj.get_trait(trait1))

        trait1_inst = trait1impl()
        cfgtrait1_inst = cfgtrait1(5)
        impl2_inst = impl2()

        # Test getting trait
        obj.add_trait(trait1_inst)
        self.assertTrue(obj.has_trait(trait1))
        self.assertEqual(trait1_inst, obj.get_trait(trait1))
        self.assertEqual(trait1_inst.do(), obj.get_trait(trait1).do())

        # Test double add
        self.assertRaises(AssertionError, lambda: obj.add_trait(trait1_inst))

        # Test replace
        obj.add_trait(cfgtrait1_inst)
        self.assertEqual(cfgtrait1_inst, obj.get_trait(trait1))
        self.assertEqual(cfgtrait1_inst.do(), obj.get_trait(trait1).do())
        obj.add_trait(trait1_inst)
        self.assertEqual(trait1_inst, obj.get_trait(trait1))

        # Test remove
        obj.del_trait(trait2)
        self.assertTrue(obj.has_trait(trait1))
        obj.del_trait(trait1)
        self.assertFalse(obj.has_trait(trait1))

        # Test get obj
        self.assertRaises(AssertionError, lambda: trait1_inst.get_obj())
        obj.add_trait(trait1_inst)
        _impl: TraitImpl = cast(TraitImpl, obj.get_trait(trait1))
        self.assertEqual(_impl.get_obj(), obj)
        obj.del_trait(trait1)
        self.assertRaises(AssertionError, lambda: trait1_inst.get_obj())

        # Test specific override
        obj.add_trait(impl2_inst)
        obj.add_trait(trait1_inst)
        self.assertEqual(impl2_inst, obj.get_trait(trait1))

        # Test child delete
        obj.del_trait(trait1)
        self.assertFalse(obj.has_trait(trait1))


class TestGraph(unittest.TestCase):
    def test_gifs(self):
        from faebryk.core.core import GraphInterface as GIF

        gif1 = GIF()
        gif2 = GIF()

        gif1.connect(gif2)

        self.assertIn(gif2, gif1.edges)
        self.assertTrue(gif1.is_connected(gif2) is not None)

        gif3 = GIF()

        class linkcls(LinkDirect):
            pass

        gif1.connect(gif3, linkcls)
        self.assertIsInstance(gif1.is_connected(gif3), linkcls)
        self.assertEqual(gif1.is_connected(gif3), gif3.is_connected(gif1))

        self.assertRaises(AssertionError, lambda: gif1.connect(gif3))
        gif1.connect(gif3, linkcls)

        self.assertEqual(gif1.G, gif2.G)

    def test_node_gifs(self):
        from faebryk.core.core import Node

        n1 = Node()

        self.assertIsInstance(n1.GIFs.self.is_connected(n1.GIFs.parent), LinkSibling)
        self.assertIsInstance(n1.GIFs.self.is_connected(n1.GIFs.children), LinkSibling)

        n2 = Node()
        n1.NODEs.n2 = n2

        self.assertIsInstance(n1.GIFs.children.is_connected(n2.GIFs.parent), LinkParent)

        print(n1.get_graph())

        p = n2.get_parent()
        self.assertIsNotNone(p)
        assert p is not None
        self.assertIs(p[0], n1)

        self.assertEqual(n1.GIFs.self.G, n2.GIFs.self.G)


if __name__ == "__main__":
    unittest.main()
