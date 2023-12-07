# %%
import toolz
import logging
import sys
from itertools import chain
from pathlib import Path
from textwrap import dedent

import click
import rich
import rich.tree
from omegaconf import OmegaConf

from atopile import address
from atopile.address import AddrStr
# from atopile.cli.common import project_options
# from atopile.config import Config
from atopile.errors import ErrorHandler, HandlerMode
from atopile.front_end import Dizzy, Instance, Lofty, Scoop
from atopile.parse import FileParser

from collections import ChainMap, defaultdict
from pathlib import Path
from typing import Any, Callable, Hashable, Iterable, Iterator, List, Optional, Tuple

from attrs import define, frozen
from toolz import groupby
from pathlib import Path

from atopile.datatypes import Ref
from atopile.loop_soup import LoopSoup

# %%

error_handler = ErrorHandler(handel_mode=HandlerMode.RAISE_ALL)

search_paths = [
    Path("/Users/mattwildoer/Projects/atopile-workspace/servo-drive/elec/src/"),
]

parser = FileParser()

scoop = Scoop(error_handler, parser.get_ast_from_file, search_paths)
dizzy = Dizzy(error_handler, scoop.get_obj_def)
lofty = Lofty(error_handler, dizzy.get_obj_layer)

# entry_instance_tree = lofty.get_instance_tree(config.selected_build.abs_entry)

ROOT = address.from_parts("/Users/mattwildoer/Projects/atopile-workspace/servo-drive/elec/src/spin_servo_nema17.ato", "SpinServoNEMA17")
lofty.get_instance_tree(ROOT)

# %%

def get_children(addr: str) -> Iterable[Instance]:
    root_addr = address.get_entry(addr)
    root_instance = lofty.get_instance_tree(root_addr)
    ref_str = address.get_instance_section(addr)

    nested_instance = root_instance
    if ref_str:
        for child_ref in ref_str.split("."):
            nested_instance = nested_instance.children[child_ref]

    for child in nested_instance.children.values():
        yield child.addr

def get_data_dict(addr: str) -> dict[str, str | int | bool | float]:
    """
    Return the data at the given address
    """
    return lofty._output_cache[addr].data

def get_lock_data_dict(addr: str) -> dict[str, str | int | bool | float]:
    """
    Return the data at the given address
    """
    # TODO: write me irl
    return {}
    return _lock_data[addr]

def set_lock_data_dict(addr: str, data: dict[str, str | int | bool | float]) -> None:
    """
    Set the data at the given address
    """
    return
    _lock_data[addr] = data

def all_descendants(addr: str) -> Iterable[str]:
    """
    Return a list of addresses in depth-first order
    """
    for child in get_children(addr):
        yield from all_descendants(child)
    yield addr

#%%

def _make_dumb_matcher(pass_list: Iterable[str]) -> Callable[[str], bool]:
    """
    Return a filter that checks if the addr is in the pass_list
    """
    # TODO: write me irl
    def _filter(addr: AddrStr) -> bool:
        instance = lofty._output_cache[addr]
        for super_ in reversed(instance.supers):
            if super_.address in pass_list:
                return True
        return False
    return _filter


match_components = _make_dumb_matcher(["<Built-in>:Component"])
match_modules = _make_dumb_matcher(["<Built-in>:Module"])
match_signals = _make_dumb_matcher(["<Built-in>:Signal"])
match_pins = _make_dumb_matcher("<Built-in>:Pin")
match_pins_and_signals = _make_dumb_matcher(["<Built-in>:Pin", "<Built-in>:Signal"])
match_interfaces = _make_dumb_matcher(["<Built-in>:Interface"])

def get_parent(addr: str) -> Optional[str]:
    """
    Return the parent of the given address
    """
    # TODO: write me irl
    if "::" not in addr:
        return None
    root_path, instance_path = addr.rsplit("::", 1)
    if "." in instance_path:
        return addr.rsplit(".", 1)[0]
    elif instance_path:
        return root_path

def get_name(addr: str) -> list[str]:
    # TODO: write me irl
    addr_list = addr.split(".")
    return addr_list[-1]

def iter_parents(addr: str) -> Iterator[str]:
    """
    Iterate over the parents of the given address
    """
    while addr := get_parent(addr):
        yield addr

# %%

def _get_links(addr: AddrStr) -> Iterable[tuple[AddrStr, AddrStr]]:
    """TODO: write me irl"""
    links = lofty._output_cache[addr].links
    for link in links:
        yield (link.source.addr, link.target.addr)

