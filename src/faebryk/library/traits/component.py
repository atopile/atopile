# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

logger = logging.getLogger("library")

from faebryk.library.core import Component, ComponentTrait, Footprint


class has_type_description(ComponentTrait):
    def get_type_description(self) -> str:
        raise NotImplementedError(type(self))


class contructable_from_component(ComponentTrait):
    def from_comp(self, comp: Component):
        raise NotImplementedError()


class has_footprint(ComponentTrait):
    def get_footprint(self) -> Footprint:
        raise NotImplementedError()


class has_footprint_pinmap(ComponentTrait):
    def get_pin_map(self):
        raise NotImplementedError()


class can_bridge(ComponentTrait):
    def bridge(self, _in, out):
        _in.connect(self.get_in())
        out.connect(self.get_out())

    def get_in(self):
        raise NotImplementedError(type(self))

    def get_out(self):
        raise NotImplementedError(type(self))


class has_overriden_name(ComponentTrait):
    def get_name(self):
        raise NotImplementedError
