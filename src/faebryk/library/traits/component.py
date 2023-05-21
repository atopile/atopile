# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

logger = logging.getLogger("library")

from faebryk.library.core import Component, ComponentTrait, Footprint


class has_type_description(ComponentTrait):
    def __init__(self):
        super().__init__(pretty_child_fns=[self.get_type_description])

    def get_type_description(self) -> str:
        raise NotImplementedError(type(self))


class contructable_from_component(ComponentTrait):
    def from_comp(self, comp: Component):
        raise NotImplementedError()


class has_footprint(ComponentTrait):
    def __init__(self):
        super().__init__(pretty_child_fns=[self.get_footprint])

    def get_footprint(self) -> Footprint:
        raise NotImplementedError()


class has_footprint_pinmap(ComponentTrait):
    def __init__(self):
        super().__init__(pretty_child_fns=[self.get_pin_map])

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

    def __str__(self):
        s = super().__str__()
        try:
            return f"{s}({self.get_in()} -> {self.get_out()})"
        except NotImplementedError:
            return s

    def __pretty__(self, p, cycle):
        s = super().__str__()
        try:
            with p.group(4, f"{s}(", ")"):
                p.breakable(sep="")
                p.pretty(self.get_in())
                p.breakable()
                p.text("->")
                p.breakable()
                p.pretty(self.get_out())
        except NotImplementedError:
            p.pretty(s)


class has_overriden_name(ComponentTrait):
    def __init__(self):
        super().__init__(pretty_child_fns=[self.get_name])

    def get_name(self):
        raise NotImplementedError


class has_descriptive_properties(ComponentTrait):
    def get_properties(self) -> dict[str, str]:
        raise NotImplementedError()

    def add_properties(self, propertis: dict[str, str]):
        raise NotImplementedError()
