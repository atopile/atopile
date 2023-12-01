import functools
import itertools
import logging
from collections import defaultdict
from typing import Any, Callable, Mapping

from atopile.model2.datamodel import Instance
from atopile.model2.instance_methods import (
    get_instance_key,
    match_modules,
    match_components,
    match_pins,
)
from atopile.model2.object_methods import lowest_common_super
from atopile.model2.datamodel import Object
from atopile.model.utils import generate_uid_from_path

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
        self.components: list = []
        self.libparts: dict[tuple, KicadLibpart] = {}
        self.designator_counter: Mapping[str, Callable[[], int]] = defaultdict(functools.partial(itertools.count, firstval=1))

    def make_designator(self, component: Instance) -> str:
        """Give me a designator"""
        prefix = str(component.children.get("designator_prefix", "U"))
        index = next(self.designator_counter[prefix])
        return prefix + str(index)

    def make_libpart(self, component: Instance) -> KicadLibpart:
        """Make a KiCAD libpart object from a representative instance object."""
        libpart_pins = []
        libpart_fields = {}
        for child_name, child in component.children.items():
            if isinstance(child, str) or isinstance(child, int):
                libpart_fields[child_name] = child
            elif isinstance(child, Instance):
                if match_pins(child):
                    libpart_pins.append(self.visit_libpart_pin(child))

        def __get_origin_of_instance(instance: Instance) -> Object:
            return instance.origin

        lowest_common_ancestor = "NotImplemented" # need to fix this later lowest_common_super(__get_origin_of_instance(component))

        constructed_libpart = KicadLibpart(
            lib="component_class_path",  # FIXME: this may require sanitisation (eg. no slashes, for Kicad)
            part=component.children.get(key="mpn", default="No mpn set"),
            description=lowest_common_ancestor,  # here we should find the lowest common ancestor
            fields=[KicadField(name=field[0], value=field[1]) for field in libpart_fields],
            pins=libpart_pins,
            # TODO: something better for these:
            docs="~",
            footprints=["*"],
        )
        return constructed_libpart

    def get_libpart(self, component: Instance) -> KicadLibpart:
        """Get a libpart from the instance"""
        uniqueness_key = get_instance_key(component)
        if uniqueness_key not in self.libparts:
            self.libparts[uniqueness_key] = self.make_libpart(component)

    def create_component(self, component: Instance) -> KicadComponent:
        """Create kicad component from instance"""
        component_fields = {}
        for child_name, child in component.children.items():
            if isinstance(child, str) or isinstance(child, int):
                component_fields[child_name] = child

        sheetpath = KicadSheetpath( # That's not actually what we want. Will have to fix
            names=str(component.ref),
            tstamps=generate_uid_from_path(str(component.ref))
        )

        constructed_component = KicadComponent(
            ref=component.children.get("designator", "designator not set"),
            value=component.children.get("value", ""),
            footprint=component.children.get("footprint", ""), #TODO: have to associate this with the lib
            libsource="libparts[component_class_path]",
            tstamp=generate_uid_from_path(str(component.ref)),
            fields=[KicadField(name=field_name, value=field_value) for field_name, field_value in component_fields.items()],
            sheetpath=sheetpath,
            src_path=str(component.ref),
        )
        self.components.append(constructed_component)


    def visit(self, instance: Instance) -> list:
        if match_components(instance):
            return self.visit_component(instance)
        if match_modules(instance):
            return self.visit_children(instance)


    def visit_children(self, instance: Instance) -> Any:
        """Visit an instance"""
        for child in instance.children.values():
            if hasattr(child, "children"):
                if isinstance(child, Instance):
                    self.visit(child)

    def visit_component(self, component: Instance) -> KicadComponent:
        """Visit and create a KiCAD component"""
        self.get_libpart(component)
        self.create_component(component)

    def visit_libpart_pin(self, pin: Instance) -> KicadPin:
        """Visit and create a KiCAD pin"""
        return KicadPin(
            num=pin.ref[-1],
            name=pin.ref[-1],
            type="stereo"
        )
