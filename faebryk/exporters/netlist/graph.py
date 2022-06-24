# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

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
    from faebryk.libs.exceptions import FaebrykException
    from faebryk.library.traits.component import (
        has_footprint,
        has_type_description,
        has_footprint_pinmap,
    )
    from faebryk.library.traits.interface import is_part_of_component
    from faebryk.library.kicad import has_kicad_footprint
    from faebryk.library.kicad import has_kicad_ref

    class wrapper:
        def __init__(self, component: Component) -> None:
            self.component = component
            self._setup_non_rec()

        def _setup_non_rec(self):
            import random

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
            if c.has_trait(has_kicad_ref):
                self.name = c.get_trait(has_kicad_ref).get_ref()
            else:
                self.name = "COMP[{}:{}]@{:08X}".format(
                    type(self.component).__name__,
                    self.value if self.real else "virt",
                    int(random.random() * 2**32),
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

    wrapped_list = list(map(wrapper, components))
    for i in wrapped_list:
        i.wrapped_list = wrapped_list

    logger.debug(
        "Making graph from components:\n\t{}".format("\n\t".join(map(str, components)))
    )

    return wrapped_list
