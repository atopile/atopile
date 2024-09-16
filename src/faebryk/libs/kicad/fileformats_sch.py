import logging
from dataclasses import dataclass, field
from enum import auto
from typing import Optional

from faebryk.libs.kicad.fileformats_common import (
    UUID,
    C_effects,
    C_pts,
    C_xy,
    C_xyr,
)
from faebryk.libs.sexp.dataclass_sexp import SEXP_File, SymEnum, sexp_field

logger = logging.getLogger(__name__)

# TODO find complete examples of the fileformats, maybe in the kicad repo


@dataclass
class C_property:
    name: str = field(**sexp_field(positional=True))
    value: str = field(**sexp_field(positional=True))
    id: Optional[int] = None
    at: Optional[C_xyr] = None
    effects: Optional[C_effects] = field(
        **sexp_field(preprocessor=C_effects.preprocess_shitty_hide), default=None
    )


@dataclass(kw_only=True)  # TODO: when to use kw_only?
class C_fill:
    class E_type(SymEnum):
        background = "background"
        none = "none"

    type: E_type = field(default=E_type.background)


@dataclass
class C_stroke:
    class E_type(SymEnum):
        solid = auto()
        default = auto()

    width: float
    type: E_type
    color: tuple[int, int, int, int]


@dataclass(kw_only=True)
class C_circle:
    center: C_xy
    end: C_xy
    stroke: C_stroke
    fill: C_fill


@dataclass(kw_only=True)
class C_arc:
    start: C_xy
    mid: C_xy
    end: C_xy
    stroke: C_stroke
    fill: C_fill


@dataclass(kw_only=True)
class C_rect:
    start: C_xy
    end: C_xy
    stroke: C_stroke
    fill: C_fill


@dataclass(kw_only=True)
class C_polyline:
    stroke: C_stroke
    fill: C_fill
    pts: C_pts = field(default_factory=C_pts)


