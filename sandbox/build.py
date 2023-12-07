# %%
import logging
from collections import ChainMap, defaultdict
from pathlib import Path
from typing import Any, Callable, Hashable, Iterable, Iterator, List, Optional, Tuple

from attrs import define, frozen
from toolz import groupby

from atopile.datatypes import Ref
from atopile.loop_soup import LoopSoup
from atopile.front_end import Instance

# %%

ato_src = """
interface Power:
    signal vcc
    signal gnd

component Resistor:
    pin 1
    pin 2
    designator_prefix = "R"

module VDiv:
    signal top
    signal out
    signal bottom

    power = new Power
    power.vcc ~ top
    power.gnd ~ bottom

    r_top = new Resistor
    r_bottom = new Resistor
    top ~ r_top.1
    r_top.2 ~ out
    r_top.2 ~ r_bottom.1
    r_bottom.2 ~ bottom

module Root:
    vdiv = new VDiv
    vdiv.r_top.value = 123
    vdiv.r_bottom.value = 456
"""

# example addr str:
ROOT = ":Root::"

_children: dict[str, list[str]] = {
    ":Root::": [":Root::vdiv"],
    ":Root::vdiv": [
        ":Root::vdiv.top",
        ":Root::vdiv.out",
        ":Root::vdiv.bottom",
        ":Root::vdiv.r_top",
        ":Root::vdiv.r_bottom",
        ":Root::vdiv.power",
    ],
    ":Root::vdiv.top": [],
    ":Root::vdiv.out": [],
    ":Root::vdiv.bottom": [],
    ":Root::vdiv.r_top": [":Root::vdiv.r_top.1", ":Root::vdiv.r_top.2"],
    ":Root::vdiv.r_bottom": [":Root::vdiv.r_bottom.1", ":Root::vdiv.r_bottom.2"],
    ":Root::vdiv.r_top.1": [],
    ":Root::vdiv.r_top.2": [],
    ":Root::vdiv.r_bottom.1": [],
    ":Root::vdiv.r_bottom.2": [],
    ":Root::vdiv.power": [":Root::vdiv.power.vcc", ":Root::vdiv.power.gnd"],
    ":Root::vdiv.power.vcc": [],
    ":Root::vdiv.power.gnd": [],
}

# def get_children(addr: str) -> list[str]:
#     # TODO: write me irl
#     return _children[addr]

from atopile.address import get_entry, get_instance_section

def get_children(address: str) -> Iterable[Instance]:
    root_addr = get_entry(address)
    root_instance = lofty[root_addr]
    ref_str = get_instance_section(address)
    for child_ref in ref_str:
        nested_instance = root_instance.children[child_ref]
    children_to_return = {}
    for child_key, child_to_return in nested_instance.children.items():
        children_to_return[address + child_key] = child_to_return #TODO: might want to add a function to append two strings together

    return children_to_return

_data: dict[str, dict[str, Any]] = {
    ":Root::": {},
    ":Root::vdiv": {},
    ":Root::vdiv.top": {},
    ":Root::vdiv.out": {},
    ":Root::vdiv.bottom": {},
    ":Root::vdiv.r_top": {
        "value": 123,
        "designator_prefix": "R",
        "footprint": "0402",
    },
    ":Root::vdiv.r_bottom": {
        "value": 456,
        "designator_prefix": "R",
        "footprint": "0402",
    },
    ":Root::vdiv.r_top.1": {},
    ":Root::vdiv.r_top.2": {},
    ":Root::vdiv.r_bottom.1": {},
    ":Root::vdiv.r_bottom.2": {},
    ":Root::vdiv.power": {},
    ":Root::vdiv.power.vcc": {},
    ":Root::vdiv.power.gnd": {},
}

_lock_data: dict[str, dict[str, Any]] = {
    ":Root::": {},
    ":Root::vdiv": {},
    ":Root::vdiv.top": {},
    ":Root::vdiv.out": {},
    ":Root::vdiv.bottom": {},
    ":Root::vdiv.r_top": {},
    ":Root::vdiv.r_bottom": {"designator": "R10",},
    ":Root::vdiv.r_top.1": {},
    ":Root::vdiv.r_top.2": {},
    ":Root::vdiv.r_bottom.1": {},
    ":Root::vdiv.r_bottom.2": {},
    ":Root::vdiv.power": {},
    ":Root::vdiv.power.vcc": {},
    ":Root::vdiv.power.gnd": {},
}

# %%

