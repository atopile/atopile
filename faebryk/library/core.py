# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from __future__ import annotations
from faebryk.libs.exceptions import FaebrykException
import typing

import logging
logger = logging.getLogger("library")

# 1st order classes -----------------------------------------------------------
class Trait:
    def __eq__(self, other: Trait) -> bool:
        return isinstance(self, other)

class FaebrykLibObject:
    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        #TODO maybe dict[class => [obj]
        self.traits = []
        return self

    def __init__(self) -> None:
        pass

    #TODO trait should always get ref to object
    def add_trait(self, trait : Trait) -> None:
        if type(trait) not in self.traits:
            self.traits.append(trait)
            return

        self.traits[self.traits.index(type(trait))] = trait

    def del_trait(self, trait):
        if self.has_trait(trait):
            del self.traits[trait]

    def has_trait(self, trait) -> bool:
        #return any(lambda t: type(t) is trait, self.traits)
        return trait in self.traits

    def get_trait(self, trait):
        assert (trait in self.traits), "{} not in {}[{}]".format(trait, type(self), self)
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
        
    def add_trait(self, trait : FootprintTrait):
        return super().add_trait(trait)

class Interface(FaebrykLibObject):
    def __new__(cls, *args, component=None, **kwargs):
        self = super().__new__(cls)
        self.connections = []
        if component is not None:
            self.set_component(component)
        return self

    def __init__(self) -> None:
        super().__init__()

    def add_trait(self, trait: InterfaceTrait) -> None:
        return super().add_trait(trait)

    def connect(self, other: Interface):
        assert (type(other) is type(self)), "{} is not {}".format(type(other), type(self))
        self.connections.append(other)

    def set_component(self, component):
        from faebryk.library.traits.interface import is_part_of_component, can_list_interfaces

        self.component = component

        class _(is_part_of_component):
            @staticmethod
            def get_component() -> Component:
                return self.component

        self.add_trait(_())

        #TODO I think its nicer to have a parent relationship to the other interface
        #   instead of carrying the component through all compositions
        if self.has_trait(can_list_interfaces):
            for i in self.get_trait(can_list_interfaces).get_interfaces():
                if i == self:
                    continue
                i.set_component(component)

class Component(FaebrykLibObject):
    def __init__(self) -> None:
        super().__init__()

    def add_trait(self, trait: ComponentTrait) -> None:
        return super().add_trait(trait)

    def from_comp(other: Component) -> Component:
        #TODO traits?
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