@dataclass
class C_kicad_sch_file(SEXP_File):
    """
    When in doubt check: kicad/eeschema/sch_io/kicad_sexpr/sch_io_kicad_sexpr_parser.cpp
    """

    @dataclass
    class C_kicad_sch:
        @dataclass
        class C_title_block:
            title: Optional[str] = None
            date: Optional[str] = None
            rev: Optional[str] = None
            company: Optional[str] = None

        @dataclass
        class C_lib_symbols:
            @dataclass
            class C_symbol:
                @dataclass
                class C_pin_names:
                    offset: float

                @dataclass
                class C_symbol:
                    @dataclass
                    class C_pin:
                        class E_type(SymEnum):
                            # sorted alphabetically
                            bidirectional = "bidirectional"
                            free = "free"
                            input = "input"
                            no_connect = "no_connect"
                            open_collector = "open_collector"
                            open_emitter = "open_emitter"
                            output = "output"
                            passive = "passive"
                            power_in = "power_in"
                            power_out = "power_out"
                            tri_state = "tri_state"
                            unspecified = "unspecified"

                        class E_style(SymEnum):
                            # sorted alphabetically
                            clock = "clock"
                            clock_low = "clock_low"
                            edge_clock_high = "edge_clock_high"
                            input_low = "input_low"
                            inverted = "inverted"
                            inverted_clock = "inverted_clock"
                            line = "line"
                            non_logic = "non_logic"
                            output_low = "output_low"

                        @dataclass
                        class C_name:
                            name: str = field(**sexp_field(positional=True))
                            effects: C_effects = field(default_factory=C_effects)

                        @dataclass
                        class C_number:
                            number: str = field(**sexp_field(positional=True))
                            effects: C_effects = field(default_factory=C_effects)

                        at: C_xyr
                        length: float
                        type: E_type = field(**sexp_field(positional=True))
                        style: E_style = field(**sexp_field(positional=True))
                        name: C_name = field(default_factory=C_name)
                        number: C_number = field(default_factory=C_number)

                    name: str = field(**sexp_field(positional=True))
                    polylines: list[C_polyline] = field(
                        **sexp_field(multidict=True), default_factory=list
                    )
                    circles: list[C_circle] = field(
                        **sexp_field(multidict=True), default_factory=list
                    )
                    rectangles: list[C_rect] = field(
                        **sexp_field(multidict=True), default_factory=list
                    )
                    arcs: list[C_arc] = field(
                        **sexp_field(multidict=True), default_factory=list
                    )
                    pins: list[C_pin] = field(
                        **sexp_field(multidict=True), default_factory=list
                    )

                class E_hide(SymEnum):
                    hide = "hide"

                @dataclass
                class C_power:
                    pass

                name: str = field(**sexp_field(positional=True))
                power: Optional[C_power] = None
                propertys: dict[str, C_property] = field(
                    **sexp_field(multidict=True, key=lambda x: x.name),
                    default_factory=dict,
                )
                pin_numbers: Optional[E_hide] = None
                pin_names: Optional[C_pin_names] = None
                in_bom: Optional[bool] = None
                on_board: Optional[bool] = None
                symbols: list[C_symbol] = field(
                    **sexp_field(multidict=True), default_factory=list
                )
                convert: Optional[int] = None

            symbol: dict[str, C_symbol] = field(
                **sexp_field(multidict=True, key=lambda x: x.name), default_factory=dict
            )

        @dataclass
        class C_symbol_instance:
            @dataclass
            class C_pin:
                uuid: UUID
                pin: str = field(**sexp_field(positional=True))

            lib_id: str
            uuid: UUID
            at: C_xyr
            unit: int
            in_bom: bool
            on_board: bool
            fields_autoplaced: bool = True
            propertys: dict[str, C_property] = field(
                **sexp_field(multidict=True, key=lambda x: x.name),
                default_factory=dict,
            )
            pins: list[C_pin] = field(
                **sexp_field(multidict=True), default_factory=list
            )
            convert: Optional[int] = None

        @dataclass
        class C_junction:
            at: C_xy
            diameter: float
            color: tuple[int, int, int, int]
            uuid: UUID

        @dataclass
        class C_wire:
            pts: C_pts
            stroke: C_stroke
            uuid: UUID

        @dataclass
        class C_text:
            at: C_xyr
            effects: C_effects
            uuid: UUID
            text: str = field(**sexp_field(positional=True))

        @dataclass
        class C_sheet:
            @dataclass
            class C_pin:
                class E_type(SymEnum):
                    # sorted alphabetically
                    bidirectional = "bidirectional"
                    input = "input"
                    output = "output"
                    passive = "passive"
                    tri_state = "tri_state"

                at: C_xyr
                effects: C_effects
                uuid: UUID
                name: str = field(**sexp_field(positional=True))
                type: E_type = field(**sexp_field(positional=True))

            at: C_xy
            size: C_xy
            stroke: C_stroke
            fill: C_fill
            uuid: UUID
            fields_autoplaced: bool = True
            propertys: dict[str, C_property] = field(
                **sexp_field(multidict=True, key=lambda x: x.name),
                default_factory=dict,
            )
            pins: list[C_pin] = field(
                **sexp_field(multidict=True), default_factory=list
            )

        @dataclass
        class C_global_label:
            class E_shape(SymEnum):
                # sorted alphabetically
                input = "input"
                output = "output"
                bidirectional = "bidirectional"
                tri_state = "tri_state"
                passive = "passive"
                dot = "dot"
                round = "round"
                diamond = "diamond"
                rectangle = "rectangle"

            shape: E_shape
            at: C_xyr
            effects: C_effects
            uuid: UUID
            text: str = field(**sexp_field(positional=True))
            fields_autoplaced: bool = True
            propertys: dict[str, C_property] = field(
                **sexp_field(multidict=True, key=lambda x: x.name),
                default_factory=dict,
            )

        # TODO: inheritance
        # text
        # label
        # global_label
        # hierarchical_label
        # netclass_flag
        # directive_label
        @dataclass
        class C_label:
            at: C_xyr
            effects: C_effects
            uuid: UUID
            text: str = field(**sexp_field(positional=True))

        @dataclass
        class C_bus:
            pts: C_pts
            stroke: C_stroke
            uuid: UUID

        @dataclass
        class C_bus_entry:
            at: C_xy
            size: C_xy
            stroke: C_stroke
            uuid: UUID

        version: int = field(**sexp_field(assert_value=20211123))
        generator: str
        uuid: UUID
        paper: str
        lib_symbols: C_lib_symbols = field(default_factory=C_lib_symbols)
        title_block: C_title_block = field(default_factory=C_title_block)

        junctions: list[C_junction] = field(
            **sexp_field(multidict=True), default_factory=list
        )
        wires: list[C_wire] = field(**sexp_field(multidict=True), default_factory=list)

        texts: list[C_text] = field(**sexp_field(multidict=True), default_factory=list)
        symbols: list[C_symbol_instance] = field(
            **sexp_field(multidict=True), default_factory=list
        )
        sheets: list[C_sheet] = field(
            **sexp_field(multidict=True), default_factory=list
        )
        global_labels: list[C_global_label] = field(
            **sexp_field(multidict=True), default_factory=list
        )
        no_connects: list[C_xy] = field(
            **sexp_field(multidict=True), default_factory=list
        )
        buss: list[C_bus] = field(**sexp_field(multidict=True), default_factory=list)
        labels: list[C_label] = field(
            **sexp_field(multidict=True), default_factory=list
        )
        bus_entrys: list[C_bus_entry] = field(
            **sexp_field(multidict=True), default_factory=list
        )

    kicad_sch: C_kicad_sch
