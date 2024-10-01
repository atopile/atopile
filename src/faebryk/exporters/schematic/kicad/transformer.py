# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import hashlib
import logging
import pprint
from copy import deepcopy
from functools import singledispatchmethod
from itertools import chain, groupby
from os import PathLike
from pathlib import Path
from typing import Any, List, Protocol, Unpack

import rich
import rich.table

import faebryk.library._F as F
from faebryk.core.graphinterface import Graph
from faebryk.core.module import Module
from faebryk.core.node import Node

# import numpy as np
# from shapely import Polygon
from faebryk.exporters.pcb.kicad.transformer import is_marked
from faebryk.exporters.schematic.kicad.skidl import shims
from faebryk.libs.exceptions import FaebrykException
from faebryk.libs.geometry.basic import Geometry
from faebryk.libs.kicad.fileformats import (
    C_kicad_fp_lib_table_file,
)
from faebryk.libs.kicad.fileformats import (
    gen_uuid as _gen_uuid,
)
from faebryk.libs.kicad.fileformats_common import C_effects, C_pts, C_wh, C_xy, C_xyr
from faebryk.libs.kicad.fileformats_sch import (
    UUID,
    C_arc,
    C_circle,
    C_kicad_sch_file,
    C_kicad_sym_file,
    C_polyline,
    C_property,
    C_rect,
    C_stroke,
)
from faebryk.libs.kicad.paths import GLOBAL_FP_DIR_PATH, GLOBAL_FP_LIB_PATH
from faebryk.libs.sexp.dataclass_sexp import dataclass_dfs
from faebryk.libs.util import (
    FuncDict,
    KeyErrorNotFound,
    cast_assert,
    find,
    not_none,
    once,
)

logger = logging.getLogger(__name__)


SCH = C_kicad_sch_file.C_kicad_sch

Geom = C_polyline | C_arc | C_rect | C_circle
Font = C_effects.C_font

Point = Geometry.Point
Point2D = Geometry.Point2D

Justify = C_effects.C_justify.E_justify
Alignment = tuple[Justify, Justify, Justify]
Alignment_Default = (Justify.center_horizontal, Justify.center_vertical, Justify.normal)


class _HasUUID(Protocol):
    uuid: UUID


class _HasPropertys(Protocol):
    propertys: dict[str, C_property]


