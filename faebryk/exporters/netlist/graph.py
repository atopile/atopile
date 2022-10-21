# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from itertools import groupby
from typing import List

from typing_extensions import Self

from faebryk.library.traits.component import has_overriden_name

logger = logging.getLogger("netlist")


def make_t1_netlist_from_graph(comps):
    t1_netlist = [comp.get_comp() for comp in comps]

    return t1_netlist


# This method is a temporary solution to convert high-level faebryk relations
#   as a netlist graph
# In the future we will generate a high-level graph which the netlist can be
#   built from directly
def make_graph_from_components(components):
    from faebryk.library.core import Component
    from faebryk.library.kicad import has_kicad_footprint
    from faebryk.library.traits.component import (
        has_footprint,
        has_footprint_pinmap,
        has_type_description,
    )
    from faebryk.library.traits.interface import is_part_of_component
    from faebryk.library.util import get_all_components
    from faebryk.libs.exceptions import FaebrykException

    class wrapper:
        def __init__(self, component: Component, wrapped_list: List[Self]) -> None:
            self.component = component
            self._setup_non_rec()
            self.wrapped_list: List[Self]

        def _setup_non_rec(self):
            c = self.component
            self.real = c.has_trait(has_footprint) and c.has_trait(has_footprint_pinmap)
            self.properties = {}
            self.neighbors = {}
            if self.real:
                self.value = c.get_trait(has_type_description).get_type_description()
                self.properties["footprint"] = (
                    c.get_trait(has_footprint)
                    .get_footprint()
                    .get_trait(has_kicad_footprint)
                    .get_kicad_footprint()
                )
            if self.component.has_trait(has_overriden_name):
                self.name = self.component.get_trait(has_overriden_name).get_name()
            else:
                self.name = "{}[{}:{}]".format(
                    ".".join(
                        [pname for parent, pname in self.component.get_hierarchy()]
                    )
                    if self.component.parent is not None
                    else "",
                    type(self.component).__name__,
                    self.value if self.real else "virt",
                )
            self._comp = {}
            self._update_comp()

        def _update_comp(self):
            self._comp.update(
                {
                    "name": self.name,
                    "real": self.real,
                    "properties": self.properties,
                    "neighbors": self.neighbors,
                }
            )
            if self.real:
                self._comp["value"] = self.value

        def _get_comp(self):
            return self._comp

        def get_comp(self):
            # only executed once
            neighbors = {}
            for pin, interface in (
                self.component.get_trait(has_footprint_pinmap).get_pin_map().items()
            ):
                neighbors[pin] = []
                for target_interface in interface.connections:
                    if target_interface.has_trait(is_part_of_component):
                        target_component = target_interface.get_trait(
                            is_part_of_component
                        ).get_component()
                        target_pinmap = target_component.get_trait(
                            has_footprint_pinmap
                        ).get_pin_map()
                        try:
                            target_pin = list(target_pinmap.items())[
                                list(target_pinmap.values()).index(target_interface)
                            ][0]
                        except ValueError:
                            raise FaebrykException(
                                "Pinmap of component does not contain referenced pin"
                            )
                        try:
                            target_wrapped = [
                                i
                                for i in wrapped_list
                                if i.component == target_component
                            ][0]
                        except IndexError:
                            raise FaebrykException(
                                "Discovered associated component not in component list:",
                                target_component,
                            )

                        neighbors[pin].append(
                            {"vertex": target_wrapped._get_comp(), "pin": target_pin}
                        )
                    else:
                        logger.warn(
                            "{comp} pin {pin} is connected to interface without component".format(
                                comp=self.name,
                                # intf=target_interface,
                                pin=pin,
                            )
                        )

            self.neighbors = neighbors
            self._update_comp()

            return self._get_comp()

    all_components = list(components)
    # add subcomponents to graph
    for i in map(get_all_components, components):
        all_components.extend(i)

    wrapped_list = []
    wrapped_list += [wrapper(comp, wrapped_list) for comp in all_components]

    names = groupby(wrapped_list, key=lambda w: w.name)
    for name, _objs in names:
        objs = list(_objs)
        if len(objs) <= 1:
            continue
        for i, obj in enumerate(objs):
            # TODO deterministic
            # maybe prefix name of parent instead
            obj.name += f"@{i}"

    logger.debug(
        "Making graph from components:\n\t{}".format(
            "\n\t".join(map(str, all_components))
        )
    )

    return wrapped_list
