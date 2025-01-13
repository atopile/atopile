from abc import abstractmethod
from typing import cast

import pytest

from faebryk.core.node import Node, NodeAlreadyBound
from faebryk.core.trait import (
    Trait,
    TraitImpl,
    TraitImplementationConfusedWithTrait,
    TraitNotFound,
    TraitUnbound,
)


def test_trait_equality():
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

    # Test instance and class equality
    assert impl1() != impl1()  # different instances
    assert a == a  # same instance
    assert impl1 == impl1  # same class
    assert impl1_1 != impl1  # class & parent/child class
    assert impl2 != impl1  # class & parallel class

    # Test trait implementation comparisons
    assert impl1().cmp(impl1())[0]  # inst & class
    assert impl1_1().cmp(impl1_1())[0]  # inst & class
    assert impl1_1().cmp(impl1())[0]  # inst & parent class
    assert impl1().cmp(impl1_1())[0]  # inst & child class
    assert not impl2().cmp(impl1())[0]  # inst & parallel class
    assert not impl2().cmp(impl1_1())[0]  # inst & parallel class
    assert impl1_1_1().cmp(impl1())[0]  # inst & double child class
    assert impl1().cmp(impl1_1_1())[0]  # inst & double parent class
    assert impl1_2().cmp(impl1_1())[0]  # inst & sister class
    assert impl1_2().cmp(impl1_1_1())[0]  # inst & nephew class

    # Test trait inheritance
    assert impl1().cmp(impl_1_1())[0]
    assert impl_1_1().cmp(impl1())[0]


def test_trait_basic_operations():
    obj = Node()

    class trait1(Trait):
        @abstractmethod
        def do(self) -> int:
            raise NotImplementedError

    class trait1impl(trait1.impl()):
        def do(self) -> int:
            return 1

    # Test failure on getting non-existent trait
    assert not obj.has_trait(trait1)
    with pytest.raises(TraitNotFound):
        obj.get_trait(trait1)

    # Test adding and getting trait
    trait1_inst = trait1impl()
    obj.add(trait1_inst)
    assert obj.has_trait(trait1)
    assert trait1_inst == obj.get_trait(trait1)
    assert trait1_inst.do() == obj.get_trait(trait1).do()

    # Test double add
    with pytest.raises(NodeAlreadyBound):
        obj.add(trait1_inst)

    # Test trait removal
    obj.del_trait(trait1)
    assert not obj.has_trait(trait1)


def test_trait_replacement():
    obj = Node()

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

    trait1_inst = trait1impl()
    cfgtrait1_inst = cfgtrait1(5)

    # Test trait replacement
    obj.add(trait1_inst)
    obj.add(cfgtrait1_inst)
    assert cfgtrait1_inst == obj.get_trait(trait1)
    assert cfgtrait1_inst.do() == obj.get_trait(trait1).do()
    obj.add(trait1_inst)
    assert trait1_inst == obj.get_trait(trait1)


def test_trait_object_binding():
    obj = Node()

    class trait1(Trait):
        pass

    class trait1impl(trait1.impl()):
        pass

    trait1_inst = trait1impl()

    # Test trait object binding
    with pytest.raises(TraitUnbound):
        trait1_inst.obj
    obj.add(trait1_inst)
    _impl: TraitImpl = cast(TraitImpl, obj.get_trait(trait1))
    assert _impl.obj == obj
    obj.del_trait(trait1)
    with pytest.raises(TraitUnbound):
        trait1_inst.obj


def test_trait_inheritance_and_override():
    obj = Node()

    class trait1(Trait):
        pass

    class trait2(trait1):
        pass

    class impl1(trait1.impl()):
        pass

    class impl2(trait2.impl()):
        pass

    impl1_inst = impl1()
    impl2_inst = impl2()

    # Test specific override
    obj.add(impl2_inst)
    obj.add(impl1_inst)
    assert impl2_inst == obj.get_trait(trait1)

    # Test child delete
    obj.del_trait(trait1)
    assert not obj.has_trait(trait1)


def test_trait_impl_confusion():
    obj = Node()

    class trait1(Trait):
        pass

    class trait1impl(trait1.impl()):
        pass

    t1 = obj.add(trait1impl())
    with pytest.raises(TraitImplementationConfusedWithTrait):
        obj.get_trait(trait1impl)

    assert obj.get_trait(trait1) == t1


def test_trait_impl_exception():
    obj = Node()

    class trait1impl(Trait.decless()):
        pass

    # ensure it's a class attribute
    assert trait1impl.__trait__ is trait1impl().__trait__

    t1 = obj.add(trait1impl())
    assert obj.get_trait(trait1impl) is t1


def test_trait_decless_basic():
    class T1(Trait.decless()):
        def __init__(self, data: str) -> None:
            super().__init__()
            self.data = data

    n = Node()
    n.add(T1("test"))

    assert n.has_trait(T1)
    assert n.get_trait(T1).data == "test"


def test_trait_decless_inherit():
    class T1(Trait.decless()):
        def __init__(self, data: str) -> None:
            super().__init__()
            self.data = data

    class T2(T1):
        def __init__(self, data: str, more_data: str) -> None:
            super().__init__(data)
            self.more_data = more_data

    n = Node()
    n.add(T2("test", "more"))

    assert n.has_trait(T1)
    assert n.get_trait(T1).data == "test"
    assert n.has_trait(T2)
    assert n.get_trait(T2).more_data == "more"


def test_trait_decless_inherit_2():
    class T1(Trait):
        pass

    class T2(T1.decless()):
        def __init__(self, data: str) -> None:
            super().__init__()
            self.data = data

    n = Node()
    n.add(T2("test"))

    assert n.has_trait(T1)
    assert n.has_trait(T2)
    assert n.get_trait(T2).data == "test"