def _get_nets(root: AddrStr) -> Iterable[Iterable[str]]:
    # TODO: support interfaces
    net_soup = LoopSoup()
    for addr in all_descendants(root):
        if match_pins_and_signals(addr):
            net_soup.add(addr)
        for source, target in _get_links(addr):
            if match_interfaces(source) or match_interfaces(target):
                pass  # FIXME:
            else:
                net_soup.join(source, target)
    return net_soup.groups()

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
                        net.prefix = address.get_instance_section(parent_module)


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

# print(_net_names_to_nodes)

# %%

def get_mpn(addr: str) -> str:
    """
    Return the MPN for a component
    """
    # TODO: write me irl
    comp_data = get_data_dict(addr)
    return comp_data["mpn"]

def get_value(addr: str) -> str:
    """
    Return the value for a component
    """
    # TODO: write me irl
    comp_data = get_data_dict(addr)
    return comp_data["value"]

# %%

# import tempfile
# import textwrap

# from atopile.project.config import Config, make_config

# with tempfile.NamedTemporaryFile() as fp:
#     fp.write(
#         textwrap.dedent(
#             """
#             ato-version: ^0.0.21
#             paths:
#                 footprints: footprints
#             """
#         ).encode("utf-8")
#     )
#     fp.flush()

#     _config = make_config(Path(fp.name))

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
Designators
- All the components
- Checks if the component has a designator
- If it does not, it assigns one
"""
from typing import Any, Iterable, Mapping, Optional, Type


def _make_designators(root: str) -> dict[str,str]:
    designators: dict[str, str] = {}
    unnamed_components = []
    used_designators = set()

    # first pass: grab all the designators from the lock data
    for component in filter(match_components, all_descendants(root)):
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
        used_designators.add(designators[component])
        set_lock_data_dict(component, {"designator": f"{prefix}{i}"})

    return designators

_designators = _make_designators(ROOT)

_designators

#%%

def get_designator(addr: str) -> str:
    """Return a mapping of instance address to designator."""
    # find component specified by address and return designator

    return _designators[addr]

def set_designator(addr: str, designator: str) -> None:
    """Set the designator for the given address. To its lock data."""
    set_lock_data_dict(addr, {"designator": designator})

# print(get_designator(":Root::vdiv.r_top"))
# print(get_designator(":Root::vdiv.r_bottom"))

# print(_lock_data)
# %%
"""
BOM
- All the components
- Designators for each component
- LCSC part number for each component
"""

components = list(filter(match_components, all_descendants(ROOT)))
bom = defaultdict(dict)
#JLC format: Comment(whatever might be helpful)	Designator	Footprint	LCSC
for component in components:
    try:
        mpn = get_mpn(component)
    except KeyError:
        continue
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

# Print the table
print(table)

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

# %%

def _get_footprint(addr: str) -> str:
    """
    Return the footprint for a component
    """
    try:
        return get_footprint(addr)
    except KeyError:
        return "<FIXME: footprint>"

# groupby(_get_footprint, filter(match_components, all_descendants(ROOT)))

#%%
def get_pins(component) -> dict:
    pins = filter(match_pins, get_children(component))
    return pins


#%%

import uuid
import hashlib

def generate_uid_from_path(path: str) -> str:
    path_as_bytes = path.encode('utf-8')
    hashed_path = hashlib.blake2b(path_as_bytes, digest_size=16).digest()
    return str(uuid.UUID(bytes=hashed_path))


#%%
from atopile.kicad6_datamodel import (
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

        def _get_mpn(addr: AddrStr) -> str:
            try:
                return get_mpn(addr)
            except KeyError:
                return "<FIXME: MPN>"

        constructed_libpart = KicadLibpart(
            part=_get_mpn(compAddrStr),
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

        def _get_value(addr: AddrStr) -> str:
            try:
                return get_value(addr)
            except KeyError:
                return "<FIXME: value>"

        def _get_footprint(addr: AddrStr) -> str:
            try:
                return get_footprint(addr)
            except KeyError:
                return "<FIXME: footprint>"

        designator = get_designator(compAddrStr)
        constructed_component = KicadComponent(
            ref=designator,
            value=_get_value(compAddrStr),
            footprint=_get_footprint(compAddrStr),
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
        for footprint, components in groupby(_get_footprint, filter(match_components, all_descendants(root))).items():
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
print(netlist)

# Create a Jinja2 environment
# this_dir = Path(__file__).parent
this_dir = Path(__file__).parent
env = Environment(loader=FileSystemLoader(this_dir), undefined=StrictUndefined)

# Create the complete netlist
template = env.get_template("kicad6.j2")
netlist_str = template.render(nl=builder.netlist)
print(netlist_str)

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
