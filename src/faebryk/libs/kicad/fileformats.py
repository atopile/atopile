import logging
from dataclasses import dataclass, field
from enum import IntEnum, StrEnum, auto
from pathlib import Path
from typing import Any, Optional

from dataclasses_json import CatchAll, Undefined, dataclass_json

from faebryk.libs.kicad.fileformats_common import (
    UUID,
    C_effects,
    C_pts,
    C_stroke,
    C_wh,
    C_xy,
    C_xyr,
    C_xyz,
    gen_uuid,
)
from faebryk.libs.sexp.dataclass_sexp import JSON_File, SEXP_File, SymEnum, sexp_field

logger = logging.getLogger(__name__)

# TODO find complete examples of the fileformats, maybe in the kicad repo

# Release dates for reference:
# KiCad 9.0.0 - February 19, 2025
# KiCad 8.0.0 - January 31, 2024
# KiCad 7.0.0 - March 1, 2023
# KiCad 6.0.0 - December 15, 2021
# KiCad 5.1.0 - May 22, 2019
# KiCad 5.0.0 - July 21, 2018

KICAD_PCB_VERSION = 20250219  # TODO: check if this is also what KiCad is saying


@dataclass_json(undefined=Undefined.INCLUDE)
@dataclass
class C_kicad_project_file(JSON_File):
    """
    Generated with ChatGPT by giving it the test.kicad_pro
    """

    @dataclass_json(undefined=Undefined.INCLUDE)
    @dataclass
    class C_pcbnew:
        @dataclass_json(undefined=Undefined.INCLUDE)
        @dataclass
        class C_last_paths:
            gencad: str = ""
            idf: str = ""
            netlist: str = ""
            plot: str = ""
            pos_files: str = ""
            specctra_dsn: str = ""
            step: str = ""
            svg: str = ""
            vrml: str = ""
            unknown: CatchAll = None

        last_paths: C_last_paths = field(default_factory=C_last_paths)
        page_layout_descr_file: str = ""
        unknown: CatchAll = None

    pcbnew: C_pcbnew = field(default_factory=C_pcbnew)

    @dataclass_json(undefined=Undefined.INCLUDE)
    @dataclass
    class C_board:
        @dataclass_json(undefined=Undefined.INCLUDE)
        @dataclass
        class C_design_settings:
            @dataclass_json(undefined=Undefined.INCLUDE)
            @dataclass
            class C_defaults:
                apply_defaults_to_fp_fields: bool = False
                apply_defaults_to_fp_shapes: bool = False
                apply_defaults_to_fp_text: bool = False
                board_outline_line_width: float = 0.05
                copper_line_width: float = 0.2
                copper_text_italic: bool = False
                copper_text_size_h: float = 1.5
                copper_text_size_v: float = 1.5
                copper_text_thickness: float = 0.3
                copper_text_upright: bool = False
                courtyard_line_width: float = 0.05
                dimension_precision: int = 4
                dimension_units: int = 3

                @dataclass_json(undefined=Undefined.INCLUDE)
                @dataclass
                class C_dimensions:
                    arrow_length: int = 1270000
                    extension_offset: int = 500000
                    keep_text_aligned: bool = True
                    suppress_zeroes: bool = False
                    text_position: int = 0
                    units_format: int = 1
                    unknown: CatchAll = None

                dimensions: C_dimensions = field(default_factory=C_dimensions)
                fab_line_width: float = 0.1
                fab_text_italic: bool = False
                fab_text_size_h: float = 1.0
                fab_text_size_v: float = 1.0
                fab_text_thickness: float = 0.15
                fab_text_upright: bool = False
                other_line_width: float = 0.1
                other_text_italic: bool = False
                other_text_size_h: float = 1.0
                other_text_size_v: float = 1.0
                other_text_thickness: float = 0.15
                other_text_upright: bool = False

                @dataclass_json(undefined=Undefined.INCLUDE)
                @dataclass
                class C_pads:
                    drill: float = 0.762
                    height: float = 1.524
                    width: float = 1.524
                    unknown: CatchAll = None

                pads: C_pads = field(default_factory=C_pads)
                silk_line_width: float = 0.1
                silk_text_italic: bool = False
                silk_text_size_h: float = 1.0
                silk_text_size_v: float = 1.0
                silk_text_thickness: float = 0.1
                silk_text_upright: bool = False

                @dataclass_json(undefined=Undefined.INCLUDE)
                @dataclass
                class C_zones:
                    min_clearance: float = 0.5
                    unknown: CatchAll = None

                zones: C_zones = field(default_factory=C_zones)
                unknown: CatchAll = None

            defaults: C_defaults = field(default_factory=C_defaults)

            @dataclass_json(undefined=Undefined.INCLUDE)
            @dataclass
            class C_diff_pair_dimensions:
                unknown: CatchAll = None

            diff_pair_dimensions: list[C_diff_pair_dimensions] = field(
                default_factory=list
            )

            @dataclass_json(undefined=Undefined.INCLUDE)
            @dataclass
            class C_drc_exclusions:
                unknown: CatchAll = None

            drc_exclusions: list[C_drc_exclusions] = field(default_factory=list)

            @dataclass_json(undefined=Undefined.INCLUDE)
            @dataclass
            class C_meta:
                version: int = 2
                unknown: CatchAll = None

            meta: C_meta = field(default_factory=C_meta)

            @dataclass_json(undefined=Undefined.INCLUDE)
            @dataclass
            class C_rule_severities:
                annular_width: str = "error"
                clearance: str = "error"
                connection_width: str = "warning"
                copper_edge_clearance: str = "error"
                copper_sliver: str = "warning"
                courtyards_overlap: str = "error"
                diff_pair_gap_out_of_range: str = "error"
                diff_pair_uncoupled_length_too_long: str = "error"
                drill_out_of_range: str = "error"
                duplicate_footprints: str = "warning"
                extra_footprint: str = "warning"
                footprint: str = "error"
                footprint_symbol_mismatch: str = "warning"
                footprint_type_mismatch: str = "ignore"
                hole_clearance: str = "error"
                hole_near_hole: str = "error"
                holes_co_located: str = "warning"
                invalid_outline: str = "error"
                isolated_copper: str = "warning"
                item_on_disabled_layer: str = "error"
                items_not_allowed: str = "error"
                length_out_of_range: str = "error"
                lib_footprint_issues: str = "warning"
                lib_footprint_mismatch: str = "warning"
                malformed_courtyard: str = "error"
                microvia_drill_out_of_range: str = "error"
                missing_courtyard: str = "ignore"
                missing_footprint: str = "warning"
                net_conflict: str = "warning"
                npth_inside_courtyard: str = "ignore"
                padstack: str = "warning"
                pth_inside_courtyard: str = "ignore"
                shorting_items: str = "error"
                silk_edge_clearance: str = "warning"
                silk_over_copper: str = "warning"
                silk_overlap: str = "warning"
                skew_out_of_range: str = "error"
                solder_mask_bridge: str = "error"
                starved_thermal: str = "error"
                text_height: str = "warning"
                text_thickness: str = "warning"
                through_hole_pad_without_hole: str = "error"
                too_many_vias: str = "error"
                track_dangling: str = "warning"
                track_width: str = "error"
                tracks_crossing: str = "error"
                unconnected_items: str = "error"
                unresolved_variable: str = "error"
                via_dangling: str = "warning"
                zones_intersect: str = "error"
                unknown: CatchAll = None

            rule_severities: C_rule_severities = field(
                default_factory=C_rule_severities
            )

            @dataclass_json(undefined=Undefined.INCLUDE)
            @dataclass
            class C_rules:
                max_error: float = 0.005
                min_clearance: float = 0.0
                min_connection: float = 0.0
                min_copper_edge_clearance: float = 0.5
                min_hole_clearance: float = 0.25
                min_hole_to_hole: float = 0.25
                min_microvia_diameter: float = 0.2
                min_microvia_drill: float = 0.1
                min_resolved_spokes: int = 2
                min_silk_clearance: float = 0.0
                min_text_height: float = 0.8
                min_text_thickness: float = 0.08
                min_through_hole_diameter: float = 0.3
                min_track_width: float = 0.0
                min_via_annular_width: float = 0.1
                min_via_diameter: float = 0.5
                solder_mask_to_copper_clearance: float = 0.0
                use_height_for_length_calcs: bool = True
                unknown: CatchAll = None

            rules: C_rules = field(default_factory=C_rules)

            @dataclass_json(undefined=Undefined.INCLUDE)
            @dataclass
            class C_teardrop_options:
                td_onpadsmd: bool = True
                td_onroundshapesonly: bool = False
                td_ontrackend: bool = False
                td_onviapad: bool = True
                unknown: CatchAll = None

            teardrop_options: list[C_teardrop_options] = field(default_factory=list)

            @dataclass_json(undefined=Undefined.INCLUDE)
            @dataclass
            class C_teardrop_parameters:
                td_allow_use_two_tracks: bool = True
                td_curve_segcount: int = 0
                td_height_ratio: float = 1.0
                td_length_ratio: float = 0.5
                td_maxheight: float = 2.0
                td_maxlen: float = 1.0
                td_on_pad_in_zone: bool = False
                td_target_name: str = "td_round_shape"
                td_width_to_size_filter_ratio: float = 0.9
                unknown: CatchAll = None

            teardrop_parameters: list[C_teardrop_parameters] = field(
                default_factory=list
            )

            track_widths: list[float] = field(default_factory=list)

            @dataclass_json(undefined=Undefined.INCLUDE)
            @dataclass
            class C_tuning_pattern_settings:
                @dataclass_json(undefined=Undefined.INCLUDE)
                @dataclass
                class C_diff_pair_defaults:
                    corner_radius_percentage: int = 80
                    corner_style: int = 1
                    max_amplitude: float = 1.0
                    min_amplitude: float = 0.2
                    single_sided: bool = False
                    spacing: float = 1.0
                    unknown: CatchAll = None

                diff_pair_defaults: C_diff_pair_defaults = field(
                    default_factory=C_diff_pair_defaults
                )

                @dataclass_json(undefined=Undefined.INCLUDE)
                @dataclass
                class C_diff_pair_skew_defaults:
                    corner_radius_percentage: int = 80
                    corner_style: int = 1
                    max_amplitude: float = 1.0
                    min_amplitude: float = 0.2
                    single_sided: bool = False
                    spacing: float = 0.6
                    unknown: CatchAll = None

                diff_pair_skew_defaults: C_diff_pair_skew_defaults = field(
                    default_factory=C_diff_pair_skew_defaults
                )

                @dataclass_json(undefined=Undefined.INCLUDE)
                @dataclass
                class C_single_track_defaults:
                    corner_radius_percentage: int = 80
                    corner_style: int = 1
                    max_amplitude: float = 1.0
                    min_amplitude: float = 0.2
                    single_sided: bool = False
                    spacing: float = 0.6
                    unknown: CatchAll = None

                single_track_defaults: C_single_track_defaults = field(
                    default_factory=C_single_track_defaults
                )
                unknown: CatchAll = None

            tuning_pattern_settings: C_tuning_pattern_settings = field(
                default_factory=C_tuning_pattern_settings
            )

            @dataclass_json(undefined=Undefined.INCLUDE)
            @dataclass
            class C_via_dimensions:
                unknown: CatchAll = None

            via_dimensions: list[C_via_dimensions] = field(default_factory=list)
            zones_allow_external_fillets: bool = False
            unknown: CatchAll = None

        design_settings: C_design_settings = field(default_factory=C_design_settings)

        @dataclass_json(undefined=Undefined.INCLUDE)
        @dataclass
        class C_ipc2581:
            dist: str = ""
            distpn: str = ""
            internal_id: str = ""
            mfg: str = ""
            mpn: str = ""
            unknown: CatchAll = None

        ipc2581: C_ipc2581 = field(default_factory=C_ipc2581)

        @dataclass_json(undefined=Undefined.INCLUDE)
        @dataclass
        class C_layer_presets:
            unknown: CatchAll = None

        layer_presets: list[C_layer_presets] = field(default_factory=list)

        @dataclass_json(undefined=Undefined.INCLUDE)
        @dataclass
        class C_viewports:
            unknown: CatchAll = None

        viewports: list[C_viewports] = field(default_factory=list)
        unknown: CatchAll = None

    board: C_board = field(default_factory=C_board)

    @dataclass_json(undefined=Undefined.INCLUDE)
    @dataclass
    class C_boards:
        unknown: CatchAll = None

    boards: list[C_boards] = field(default_factory=list)

    @dataclass_json(undefined=Undefined.INCLUDE)
    @dataclass
    class C_cvpcb:
        @dataclass_json(undefined=Undefined.INCLUDE)
        @dataclass
        class C_equivalence_files:
            unknown: CatchAll = None

        equivalence_files: list[C_equivalence_files] = field(default_factory=list)
        unknown: CatchAll = None

    cvpcb: C_cvpcb = field(default_factory=C_cvpcb)

    @dataclass_json(undefined=Undefined.INCLUDE)
    @dataclass
    class C_libraries:
        @dataclass_json(undefined=Undefined.INCLUDE)
        @dataclass
        class C_pinned_footprint_libs:
            unknown: CatchAll = None

        pinned_footprint_libs: list[C_pinned_footprint_libs] = field(
            default_factory=list
        )

        @dataclass_json(undefined=Undefined.INCLUDE)
        @dataclass
        class C_pinned_symbol_libs:
            unknown: CatchAll = None

        pinned_symbol_libs: list[C_pinned_symbol_libs] = field(default_factory=list)
        unknown: CatchAll = None

    libraries: C_libraries = field(default_factory=C_libraries)

    @dataclass_json(undefined=Undefined.INCLUDE)
    @dataclass
    class C_meta:
        filename: str = "example.kicad_pro"
        version: int = 1
        unknown: CatchAll = None

    meta: C_meta = field(default_factory=C_meta)

    @dataclass_json(undefined=Undefined.INCLUDE)
    @dataclass
    class C_net_settings:
        @dataclass_json(undefined=Undefined.INCLUDE)
        @dataclass
        class C_classes:
            bus_width: int = 12
            clearance: float = 0.2
            diff_pair_gap: float = 0.25
            diff_pair_via_gap: float = 0.25
            diff_pair_width: float = 0.2
            line_style: int = 0
            microvia_diameter: float = 0.3
            microvia_drill: float = 0.1
            name: str = "Default"
            pcb_color: str = "rgba(0, 0, 0, 0.000)"
            schematic_color: str = "rgba(0, 0, 0, 0.000)"
            track_width: float = 0.2
            via_diameter: float = 0.6
            via_drill: float = 0.3
            wire_width: int = 6
            unknown: CatchAll = None

        classes: list[C_classes] = field(default_factory=list)

        @dataclass_json(undefined=Undefined.INCLUDE)
        @dataclass
        class C_meta:
            version: int = 3
            unknown: CatchAll = None

        meta: C_meta = field(default_factory=C_meta)
        net_colors: Optional[Any] = None
        netclass_assignments: Optional[Any] = None
        netclass_patterns: list = field(default_factory=list)
        unknown: CatchAll = None

    net_settings: C_net_settings = field(default_factory=C_net_settings)

    @dataclass_json(undefined=Undefined.INCLUDE)
    @dataclass
    class C_schematic:
        legacy_lib_dir: str = ""
        legacy_lib_list: list = field(default_factory=list)
        unknown: CatchAll = None

    schematic: C_schematic = field(default_factory=C_schematic)

    @dataclass_json(undefined=Undefined.INCLUDE)
    @dataclass
    class C_sheets:
        @dataclass
        class C_sheet:
            uuid: str = field(**sexp_field(positional=True))
            title: str = field(**sexp_field(positional=True))

        sheet: list[C_sheet] = field(
            **sexp_field(positional=True), default_factory=list
        )

    sheets: list[C_sheets] = field(default_factory=list)

    @dataclass_json(undefined=Undefined.INCLUDE)
    @dataclass
    class C_text_variables:
        unknown: CatchAll = None

    text_variables: dict = field(default_factory=dict)
    unknown: CatchAll = None


