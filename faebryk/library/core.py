# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from __future__ import annotations

import logging
from typing import List, Tuple, Type, TypeVar

from faebryk.libs.util import Holder

logger = logging.getLogger("library")

# 1st order classes -----------------------------------------------------------
class Trait:
    @classmethod
    def impl(cls: Type[Trait]):
        class _Impl(TraitImpl, cls):
            pass

        return _Impl


class TraitImpl:
    trait: Type[Trait]

    def __init__(self) -> None:
        self._obj = None

        found = False
        bases = type(self).__bases__
        while not found:
            for base in bases:
                if not issubclass(base, TraitImpl) and issubclass(base, Trait):
                    self.trait = base
                    found = True
                    break
            bases = [
                new_base
                for base in bases
                if issubclass(base, TraitImpl)
                for new_base in base.__bases__
            ]
            assert len(bases) > 0

        assert type(self.trait) is type
        assert issubclass(self.trait, Trait)
        assert self.trait is not TraitImpl

    def set_obj(self, _obj):
        self._obj = _obj

    def remove_obj(self):
        self._obj = None

    def get_obj(self):
        assert self._obj is not None, "trait is not linked to object"
        return self._obj

    def cmp(self, other: TraitImpl) -> tuple[bool, TraitImpl]:
        assert type(other), TraitImpl

        # If other same or more specific
        if other.implements(self.trait):
            return True, other

        # If we are more specific
        if self.implements(other.trait):
            return True, self

        return False, self

    def implements(self, trait: type):
        assert issubclass(trait, Trait)

        return issubclass(self.trait, trait)

    # override this to implement a dynamic trait
    def is_implemented(self):
        return True


class FaebrykLibObject:
    traits: List[TraitImpl]

    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        # TODO maybe dict[class => [obj]
        self.traits = []
        return self

    def __init__(self) -> None:
        if not hasattr(self, "parent"):
            self.parent = None

    def add_trait(self, trait: TraitImpl) -> None:
        assert isinstance(trait, TraitImpl), ("not a traitimpl:", trait)
        assert isinstance(trait, Trait)
        assert trait._obj is None, "trait already in use"
        trait.set_obj(self)

        # Override existing trait if more specific or same
        # TODO deal with dynamic traits
        for i, t in enumerate(self.traits):
            hit, replace = t.cmp(trait)
            if hit:
                if replace == trait:
                    t.remove_obj()
                    self.traits[i] = replace
                return

        # No hit: Add new trait
        self.traits.append(trait)

    def _find(self, trait, only_implemented: bool):
        return list(
            filter(
                lambda tup: tup[1].implements(trait)
                and (tup[1].is_implemented() or not only_implemented),
                enumerate(self.traits),
            )
        )

    def del_trait(self, trait):
        candidates = self._find(trait, only_implemented=False)
        assert len(candidates) <= 1
        if len(candidates) == 0:
            return
        assert len(candidates) == 1, "{} not in {}[{}]".format(trait, type(self), self)
        i, impl = candidates[0]
        assert self.traits[i] == impl
        impl.remove_obj()
        del self.traits[i]

    def has_trait(self, trait) -> bool:
        return len(self._find(trait, only_implemented=True)) > 0

    T = TypeVar("T", bound=Trait)

    def get_trait(self, trait: Type[T]) -> T:
        candidates = self._find(trait, only_implemented=True)
        assert len(candidates) <= 1
        assert len(candidates) == 1, "{} not in {}[{}]".format(trait, type(self), self)

        out = candidates[0][1]
        assert isinstance(out, trait)
        return out

    def set_parent(self, parent: FaebrykLibObject, name: str) -> None:
        self.parent = (parent, name)

    def get_hierarchy(self) -> List[Tuple[FaebrykLibObject, str]]:
        if self.parent is None:
            return []
        return self.parent[0].get_hierarchy() + [self.parent]


# -----------------------------------------------------------------------------

# Traits ----------------------------------------------------------------------
class FootprintTrait(Trait):
    pass


class InterfaceTrait(Trait):
    pass


class ComponentTrait(Trait):
    pass


class LinkTrait(Trait):
    pass