def get_data_dict(addr: str) -> dict[str, str | int | bool | float]:
    """
    Return the data at the given address
    """
    root_addr = get_entry(addr)
    root_instance = lofty[root_addr]
    ref_str = get_instance_section(address)
    for child_ref in ref_str:
        nested_instance = root_instance.children[child_ref]
    return nested_intance.

    return children_to_return
    return _data[addr]

def get_lock_data_dict(addr: str) -> dict[str, str | int | bool | float]:
    """
    Return the data at the given address
    """
    # TODO: write me irl
    return _lock_data[addr]

def set_lock_data_dict(addr: str, data: dict[str, str | int | bool | float]) -> None:
    """
    Set the data at the given address
    """
    _lock_data[addr] = data


# %%

def all_descendants(root: str) -> Iterable[str]:
    """
    Return a list of addresses in depth-first order
    """
    for child in get_children(root):
        yield from all_descendants(child)
    yield root


def _make_dumb_matcher(pass_list) -> Callable[[str], bool]:
    """
    Return a filter that checks if the addr is in the pass_list
    """
    def _filter(addr: str) -> bool:
        if addr in pass_list:
            return True
        return False
    return _filter

_component_addrs = [
    ":Root::vdiv.r_top",
    ":Root::vdiv.r_bottom",
]
match_components = _make_dumb_matcher(_component_addrs)

_module_addrs = [
    ":Root::vdiv",
    ":Root::",
]
match_modules = _make_dumb_matcher(_module_addrs)

_pin_addrs = [
    ":Root::vdiv.r_top.1",
    ":Root::vdiv.r_top.2",
    ":Root::vdiv.r_bottom.1",
    ":Root::vdiv.r_bottom.2",
]

match_pins = _make_dumb_matcher(_pin_addrs)

_signal_addrs = [
    ":Root::vdiv.top",
    ":Root::vdiv.bottom",
    ":Root::vdiv.out",
    ":Root::vdiv.power.vcc",
    ":Root::vdiv.power.gnd",
]

match_signals = _make_dumb_matcher(_signal_addrs)

match_pins_and_signals = _make_dumb_matcher([*_pin_addrs, *_signal_addrs])

_interface_addrs = [":Root::vdiv.power"]

match_interfaces = _make_dumb_matcher(_interface_addrs)


# %%

def get_parent(addr: str) -> Optional[str]:
    """
    Return the parent of the given address
    """
    # TODO: write me irl
    if "::" not in addr:
        raise ValueError("Address isn't an instance")
    root_path, instance_path = addr.rsplit("::", 1)
    if "." in instance_path:
        return addr.rsplit(".", 1)[0]
    elif instance_path:
        return root_path + "::"
    return None  # there is no parent

def get_name(addr: str) -> list[str]:
    # TODO: write me irl
    addr_list = addr.split(".")
    return addr_list[-1]


# %%

def iter_parents(addr: str) -> Iterator[str]:
    """
    Iterate over the parents of the given address
    """
    while addr := get_parent(addr):
        yield addr


# %%


_links: dict[str, list[tuple[str, str]]] = {
    ":Root::": [],
    ":Root::vdiv": [
        (":Root::vdiv.top", ":Root::vdiv.r_top.1"),
        (":Root::vdiv.out", ":Root::vdiv.r_top.2"),
        (":Root::vdiv.r_top.2", ":Root::vdiv.r_bottom.1"),
        (":Root::vdiv.r_bottom.2", ":Root::vdiv.bottom"),
        (":Root::vdiv.power.vcc", ":Root::vdiv.top"),
        (":Root::vdiv.power.gnd", ":Root::vdiv.bottom"),
    ],
    ":Root::vdiv.top": [],
    ":Root::vdiv.out": [],
    ":Root::vdiv.bottom": [],
    ":Root::vdiv.r_top": [],
    ":Root::vdiv.r_bottom": [],
    ":Root::vdiv.r_top.1": [],
    ":Root::vdiv.r_top.2": [],
    ":Root::vdiv.r_bottom.1": [],
    ":Root::vdiv.r_bottom.2": [],
    ":Root::vdiv.power": [],
    ":Root::vdiv.power.vcc": [],
    ":Root::vdiv.power.gnd": [],
}


# %%

def _get_nets(root: str) -> Iterable[Iterable[str]]:
    # TODO: support interfaces
    net_soup = LoopSoup()
    for addr in all_descendants(root):
        if match_pins_and_signals(addr):
            net_soup.add(addr)
        for source, target in _links[addr]:
            net_soup.join(source, target)
    return net_soup.groups()


# %%