@dataclass
class C_text_layer:
    class E_knockout(SymEnum):
        knockout = auto()

    layer: str = field(**sexp_field(positional=True))
    knockout: Optional[E_knockout] = field(**sexp_field(positional=True), default=None)


class E_fill(SymEnum):
    none = auto()
    solid = auto()


@dataclass(kw_only=True)
class C_shape:  # TODO: Should be used for all shapes
    layer: str
    layers: Optional[list[str]] = None
    solder_mask_margin: float
    stroke: C_stroke
    fill: E_fill
    locked: Optional[bool] = None
    # net: Optional[str] = None #TODO: is this supposed to be here?
    uuid: UUID = field(default_factory=gen_uuid)


# gr_vector
# gr_line
# fp_line
@dataclass(kw_only=True)
class C_line:
    start: C_xy
    end: C_xy
    stroke: C_stroke
    layer: str
    uuid: UUID = field(default_factory=gen_uuid)


# gr_circle
# fp_circle
@dataclass(kw_only=True)
class C_circle:
    center: C_xy
    end: C_xy
    stroke: C_stroke
    fill: E_fill
    layer: str
    uuid: UUID = field(default_factory=gen_uuid)


# gr_arc
# fp_arc
@dataclass(kw_only=True)
class C_arc:
    start: C_xy
    mid: C_xy
    end: C_xy
    stroke: C_stroke
    layer: str
    layers: Optional[list[str]] = None
    solder_mask_margin: float
    uuid: UUID = field(default_factory=gen_uuid)


