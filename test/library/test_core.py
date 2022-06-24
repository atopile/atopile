# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod
from numbers import Integral
import os


if __name__ == "__main__":
    import os
    import sys

    root = os.path.join(os.path.dirname(__file__), "../../../..")
    sys.path.append(root)

import unittest


class TestTraits(unittest.TestCase):
    def test_equality(self):
        from faebryk.library.core import Trait

        class trait1(Trait):
            def do(self) -> Integral:
                return 1

        class trait1_1(trait1):
            def do(self) -> Integral:
                return 11

        class trait1_1_1(trait1_1):
            def do(self) -> Integral:
                return 111

        class trait1_2(trait1):
            def do(self) -> Integral:
                return 12

        class trait2(Trait):
            def do(self) -> Integral:
                return 2

        a = trait1()

        def assertEqualSym(one, two):
            self.assertEqual(one, two)
            self.assertEqual(two, one)

        def assertNotEqualSym(one, two):
            self.assertNotEqual(one, two)
            self.assertNotEqual(two, one)

        # different inst
        assertNotEqualSym(trait1(), trait1())
        # same inst
        assertEqualSym(a, a)
        # same class
        assertEqualSym(trait1, trait1)
        # class & parent/child class
        assertNotEqualSym(trait1_1, trait1)
        # class & parallel class
        assertNotEqualSym(trait2, trait1)

        # inst & class
        assertEqualSym(trait1(), trait1)
        assertEqualSym(trait1_1(), trait1_1)
        # inst & parent class
        assertEqualSym(trait1_1(), trait1)
        # inst & child class
        assertEqualSym(trait1(), trait1_1)
        # inst & parallel class
        assertNotEqualSym(trait2(), trait1)
        assertNotEqualSym(trait2(), trait1_1)
        # inst & double child class
        assertEqualSym(trait1_1_1(), trait1)
        # inst & double parent class
        assertEqualSym(trait1(), trait1_1_1)
        # inst & sister class
        assertEqualSym(trait1_2(), trait1_1)
        # inst & nephew class
        assertEqualSym(trait1_2(), trait1_1_1)

    def test_obj_traits(self):
        from faebryk.library.core import FaebrykLibObject, Trait

        obj = FaebrykLibObject()

        class trait1(Trait):
            @abstractmethod
            def do(self) -> Integral:
                raise NotImplementedError

        class trait1impl(trait1):
            def do(self) -> Integral:
                return 1

        class cfgtrait1(trait1impl):
            def __init__(self, cfg) -> None:
                super().__init__()
                self.cfg = cfg

            def do(self) -> Integral:
                return self.cfg

        # Test failure on getting non existent
        self.assertFalse(obj.has_trait(trait1))
        self.assertRaises(AssertionError, lambda: obj.get_trait(trait1))

        trait1_inst = trait1impl()
        cfgtrait1_inst = cfgtrait1(5)

        # Test getting trait
        obj.add_trait(trait1_inst)
        self.assertTrue(obj.has_trait(trait1))
        self.assertEquals(trait1_inst, obj.get_trait(trait1))
        self.assertEquals(trait1_inst.do(), obj.get_trait(trait1).do())

        # Test double add
        self.assertRaises(AssertionError, lambda: obj.add_trait(trait1_inst))

        # Test replace
        obj.add_trait(cfgtrait1_inst)
        self.assertEquals(cfgtrait1_inst, obj.get_trait(trait1))
        self.assertEquals(cfgtrait1_inst.do(), obj.get_trait(trait1).do())
        obj.add_trait(trait1_inst)
        self.assertEquals(trait1_inst, obj.get_trait(trait1))

        # Test remove
        obj.del_trait(trait1)
        self.assertFalse(obj.has_trait(trait1))

        # Test get obj
        self.assertRaises(AssertionError, lambda: trait1_inst.get_obj())
        obj.add_trait(trait1_inst)
        self.assertEquals(obj.get_trait(trait1).get_obj(), obj)
        obj.del_trait(trait1)
        self.assertRaises(AssertionError, lambda: trait1_inst.get_obj())


if __name__ == "__main__":
    unittest.main()