@define
class Net:
    nodes_on_net: list[str]

    base_name: Optional[str] = None

    lcp: Optional[str] = None
    prefix: Optional[Ref] = None

    suffix: Optional[int] = None

    def get_name(self) -> str:
        """Get the name of the net."""
        #suffix is a ref (tuple of strings)
        return (f"{'-'.join(self.prefix) + '-' if self.prefix else ''}"
                f"{self.base_name or 'net'}"
                f"{'-' + str(self.suffix) if self.suffix else ''}")

    def generate_base_net_name(self) -> Optional[str]:
        """TODO:"""
        WEIGHT_NO_GRANDPARENTS = 10
        WEIGHT_INTERFACE_GRANDPARENT = 5
        WEIGHT_SIGNAL = 2

        name_candidates = defaultdict(int)

        for signal in filter(match_signals, self.nodes_on_net):
            name = get_name(signal)
            if get_parent(signal) is None:
                name_candidates[name] += WEIGHT_NO_GRANDPARENTS
            elif any(map(match_interfaces, iter_parents(signal))):
                name_candidates[name] += WEIGHT_INTERFACE_GRANDPARENT
            else:
                name_candidates[name] += WEIGHT_SIGNAL

        if name_candidates:
            highest_rated_name = max(name_candidates, key=name_candidates.get)
            self.base_name = highest_rated_name


def find_net_names(nets: Iterable[Iterable[str]]) -> dict[str, list[str]]:
    """Find the names of the nets."""
    # make net objects
    net_objs = [Net(list(net)) for net in nets]

    # grab all the nets base names
    for net in net_objs:
        net.generate_base_net_name()

    # for the net objects that still conflict, grab a prefix
    conflicing_nets = find_conflicts(net_objs)
    add_prefix(conflicing_nets)

    # if they still conflict, slap a suffix on that bad boi
    conflicing_nets = find_conflicts(net_objs)
    add_suffix(conflicing_nets)

    return {net.get_name(): net.nodes_on_net for net in net_objs}


def find_conflicts(nets: Iterable[Net]) -> Iterable[Iterable[Net]]:
    """"""
    nets_grouped_by_name = groupby(lambda net: net.get_name(), nets)
    for nets in nets_grouped_by_name.values():
        if len(nets) > 1:
            yield nets


def add_prefix(conflicts: Iterator[list[Net]]):
    """Resolve conflicts in net names."""
    for conflict_nets in conflicts:
        for net in conflict_nets:
            if net.base_name:
                # Find the parent of the net that is a module
                parent_module_iter = filter(match_modules, iter_parents(net.nodes_on_net[0]))

                # Get the first parent module that matches, or None if there's no match
                parent_module = next(parent_module_iter, None)

                # Check if a parent module was found
                if parent_module:
                    # Get the ref of the parent module
                    if hasattr(parent_module, "ref"):
                        net.prefix = address.get_instparent_module


def add_suffix(conflicts: Iterator[list[Net]]):
    """Add an integer suffix to the nets to resolve conflicts."""
    for conflict_nets in conflicts:
        for i, net in enumerate(conflict_nets):
            net.suffix = i

#%%

_unnamed_nets = _get_nets(ROOT)
_net_names_to_nodes = find_net_names(_unnamed_nets)
_nodes_to_net_names = {node: net_name for net_name, nodes in _net_names_to_nodes.items() for node in nodes}

def get_net_name_node_is_on(addr: str) -> str:
    """
    Return the net name for the given address
    """
    return _nodes_to_net_names[addr]

def get_nets(root: str) -> dict[str, list[str]]:
    """
    Return a dict of net names to nodes
    """
    if root != ROOT:
        raise NotImplementedError("Only ROOT is supported for now")
    return _net_names_to_nodes

# %%

def get_mpn(addr: str) -> str:
    """
    Return the MPN for a component
    """
    # TODO: write me irl
    _mpns = {
        ":Root::vdiv.r_top": "LCSC-123",
        ":Root::vdiv.r_bottom": "LCSC-456",
    }
    return _mpns[addr]

def get_value(addr: str) -> str:
    """
    Return the value for a component
    """
    # TODO: write me irl
    comp_data = get_data_dict(addr)
    return comp_data["value"]

# %%

import tempfile
import textwrap

from atopile.project.config import Config, make_config

with tempfile.NamedTemporaryFile() as fp:
    fp.write(
        textwrap.dedent(
            """
            ato-version: ^0.0.21
            paths:
                footprints: footprints
            """
        ).encode("utf-8")
    )
    fp.flush()

    _config = make_config(Path(fp.name))

