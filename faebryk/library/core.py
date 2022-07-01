# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from __future__ import annotations
from faebryk.libs.exceptions import FaebrykException
import typing

import logging

logger = logging.getLogger("library")

# 1st order classes -----------------------------------------------------------
class Trait:
    def __init__(self) -> None:
        self._obj = None

    def __eq__(self, other) -> bool:
        if type(other) is type:
            return isinstance(self, other) or issubclass(other, type(self))
        else:
            return super.__eq__(self, other)

    def set_obj(self, _obj):
        self._obj = _obj

    def remove_obj(self):
        self._obj = None

    def get_obj(self):
        assert self._obj is not None, "trait is not linked to object"
        return self._obj


class FaebrykLibObject:
    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        # TODO maybe dict[class => [obj]
        self.traits = []
        return self

    def __init__(self) -> None:
        pass

    def add_trait(self, trait: Trait) -> None:
        assert trait._obj is None, "trait already in use"
        trait.set_obj(self)

        # Add trait if new
        # Be careful with parent/child classes of a trait
        # They count as one, but not sister/nephew classes
        if type(trait) not in self.traits:
            self.traits.append(trait)
            return

        # Replace old trait
        old_idx = self.traits.index(type(trait))
        self.traits[old_idx].remove_obj()
        self.traits[old_idx] = trait

    def del_trait(self, trait):
        if self.has_trait(trait):
            trait_idx = self.traits.index(trait)
            self.traits[trait_idx].remove_obj()
            del self.traits[trait_idx]

    def has_trait(self, trait) -> bool:
        # Make use of eq overload
        return trait in self.traits

    def get_trait(self, trait):
        assert trait in self.traits, "{} not in {}[{}]".format(trait, type(self), self)
        return self.traits[self.traits.index(trait)]


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

# FaebrykLibObjects -----------------------------------------------------------
class Footprint(FaebrykLibObject):
    def __init__(self) -> None:
        super().__init__()

    def add_trait(self, trait: FootprintTrait):
        return super().add_trait(trait)


class Interface(FaebrykLibObject):
    def __new__(cls, *args, component=None, **kwargs):
        self = super().__new__(cls)
        self.connections = []
        self.component = None
        if component is not None:
            self.set_component(component)
        return self

    def __init__(self) -> None:
        super().__init__()

        from faebryk.library.util import NotifiesOnPropertyChange

        class _Interfaces(NotifiesOnPropertyChange):
            def __init__(_self) -> None:
                super().__init__(
                    # TODO maybe throw warnig?
                    lambda k, v: _self.on_change(k, v)
                    if issubclass(type(v), Interface)
                    else _self.on_change_s(k, v)
                    if type(v) is list
                    and all([issubclass(type(x), Interface) for x in v])
                    else None
                )
                _self._unnamed = ()

            def on_change(_self, name, intf: Interface):
                if self.component is None:
                    return
                intf.set_component(self.component)

            def on_change_s(_self, name, intfs: list[Interface]):
                if self.component is None:
                    return
                for intf in intfs:
                    intf.set_component(self.component)

            def add(_self, intf: Interface):
                _self._unnamed += (intf,)
                if self.component is None:
                    return
                intf.set_component(self.component)

            def add_all(_self, intfs: typing.Iterable[Interface]):
                for intf in intfs:
                    _self.add(intf)

            def get_all(_self) -> list[Interface]:
                return \
                    [
                        intf
                        for intf in vars(_self).values()
                        if issubclass(type(intf), Interface)
                    ] \
                    + [
                        intf
                        for name, intfs in vars(_self).items()
                        if type(intfs) in [tuple, list]
                        for intf in intfs
                    ]

        self.IFs = _Interfaces()

    def add_trait(self, trait: InterfaceTrait) -> None:
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

    def set_component(self, component):
        from faebryk.library.traits.interface import is_part_of_component

        self.component = component

        class _(is_part_of_component):
            @staticmethod
            def get_component() -> Component:
                return self.component

        if component is None:
            self.del_trait(is_part_of_component)
        else:
            self.add_trait(_())

        # TODO I think its nicer to have a parent relationship to the other interface
        #   instead of carrying the component through all compositions
        for i in self.IFs.get_all():
            i.set_component(component)


class Component(FaebrykLibObject):
    def __init__(self) -> None:
        super().__init__()

        from faebryk.library.util import NotifiesOnPropertyChange

        class _Interfaces(NotifiesOnPropertyChange):
            def __init__(_self) -> None:
                super().__init__(
                    # TODO maybe throw warnig?
                    lambda k, v: _self.on_change(k, v)
                    if issubclass(type(v), Interface)
                    else _self.on_change_s(k, v)
                    if type(v) is list
                    and all([issubclass(type(x), Interface) for x in v])
                    else None
                )
                _self._unnamed = ()
                # helper array for next method
                _self._unpopped = []

            def on_change(_self, name, intf: Interface):
                intf.set_component(self)

            def on_change_s(_self, name, intfs: list[Interface]):
                for intf in intfs:
                    intf.set_component(self)

            def add(_self, intf: Interface):
                _self._unnamed += (intf,)
                intf.set_component(self)
                _self._unpopped.append(intf)

            def add_all(_self, intfs: typing.Iterable[Interface]):
                for intf in intfs:
                    _self.add(intf)

            def get_all(_self) -> list[Interface]:
                return \
                    [
                        intf
                        for intf in vars(_self).values()
                        if issubclass(type(intf), Interface)
                    ] \
                    + [
                        intf
                        for name, intfs in vars(_self).items()
                        if type(intfs) in [tuple, list] and name != "_unpopped"
                        for intf in intfs
                    ]

            """ returns iterator on unnamed interfaces """

            def next(_self):
                assert len(_self._unpopped) > 0, "No more interfaces to pop"
                return _self._unpopped.pop(0)


        class _Components(NotifiesOnPropertyChange):
            def __init__(_self) -> None:
                super().__init__(
                    # TODO maybe throw warnig?
                    lambda k, v: _self.on_change(k, v)
                    if issubclass(type(v), Component)
                    else _self.on_change_s(k, v)
                    if type(v) is list
                    and all([issubclass(type(x), Component) for x in v])
                    else None
                )
                _self._unnamed = ()

            def on_change(_self, name, cmp: Component):
                pass

            def on_change_s(_self, name, cmps: list[Component]):
                pass

            def add(_self, cmp: Component):
                _self._unnamed += (cmp,)

            def add_all(_self, cmps: typing.Iterable[Component]):
                for cmp in cmps:
                    _self.add(cmp)

            def get_all(_self) -> list[Component]:
                return \
                    [
                        cmp
                        for cmp in vars(_self).values()
                        if issubclass(type(cmp), Component)
                    ] \
                    + [
                        cmp
                        for name, cmps in vars(_self).items()
                        if type(cmps) in [tuple, list]
                        for cmp in cmps
                    ]

        self.IFs = _Interfaces()
        self.CMPs = _Components()

    def add_trait(self, trait: ComponentTrait) -> None:
        return super().add_trait(trait)

    def from_comp(other: Component) -> Component:
        # TODO traits?
        return Component()


class Link(FaebrykLibObject):
    def __init__(self) -> None:
        super().__init__()

    def add_trait(self, trait: LinkTrait) -> None:
        return super().add_trait(trait)


class Parameter(FaebrykLibObject):
    def __init__(self) -> None:
        super().__init__()

    def add_trait(self, trait: ParameterTrait) -> None:
        return super().add_trait(trait)


# -----------------------------------------------------------------------------