# gr_curve
# fp_curve
@dataclass(kw_only=True)
class C_curve(C_shape):
    pts: list[C_xy]


@dataclass(kw_only=True)
class C_text:
    text: str = field(**sexp_field(positional=True))
    at: C_xyr
    layer: C_text_layer
    uuid: UUID = field(default_factory=gen_uuid)
    effects: C_effects


@dataclass(kw_only=True)
class C_fp_text:  # TODO: Inherit from C_text maybe ?
    class E_type(SymEnum):
        user = auto()
        reference = auto()
        value = auto()

    class C_fp_text_effects(C_effects):
        hide: Optional[bool] = (
            None  # TODO: is this correct? KiCad:parsePCB_TEXT_effects
        )

    type: E_type = field(**sexp_field(positional=True))
    text: str = field(**sexp_field(positional=True))
    at: C_xyr
    layer: C_text_layer
    hide: Optional[bool] = None
    uuid: UUID = field(default_factory=gen_uuid)
    effects: C_fp_text_effects
    unlocked: bool = False


# gr_bbox
# gr_rect
# fp_rect
@dataclass(kw_only=True)
class C_rect:
    start: C_xy
    end: C_xy
    stroke: C_stroke
    fill: E_fill
    layer: str
    uuid: UUID = field(default_factory=gen_uuid)


# gr_poly
# fp_poly
@dataclass
class C_polygon:
    pts: C_pts


@dataclass(kw_only=True)
class C_teardrop:
    enabled: bool = False
    allow_two_segments: bool = False
    prefer_zone_connections: bool = True
    best_length_ratio: float
    max_length: float
    best_width_ratio: float
    max_width: float
    curve_points: int  # legacy
    curved_edges: bool
    filter_ratio: float


@dataclass(kw_only=True)
class C_render_cache:
    polygon: C_polygon
    # TODO: KiCad:parseRenderCache


@dataclass(kw_only=True)
class C_image:
    at: C_xy
    layer: str
    scale: float = 1.0
    data: bytes  # base64 encoded image data


@dataclass(kw_only=True)
class C_textbox:
    @dataclass
    class C_margins:
        left: int
        top: int
        right: int
        bottom: int

    @dataclass
    class C_span:
        cols: int
        rows: int

    text: str
    locked: bool = False
    start: C_xy
    pts: list[C_xy]
    angle: float
    stroke: C_stroke
    border: bool
    margins: Optional[C_margins] = None
    layer: str
    span: Optional[C_span] = None
    effects: C_effects  # TODO: KiCad:parseEDA_TEXT
    render_cache: C_render_cache
    uuid: UUID = field(default_factory=gen_uuid)


