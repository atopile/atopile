import hashlib
import uuid
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from toolz import groupby

from atopile import components, nets
from atopile.address import AddrStr, get_name, get_relative_addr_str
from atopile.instance_methods import (
    all_descendants,
    get_children,
    get_next_super,
    get_parent,
    match_components,
    match_pins,
)
from atopile.kicad6_datamodel import (
    KicadComponent,
    KicadLibpart,
    KicadNet,
    KicadNetlist,
    KicadNode,
    KicadPin,
    KicadSheetpath,
)


def get_value(addr: AddrStr) -> str:
    try:
        return components.get_value(addr)
    except KeyError:
        return "<help! no value>"


def get_footprint(addr: AddrStr) -> str:
    """
    Return the footprint for a component
    """
    try:
        return components.get_footprint(addr)
    except KeyError:
        return "<help! no footprint>"


def get_mpn(addr: AddrStr) -> str:
    """
    Return the footprint for a component
    """
    try:
        return components.get_mpn(addr)
    except KeyError:
        return "<help! no mpn>"


def generate_uid_from_path(path: str) -> str:
    """Spits out a uuid in hex from a string"""
    path_as_bytes = path.encode("utf-8")
    hashed_path = hashlib.blake2b(path_as_bytes, digest_size=16).digest()
    return str(uuid.UUID(bytes=hashed_path))


class NetlistBuilder:
    """He builds netlists."""

    def __init__(self):
        """TODO:"""
        self.netlist: Optional[KicadNetlist] = None
        self._libparts: dict[tuple, KicadLibpart] = {}
        self._components: dict[tuple, KicadComponent] = {}
        self._nets: dict[str, KicadNet] = {}

    def make_kicad_pin(self, pin_addr) -> KicadPin:
        """Make a KiCAD pin object from a representative instance object."""
        return KicadPin(name=get_name(pin_addr), type="stereo")

    def make_libpart(self, comp_addr: AddrStr) -> KicadLibpart:
        """Make a KiCAD libpart object from a representative instance object."""
        model_pins = filter(match_pins, get_children(comp_addr))
        pins = [self.make_kicad_pin(pin) for pin in model_pins]
        # def _get_origin_of_instance(instance: Instance) -> Object:
        #     return instance.origin

        super_abs_addr = get_next_super(comp_addr).obj_def.address
        super_addr = get_relative_addr_str(super_abs_addr)
        constructed_libpart = KicadLibpart(
            part=get_mpn(comp_addr),
            description=super_addr,
            fields=[],
            pins=pins,
            # TODO: something better for these:
            lib="lib",
            docs="~",
            footprints=["*"],
        )
        return constructed_libpart

    def make_node(self, node_addr: AddrStr) -> KicadNode:
        """Make a KiCAD node object from a representative instance object."""
        parent = get_parent(node_addr)
        node = KicadNode(
            pin=get_name(node_addr),  # eg. 1
            ref=components.get_designator(parent),  # eg. R1
            pintype="stereo",
        )
        return node

    def make_net(self, code, net_name, net_list) -> KicadNet:
        """Make a KiCAD net object from a representative instance object."""
        net = KicadNet(
            code=code,
            name=net_name,
            nodes=[self.make_node(pin) for pin in filter(match_pins, net_list)],
        )
        return net

    def make_component(
        self, comp_addr: AddrStr, libsource: KicadLibpart
    ) -> KicadComponent:
        """Make a KiCAD component object from a representative instance object."""

        # TODO: improve this
        sheetpath = (
            KicadSheetpath(  # That's not actually what we want. Will have to fix
                names=comp_addr,  # TODO: going to have to strip the comp name from this
                tstamps=generate_uid_from_path(str(comp_addr)),
            )
        )

        def _get_footprint(addr: AddrStr) -> str:
            try:
                return get_footprint(addr)
            except KeyError:
                return "<FIXME: footprint>"

        designator = components.get_designator(comp_addr)
        constructed_component = KicadComponent(
            ref=designator,
            value=get_value(comp_addr),
            footprint=_get_footprint(comp_addr),
            libsource=libsource,
            tstamp=generate_uid_from_path(str(comp_addr)),
            fields=[],
            sheetpath=sheetpath,
            src_path=comp_addr,
        )
        return constructed_component

    def build(self, root) -> KicadNetlist:
        """Build a netlist from an instance"""
        self.netlist = KicadNetlist()

        all_components = filter(match_components, all_descendants(root))
        for footprint, group_components in groupby(get_footprint, all_components).items():
            libsource = self._libparts[footprint] = self.make_libpart(group_components[0])

            for component in group_components:
                self._components[component] = self.make_component(component, libsource)

        for code, (net_name, pin_signal_list) in enumerate(
            nets.get_nets_by_name(root).items(), start=1
        ):
            self._nets[net_name] = self.make_net(code, net_name, pin_signal_list)

        self.netlist.libparts = list(self._libparts.values())
        self.netlist.components = list(self._components.values())
        self.netlist.nets = list(self._nets.values())

        return self.netlist


def get_netlist_as_str(root: AddrStr) -> str:
    """Return the netlist as a string."""
    builder = NetlistBuilder()
    netlist = builder.build(root)

    env = Environment(
        loader=FileSystemLoader(Path(__file__).parent), undefined=StrictUndefined
    )

    # Create the complete netlist
    template = env.get_template("kicad6.j2")
    netlist_str = template.render(nl=netlist)
    return netlist_str
