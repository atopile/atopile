import functools
import itertools
import logging
from collections import defaultdict
from typing import Any, Callable, Mapping

from atopile.model2.datamodel import Instance
from atopile.model2.instance_methods import (
    get_instance_key,
    match_components,
    match_pins,
)

from .kicad6_datamodel import (
    KicadComponent,
    KicadField,
    KicadLibpart,
    KicadLibraries,
    KicadNet,
    KicadNetlist,
    KicadNode,
    KicadPin,
    KicadSheetpath,
)

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class Builder:
    def __init__(self):
        """TODO:"""
        self.netlist = KicadNetlist()
        self.libparts: dict[tuple, KicadLibpart] = {}
        self.designator_counter: Mapping[str, Callable[[], int]] = defaultdict(functools.partial(itertools.count, firstval=1))

    def make_designator(self, component: Instance) -> str:
        """Give me a designator"""
        prefix = str(component.children.get("designator_prefix", "U"))
        index = next(self.designator_counter[prefix])
        return prefix + str(index)

    def make_libpart(self, component: Instance) -> KicadLibpart:
        """Make a KiCAD libpart object from a representative instance object."""
        raise NotImplementedError

    def get_libpart(self, components: Instance) -> KicadLibpart:
        """Get a libpart from the instance"""
        uniqueness_key = get_instance_key(components)
        if uniqueness_key not in self.libparts:
            self.libparts[uniqueness_key] = self.make_libpart(components)
        return self.libparts[uniqueness_key]

    def dispatch(self, instance: Instance) -> list:
        if match_components(instance):
            return self.visit_component(instance)
        if match_pins(instance):
            return self.visit_pin(instance)

        # default back to the generic visit method
        return self.visit(instance)

    def visit(self, instance: Instance) -> Any:
        """Visit an instance"""
        for child in instance.children.values():
            if hasattr(child, "children"):
                self.dispatch(child)

    def visit_component(self, component: Instance) -> KicadComponent:
        """Visit and create a KiCAD component"""
        libpart = self.get_libpart(component)

    def visit_pin(self, pin: Instance) -> KicadPin:
        """Visit and create a KiCAD pin"""