# pylint: disable=pointless-string-statement
"""
Footprints have their own type, because they need to be "absolute" in some sense
When you install some subproject, it comes with its own footprints, and you need to
be able to reference those from the parent project.
Additionally, the generic component pickers might select components on your behalf that
assign footprints, and you need to know how to access their footprints.
"""

def get_footprint(addr: str) -> str:
    """
    Return the footprint for a component
    """
    # TODO: write me irl
    comp_data = get_data_dict(addr)
    user_footprint_name = comp_data["footprint"]
    return user_footprint_name


# %%

"""
Dicts we will need at the end:
- COMPONENTS: List of [AddrStr] for all components
- BOM: Dict of [('value', 'mpn') : ['compAddrStr']]
- LIBPART: Dict of ['footprint' : ['compAddrStr']]
- DESIGNATOR: Dict [compAddrStr : "Designator"]
- NETS: List of signals and pins representing netlist -> netlist naming algorithm should produce: Dict ["net name" : [pinAddrStr]]
- VALUE: [compAddrStr : value]
- MPN: [[compAddrStr : mpn]
"""




# %%
"""
Designators
- All the components
- Checks if the component has a designator
- If it does not, it assigns one
"""
from typing import Any, Iterable, Mapping, Optional, Type


def _make_designators(root: str) -> dict[str,str]:
    components = filter(match_components, all_descendants(root))
    designators: dict[str, str] = {}
    unnamed_components = []
    used_designators = set()

    # first pass: grab all the designators from the lock data
    for component in components:
        designator = get_lock_data_dict(component).get("designator")
        if designator:
            used_designators.add(designator)
            designators[component] = designator
        else:
            unnamed_components.append(component)

    # second pass: assign designators to the unnamed components
    for component in unnamed_components:
        prefix = get_data_dict(component).get("designator_prefix", "U")
        i = 1
        while f"{prefix}{i}" in used_designators:
            i += 1
        designators[component] = f"{prefix}{i}"
        set_lock_data_dict(component, {"designator": f"{prefix}{i}"})

    return designators

_designators = _make_designators(ROOT)

def get_designator(addr: str) -> str:
    """Return a mapping of instance address to designator."""
    # find component specified by address and return designator

    return _designators[addr]

def set_designator(addr: str, designator: str) -> None:
    """Set the designator for the given address. To its lock data."""
    set_lock_data_dict(addr, {"designator": designator})

# %%
"""
BOM
- All the components
- Designators for each component
- LCSC part number for each component
"""

components = filter(match_components, all_descendants(ROOT))
bom = defaultdict(dict)
#JLC format: Comment(whatever might be helpful)	Designator	Footprint	LCSC
for component in components:
    mpn = get_mpn(component)
    # add to bom keyed on mpn
    bom[mpn]["value"] = get_value(component)
    bom[mpn]["footprint"] = get_footprint(component)
    bom[mpn]["designator"] = get_designator(component)

import csv

from rich import print
from rich.table import Table

# Create a table
table = Table(show_header=True, header_style="bold magenta")
table.add_column("Comment")
table.add_column("Designator")
table.add_column("Footprint")
table.add_column("LCSC")

# Add rows to the table
for mpn, data in bom.items():
    table.add_row(str(data['value']), data['designator'], data['footprint'], mpn)


# generate csv
# with open('bom.csv', 'w', newline='') as csvfile:
#     fieldnames = ['Comment', 'Designator', 'Footprint', 'LCSC']
#     writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

#     writer.writeheader()
#     for mpn, data in bom.items():
#         writer.writerow({'Comment': data['value'], 'Designator': data['designator'], 'Footprint': data['footprint'], 'LCSC': mpn})



# %%


# %%


####
# Netlist
####

def get_name(addr: str) -> list[str]:
    # TODO: write me irl
    addr_list = addr.split(".")
    return addr_list[-1]
#%%
def get_libpart_unique_components() -> dict:
    """Get a libpart from the instance"""
    unique_keys = []
    libparts = defaultdict(list)
    footprints = {}
    components = filter(match_components, all_descendants(ROOT))
    for component in components:
        footprint = get_footprint(component)
        footprints[component] = footprint
        if footprint not in unique_keys:
            libparts[footprint].append(component)

    return libparts


#%%
def get_pins(component) -> dict:
    pins = filter(match_pins, get_children(component))
    return pins


#%%
# def get_component_footprints(root) -> dict:
#     """Get a libpart from the instance"""
#     libparts = defaultdict(list)
#     footprints = {}
#     components = filter(match_components, all_descendants(root))
#     for component in components:
#         footprint = get_footprint(component)
#         footprints[component] = footprint

