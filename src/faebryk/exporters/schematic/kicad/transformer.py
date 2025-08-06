# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
import pprint
from copy import deepcopy
from functools import singledispatch
from itertools import chain
from os import PathLike
from pathlib import Path
from typing import Any, List, Protocol

# import numpy as np
# from shapely import Polygon
import faebryk.library._F as F
from faebryk.core.graph import Graph, GraphFunctions
from faebryk.core.module import Module
from faebryk.core.node import Node
from faebryk.libs.exceptions import UserException
from faebryk.libs.geometry.basic import Geometry
from faebryk.libs.kicad.fileformats_common import C_effects, C_pts, C_wh, C_xy, C_xyr
from faebryk.libs.kicad.fileformats_common import (
    gen_uuid as _gen_uuid,
)
from faebryk.libs.kicad.fileformats_latest import (
    C_kicad_fp_lib_table_file,
)
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
    C_symbol,
)
from faebryk.libs.kicad.paths import GLOBAL_FP_DIR_PATH, GLOBAL_FP_LIB_PATH
from faebryk.libs.sexp.dataclass_sexp import visit_dataclass
from faebryk.libs.util import (
    cast_assert,
    find,
    get_key,
    groupby,
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


def gen_uuid(mark: str = "") -> UUID:
    return _gen_uuid(mark)


def is_marked(uuid: UUID, mark: str):
    suffix = mark.encode().hex()
    return uuid.replace("-", "").endswith(suffix)


class _HasUUID(Protocol):
    uuid: UUID


# TODO: consider common transformer base
class SchTransformer:
    class has_linked_sch_symbol(Module.TraitT):
        symbol: SCH.C_symbol_instance

    class has_linked_sch_symbol_defined(has_linked_sch_symbol.impl()):
        def __init__(self, symbol: SCH.C_symbol_instance) -> None:
            super().__init__()
            self.symbol = symbol

    class has_linked_pins(F.Symbol.Pin.TraitT):
        pins: list[SCH.C_symbol_instance.C_pin]

    class has_linked_pins_defined(has_linked_pins.impl()):
        def __init__(
            self,
            pins: list[SCH.C_symbol_instance.C_pin],
        ) -> None:
            super().__init__()
            self.pins = pins

    def __init__(
        self, sch: SCH, graph: Graph, app: Module, cleanup: bool = True
    ) -> None:
        self.sch = sch
        self.graph = graph
        self.app = app
        self._symbol_files_index: dict[str, Path] = {}

        self.missing_lib_symbols: list[C_symbol] = []

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
        for node, sym_trait in GraphFunctions(self.graph).nodes_with_trait(
            F.Symbol.has_symbol
        ):
            # FIXME: I believe this trait is used as a proxy for being a component
            # since, names are replaced with designators during typical pipelines
            if not node.has_trait(F.has_overriden_name):
                continue

            symbol = sym_trait.reference

            if not symbol.has_trait(F.Symbol.has_kicad_symbol):
                continue

            sym_ref = node.get_trait(F.has_overriden_name).get_name()
            sym_name = symbol.get_trait(F.Symbol.has_kicad_symbol).symbol_name

            try:
                sym = symbols[(sym_ref, sym_name)]
            except KeyError:
                # TODO: add diag
                self.missing_lib_symbols.append(symbol)
                continue

            self.attach_symbol(node, sym)

        # Log what we were able to attach
        attached = {
            n: t.symbol
            for n, t in GraphFunctions(self.graph).nodes_with_trait(
                SchTransformer.has_linked_sch_symbol
            )
        }
        logger.debug(f"Attached: {pprint.pformat(attached)}")

        if self.missing_lib_symbols:
            # TODO: just go look for the symbols instead
            raise ExceptionGroup(
                "Missing lib symbols",
                [
                    f"Symbol {sym.name} not found in symbols dictionary"
                    for sym in self.missing_lib_symbols
                ],
            )

    def attach_symbol(self, node: Node, symbol: SCH.C_symbol_instance):
        """Bind the module and symbol together on the graph"""
        graph_sym = node.get_trait(F.Symbol.has_symbol).reference

        graph_sym.add(self.has_linked_sch_symbol_defined(symbol))

        # Attach the pins on the symbol to the module interface
        for pin_name, pins in groupby(symbol.pins, key=lambda p: p.name).items():
            graph_sym.pins[pin_name].add(SchTransformer.has_linked_pins_defined(pins))

    def cleanup(self):
        """Delete faebryk-created objects in schematic."""

        # find all objects with path_len 2 (direct children of a list in pcb)
        candidates = [
            o.value for o in visit_dataclass(self.sch) if len(o.value[1]) == 2
        ]
        for obj, path, _ in candidates:
            if not self.is_marked(obj):
                continue

            # delete object by removing it from the container they are in
            holder = path[-1]
            if isinstance(holder, list):
                holder.remove(obj)
            elif isinstance(holder, dict):
                del holder[get_key(obj, holder)]

    def index_symbol_files(
        self, fp_lib_tables: PathLike | list[PathLike], load_globals: bool = True
    ) -> None:
        if isinstance(fp_lib_tables, (str, Path)):
            fp_lib_table_paths = [Path(fp_lib_tables)]
        else:
            assert isinstance(fp_lib_tables, list)
            fp_lib_table_paths = [Path(p) for p in fp_lib_tables]

        # non-local lib, search in kicad global lib
        if load_globals:
            fp_lib_table_paths += [GLOBAL_FP_LIB_PATH]

        for lib_path in fp_lib_table_paths:
            for lib in C_kicad_fp_lib_table_file.loads(
                lib_path
            ).fp_lib_table.libs.values():
                resolved_lib_dir = Path(
                    str(lib.uri)
                    .replace("${KIPRJMOD}", str(lib_path.parent))
                    .replace("${KICAD9_FOOTPRINT_DIR}", str(GLOBAL_FP_DIR_PATH))
                )
                for path in resolved_lib_dir.glob("*.kicad_sym"):
                    if path.stem not in self._symbol_files_index:
                        self._symbol_files_index[path.stem] = path

    @staticmethod
    def flipped[T](input_list: list[tuple[T, int]]) -> list[tuple[T, int]]:
        return [(x, (y + 180) % 360) for x, y in reversed(input_list)]

    @staticmethod
    def gen_uuid(mark: bool = False):
        return gen_uuid(mark="FBRK" if mark else "")

    @staticmethod
    def is_marked(obj) -> bool:
        if not hasattr(obj, "uuid"):
            return False
        return is_marked(obj.uuid, "FBRK")

    # Getter ---------------------------------------------------------------------------
    @staticmethod
    def get_symbol(cmp: Node) -> F.Symbol:
        return not_none(cmp.get_trait(SchTransformer.has_linked_sch_symbol)).symbol

    def get_all_symbols(self) -> List[tuple[Module, F.Symbol]]:
        return [
            (cast_assert(Module, cmp), t.symbol)
            for cmp, t in GraphFunctions(self.graph).nodes_with_trait(
                SchTransformer.has_linked_sch_symbol
            )
        ]

    @once
    def get_symbol_file(self, lib_name: str) -> C_kicad_sym_file:
        # primary caching handled by @once
        if lib_name not in self._symbol_files_index:
            raise UserException(f"Symbol file {lib_name} not found")

        path = self._symbol_files_index[lib_name]
        return C_kicad_sym_file.loads(path)

    @staticmethod
    def get_related_lib_sym_units(
        lib_sym: C_symbol,
    ) -> dict[int, list[C_symbol.C_symbol]]:
        """
        Figure out units.
        This seems to be purely based on naming convention.
        There are two suffixed numbers on the end eg. _0_0, _0_1
        They're in two sets of groups:
            1. subunit. used to represent graphical vs. pin objects within a unit
            2. unit. eg, a single op-amp in a package with 4
        We need to lump the subunits together for further processing.

        That is, we group them by the last number.
        """
        groups = groupby(lib_sym.symbols.items(), key=lambda item: int(item[0][-1]))
        return {k: [v[1] for v in vs] for k, vs in groups.items()}

    @singledispatch
    def get_lib_symbol(self, sym) -> C_symbol:
        raise NotImplementedError(f"Don't know how to get lib symbol for {type(sym)}")

    @get_lib_symbol.register
    def _(self, sym: F.Symbol) -> C_symbol:
        lib_id = sym.get_trait(F.Symbol.has_kicad_symbol).symbol_name
        return self._ensure_lib_symbol(lib_id)

    @get_lib_symbol.register
    def _(self, sym: SCH.C_symbol_instance) -> C_symbol:
        return self.sch.lib_symbols.symbols[sym.lib_id]

    @singledispatch
    def get_lib_pin(self, pin) -> C_symbol.C_symbol.C_pin:
        raise NotImplementedError(f"Don't know how to get lib pin for {type(pin)}")

    @get_lib_pin.register
    def _(self, pin: F.Symbol.Pin) -> C_symbol.C_symbol.C_pin:
        graph_symbol, _ = not_none(pin.get_parent())
        assert isinstance(graph_symbol, Node)
        lib_sym = self.get_lib_symbol(graph_symbol)
        units = self.get_related_lib_sym_units(lib_sym)
        sym = graph_symbol.get_trait(SchTransformer.has_linked_sch_symbol).symbol

        def _name_filter(sch_pin: C_symbol.C_symbol.C_pin):
            return sch_pin.name in {
                p.name for p in pin.get_trait(self.has_linked_pins).pins
            }

        lib_pin = find(
            chain.from_iterable(u.pins for u in units[sym.unit]),
            _name_filter,
        )
        return lib_pin

    # Insert ---------------------------------------------------------------------------
    @staticmethod
    def mark[R: _HasUUID](node: R) -> R:
        if hasattr(node, "uuid"):
            node.uuid = SchTransformer.gen_uuid(mark=True)  # type: ignore

        return node

    def _get_list_field[R](self, node: R, prefix: str = "") -> list[R]:
        root = self.sch
        key = prefix + type(node).__name__.removeprefix("C_") + "s"

        assert hasattr(root, key)

        target = getattr(root, key)
        assert isinstance(target, list)
        assert all(isinstance(x, type(node)) for x in target)
        return target

    def _insert(self, obj: Any, prefix: str = ""):
        obj = SchTransformer.mark(obj)
        self._get_list_field(obj, prefix=prefix).append(obj)

    def _delete(self, obj: Any, prefix: str = ""):
        self._get_list_field(obj, prefix=prefix).remove(obj)

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
                    justifys=[C_effects.C_justify(list(alignment))]
                    if alignment
                    else [],
                ),
                uuid=self.gen_uuid(mark=True),
            )
        )

    def _ensure_lib_symbol(
        self,
        lib_id: str,
    ) -> C_symbol:
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
        for unit_key, unit_objs in self.get_related_lib_sym_units(lib_sym).items():
            pins = []

            for subunit in unit_objs:
                for pin in subunit.pins:
                    pins.append(
                        SCH.C_symbol_instance.C_pin(
                            name=pin.name.name,
                            uuid=self.gen_uuid(mark=True),
                        )
                    )

            unit_instance = SCH.C_symbol_instance(
                lib_id=lib_id,
                unit=unit_key + 1,  # yes, these are indexed from 1...
                at=C_xyr(at[0], at[1], rotation),
                in_bom=True,
                on_board=True,
                pins=pins,
                uuid=self.gen_uuid(mark=True),
            )

            # Add a C_property for the reference based on the override name
            if reference_name := module.get_trait(F.has_overriden_name).get_name():
                unit_instance.propertys["Reference"] = C_property(
                    name="Reference",
                    value=reference_name,
                )
            else:
                # TODO: handle not having an overriden name better
                raise Exception(f"Module {module} has no overriden name")

            self.attach_symbol(module, unit_instance)

            self.sch.symbols.append(unit_instance)