class ParameterTrait(Trait):
    pass


# -----------------------------------------------------------------------------

from faebryk.libs.util import _wrapper

T = TypeVar("T")
P = TypeVar("P")


def ParentContainer(_type: Type[T], _ptype: Type[P]) -> Type[_wrapper[T, P]]:
    assert issubclass(_ptype, FaebrykLibObject)
    assert issubclass(_type, FaebrykLibObject)

    class _(Holder(_type, _ptype)):
        def handle_add(self, name: str, obj: T) -> None:
            assert isinstance(obj, FaebrykLibObject)
            parent: P = self.get_parent()
            obj.set_parent(parent, name)
            return super().handle_add(name, obj)

    return _


# FaebrykLibObjects -----------------------------------------------------------
class Footprint(FaebrykLibObject):
    def __init__(self) -> None:
        super().__init__()

    def add_trait(self, trait: TraitImpl):
        assert isinstance(trait, FootprintTrait)
        return super().add_trait(trait)


class Interface(FaebrykLibObject):
    connections: List[Interface]

    @classmethod
    def InterfacesCls(cls):
        return ParentContainer(Interface, Interface)

    def __new__(cls):
        self = super().__new__(cls)
        self.connections = []

        from faebryk.library.traits.interface import is_part_of_component

        class _(is_part_of_component.impl()):
            @staticmethod
            def _get_component() -> Component | None:
                if self.parent is None:
                    return None
                parent = self.parent[0]
                if isinstance(parent, Component):
                    return parent
                assert isinstance(parent, Interface)
                return parent.get_trait(is_part_of_component).get_component()

            @staticmethod
            def get_component() -> Component:
                comp = _._get_component()
                assert comp is not None
                return comp

            def is_implemented(self):
                if _._get_component() is None:
                    return False

                return super().is_implemented()

        self.add_trait(_())

        return self

    def __init__(self) -> None:
        super().__init__()

        self.IFs = Interface.InterfacesCls()(self)

    def add_trait(self, trait: TraitImpl) -> None:
        assert isinstance(trait, InterfaceTrait)
        return super().add_trait(trait)

    def connect(self, other: Interface) -> Interface:
        assert type(other) is type(self), "{} is not {}".format(type(other), type(self))
        self.connections.append(other)
        other.connections.append(self)

        return self

    def connect_all(self, others: list[Interface]) -> Interface:
        for i in others:
            self.connect(i)

        return self

    def connect_via(self, bridge: Component, target: Interface):
        from faebryk.library.traits.component import can_bridge

        bridge.get_trait(can_bridge).bridge(self, target)

    def connect_via_chain(self, bridges: list[Interface], target: Interface):
        from faebryk.library.traits.component import can_bridge

        end = self
        for bridge in bridges:
            end.connect(bridge.get_trait(can_bridge).get_in())
            end = bridge.get_trait(can_bridge).get_out()
        end.connect(target)


class Component(FaebrykLibObject):
    @classmethod
    def InterfacesCls(cls):
        return ParentContainer(Interface, Component)

    @classmethod
    def ComponentsCls(cls):
        return ParentContainer(Component, Component)

    def __init__(self) -> None:
        super().__init__()

        if not hasattr(self, "IFs"):
            self.IFs = Component.InterfacesCls()(self)

        if not hasattr(self, "CMPs"):
            self.CMPs = Component.ComponentsCls()(self)

    def add_trait(self, trait: TraitImpl) -> None:
        assert isinstance(trait, ComponentTrait)
        return super().add_trait(trait)

    @staticmethod
    def from_comp(other: Component) -> Component:
        # TODO traits?
        return Component()


class Link(FaebrykLibObject):
    def __init__(self) -> None:
        super().__init__()

    def add_trait(self, trait: TraitImpl) -> None:
        assert isinstance(trait, LinkTrait)
        return super().add_trait(trait)


class Parameter(FaebrykLibObject):
    def __init__(self) -> None:
        super().__init__()

    def add_trait(self, trait: TraitImpl) -> None:
        assert isinstance(trait, ParameterTrait)
        return super().add_trait(trait)


# -----------------------------------------------------------------------------
