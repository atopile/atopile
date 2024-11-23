# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import os
import sys
from pathlib import Path
from typing import Any, Callable, TypeVar

import psutil

import faebryk.library._F as F
from faebryk.core.graph import Graph
from faebryk.core.module import Module
from faebryk.core.node import Node
from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer
from faebryk.exporters.pcb.routing.util import apply_route_in_pcb
from faebryk.libs.app.kicad_netlist import write_netlist
from faebryk.libs.app.parameters import resolve_dynamic_parameters
from faebryk.libs.kicad.fileformats import (
    C_kicad_fp_lib_table_file,
    C_kicad_pcb_file,
    C_kicad_project_file,
)
from faebryk.libs.util import ConfigFlag

logger = logging.getLogger(__name__)

PCBNEW_AUTO = ConfigFlag(
    "PCBNEW_AUTO",
    default=False,
    descr="Automatically open pcbnew when applying netlist",
)


def make_point_with_offsets(
    point: F.has_pcb_position.Point,
    x: float = 0,
    y: float = 0,
    z: float = 0,
    layer: F.has_pcb_position.layer_type | None = None,
) -> F.has_pcb_position.Point:
    p_x, p_y, p_z, p_layer = point
    return F.has_pcb_position.Point(
        (p_x + x, p_y + y, p_z + z, layer if layer else p_layer)
    )


T = TypeVar("T", bound="DrawTree")


class DrawTree:
    """Tree layout algorithm implementation for PCB component placement."""

    def __init__(self, node: Node, parent=None, depth=0, number=1):
        self.x = -1.0
        self.y = depth
        self.node = node
        self.parent = parent
        self.thread = None
        self.offset = 0
        self.ancestor = self
        self.change = self.shift = 0
        self._lmost_sibling = None
        self.mod = 0.0
        self.number = number

        # Get all descendant nodes that have footprints, maintaining hierarchy
        self.children = self._build_component_children(node, depth + 1)

    def _build_component_children(self, node: Node, depth: int) -> list["DrawTree"]:
        """Build tree of components, skipping intermediary nodes without footprints."""
        component_children: list[DrawTree] = []
        child_num = 1

        def collect_component_children(n: Node, current_depth: int):
            nonlocal child_num
            # If this node has a footprint, add it directly
            if n.has_trait(F.has_footprint):
                component_children.append(DrawTree(n, self, current_depth, child_num))
                child_num += 1
                return

            # Otherwise, recursively check its children
            for child in n.get_children(direct_only=True, types=Node):
                collect_component_children(child, current_depth)

        # Process all direct children
        for child in node.get_children(direct_only=True, types=Node):
            collect_component_children(child, depth)

        return component_children

    def left(self) -> "DrawTree | None":
        """Return the leftmost child of the node."""
        if self.thread:
            return self.thread
        if len(self.children) > 0:
            return self.children[0]
        return None

    def right(self) -> "DrawTree | None":
        """Return the rightmost child of the node."""
        if self.thread:
            return self.thread
        if len(self.children) > 0:
            return self.children[-1]
        return None

    def left_brother(self):
        """Get the node's left sibling in the tree."""
        n = None
        if self.parent:
            for node in self.parent.children:
                if node == self:
                    return n
                else:
                    n = node
        return n

    def get_lmost_sibling(self):
        """Get the leftmost sibling of this node."""
        if not self._lmost_sibling and self.parent and self != self.parent.children[0]:
            self._lmost_sibling = self.parent.children[0]
        return self._lmost_sibling

    leftmost_sibling = property(get_lmost_sibling)


def buchheim(tree):
    dt = firstwalk(tree)
    min = second_walk(dt)
    if min < 0:
        third_walk(dt, -min)
    return dt


def firstwalk(v, distance=1.0):
    if len(v.children) == 0:
        if v.leftmost_sibling:
            v.x = v.left_brother().x + distance
        else:
            v.x = 0.0
    else:
        default_ancestor = v.children[0]
        for w in v.children:
            firstwalk(w)
            default_ancestor = apportion(w, default_ancestor, distance)
        execute_shifts(v)

        midpoint = (v.children[0].x + v.children[-1].x) / 2

        ell = v.children[0]
        arr = v.children[-1]
        w = v.left_brother()
        if w:
            v.x = w.x + distance
            v.mod = v.x - midpoint
        else:
            v.x = midpoint
    return v


