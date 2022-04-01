# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

logger = logging.getLogger("library")

from typing import Iterable
from faebryk.library.core import Component, Interface, InterfaceTrait

# class is_composed(InterfaceTrait):
#    def get_components(self) -> list(Interface):
#        raise NotImplemented


class can_list_interfaces(InterfaceTrait):
    def get_interfaces(self) -> list[Interface]:
        raise NotImplementedError()


class contructable_from_interface_list(InterfaceTrait):
    def from_interfaces(self, interfaces: Iterable[Interface]):
        raise NotImplementedError()


class is_part_of_component(InterfaceTrait):
    def get_component(self) -> Component:
        raise NotImplementedError
