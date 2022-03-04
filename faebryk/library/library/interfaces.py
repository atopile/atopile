# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

logger = logging.getLogger("library")

from faebryk.library.core import Interface
from faebryk.library.traits import *
from faebryk.library.util import get_components_of_interfaces
from faebryk.library.traits.interface import can_list_interfaces, contructable_from_interface_list

class Electrical(Interface):
    def __init__(self) -> None:
        super().__init__()

        class _can_list_interfaces(can_list_interfaces):
            @staticmethod
            def get_interfaces() -> list[Electrical]:
                return [self]

        class _contructable_from_interface_list(contructable_from_interface_list):
            @staticmethod
            def from_interfaces(interfaces: list[Electrical]) -> Electrical:
                return next(interfaces)

        self.add_trait(_can_list_interfaces())
        self.add_trait(_contructable_from_interface_list())

class Power(Interface):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.hv = Electrical()
        self.lv = Electrical()

        self.set_component(kwargs.get("component"))

        class _can_list_interfaces(can_list_interfaces):
            @staticmethod
            def get_interfaces() -> list[Electrical]:
                return [self.hv, self.lv]

        class _contructable_from_interface_list(contructable_from_interface_list):
            @staticmethod
            def from_interfaces(interfaces: list[Electrical]) -> Power:
                p = Power()
                p.hv = next(interfaces)
                p.lv = next(interfaces)

                comps = get_components_of_interfaces(p.get_trait(can_list_interfaces).get_interfaces())
                assert (len(comps) < 2 or comps[0] == comps[1])
                if len(comps) > 0:
                    p.set_component(comps[0])

                return p

        self.add_trait(_can_list_interfaces())
        self.add_trait(_contructable_from_interface_list())

        #TODO finish the trait stuff
#        self.add_trait(is_composed([self.hv, self.lv]))

    def connect(self, other: Interface):
        #TODO feels a bit weird
        # maybe we need to look at how aggregate interfaces connect
        assert(type(other) is Power), "can't connect to non power"
        for s,d in zip(
                self.get_trait(can_list_interfaces).get_interfaces(),
                other.get_trait(can_list_interfaces).get_interfaces(),
            ):
            s.connect(d)