@dataclass(kw_only=True)
class C_table:
    @dataclass
    class C_table_cell:
        table_cell: C_textbox

    @dataclass
    class C_border:
        external: bool
        header: bool
        stroke: C_stroke

    @dataclass
    class C_separator:
        rows: bool
        cols: bool
        stroke: C_stroke

    columns: int
    locked: Optional[bool] = None
    layer: str
    col_widths: list[float]
    row_heights: list[float]
    cells: list[C_table_cell]
    border: C_border
    separators: C_separator


@dataclass(kw_only=True)
class C_dimension:
    @dataclass
    class C_format:
        prefix: str
        suffix: str
        units: int
        units_format: int
        precision: int
        override_value: str | int
        suppress_zeroes: bool

        def __post_init__(self):
            if self.units < 0 or self.units > 4:
                raise ValueError(f"units must be between 0 and 4, got {self.units}")
            if self.units_format < 0 or self.units_format > 3:
                raise ValueError(
                    f"units_format must be between 0 and 3, got {self.units_format}"
                )

    aligned: float
    orthogonal: float
    leader: float
    center: float
    radial: float
    layer: str
    uuid: UUID = field(default_factory=gen_uuid)
    gr_text: C_text
    pts: list[C_xy]
    height: float
    leader_length: float
    orientation: float
    format: C_format


@dataclass(kw_only=True)
class C_footprint:
    class E_attr(SymEnum):
        smd = auto()
        dnp = auto()
        board_only = auto()
        through_hole = auto()
        exclude_from_pos_files = auto()
        exclude_from_bom = auto()
        allow_missing_courtyard = auto()

    @dataclass(kw_only=True)
    class C_property:
        @dataclass(kw_only=True)
        class C_footprint_property_effects(C_effects):
            hide: Optional[bool] = None

        name: str = field(**sexp_field(positional=True))
        value: str = field(**sexp_field(positional=True))
        at: C_xyr
        layer: C_text_layer
        hide: bool = False
        uuid: UUID = field(default_factory=gen_uuid)
        effects: C_footprint_property_effects

    @dataclass
    class C_footprint_polygon(C_polygon):
        stroke: C_stroke
        fill: E_fill
        layer: str
        uuid: UUID = field(default_factory=gen_uuid)

    @dataclass(kw_only=True)
    class C_pad:
        class E_type(SymEnum):
            thru_hole = auto()
            smd = auto()
            non_plated_through_hole = "np_thru_hole"
            edge_connector = "connect"

        class E_shape(SymEnum):
            circle = auto()
            rect = auto()
            stadium = "oval"
            roundrect = auto()
            custom = auto()

        @dataclass
        class C_options:
            class E_clearance(SymEnum):
                outline = auto()

            class E_anchor(SymEnum):
                rect = auto()
                circle = auto()

            clearance: E_clearance
            anchor: E_anchor

        @dataclass
        class C_drill:
            class E_shape(SymEnum):
                circle = ""
                stadium = "oval"

            shape: E_shape = field(
                **sexp_field(positional=True), default=E_shape.circle
            )
            size_x: Optional[float] = field(**sexp_field(positional=True), default=None)
            size_y: Optional[float] = field(**sexp_field(positional=True), default=None)
            offset: Optional[C_xy] = None

        class E_chamfer(SymEnum):
            top_left = "chamfer_top_left"
            top_right = "chamfer_top_right"
            bottom_left = "chamfer_bottom_left"
            bottom_right = "chamfer_bottom_right"

        class E_property(SymEnum):
            bga = "pad_prop_bga"
            fiducial_glob = "pad_prop_fiducial_glob"
            fiducial_loc = "pad_prop_fiducial_loc"
            testpoint = "pad_prop_testpoint"
            castellated = "pad_prop_castellated"
            heatsink = "pad_prop_heatsink"
            mechanical = "pad_prop_mechanical"
            none = ""

        @dataclass
        class C_padstack:
            class E_mode(SymEnum):
                front_inner_back = auto()
                custom = auto()

            @dataclass
            class C_layer:
                class E_shape(SymEnum):
                    circle = auto()
                    rectangle = auto()
                    roundrect = auto()
                    oval = auto()
                    trapezoid = auto()
                    custom = auto()

                name: str
                shape: E_shape
                size: C_wh
                offset: C_xy
                ...  # TODO add till line 5935 pcb_io_kicad_sexpr_parser.cpp (v9)

            mode: E_mode
            layer: C_layer

        @dataclass
        class C_tenting:
            class E_type(SymEnum):
                front = auto()
                back = auto()
                none = auto()

            type: E_type = field(**sexp_field(positional=True))

        @dataclass
        class C_rect_delta:
            width: float = field(**sexp_field(positional=True))
            height: float = field(**sexp_field(positional=True))

        name: str = field(**sexp_field(positional=True))
        type: E_type = field(**sexp_field(positional=True))
        shape: E_shape = field(**sexp_field(positional=True))
        size: C_wh
        at: C_xyr
        rect_delta: Optional[C_rect_delta] = None
        drill: Optional[C_drill] = None
        layers: list[str]
        die_length: Optional[float] = None
        solder_mask_margin: Optional[float] = None
        solder_paste_margin: Optional[float] = None
        solder_paste_margin_ratio: Optional[float] = None
        clearance: Optional[float] = None
        teardrops: Optional[C_teardrop] = None
        zone_connect: Optional[bool] = None
        thermal_bridge_width: Optional[float] = None
        thermal_bridge_angle: Optional[float] = None
        thermal_gap: Optional[float] = None
        roundrect_rratio: Optional[float] = None
        chamfer_ratio: Optional[float] = None
        chamfer: Optional[E_chamfer] = None
        properties: Optional[E_property] = None
        options: Optional[C_options] = None
        padstack: Optional[C_padstack] = None  # see parsePadstack
        # TODO: primitives: gr_line, gr_arc, gr_circle, gr_curve, gr_rect, gr_bbox or
        # gr_poly
        remove_unused_layers: Optional[bool] = True
        keep_end_layers: Optional[bool] = True
        tenting: Optional[C_tenting] = None
        zone_layer_connections: Optional[list[str]] = None
        uuid: UUID = field(default_factory=gen_uuid)
        unknown: CatchAll = None

    @dataclass
    class C_model:
        path: Path = field(**sexp_field(positional=True))

        @dataclass
        class C_offset:
            xyz: C_xyz

        @dataclass
        class C_scale:
            xyz: C_xyz

        @dataclass
        class C_rotate:
            xyz: C_xyz

        offset: C_offset
        scale: C_scale
        rotate: C_rotate
        unknown: CatchAll = None

    name: str = field(**sexp_field(positional=True))
    layer: str = field(**sexp_field(order=-20))
    propertys: dict[str, C_property] = field(
        **sexp_field(multidict=True, key=lambda x: x.name), default_factory=dict
    )
    attr: list[E_attr]
    fp_lines: list[C_line] = field(**sexp_field(multidict=True), default_factory=list)
    fp_arcs: list[C_arc] = field(**sexp_field(multidict=True), default_factory=list)
    fp_circles: list[C_circle] = field(
        **sexp_field(multidict=True), default_factory=list
    )
    fp_rects: list[C_rect] = field(**sexp_field(multidict=True), default_factory=list)
    fp_texts: list[C_fp_text] = field(
        **sexp_field(multidict=True), default_factory=list
    )
    fp_poly: list[C_footprint_polygon] = field(
        **sexp_field(multidict=True), default_factory=list
    )
    pads: list[C_pad] = field(**sexp_field(multidict=True), default_factory=list)
    model: list[C_model] = field(**sexp_field(multidict=True), default_factory=list)