def apportion(v, default_ancestor, distance):
    w = v.left_brother()
    if w is not None:
        # in buchheim notation:
        # i == inner; o == outer; r == right; l == left;
        vir = vor = v
        vil = w
        vol = v.leftmost_sibling
        sir = sor = v.mod
        sil = vil.mod
        sol = vol.mod
        while vil.right() and vir.left():
            vil = vil.right()
            vir = vir.left()
            vol = vol.left()
            vor = vor.right()
            vor.ancestor = v
            shift = (vil.x + sil) - (vir.x + sir) + distance
            if shift > 0:
                a = ancestor(vil, v, default_ancestor)
                move_subtree(a, v, shift)
                sir = sir + shift
                sor = sor + shift
            sil += vil.mod
            sir += vir.mod
            sol += vol.mod
            sor += vor.mod
        if vil.right() and not vor.right():
            vor.thread = vil.right()
            vor.mod += sil - sor
        else:
            if vir.left() and not vol.left():
                vol.thread = vir.left()
                vol.mod += sir - sol
            default_ancestor = v
    return default_ancestor


def move_subtree(wl, wr, shift):
    subtrees = wr.number - wl.number
    wr.change -= shift / subtrees
    wr.shift += shift
    wl.change += shift / subtrees
    wr.x += shift
    wr.mod += shift


def execute_shifts(v):
    shift = change = 0
    for w in v.children[::-1]:
        w.x += shift
        w.mod += shift
        change += w.change
        shift += w.shift + change


def ancestor(vil, v, default_ancestor):
    if vil.ancestor in v.parent.children:
        return vil.ancestor
    else:
        return default_ancestor


def second_walk(v, m=0, depth=0, min=None):
    v.x += m
    v.y = depth

    if min is None or v.x < min:
        min = v.x

    for w in v.children:
        min = second_walk(w, m + v.mod, depth + 1, min)

    return min


def third_walk(tree, n):
    tree.x += n
    for c in tree.children:
        third_walk(c, n)


def apply_layouts(app: Module):
    """Apply automatic layout to components in the PCB."""
    # Starting point for the layout
    origin = F.has_pcb_position.Point((0, 0, 0, F.has_pcb_position.layer_type.NONE))

    if not app.has_trait(F.has_pcb_position):
        app.add(F.has_pcb_position_defined(origin))

    # Build tree of nodes that have footprints
    tree = DrawTree(app)
    positioned_tree = buchheim(tree)

    # Convert the computed positions to PCB coordinates
    HORIZONTAL_SPACING = 10
    VERTICAL_SPACING = 40

    def apply_positions(dt: DrawTree):
        # Only apply positions to nodes with footprints
        if dt.node.has_trait(F.has_footprint):
            pos = make_point_with_offsets(
                origin,
                x=dt.x * HORIZONTAL_SPACING,
                y=dt.y * VERTICAL_SPACING,
                layer=F.has_pcb_position.layer_type.TOP_LAYER,
            )
            dt.node.add(F.has_pcb_position_defined(pos))

        for child in dt.children:
            apply_positions(child)

    apply_positions(positioned_tree)


def apply_routing(app: Module, transformer: PCB_Transformer):
    strategies: list[tuple[F.has_pcb_routing_strategy, int]] = []

    for i, level in enumerate(app.get_tree(types=Node).iter_by_depth()):
        for n in level:
            if not n.has_trait(F.has_pcb_routing_strategy):
                continue

            strategies.append((n.get_trait(F.has_pcb_routing_strategy), i))

    logger.info("Applying routes")

    # sort by (prio, level)
    for strategy, level in sorted(
        strategies, key=lambda x: (x[0].priority, x[1]), reverse=True
    ):
        logger.debug(f"{strategy} | {level=}")

        routes = strategy.calculate(transformer)
        for route in routes:
            apply_route_in_pcb(route, transformer)