#     return footprints


from atopile.model.utils import generate_uid_from_path

#%%
from atopile.targets.netlist.kicad6_datamodel import (
    KicadComponent,
    KicadLibpart,
    KicadNet,
    KicadNetlist,
    KicadNode,
    KicadPin,
    KicadSheetpath,
)


class Builder:
    def __init__(self):
        """TODO:"""
        self.netlist: Optional[KicadNetlist] = None
        self._libparts: dict[tuple, KicadLibpart] = {}
        self._components: dict[tuple, KicadComponent] = {}
        self._nets: dict[str, KicadNet] = {}

    def make_kicad_pin(self, pinAddrStr) -> KicadPin:
        """Make a KiCAD pin object from a representative instance object."""
        return KicadPin(
            name=get_name(pinAddrStr),
            type="stereo"
        )

    def make_libpart(self, compAddrStr) -> KicadLibpart:
        """Make a KiCAD libpart object from a representative instance object."""
        pins = [self.make_kicad_pin(pin) for pin in get_pins(compAddrStr)]
        # def _get_origin_of_instance(instance: Instance) -> Object:
        #     return instance.origin

        # lowest_common_ancestor = lowest_common_super(map(_get_origin_of_instance, component))
        # lowest_common_ancestor = "FIXME: lowest_common_ancestor"

        constructed_libpart = KicadLibpart(
            part=get_mpn(compAddrStr),
            description="lowest_common_ancestor",
            fields=[],
            pins=pins,

            # TODO: something better for these:
            lib="lib",
            docs="~",
            footprints=["*"],
        )
        return constructed_libpart

    def make_node(self, nodeAddr) -> KicadNode:
        node = KicadNode(
            pin=get_name(nodeAddr),  # eg. 1
            ref=get_designator(get_parent(nodeAddr)),  # eg. R1
            pintype="stereo"
        )
        return node

    def make_net(self, code, net_name, net_list) -> KicadNet:
        net = KicadNet(
            code=code,
            name=net_name,
            nodes=[
                self.make_node(pin) for pin in filter(match_pins, net_list)
            ]
        )
        return net

    def make_component(self, compAddrStr, libsource) -> KicadComponent:
        # TODO: improve this
        sheetpath = KicadSheetpath( # That's not actually what we want. Will have to fix
            names=compAddrStr, # TODO: going to have to strip the comp name from this
            tstamps=generate_uid_from_path(str(compAddrStr))
        )

        designator = get_designator(compAddrStr)
        constructed_component = KicadComponent(
            ref=designator,
            value=get_value(compAddrStr),
            footprint=get_footprint(compAddrStr),
            libsource=libsource,
            tstamp=generate_uid_from_path(str(compAddrStr)),
            fields=[],
            sheetpath=sheetpath,
            src_path=compAddrStr,
        )
        return constructed_component

    def build(self, root) -> KicadNetlist:
        """Build a netlist from an instance"""
        self.netlist = KicadNetlist()

        ######
        for footprint, components in groupby(get_footprint, filter(match_components, all_descendants(root))).items():
            libsource = self._libparts[footprint] = self.make_libpart(components[0])

            for component in components:
                self._components[component] = self.make_component(component, libsource)

        ######


        for code, (net_name, pin_signal_list) in enumerate(get_nets(root).items(), start=1):
            self._nets[net_name] = self.make_net(code, net_name, pin_signal_list)

        self.netlist.libparts = list(self._libparts.values())
        self.netlist.components = list(self._components.values())
        self.netlist.nets = list(self._nets.values())

        return self.netlist

# %%
import logging
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, StrictUndefined


builder = Builder()

netlist = builder.build(ROOT)

# Create a Jinja2 environment
# this_dir = Path(__file__).parent
this_dir = Path(__file__).parent
env = Environment(loader=FileSystemLoader(this_dir), undefined=StrictUndefined)

# Create the complete netlist
template = env.get_template("kicad6.j2")
netlist_str = template.render(nl=builder.netlist)

# %%

import shutil

fp_target = Path("/Users/mattwildoer/Projects/atopile-workspace/servo-drive/footprints")
fp_target.mkdir(exist_ok=True)
for fp in Path("/Users/mattwildoer/Projects/atopile-workspace/servo-drive").glob("**/*.kicad_mod"):
    try:
        shutil.copy(fp, fp_target)
    except shutil.SameFileError:
        print(f"same file error {fp}")

# %%