@dataclass
class C_kicad_pcb_file(SEXP_File):
    @dataclass
    class C_kicad_pcb:
        @dataclass
        class C_general:
            thickness: float = 1.6
            legacy_teardrops: bool = False

        @dataclass
        class C_paper:
            class E_type(SymEnum):
                A5 = "A5"
                A4 = "A4"
                A3 = "A3"
                A2 = "A2"
                A1 = "A1"
                A0 = "A0"
                A = "A"
                B = "B"
                C = "C"
                D = "D"
                E = "E"
                USLetter = "USLetter"
                USLegal = "USLegal"
                USLedger = "USLedger"
                Custom = auto()

            class E_orientation(SymEnum):
                portrait = auto()
                landscape = ""

            type: E_type = field(**sexp_field(positional=True), default=E_type.A4)
            size: Optional[C_xy] = field(**sexp_field(positional=True), default=None)
            orientation: Optional[E_orientation] = field(
                **sexp_field(positional=True), default=E_orientation.landscape
            )

            def __post_init__(self):
                if self.type == self.E_type.Custom:
                    if self.size is None:
                        raise ValueError(
                            "Paper size must be specified for custom paper type"
                        )
                    if self.orientation:
                        raise ValueError(
                            "Paper orientation must not be specified for custom paper type"  # noqa: E501
                        )

        @dataclass
        class C_title_block:
            @dataclass
            class C_comment:
                number: int = field(**sexp_field(positional=True))
                text: str = field(**sexp_field(positional=True))

                def __post_init__(self):
                    if self.number < 1 or self.number > 9:
                        raise ValueError(
                            "KiCad title block comment number must be between 1 and 9"
                        )

            title: Optional[str] = None
            date: Optional[str] = None
            revision: Optional[str] = None
            company: Optional[str] = None
            comment: Optional[list[C_comment]] = None

        @dataclass
        class C_layer:
            class E_type(SymEnum):
                signal = auto()
                user = auto()
                mixed = auto()
                jumper = auto()
                power = auto()

            number: int = field(**sexp_field(positional=True))
            name: str = field(**sexp_field(positional=True))
            type: E_type = field(**sexp_field(positional=True))
            alias: Optional[str] = field(**sexp_field(positional=True), default=None)
            unknown: CatchAll = None

        @dataclass(kw_only=True)
        class C_setup:
            @dataclass
            class C_pcbplotparams:
                layerselection: str = "0x00010fc_ffffffff"
                plot_on_all_layers_selection: str = "0x0000000_00000000"
                disableapertmacros: bool = False
                usegerberextensions: bool = False
                usegerberattributes: bool = True
                usegerberadvancedattributes: bool = True
                creategerberjobfile: bool = True
                dashed_line_dash_ratio: float = 12.0
                dashed_line_gap_ratio: float = 3.0
                svgprecision: int = 4
                plotframeref: bool = False
                viasonmask: bool = False
                mode: int = 1
                useauxorigin: bool = False
                hpglpennumber: int = 1
                hpglpenspeed: int = 20
                hpglpendiameter: float = 15.0
                pdf_front_fp_property_popups: bool = True
                pdf_back_fp_property_popups: bool = True
                dxfpolygonmode: bool = True
                dxfimperialunits: bool = True
                dxfusepcbnewfont: bool = True
                psnegative: bool = False
                psa4output: bool = False
                plotreference: bool = True
                plotvalue: bool = True
                plotfptext: bool = True
                plotinvisibletext: bool = False
                sketchpadsonfab: bool = False
                subtractmaskfromsilk: bool = False
                outputformat: int = 1
                mirror: bool = False
                drillshape: int = 1
                scaleselection: int = 1
                outputdirectory: str = ""
                unknown: CatchAll = None

            @dataclass
            class C_stackup:
                @dataclass
                class C_layer:
                    name: str = field(**sexp_field(positional=True))
                    type: str
                    color: Optional[str] = None
                    thickness: Optional[float] = None
                    material: Optional[str] = None
                    epsilon_r: Optional[float] = None
                    loss_tangent: Optional[float] = None
                    unknown: CatchAll = None

                class E_edge_connector_type(SymEnum):
                    edge_connector_bevelled = "bevelled"
                    edge_connector = "yes"

                class E_copper_finish(StrEnum):
                    ENIG = "ENIG"
                    ENEPIG = auto()
                    HAL_SNPB = "HAL SnPb"
                    HAL_LEAD_FREE = "HAL lead-free"
                    HARD_GOLD = "Hard Gold"
                    IMERSION_TIN = "Immersion tin"
                    IMERSION_SILVER = "Immersion silver"
                    IMERSION_NICKEL = "Immersion nickel"
                    IMERSION_GOLD = "Immersion gold"
                    OSP = auto()
                    HT_OSP = auto()
                    NONE = "None"
                    USER_DEFINED = "User defined"

                layers: list[C_layer] = field(
                    **sexp_field(multidict=True), default_factory=list
                )
                copper_finish: Optional[E_copper_finish] = None
                dielectric_constraints: Optional[bool] = None
                edge_connector: Optional[E_edge_connector_type] = None
                castellated_pads: Optional[bool] = None
                edge_plating: Optional[bool] = None
                unknown: CatchAll = None

            stackup: Optional[C_stackup] = None
            pad_to_mask_clearance: int = 0
            allow_soldermask_bridges_in_footprints: bool = False
            pcbplotparams: C_pcbplotparams = field(default_factory=C_pcbplotparams)
            unknown: CatchAll = None

        @dataclass
        class C_properties:
            name: str = field(**sexp_field(positional=True))
            value: str = field(**sexp_field(positional=True))

        @dataclass
        class C_net:
            number: int = field(**sexp_field(positional=True))
            name: str = field(**sexp_field(positional=True))

        @dataclass(kw_only=True)
        class C_pcb_footprint(C_footprint):
            @dataclass(kw_only=True)
            class C_pad(C_footprint.C_pad):
                @dataclass
                class C_net:
                    number: int = field(**sexp_field(positional=True))
                    name: str = field(**sexp_field(positional=True))

                net: Optional[C_net] = None

            uuid: UUID = field(**sexp_field(order=-15))
            at: C_xyr = field(**sexp_field(order=-10))
            pads: list[C_pad] = field(
                **sexp_field(multidict=True), default_factory=list
            )
            path: Optional[str] = None
            unknown: CatchAll = None

        @dataclass(kw_only=True)
        class C_via:
            @dataclass
            class C_padstack:
                class E_mode(SymEnum):
                    front_inner_back = auto()
                    custom = auto()

                @dataclass
                class C_layer:
                    size: C_xy

                mode: E_mode = field(**sexp_field(positional=True))
                layer: C_layer

            # blind: bool = False
            # micro: bool = False
            at: C_xy
            size: float
            drill: float
            layers: list[str] = field(default_factory=list)
            net: int
            # remove_unused_layers
            # keep_end_layers
            # zone_layer_connections
            padstack: C_padstack
            teardrops: C_teardrop
            # tenting
            # free
            uuid: UUID
            unknown: CatchAll = None

        @dataclass(kw_only=True)
        class C_zone:
            @dataclass
            class C_hatch:
                class E_mode(SymEnum):
                    edge = auto()
                    full = auto()
                    none = auto()

                mode: E_mode = field(**sexp_field(positional=True))
                pitch: float = field(**sexp_field(positional=True))
                unknown: CatchAll = None

            @dataclass(kw_only=True)
            class C_connect_pads:
                class E_mode(SymEnum):
                    none = "no"
                    solid = "yes"
                    thermal_reliefs = ""
                    thru_hole_only = "thru_hole_only"

                mode: Optional[E_mode] = field(
                    **sexp_field(positional=True), default=None
                )
                clearance: float
                unknown: CatchAll = None

            @dataclass(kw_only=True)
            class C_fill:
                class E_yes(SymEnum):
                    yes = "yes"

                class E_mode(SymEnum):
                    hatch = auto()
                    polygon = auto()

                class E_hatch_border_algorithm(SymEnum):
                    hatch_thickness = auto()
                    min_thickness = ""

                class E_smoothing(SymEnum):
                    fillet = "fillet"
                    chamfer = "chamfer"
                    none = ""

                class E_island_removal_mode(IntEnum):
                    always = 0
                    do_not_remove = 1
                    below_area_limit = 2

                enable: Optional[E_yes] = field(
                    **sexp_field(positional=True), default=None
                )
                mode: Optional[E_mode] = None
                hatch_thickness: Optional[float] = None
                hatch_gap: Optional[float] = None
                hatch_orientation: Optional[float] = None
                hatch_smoothing_level: Optional[float] = None
                hatch_smoothing_value: Optional[float] = None
                hatch_border_algorithm: Optional[E_hatch_border_algorithm] = None
                hatch_min_hole_area: Optional[float] = None
                arc_segments: Optional[int] = None
                thermal_gap: float
                thermal_bridge_width: float
                smoothing: Optional[E_smoothing] = None
                radius: Optional[float] = None
                island_removal_mode: Optional[E_island_removal_mode] = None
                island_area_min: Optional[float] = None
                unknown: CatchAll = None

            @dataclass
            class C_keepout:
                class E_keepout_bool(SymEnum):
                    allowed = auto()
                    not_allowed = auto()

                tracks: E_keepout_bool
                vias: E_keepout_bool
                pads: E_keepout_bool
                copperpour: E_keepout_bool
                footprints: E_keepout_bool
                unknown: CatchAll = None

            @dataclass(kw_only=True)
            class C_filled_polygon:
                layer: str
                # FIXME: decode (island), a bracketed positional
                # We're currently relying on the CatchAll to re-serialise it
                pts: C_pts
                unknown: CatchAll = None

            net: int
            net_name: str
            layer: Optional[str] = None
            layers: Optional[list[str]] = None
            # NOTE: if zones is both front and back Cu layer then layer="F&B.Cu"
            # else layer="F.Cu" "B.Cu" "In1.Cu" ...
            uuid: UUID
            name: Optional[str] = None
            # locked: Optional[bool] = None #TODO: legacy -> delete?
            hatch: C_hatch
            priority: Optional[int] = None
            connect_pads: C_connect_pads
            min_thickness: float
            filled_areas_thickness: bool
            fill: C_fill
            keepout: Optional[C_keepout] = None
            polygon: C_polygon
            filled_polygon: list[C_filled_polygon] = field(
                **sexp_field(multidict=True), default_factory=list
            )
            unknown: CatchAll = None

        @dataclass
        class C_segment:
            start: C_xy
            end: C_xy
            width: float
            layer: str
            net: int
            uuid: UUID

        @dataclass
        class C_arc_segment(C_segment):
            mid: C_xy

        @dataclass(kw_only=True)
        class C_group:
            name: Optional[str] = field(**sexp_field(positional=True), default=None)
            uuid: UUID
            locked: Optional[bool] = None
            members: list[UUID]

        @dataclass
        class C_generated:
            uuid: UUID
            type: str
            name: str
            locked: bool
            layer: str
            members: list[UUID]
            unknown: CatchAll = None

        @dataclass
        class C_target:
            # x: float #TODO: no idea what this is
            # plus: bool #TODO: no idea what this is
            at: C_xy
            size: C_xy
            width: float
            layer: str
            uuid: UUID
            unknown: CatchAll = None

        version: int = field(**sexp_field(assert_value=KICAD_PCB_VERSION))
        generator: str
        generator_version: str
        general: C_general = field(default_factory=C_general)
        paper: C_paper = field(default_factory=C_paper)
        title_block: Optional[C_title_block] = None
        layers: list[C_layer] = field(
            default_factory=lambda: [
                C_kicad_pcb_file.C_kicad_pcb.C_layer(
                    number=0,
                    name="F.Cu",
                    type=C_kicad_pcb_file.C_kicad_pcb.C_layer.E_type.signal,
                ),
                C_kicad_pcb_file.C_kicad_pcb.C_layer(
                    number=31,
                    name="B.Cu",
                    type=C_kicad_pcb_file.C_kicad_pcb.C_layer.E_type.signal,
                ),
                C_kicad_pcb_file.C_kicad_pcb.C_layer(
                    number=32,
                    name="B.Adhes",
                    type=C_kicad_pcb_file.C_kicad_pcb.C_layer.E_type.user,
                    alias="B.Adhesive",
                ),
                C_kicad_pcb_file.C_kicad_pcb.C_layer(
                    number=33,
                    name="F.Adhes",
                    type=C_kicad_pcb_file.C_kicad_pcb.C_layer.E_type.user,
                    alias="F.Adhesive",
                ),
                C_kicad_pcb_file.C_kicad_pcb.C_layer(
                    number=34,
                    name="B.Paste",
                    type=C_kicad_pcb_file.C_kicad_pcb.C_layer.E_type.user,
                ),
                C_kicad_pcb_file.C_kicad_pcb.C_layer(
                    number=35,
                    name="F.Paste",
                    type=C_kicad_pcb_file.C_kicad_pcb.C_layer.E_type.user,
                ),
                C_kicad_pcb_file.C_kicad_pcb.C_layer(
                    number=36,
                    name="B.SilkS",
                    type=C_kicad_pcb_file.C_kicad_pcb.C_layer.E_type.user,
                    alias="B.Silkscreen",
                ),
                C_kicad_pcb_file.C_kicad_pcb.C_layer(
                    number=37,
                    name="F.SilkS",
                    type=C_kicad_pcb_file.C_kicad_pcb.C_layer.E_type.user,
                    alias="F.Silkscreen",
                ),
                C_kicad_pcb_file.C_kicad_pcb.C_layer(
                    number=38,
                    name="B.Mask",
                    type=C_kicad_pcb_file.C_kicad_pcb.C_layer.E_type.user,
                ),
                C_kicad_pcb_file.C_kicad_pcb.C_layer(
                    number=39,
                    name="F.Mask",
                    type=C_kicad_pcb_file.C_kicad_pcb.C_layer.E_type.user,
                ),
                C_kicad_pcb_file.C_kicad_pcb.C_layer(
                    number=40,
                    name="Dwgs.User",
                    type=C_kicad_pcb_file.C_kicad_pcb.C_layer.E_type.user,
                    alias="User.Drawings",
                ),
                C_kicad_pcb_file.C_kicad_pcb.C_layer(
                    number=41,
                    name="Cmts.User",
                    type=C_kicad_pcb_file.C_kicad_pcb.C_layer.E_type.user,
                    alias="User.Comments",
                ),
                C_kicad_pcb_file.C_kicad_pcb.C_layer(
                    number=42,
                    name="Eco1.User",
                    type=C_kicad_pcb_file.C_kicad_pcb.C_layer.E_type.user,
                    alias="User.Eco1",
                ),
                C_kicad_pcb_file.C_kicad_pcb.C_layer(
                    number=43,
                    name="Eco2.User",
                    type=C_kicad_pcb_file.C_kicad_pcb.C_layer.E_type.user,
                    alias="User.Eco2",
                ),
                C_kicad_pcb_file.C_kicad_pcb.C_layer(
                    number=44,
                    name="Edge.Cuts",
                    type=C_kicad_pcb_file.C_kicad_pcb.C_layer.E_type.user,
                ),
                C_kicad_pcb_file.C_kicad_pcb.C_layer(
                    number=45,
                    name="Margin",
                    type=C_kicad_pcb_file.C_kicad_pcb.C_layer.E_type.user,
                ),
                C_kicad_pcb_file.C_kicad_pcb.C_layer(
                    number=46,
                    name="B.CrtYd",
                    type=C_kicad_pcb_file.C_kicad_pcb.C_layer.E_type.user,
                    alias="B.Courtyard",
                ),
                C_kicad_pcb_file.C_kicad_pcb.C_layer(
                    number=47,
                    name="F.CrtYd",
                    type=C_kicad_pcb_file.C_kicad_pcb.C_layer.E_type.user,
                    alias="F.Courtyard",
                ),
                C_kicad_pcb_file.C_kicad_pcb.C_layer(
                    number=48,
                    name="B.Fab",
                    type=C_kicad_pcb_file.C_kicad_pcb.C_layer.E_type.user,
                ),
                C_kicad_pcb_file.C_kicad_pcb.C_layer(
                    number=49,
                    name="F.Fab",
                    type=C_kicad_pcb_file.C_kicad_pcb.C_layer.E_type.user,
                ),
                C_kicad_pcb_file.C_kicad_pcb.C_layer(
                    number=50,
                    name="User.1",
                    type=C_kicad_pcb_file.C_kicad_pcb.C_layer.E_type.user,
                ),
                C_kicad_pcb_file.C_kicad_pcb.C_layer(
                    number=51,
                    name="User.2",
                    type=C_kicad_pcb_file.C_kicad_pcb.C_layer.E_type.user,
                ),
                C_kicad_pcb_file.C_kicad_pcb.C_layer(
                    number=52,
                    name="User.3",
                    type=C_kicad_pcb_file.C_kicad_pcb.C_layer.E_type.user,
                ),
                C_kicad_pcb_file.C_kicad_pcb.C_layer(
                    number=53,
                    name="User.4",
                    type=C_kicad_pcb_file.C_kicad_pcb.C_layer.E_type.user,
                ),
                C_kicad_pcb_file.C_kicad_pcb.C_layer(
                    number=54,
                    name="User.5",
                    type=C_kicad_pcb_file.C_kicad_pcb.C_layer.E_type.user,
                ),
                C_kicad_pcb_file.C_kicad_pcb.C_layer(
                    number=55,
                    name="User.6",
                    type=C_kicad_pcb_file.C_kicad_pcb.C_layer.E_type.user,
                ),
                C_kicad_pcb_file.C_kicad_pcb.C_layer(
                    number=56,
                    name="User.7",
                    type=C_kicad_pcb_file.C_kicad_pcb.C_layer.E_type.user,
                ),
                C_kicad_pcb_file.C_kicad_pcb.C_layer(
                    number=57,
                    name="User.8",
                    type=C_kicad_pcb_file.C_kicad_pcb.C_layer.E_type.user,
                ),
                C_kicad_pcb_file.C_kicad_pcb.C_layer(
                    number=58,
                    name="User.9",
                    type=C_kicad_pcb_file.C_kicad_pcb.C_layer.E_type.user,
                ),
            ]
        )
        setup: C_setup = field(default_factory=C_setup)
        properties: Optional[list[C_properties]] = None
        nets: list[C_net] = field(
            **sexp_field(multidict=True),
            default_factory=lambda: [
                C_kicad_pcb_file.C_kicad_pcb.C_net(number=0, name="")
            ],
        )
        footprints: list[C_pcb_footprint] = field(
            **sexp_field(multidict=True), default_factory=list
        )
        vias: list[C_via] = field(**sexp_field(multidict=True), default_factory=list)
        zones: list[C_zone] = field(**sexp_field(multidict=True), default_factory=list)
        # target??
        # embedded_fonts
        # embedded_files
        segments: list[C_segment] = field(
            **sexp_field(multidict=True), default_factory=list
        )
        arcs: list[C_arc_segment] = field(
            **sexp_field(multidict=True), default_factory=list
        )

        gr_lines: list[C_line] = field(
            **sexp_field(multidict=True), default_factory=list
        )
        gr_arcs: list[C_arc] = field(**sexp_field(multidict=True), default_factory=list)
        gr_curves: list[C_curve] = field(
            **sexp_field(multidict=True), default_factory=list
        )
        gr_polys: list[C_polygon] = field(
            **sexp_field(multidict=True), default_factory=list
        )
        gr_circles: list[C_circle] = field(
            **sexp_field(multidict=True), default_factory=list
        )
        gr_rects: list[C_rect] = field(
            **sexp_field(multidict=True), default_factory=list
        )
        gr_images: list[C_image] = field(
            **sexp_field(multidict=True), default_factory=list
        )
        gr_texts: list[C_text] = field(
            **sexp_field(multidict=True), default_factory=list
        )
        gr_textboxes: list[C_textbox] = field(
            **sexp_field(multidict=True), default_factory=list
        )
        tables: list[C_table] = field(
            **sexp_field(multidict=True), default_factory=list
        )
        dimensions: list[C_dimension] = field(
            **sexp_field(multidict=True), default_factory=list
        )
        groups: list[C_group] = field(
            **sexp_field(multidict=True), default_factory=list
        )
        generated: Optional[C_generated] = None
        targets: list[C_target] = field(
            **sexp_field(multidict=True), default_factory=list
        )
        # TODO
        # enbedded_fonts: list[C_embedded_font] = field(
        #    **sexp_field(multidict=True), default_factory=list
        # )
        # enbedded_files: list[C_embedded_file] = field(
        #    **sexp_field(multidict=True), default_factory=list
        # )
        unknown: CatchAll = None

    kicad_pcb: C_kicad_pcb

    @staticmethod
    def skeleton(
        generator: str,
        generator_version: str,
        version: int = KICAD_PCB_VERSION,
    ) -> "C_kicad_pcb_file":
        return C_kicad_pcb_file(
            kicad_pcb=C_kicad_pcb_file.C_kicad_pcb(
                version=version,
                generator=generator,
                generator_version=generator_version,
            )
        )