def apply_design(
    pcb_path: Path,
    netlist_path: Path,
    G: Graph,
    app: Module,
    transform: Callable[[PCB_Transformer], Any] | None = None,
):
    resolve_dynamic_parameters(G)

    logger.info(f"Writing netlist to {netlist_path}")
    changed = write_netlist(G, netlist_path, use_kicad_designators=True)
    apply_netlist(pcb_path, netlist_path, changed)

    logger.info("Load PCB")
    pcb = C_kicad_pcb_file.loads(pcb_path)

    transformer = PCB_Transformer(pcb.kicad_pcb, G, app)

    logger.info("Transform PCB")
    if transform:
        transform(transformer)

    # set layout
    apply_layouts(app)
    transformer.move_footprints()
    apply_routing(app, transformer)

    logger.info(f"Writing pcbfile {pcb_path}")
    pcb.dumps(pcb_path)

    print("Reopen PCB in kicad")
    if PCBNEW_AUTO:
        try:
            open_pcb(pcb_path)
        except FileNotFoundError:
            print(f"PCB location: {pcb_path}")
        except RuntimeError as e:
            print(f"{e.args[0]}\nReload pcb manually by pressing Ctrl+O; Enter")
    else:
        print(f"PCB location: {pcb_path}")


def include_footprints(pcb_path: Path):
    fplibpath = pcb_path.parent / "fp-lib-table"
    if fplibpath.exists():
        fptable = C_kicad_fp_lib_table_file.loads(fplibpath)
    else:
        fptable = C_kicad_fp_lib_table_file(
            C_kicad_fp_lib_table_file.C_fp_lib_table(version=7, libs=[])
        )

    # TODO make more generic, this is very lcsc specific
    from faebryk.libs.picker.lcsc import LIB_FOLDER as LCSC_LIB_FOLDER

    fppath = LCSC_LIB_FOLDER / "footprints/lcsc.pretty"
    relative = True
    try:
        fppath_rel = fppath.resolve().relative_to(
            pcb_path.parent.resolve(), walk_up=True
        )
        # check if not going up too much
        if len([part for part in fppath_rel.parts if part == ".."]) > 5:
            raise ValueError()
        fppath = fppath_rel
    except ValueError:
        relative = False

    uri = str(fppath)
    if relative:
        assert not uri.startswith("/")
        assert not uri.startswith("${KIPRJMOD}")
        uri = "${KIPRJMOD}/" + uri

    if not any(fplib.name == "lcsc" for fplib in fptable.fp_lib_table.libs):
        fptable.fp_lib_table.libs.append(
            C_kicad_fp_lib_table_file.C_fp_lib_table.C_lib(
                name="lcsc",
                type="KiCad",
                uri=uri,
                options="",
                descr="FBRK: LCSC footprints auto-downloaded",
            )
        )
        logger.warning(
            "Changed fp-lib-table to include lcsc library, need to restart pcbnew"
        )

    fptable.dumps(fplibpath)


def find_pcbnew() -> os.PathLike:
    """Figure out what to call for the pcbnew CLI."""
    if sys.platform.startswith("linux"):
        return "pcbnew"

    if sys.platform.startswith("darwin"):
        base = Path("/Applications/KiCad/")
    elif sys.platform.startswith("win"):
        base = Path(os.getenv("ProgramFiles")) / "KiCad"
    else:
        raise NotImplementedError(f"Unsupported platform: {sys.platform}")

    if path := list(base.glob("**/pcbnew")):
        # TODO: find the best version
        return path[0]

    raise FileNotFoundError("Could not find pcbnew executable")


def open_pcb(pcb_path: os.PathLike):
    import subprocess

    pcbnew = find_pcbnew()

    # Check if pcbnew is already running with this pcb
    for process in psutil.process_iter(["name", "cmdline"]):
        if process.info["name"] and "pcbnew" in process.info["name"].lower():
            if process.info["cmdline"] and str(pcb_path) in process.info["cmdline"]:
                raise RuntimeError(f"PCBnew is already running with {pcb_path}")

    subprocess.Popen([str(pcbnew), str(pcb_path)], stderr=subprocess.DEVNULL)


def apply_netlist(pcb_path: Path, netlist_path: Path, netlist_has_changed: bool = True):
    from faebryk.exporters.pcb.kicad.pcb import PCB

    include_footprints(pcb_path)

    # Set netlist path in gui menu
    prj_path = pcb_path.with_suffix(".kicad_pro")
    if not prj_path.exists():
        project = C_kicad_project_file()
    else:
        project = C_kicad_project_file.loads(prj_path)
    project.pcbnew.last_paths.netlist = str(
        netlist_path.resolve().relative_to(pcb_path.parent.resolve(), walk_up=True)
    )
    project.dumps(prj_path)

    # Import netlist into pcb
    logger.info(f"Apply netlist to {pcb_path}")
    PCB.apply_netlist(pcb_path, netlist_path)