# TODO: consider common transformer base
class Transformer:

    class has_linked_sch_symbol(F.Symbol.TraitT.decless()):
        def __init__(self, symbol: SCH.C_symbol_instance) -> None:
            super().__init__()
            self.symbol = symbol

    class has_linked_sch_pins(F.Symbol.Pin.TraitT.decless()):
        def __init__(
            self,
            pins: list[SCH.C_symbol_instance.C_pin],
            symbol: SCH.C_symbol_instance,
        ) -> None:
            super().__init__()
            self.symbol = symbol
            self.pins = pins

    def __init__(
        self, sch: SCH, graph: Graph, app: Module, cleanup: bool = True
    ) -> None:
        self.sch = sch
        self.graph = graph
        self.app = app
        self._symbol_files_index: dict[str, Path] = {}

        self.missing_symbols: list[F.Symbol] = []

        self.dimensions = None

        FONT_SCALE = 8
        FONT = Font(
            size=C_wh(1 / FONT_SCALE, 1 / FONT_SCALE),
            thickness=0.15 / FONT_SCALE,
        )
        self.font = FONT

        # TODO: figure out what to do with cleanup
        # self.cleanup()
        self.attach()

    def attach(self):
        """This function matches and binds symbols to their symbols"""
        # reference (eg. C3) to symbol (eg. "Capacitor_SMD:C_0402")
        symbols = {
            (f.propertys["Reference"].value, f.lib_id): f for f in self.sch.symbols
        }
        for node, sym_trait in self.graph.nodes_with_trait(F.Symbol.has_symbol):
            if not node.has_trait(F.has_overriden_name):
                continue

            symbol = sym_trait.reference

            if not symbol.has_trait(F.Symbol.has_kicad_symbol):
                continue

            sym_ref = node.get_trait(F.has_overriden_name).get_name()
            sym_name = symbol.get_trait(F.Symbol.has_kicad_symbol).symbol_name

            if (sym_ref, sym_name) not in symbols:
                self.missing_symbols.append(symbol)
                continue

            self.attach_symbol(node, symbols[(sym_ref, sym_name)])

        # Log what we were able to attach
        attached = {
            n: t.symbol
            for n, t in self.graph.nodes_with_trait(Transformer.has_linked_sch_symbol)
        }
        logger.debug(f"Attached: {pprint.pformat(attached)}")
        logger.debug(f"Missing: {pprint.pformat(self.missing_symbols)}")

    def attach_symbol(self, f_symbol: F.Symbol, sym_inst: SCH.C_symbol_instance):
        """Bind the module and symbol together on the graph"""
        f_symbol.add(self.has_linked_sch_symbol(sym_inst))

        lib_sym = self._ensure_lib_symbol(sym_inst.lib_id)
        lib_sym_units = self.get_sub_syms(lib_sym, sym_inst.unit)
        lib_sym_pins = [p for u in lib_sym_units for p in u.pins]
        pin_no_to_name = {str(pin.number.number): pin.name.name for pin in lib_sym_pins}

        # Attach the pins on the symbol to the module interface
        pin_by_name = groupby(sym_inst.pins, key=lambda p: pin_no_to_name[p.name])
        for pin_name, pins in pin_by_name:
            f_symbol.pins[pin_name].add(Transformer.has_linked_sch_pins(pins, sym_inst))

    # TODO: remove cleanup, it shouldn't really be required if we're marking propertys
    # def cleanup(self):
    #     """Delete faebryk-created objects in schematic."""

    #     # find all objects with path_len 2 (direct children of a list in pcb)
    #     candidates = [o for o in dataclass_dfs(self.sch) if len(o[1]) == 2]
    #     for obj, path, _ in candidates:
    #         if not self.check_mark(obj):
    #             continue

    #         # delete object by removing it from the container they are in
    #         holder = path[-1]
    #         if isinstance(holder, list):
    #             holder.remove(obj)
    #         elif isinstance(holder, dict):
    #             del holder[get_key(obj, holder)]

    def index_symbol_files(
        self, fp_lib_tables: PathLike | list[PathLike], load_globals: bool = True
    ) -> None:
        if isinstance(fp_lib_tables, (str, Path)):
            fp_lib_table_paths = [Path(fp_lib_tables)]
        else:
            fp_lib_table_paths = [Path(p) for p in fp_lib_tables]

        # non-local lib, search in kicad global lib
        if load_globals:
            fp_lib_table_paths += [GLOBAL_FP_LIB_PATH]

        for lib_path in fp_lib_table_paths:
            for lib in C_kicad_fp_lib_table_file.loads(lib_path).fp_lib_table.libs:
                resolved_lib_dir = Path(
                    lib.uri.replace("${KIPRJMOD}", str(lib_path.parent)).replace(
                        "${KICAD8_FOOTPRINT_DIR}", str(GLOBAL_FP_DIR_PATH)
                    )
                )
                for path in resolved_lib_dir.glob("*.kicad_sym"):
                    if path.stem not in self._symbol_files_index:
                        self._symbol_files_index[path.stem] = path

    @staticmethod
    def flipped[T](input_list: list[tuple[T, int]]) -> list[tuple[T, int]]:
        return [(x, (y + 180) % 360) for x, y in reversed(input_list)]

    # Getter ---------------------------------------------------------------------------
    @staticmethod
    def get_symbol(cmp: Node) -> F.Symbol:
        return not_none(cmp.get_trait(Transformer.has_linked_sch_symbol)).symbol

    def get_all_symbols(self) -> List[tuple[Module, F.Symbol]]:
        return [
            (cast_assert(Module, cmp), t.symbol)
            for cmp, t in self.graph.nodes_with_trait(Transformer.has_linked_sch_symbol)
        ]

    @once
    def get_symbol_file(self, lib_name: str) -> C_kicad_sym_file:
        # primary caching handled by @once
        if lib_name not in self._symbol_files_index:
            raise FaebrykException(f"Symbol file {lib_name} not found")

        path = self._symbol_files_index[lib_name]
        return C_kicad_sym_file.loads(path)

    @staticmethod
    def get_sub_syms(
        lib_sym: SCH.C_lib_symbols.C_symbol,
        unit: int | None,
        body_style: int = 1,
    ) -> list[SCH.C_lib_symbols.C_symbol.C_symbol]:
        """
        This is purely based on naming convention.
        There are two suffixed numbers on the end: <name>_<x>_<y>, eg "LED_0_1"
        The first number is the "unit" and the second is "body style"
        Index 0 for either unit or body-style indicates "draw for all"

        References:
        - ^1 Parser:
            https://gitlab.com/kicad/code/kicad/-/blob/b043f334de6183595fda935175d2e2635daa379c/eeschema/sch_io/kicad_sexpr/sch_io_kicad_sexpr_parser.cpp#L455-476
        - ^2 Note on unit index meanings:
            https://gitlab.com/kicad/code/kicad/-/blob/2c99bc6c6d0f548f590d4681e20868e8ddb5b9c7/eeschema/eeschema_jobs_handler.cpp#L702
        """

        # kept body_style as an arg because I expect it will come up sooner than I like
        # apparently body_style == 2 is comes from some option "de morgen?"
        # don't need it now, but leaving this here for some poor sod later
        if body_style != 1:
            raise NotImplementedError("Only body style 1 is supported")

        sub_syms: list[SCH.C_lib_symbols.C_symbol.C_symbol] = []
        for name, sym in lib_sym.symbols.items():
            _, sub_sym_unit, sub_sym_body_style = name.split("_")
            sub_sym_unit = int(sub_sym_unit)
            sub_sym_body_style = int(sub_sym_body_style)

            if sub_sym_unit == unit or sub_sym_unit == 0 or unit is None:
                if sub_sym_body_style == body_style or sub_sym_body_style == 0:
                    sub_syms.append(sym)

        return sub_syms

    @staticmethod
    def get_unit_count(lib_sym: SCH.C_lib_symbols.C_symbol) -> int:
        return max(int(name.split("_")[1]) for name in lib_sym.symbols.keys())

    # TODO: remove
    # @singledispatchmethod
    # def get_lib_pin(self, pin) -> SCH.C_lib_symbols.C_symbol.C_symbol.C_pin:
    #     raise NotImplementedError(f"Don't know how to get lib pin for {type(pin)}")

    # @get_lib_pin.register
    # def _(self, pin: F.Symbol.Pin) -> SCH.C_lib_symbols.C_symbol.C_symbol.C_pin:
    #     graph_symbol, _ = pin.get_parent()
    #     assert isinstance(graph_symbol, Node)
    #     lib_sym = self.get_lib_syms(graph_symbol)
    #     units = self.get_lib_syms(lib_sym)
    #     sym = graph_symbol.get_trait(Transformer.has_linked_sch_symbol).symbol

    #     def _name_filter(sch_pin: SCH.C_lib_symbols.C_symbol.C_symbol.C_pin):
    #         return sch_pin.name in {
    #             p.name for p in pin.get_trait(self.has_linked_sch_pins).pins
    #         }

    #     lib_pin = find(
    #         chain.from_iterable(u.pins for u in units[sym.unit]),
    #         _name_filter,
    #     )
    #     return lib_pin

    # Marking -------------------------------------------------------------------------
    """
    There are two methods to mark objects in the schematic:
    1. For items with propertys, add a property with a hash of the contents of
        itself, minus the mark property. This is used to detect changes to things
        such as position that the user may have nudged externally.
    2. For items without propertys, generate the uuid with the mark.

    Anything generated by this transformer is marked.
    """

    @staticmethod
    def gen_uuid(mark: bool = False) -> UUID:
        return _gen_uuid(mark="FBRK" if mark else "")

    @staticmethod
    def is_uuid_marked(obj) -> bool:
        if not hasattr(obj, "uuid"):
            return False
        assert isinstance(obj.uuid, str)
        suffix = "FBRK".encode().hex()
        return obj.uuid.replace("-", "").endswith(suffix)

    @staticmethod
    def hash_contents(obj) -> str:
        """Hash the contents of an object, minus the mark"""

        # filter out mark properties
        def _filter(k: tuple[Any, list[Any], list[str]]) -> bool:
            obj, _, _ = k
            if isinstance(obj, C_property):
                if obj.name == "faebryk_mark":
                    return False
            return True

        hasher = hashlib.blake2b()
        for obj, _, name_path in filter(_filter, dataclass_dfs(obj)):
            hasher.update(f"{name_path}={obj}".encode())

        return hasher.hexdigest()

    @staticmethod
    def check_mark(obj) -> bool:
        """Return True if an object is validly marked"""
        if hasattr(obj, "propertys"):
            if "faebryk_mark" in obj.propertys:
                prop = obj.propertys["faebryk_mark"]
                assert isinstance(prop, C_property)
                return prop.value == Transformer.hash_contents(obj)
            else:
                # items that have the capacity to be marked
                # via propertys are only considered marked
                # if they have the property and it's valid,
                # despite their uuid
                return False

        return Transformer.is_uuid_marked(obj)

    @staticmethod
    def mark[R: _HasUUID | _HasPropertys](obj: R) -> R:
        """Mark the property if possible, otherwise ensure the uuid is marked"""
        if hasattr(obj, "propertys"):
            obj.propertys["faebryk_mark"] = C_property(
                name="faebryk_mark",
                value=Transformer.hash_contents(obj),
            )

        else:
            if not hasattr(obj, "uuid"):
                raise TypeError(f"Object {obj} has no propertys or uuid")

            if not is_marked(obj):
                obj.uuid = Transformer.gen_uuid(mark=True)

        return obj

    # Insert ---------------------------------------------------------------------------

    def insert_wire(
        self,
        coords: list[Geometry.Point2D],
        stroke: C_stroke | None = None,
    ):
        """Insert a wire with points at all the coords"""
        for section in zip(coords[:-1], coords[1:]):
            self.sch.wires.append(
                SCH.C_wire(
                    pts=C_pts(xys=[C_xy(*coord) for coord in section]),
                    stroke=stroke or C_stroke(),
                )
            )

    def insert_text(
        self,
        text: str,
        at: C_xyr,
        font: Font,
        alignment: Alignment | None = None,
    ):
        self.sch.texts.append(
            SCH.C_text(
                text=text,
                at=at,
                effects=C_effects(
                    font=font,
                    justify=alignment,
                ),
                uuid=self.gen_uuid(mark=True),
            )
        )

    def _ensure_lib_symbol(
        self,
        lib_id: str,
    ) -> SCH.C_lib_symbols.C_symbol:
        """Ensure a symbol is in the schematic library, and return it"""
        if lib_id in self.sch.lib_symbols.symbols:
            return self.sch.lib_symbols.symbols[lib_id]

        lib_name, symbol_name = lib_id.split(":")
        lib_sym = deepcopy(
            self.get_symbol_file(lib_name).kicad_symbol_lib.symbols[symbol_name]
        )
        lib_sym.name = lib_id
        self.sch.lib_symbols.symbols[lib_id] = lib_sym
        return lib_sym

    def insert_symbol(
        self,
        module: Module,
        at: Point2D | None = None,
        rotation: int | None = None,
    ):
        if at is None:
            at = (0, 0)

        if rotation is None:
            rotation = 0

        # Symbols are attached to modules earlier in the pipeline
        # Typically, by the picker (lcsc.py), but plausibly by a library component
        symbol = module.get_trait(F.Symbol.has_symbol).reference

        # Ensure lib symbol is in sch
        lib_id = symbol.get_trait(F.Symbol.has_kicad_symbol).symbol_name
        lib_sym = self._ensure_lib_symbol(lib_id)

        # insert all units
        if self.get_unit_count(lib_sym) > 1:
            # problems today:
            # - F.Symbol -> Module mapping
            # - has_linked_sch_symbol mapping is currently 1:1
            # - has_kicad_symbol mapping is currently 1:1
            raise NotImplementedError("Multiple units not implemented")

        for unit_key in range(self.get_unit_count(lib_sym)):
            unit_objs = self.get_sub_syms(lib_sym, unit_key)

            pins = []
            for subunit in unit_objs:
                for pin in subunit.pins:
                    pins.append(
                        SCH.C_symbol_instance.C_pin(
                            name=pin.number.number,
                            uuid=self.gen_uuid(mark=True),
                        )
                    )

            unit_instance = SCH.C_symbol_instance(
                lib_id=lib_id,
                unit=unit_key,
                at=C_xyr(at[0], at[1], rotation),
                in_bom=True,
                on_board=True,
                pins=pins,
                uuid=self.gen_uuid(mark=True),
            )

            # It's one of ours, until it's modified in KiCAD
            Transformer.mark(unit_instance)

            # Add a C_property for the reference based on the override name
            if reference_name := module.get_trait(F.has_overriden_name).get_name():
                unit_instance.propertys["Reference"] = C_property(
                    name="Reference",
                    value=reference_name,
                )
            else:
                # TODO: handle not having an overriden name better
                raise Exception(f"Module {module} has no overriden name")

            self.attach_symbol(symbol, unit_instance)

            self.sch.symbols.append(unit_instance)

    # Bounding boxes ----------------------------------------------------------------
    type BoundingBox = tuple[Geometry.Point2D, Geometry.Point2D]

    @singledispatchmethod
    @staticmethod
    def get_bbox(obj) -> BoundingBox | None:
        """
        Get the bounding box of the object in it's reference frame
        This means that for things like pins, which know their own position,
        the bbox returned will include the offset of the pin.
        """
        raise NotImplementedError(f"Don't know how to get bbox for {type(obj)}")

    @get_bbox.register
    @staticmethod
    def _(obj: C_arc) -> BoundingBox:
        return Geometry.bbox(
            list(
                chain.from_iterable(
                    Geometry.approximate_arc(
                        (obj.start.x, obj.start.y),
                        (obj.mid.x, obj.mid.y),
                        (obj.end.x, obj.end.y),
                    )
                )
            ),
            tolerance=obj.stroke.width,
        )

    @get_bbox.register
    @staticmethod
    def _(obj: C_polyline) -> BoundingBox | None:
        if len(obj.pts.xys) == 0:
            return None

        return Geometry.bbox(
            [(pt.x, pt.y) for pt in obj.pts.xys],
            tolerance=obj.stroke.width,
        )

    @get_bbox.register
    @staticmethod
    def _(obj: C_rect) -> BoundingBox | None:
        return Geometry.bbox(
            [
                (obj.start.x, obj.start.y),
                (obj.end.x, obj.end.y),
            ],
            tolerance=obj.stroke.width,
        )

    @get_bbox.register
    @staticmethod
    def _(obj: C_circle) -> BoundingBox:
        radius = Geometry.distance_euclid(obj.center, obj.end)
        return Geometry.bbox(
            (obj.center.x - radius, obj.center.y - radius),
            (obj.center.x + radius, obj.center.y + radius),
            tolerance=obj.stroke.width,
        )

    @get_bbox.register
    @staticmethod
    def _(obj: SCH.C_lib_symbols.C_symbol.C_symbol.C_pin) -> BoundingBox:
        # TODO: include the name and number in the bbox
        start = (obj.at.x, obj.at.y)
        end = Geometry.rotate(start, [(obj.at.x + obj.length, obj.at.y)], obj.at.r)[0]
        return Geometry.bbox([start, end])

    @get_bbox.register
    @classmethod
    def _(cls, obj: SCH.C_lib_symbols.C_symbol.C_symbol) -> BoundingBox | None:
        all_geos = list(
            chain(
                obj.arcs,
                obj.polylines,
                obj.circles,
                obj.rectangles,
                obj.pins,
            )
        )

        bboxes = []
        for geo in all_geos:
            if (new_bboxes := cls.get_bbox(geo)) is not None:
                bboxes.extend(new_bboxes)

        if len(bboxes) == 0:
            return None

        return Geometry.bbox(bboxes)

    @get_bbox.register
    @classmethod
    def _(cls, obj: SCH.C_lib_symbols.C_symbol) -> BoundingBox:
        sub_points = list(
            chain.from_iterable(
                bboxes
                for unit in obj.symbols.values()
                if (bboxes := cls.get_bbox(unit)) is not None
            )
        )
        assert len(sub_points) > 0
        return Geometry.bbox(sub_points)

    @get_bbox.register
    @classmethod
    def _(cls, obj: list) -> BoundingBox:
        return Geometry.bbox(
            list(chain.from_iterable(cls.get_bbox(item) for item in obj))
        )

    def _add_missing_symbols(self):
        """
        Add symbols to the schematic that are missing based on the fab graph
        """
        for f_symbol in self.missing_symbols:
            self.insert_symbol(f_symbol)
        self.missing_symbols = []

    def _build_shim_circuit(self) -> shims.Circuit:
        """Does what it says on the tin."""
        from faebryk.exporters.schematic.kicad.skidl.geometry import BBox, Point

        # 1.1 create hollow circuits to append to
        circuit = shims.Circuit()
        circuit.parts = []
        circuit.nets = []

        # 1.2 create maps to short-cut access between fab and sch
        sch_to_fab_pin_map: FuncDict[
            SCH.C_symbol_instance.C_pin, F.Symbol.Pin | None
        ] = FuncDict()
        sch_to_fab_sym_map: FuncDict[SCH.C_symbol_instance, F.Symbol | None] = (
            FuncDict()
        )
        # for each sch_symbol / (fab_symbol | None) pair, create a shim part
        # we need to shim sym object which aren't even in the graph to avoid colliding
        for _, f_sym_trait in self.graph.nodes_with_trait(F.Symbol.has_symbol):
            if sch_sym_trait := f_sym_trait.reference.try_get_trait(
                Transformer.has_linked_sch_symbol
            ):
                sch_to_fab_sym_map[sch_sym_trait.symbol] = f_sym_trait.reference
        for sch_sym in self.sch.symbols:
            f_symbol = sch_to_fab_sym_map.setdefault(sch_sym, None)
            for sch_pin in sch_sym.pins:
                sch_to_fab_pin_map[sch_pin] = (
                    f_symbol.pins.get(sch_pin.name) if f_symbol else None
                )

        # 2. create shim objects
        # 2.1 make nets
        sch_to_shim_pin_map: FuncDict[SCH.C_symbol_instance.C_pin, shims.Pin] = (
            FuncDict()
        )
        fab_nets = self.graph.nodes_of_type(F.Net)
        for net in fab_nets:
            shim_net = shims.Net()
            shim_net.name = net.get_trait(F.has_overriden_name).get_name()
            shim_net.netio = ""  # TODO:
            shim_net.stub = False  # TODO:

            # make partial net-oriented pins
            shim_net.pins = []
            for mif in net.get_connected_interfaces():
                if has_fab_pin := mif.try_get_trait(F.Symbol.Pin.has_pin):
                    if has_sch_pin := has_fab_pin.reference.try_get_trait(
                        Transformer.has_linked_sch_pins
                    ):
                        for sch_pin in has_sch_pin.pins:
                            shim_pin = shims.Pin()
                            shim_pin.net = shim_net
                            shim_net.pins.append(shim_pin)
                            sch_to_shim_pin_map[sch_pin] = shim_pin

            # set is_connected for all pins on net if len(net.pins) > 0
            is_connected = len(shim_net.pins) > 0
            for pin in shim_net.pins:
                pin._is_connected = is_connected

            circuit.nets.append(shim_net)

        # 2.2 make parts
        def _hierarchy(module: Module) -> str:
            """
            Make a string representation of the module's hierarchy
            using the best name for each part we have
            """

            def _best_name(module: Module) -> str:
                if name_trait := module.try_get_trait(F.has_overriden_name):
                    return name_trait.get_name()
                return module.get_name()

            # skip the root module, because it's name is just "*"
            hierarchy = [h[0] for h in module.get_hierarchy()][1:]
            return ".".join(_best_name(n) for n in hierarchy)

        # for each sch_symbol, create a shim part
        for sch_sym, f_symbol in sch_to_fab_sym_map.items():
            lib_sym = self._ensure_lib_symbol(sch_sym.lib_id)
            sch_lib_symbol_units = self.get_sub_syms(lib_sym, sch_sym.unit)
            shim_part = shims.Part()
            shim_part.ref = sch_sym.propertys["Reference"].value
            # if we don't have a fab symbol, place the part at the top of the hierarchy
            shim_part.hierarchy = (
                _hierarchy(f_symbol.represents) if f_symbol else shim_part.ref
            )
            # TODO: what's the ato analog?
            # TODO: should this desc
            shim_part.symtx = ""
            shim_part.unit = {}  # TODO: support units
            shim_part.fab_symbol = f_symbol
            shim_part.bare_bbox = BBox(
                *[Point(*pts) for pts in Transformer.get_bbox(sch_lib_symbol_units)]
            )
            shim_part.pins = []

            # 2.3 finish making pins, this time from a part-orientation
            all_sch_lib_pins = [p for u in sch_lib_symbol_units for p in u.pins]

            # if logger.isEnabledFor(logging.DEBUG): # TODO: enable
            rich.print(
                f"Symbol {sch_sym.propertys['Reference'].value=} {sch_sym.uuid=}"
            )
            pins = rich.table.Table("pin.name=", "pin.number=")
            for pin in all_sch_lib_pins:
                pins.add_row(pin.name.name, pin.number.number)
            rich.print(pins)

            for sch_pin in sch_sym.pins:
                rich.print(f"Pin {sch_pin.name=}")
                try:
                    lib_sch_pin = find(
                        all_sch_lib_pins,
                        lambda x: str(x.number.number) == str(sch_pin.name),
                    )
                except KeyErrorNotFound:
                    # KiCAD seems to make a full duplication of all the symbol objects
                    # despite not displaying them unless they're relevant to the current
                    # unit. Do our best to make sure it's at least a pin the symbol
                    # overall has (ignoring the unit)
                    lib_sym_pins_all_units = [
                        p.number.number
                        for sym in self.get_sub_syms(lib_sym, None)
                        for p in sym.pins
                    ]
                    if sch_pin.name in lib_sym_pins_all_units:
                        continue
                    raise ValueError(
                        f"Pin {sch_pin.name} not found in any unit of symbol {sch_sym.name}"
                    )

                assert isinstance(
                    lib_sch_pin, SCH.C_lib_symbols.C_symbol.C_symbol.C_pin
                )
                shim_pin = sch_to_shim_pin_map.setdefault(sch_pin, shims.Pin())
                shim_pin.name = sch_pin.name
                shim_pin.num = lib_sch_pin.number
                shim_pin.orientation = shims.angle_to_orientation(lib_sch_pin.at.r)
                shim_pin.part = shim_part

                # TODO: ideas:
                # - stub powery things
                # - override from symbol layout info trait
                shim_pin.stub = False

                shim_pin.x = lib_sch_pin.at.x
                shim_pin.y = lib_sch_pin.at.y
                shim_pin.fab_pin = sch_to_fab_pin_map[sch_pin]
                shim_pin.sch_pin = sch_pin

                shim_part.pins.append(shim_pin)

            circuit.parts.append(shim_part)

        # 2.4 generate similarity matrix
        def similarity(part: "shims.Part", other: "shims.Part", **options) -> float:
            """
            NOTE: Straight outta skidl
            Return a measure of how similar two parts are.

            Args:
                part (Part): The part to compare to for similarity.
                options (dict): Dictionary of options and settings affecting
                    similarity computation.

            Returns:
                Float value for similarity (larger means more similar).
            """

            def score_pins():
                pin_score = 0
                if len(part.pins) == len(other.pins):
                    for p_self, p_other in zip(part.ordered_pins, other.ordered_pins):
                        if p_self.is_attached(p_other):
                            pin_score += 1
                return pin_score

            # Every part starts off somewhat similar to another.
            score = 1

            if part.description == other.description:
                score += 5
            if part.name == other.name:
                score += 5
                if part.value == other.value:
                    score += 2
                score += score_pins()
            elif part.ref_prefix == other.ref_prefix:
                score += 3
                if part.value == other.value:
                    score += 2
                score += score_pins()

            return score / 3

        similarities: dict[tuple[int, int], float] = {}
        for part in circuit.parts:
            part._similarites = {}

            for other in circuit.parts:
                if part is other:
                    continue

                key = tuple(sorted((hash(part), hash(other))))

                if key not in similarities:
                    # TODO: actually compute similarity
                    # similarities[key] = similarity(part, other)
                    similarities[key] = 10

                part._similarites[other] = similarities[key]

        # 2.-1 run audit on circuit
        circuit.audit()
        return circuit

    def generate_schematic(self, **options: Unpack[shims.Options]):
        """Does what it says on the tin."""
        # 1. add missing symbols
        self._add_missing_symbols()

        # 2. build shim circuit
        circuit = self._build_shim_circuit()

        # 3. run skidl schematic generation
        from faebryk.exporters.schematic.kicad.skidl.gen_schematic import gen_schematic
        gen_schematic(circuit, ".", "test", **options)

        # 4. transform sch according to skidl
        # TODO:
