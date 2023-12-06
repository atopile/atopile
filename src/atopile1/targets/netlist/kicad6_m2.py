import functools
import itertools
import logging
from collections import defaultdict
from typing import Any, Callable, Mapping, Optional

from atopile.model2.datamodel import Instance
from atopile.model2.instance_methods import (
    get_instance_key,
    match_modules,
    match_components,
    match_pins,
    match_signals,
    match_pins_and_signals
)
from atopile.model2.object_methods import lowest_common_super
from atopile.model2.instance_methods import get_instance_key, get_address, dfs
from atopile.model2.datamodel import Object
from atopile.model.utils import generate_uid_from_path
from atopile.model2.net_naming import find_net_names
from atopile.model2.loop_soup import LoopSoup

from .kicad6_datamodel import (
    KicadComponent,
    # KicadField,
    KicadLibpart,
    # KicadLibraries,
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
        self.netlist: Optional[KicadNetlist] = None
        self._libparts: dict[tuple, KicadLibpart] = {}
        self.net_soup = LoopSoup(id)
        self._nodes: dict[int, KicadNode] = {}

    def build(self, instance: Instance) -> KicadNetlist:
        """Build a netlist from an instance"""
        self.netlist = KicadNetlist()

        self.visit(instance)

        net_names = find_net_names(self.net_soup.groups())
        for code, (net_name, net_pins) in enumerate(net_names.items(), start=1):
            net = KicadNet(
                code=code,
                name=net_name,
                nodes=[
                    self._nodes[id(pin)] for pin in net_pins if id(pin) in self._nodes
                ]
            )
            self.netlist.nets.append(net)

        # attach libparts
        self.netlist.libparts = list(self._libparts.values())

        return self.netlist

    def get_libpart(self, component: Instance) -> KicadLibpart:
        """Get a libpart from the instance"""
        uniqueness_key = get_instance_key(component)
        if uniqueness_key not in self._libparts:
            self._libparts[uniqueness_key] = self.make_libpart(component)
        return self._libparts[uniqueness_key]

    def make_libpart(self, component: Instance) -> KicadLibpart:
        """Make a KiCAD libpart object from a representative instance object."""
        pins = [self.make_kicad_pin(pin) for pin in dfs(component) if match_pins(pin)]

        # def _get_origin_of_instance(instance: Instance) -> Object:
        #     return instance.origin

        # lowest_common_ancestor = lowest_common_super(map(_get_origin_of_instance, component))
        lowest_common_ancestor = "FIXME: lowest_common_ancestor"

        constructed_libpart = KicadLibpart(
            part=component.children.get("mpn", "<no mpn>"),
            description=lowest_common_ancestor,
            fields=[],
            pins=pins,

            # TODO: something better for these:
            lib="lib",
            docs="~",
            footprints=["*"],
        )
        return constructed_libpart

    def make_kicad_pin(self, pin: Instance) -> KicadPin:
        """Make a KiCAD pin object from a representative instance object."""
        return KicadPin(
            name=pin.ref[-1],
            type="stereo"
        )

    def visit(self, instance: Instance) -> None:
        """Dispatch visits to the appropriate method"""
        try:
            if match_components(instance):
                self.visit_component(instance)
            elif match_signals(instance):
                self.visit_signal(instance)
            elif match_pins(instance):
                self.visit_pin(instance, "FIXME: designator")
                log.error(f"Found a pin that wasn't part of a component: {instance}")
            else:
                # default to visiting the children
                self.visit_children(instance)

            # make all the joints for this instance
            for joint in instance.joints:
                self.net_soup.join(joint.source, joint.target)
        except Exception as ex:
            log.error(f"Error while visiting {instance.origin.address}: {ex}")
            raise ex

    def visit_children(self, instance: Instance) -> Any:
        """Visit an instance"""
        for child in instance.children.values():
            if hasattr(child, "children"):
                self.visit(child)

    def visit_component(self, component: Instance) -> None:
        """Visit and create a KiCAD component"""
        libpart = self.get_libpart(component)

        # TODO: These should probably go to the component def
        # KicadField(name=field_name, value=field_value) for field_name, field_value in component_fields.items()
        # component_fields = {}
        # for child_name, child in component.children.items():
        #     if isinstance(child, str) or isinstance(child, int):
        #         component_fields[child_name] = child
        fields  = []

        # TODO: improve this
        sheetpath = KicadSheetpath( # That's not actually what we want. Will have to fix
            names=get_address(component),
            tstamps=generate_uid_from_path(str(component.ref))
        )

        designator = component.children.get("designator")  # FIXME:
        constructed_component = KicadComponent(
            ref=designator,
            value=component.children.get("value", ""),
            footprint=component.children.get("footprint", ""),  # FIXME: shouldn't be a get
            libsource=libpart,
            tstamp=generate_uid_from_path(str(component.ref)),
            fields=fields,
            sheetpath=sheetpath,
            src_path=get_address(component),
        )
        self.netlist.components.append(constructed_component)

        # visit all the children, but dispatch the pins to the pin visitor
        for child in component.children.values():
            if not hasattr(child, "children"):
                continue

            if match_pins(child):
                self.visit_pin(child, designator)
            else:
                self.visit(child)

    def visit_pin(self, pin: Instance, component_ref: str) -> None:
        """Make a KiCAD node object from a representative instance object."""
        node = KicadNode(
            pin=pin.ref[-1],  # eg. 1
            ref=component_ref,  # eg. R1
            pintype="stereo"
        )
        self._nodes[id(pin)] = node
        self.net_soup.add(pin)

    def visit_signal(self, signal: Instance) -> None:
        """Visit a node"""
        self.net_soup.add(signal)
