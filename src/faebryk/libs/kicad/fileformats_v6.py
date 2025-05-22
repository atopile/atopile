# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from dataclasses import dataclass, field

from dataclasses_json.undefined import CatchAll

from faebryk.libs.kicad.fileformats_common import C_stroke, C_xy, C_xyr
from faebryk.libs.kicad.fileformats_latest import (
    C_arc,
    C_footprint,
    C_fp_text,
    C_kicad_footprint_file,
)
from faebryk.libs.kicad.fileformats_sch import C_circle as C_symbol_Circle
from faebryk.libs.kicad.fileformats_sch import C_symbol
from faebryk.libs.kicad.fileformats_v5 import (
    C_circle_v5,
    C_line_v5,
    C_rect_v5,
)
from faebryk.libs.sexp.dataclass_sexp import SEXP_File, sexp_field

logger = logging.getLogger(__name__)


@dataclass(kw_only=True)
class C_arc_v6:
    start: C_xy
    mid: C_xy
    end: C_xy
    # instead of stroke
    width: float
    layer: str
    # no uuid

    def convert_to_new(self) -> C_arc:
        return C_arc(
            start=self.start,
            mid=self.mid,
            end=self.end,
            stroke=C_stroke(width=self.width, type=C_stroke.E_type.default),
            layer=self.layer,
        )


@dataclass(kw_only=True)
class C_fp_text_v6(C_fp_text):
    @dataclass(kw_only=True)
    class C_xyUnlocked:
        x: float = field(**sexp_field(positional=True))
        y: float = field(**sexp_field(positional=True))
        unknown: CatchAll = None

    at: C_xyUnlocked

    def convert_to_new(self) -> C_fp_text:
        return C_fp_text(
            type=self.type,
            text=self.text,
            at=C_xyr(x=self.at.x, y=self.at.y),
            layer=self.layer,
            uuid=self.uuid,
            effects=self.effects,
            # TODO its inside the at
            unlocked=False,
        )


@dataclass
class C_kicad_footprint_file_v6(SEXP_File):
    @dataclass(kw_only=True)
    class C_footprint_in_file(C_kicad_footprint_file.C_footprint_in_file):
        fp_lines: list[C_line_v5] = field(
            **sexp_field(multidict=True), default_factory=list
        )
        fp_arcs: list[C_arc_v6] = field(
            **sexp_field(multidict=True), default_factory=list
        )
        fp_circles: list[C_circle_v5] = field(
            **sexp_field(multidict=True), default_factory=list
        )
        fp_rects: list[C_rect_v5] = field(
            **sexp_field(multidict=True), default_factory=list
        )
        fp_texts: list[C_fp_text_v6] = field(
            **sexp_field(multidict=True), default_factory=list
        )

        version: int = 20211014

        def convert_to_new(self) -> C_kicad_footprint_file.C_footprint_in_file:
            propertys: dict[str, C_footprint.C_property] = {
                name: C_footprint.C_property(
                    name=name,
                    value=k.text,
                    at=C_xyr(x=k.at.x, y=k.at.y),
                    layer=k.layer,
                    uuid=k.uuid,
                    effects=k.effects,
                )
                for k in self.fp_texts
                if (name := k.type.capitalize()) in ("Reference", "Value")
            } | self.propertys

            texts = [t for t in self.fp_texts if t.type not in ("reference", "value")]
            for t in self.fp_texts:
                if t.type == "reference":
                    texts.append(
                        C_fp_text_v6(
                            type=C_fp_text.E_type.user,
                            text=t.text.replace("REF**", "${REFERENCE}"),
                            at=t.at,
                            layer=t.layer,
                            uuid=t.uuid,
                            effects=t.effects,
                        )
                    )

            return C_kicad_footprint_file.C_footprint_in_file(
                fp_lines=[line.convert_to_new() for line in self.fp_lines],
                fp_arcs=[arc.convert_to_new() for arc in self.fp_arcs],
                fp_circles=[circle.convert_to_new() for circle in self.fp_circles],
                fp_rects=[rect.convert_to_new() for rect in self.fp_rects],
                # fp-file
                tedit=self.tedit,
                descr=self.descr or "",
                tags=self.tags,
                generator="faebryk",
                generator_version="v6",
                # fp
                name=self.name,
                layer=self.layer,
                propertys=propertys,
                attr=self.attr,
                fp_texts=[t.convert_to_new() for t in texts],
                fp_poly=self.fp_poly,
                pads=self.pads,
                models=self.models,
            )

    footprint: C_footprint_in_file

    def convert_to_new(self) -> C_kicad_footprint_file:
        return C_kicad_footprint_file(footprint=self.footprint.convert_to_new())


@dataclass(kw_only=True)
class C_symbol_Circle_v6(C_symbol_Circle):
    radius: float
    end: C_xy = field(default_factory=lambda: C_xy(0, 0))

    def convert_to_new(self) -> C_symbol_Circle:
        return C_symbol_Circle(
            center=self.center,
            # TODO does this work?
            end=C_xy(self.center.x + self.radius, self.center.y),
            stroke=self.stroke,
            fill=self.fill,
        )


@dataclass(kw_only=True)
class C_symbol_symbol_v6(C_symbol.C_symbol):
    circles: list[C_symbol_Circle_v6] = field(
        **sexp_field(multidict=True), default_factory=list
    )

    def convert_to_new(self) -> C_symbol.C_symbol:
        return C_symbol.C_symbol(
            name=self.name,
            polylines=self.polylines,
            circles=[circle.convert_to_new() for circle in self.circles],
            rectangles=self.rectangles,
            arcs=self.arcs,
            pins=self.pins,
        )


@dataclass(kw_only=True)
class C_symbol_v6(C_symbol):
    symbols: dict[str, C_symbol_symbol_v6] = field(
        **sexp_field(multidict=True, key=lambda x: x.name),
        default_factory=dict,
    )

    def convert_to_new(self) -> C_symbol:
        return C_symbol(
            name=self.name,
            power=self.power,
            propertys=self.propertys,
            pin_numbers=self.pin_numbers,
            pin_names=self.pin_names,
            in_bom=self.in_bom,
            on_board=self.on_board,
            symbols={
                name: symbol.convert_to_new() for name, symbol in self.symbols.items()
            },
            convert=self.convert,
        )


@dataclass(kw_only=True)
class C_symbol_in_file_v6(SEXP_File):
    symbol: C_symbol_v6