@dataclass
class C_kicad_footprint_file(SEXP_File):
    @dataclass(kw_only=True)
    class C_footprint_in_file(C_footprint):
        descr: Optional[str] = None
        tags: Optional[list[str]] = None
        version: int = field(**sexp_field(assert_value=20240108), default=20240108)
        generator: str
        generator_version: str = ""
        tedit: Optional[str] = None
        unknown: CatchAll = None

    footprint: C_footprint_in_file


@dataclass
class C_fields:
    @dataclass
    class C_field:
        name: str
        value: Optional[str] = field(**sexp_field(positional=True), default=None)

    fields: dict[str, C_field] = field(
        **sexp_field(multidict=True, key=lambda x: x.name), default_factory=dict
    )


@dataclass
class C_kicad_netlist_file(SEXP_File):
    @dataclass
    class C_netlist:
        @dataclass
        class C_components:
            @dataclass(kw_only=True)
            class C_component:
                @dataclass
                class C_property:
                    name: str
                    value: str

                @dataclass
                class C_libsource:
                    lib: str
                    part: str
                    description: str

                @dataclass
                class C_sheetpath:
                    names: str
                    tstamps: str

                ref: str
                value: str
                footprint: str
                propertys: dict[str, C_property] = field(
                    **sexp_field(multidict=True, key=lambda x: x.name),
                    default_factory=dict,
                )
                tstamps: str
                fields: C_fields = field(default_factory=C_fields)
                sheetpath: Optional[C_sheetpath] = None
                libsource: Optional[C_libsource] = None

            comps: list[C_component] = field(
                **sexp_field(multidict=True), default_factory=list
            )

        @dataclass
        class C_nets:
            @dataclass
            class C_net:
                @dataclass
                class C_node:
                    ref: str
                    pin: str
                    pintype: Optional[str] = None
                    pinfunction: Optional[str] = None

                code: int
                name: str
                nodes: list[C_node] = field(
                    **sexp_field(multidict=True), default_factory=list
                )

            nets: list[C_net] = field(
                **sexp_field(multidict=True),
                default_factory=lambda: [
                    C_kicad_netlist_file.C_netlist.C_nets.C_net(code=0, name="")
                ],
            )

        @dataclass
        class C_design:
            @dataclass
            class C_sheet:
                @dataclass
                class C_title_block:
                    @dataclass
                    class C_comment:
                        number: str
                        value: str

                    title: str
                    company: str
                    rev: str
                    date: str
                    source: str
                    comment: list[C_comment] = field(
                        **sexp_field(multidict=True), default_factory=list
                    )

                number: str
                name: str
                tstamps: str
                title_block: C_title_block

            source: str
            date: str
            tool: str
            sheet: C_sheet

        @dataclass
        class C_libparts:
            @dataclass
            class C_libpart:
                @dataclass
                class C_footprints:
                    @dataclass
                    class C_fp:
                        fp: str = field(**sexp_field(positional=True))

                    fps: list[C_fp] = field(
                        **sexp_field(multidict=True), default_factory=list
                    )

                @dataclass
                class C_pins:
                    @dataclass
                    class C_pin:
                        num: str
                        name: str
                        type: str

                    pin: list[C_pin] = field(
                        **sexp_field(multidict=True), default_factory=list
                    )

                lib: str
                part: str
                fields: C_fields = field(default_factory=C_fields)
                pins: Optional[C_pins] = None
                footprints: Optional[C_footprints] = None

            libparts: list[C_libpart] = field(
                **sexp_field(multidict=True), default_factory=list
            )

        @dataclass
        class C_libraries:
            # TODO
            pass

        version: str = field(**sexp_field(assert_value="E"))
        components: C_components
        nets: C_nets
        design: Optional[C_design] = None
        libparts: C_libparts = field(default_factory=C_libparts)
        libraries: C_libraries = field(default_factory=C_libraries)

    export: C_netlist


@dataclass
class C_kicad_fp_lib_table_file(SEXP_File):
    @dataclass
    class C_fp_lib_table:
        @dataclass
        class C_lib:
            name: str
            type: str
            uri: str
            options: str
            descr: str

        version: int | None = field(default=None, **sexp_field())
        libs: list[C_lib] = field(**sexp_field(multidict=True), default_factory=list)

    fp_lib_table: C_fp_lib_table

    @classmethod
    def skeleton(cls, version: int = 7) -> "C_kicad_fp_lib_table_file":
        return cls(cls.C_fp_lib_table(version=version, libs=[]))
