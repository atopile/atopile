import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import IntEnum, StrEnum, auto
from pathlib import Path
from typing import Any, Optional, Self, override

from dataclasses_json import CatchAll, Undefined, config, dataclass_json
from more_itertools import first

from faebryk.libs.kicad.fileformats_common import (
    UUID,
    C_data,
    C_effects,
    C_property_base,
    C_pts,
    C_stroke,
    C_wh,
    C_xy,
    C_xyr,
    C_xyz,
    HasPropertiesMixin,
    gen_uuid,
)
from faebryk.libs.sexp.dataclass_sexp import (
    JSON_File,
    SEXP_File,
    Symbol,
    SymEnum,
    sexp_field,
)
from faebryk.libs.util import ConfigFlag, lazy_split

logger = logging.getLogger(__name__)

RICH_PRINT = ConfigFlag("FF_RICH_PRINT")

# TODO find complete examples of the fileformats, maybe in the kicad repo


KICAD_PCB_VERSION = 20241229


@dataclass
class _SingleOrMultiLayer:
    layer: str | None = field(**sexp_field(order=50), default=None)
    layers: list[str] | None = field(**sexp_field(order=51), default=None)

    def get_layers(self) -> list[str]:
        if self.layer is not None:
            return [self.layer]
        if self.layers is not None:
            return self.layers
        return []

    def apply_to_layers(self, func: Callable[[str], str]):
        if self.layer is not None:
            self.layer = func(self.layer)
        if self.layers is not None:
            self.layers = [func(layer) for layer in self.layers]

    def __post_init__(self):
        if self.layer is not None and self.layers is not None:
            raise ValueError("layer and layers cannot both be provided")


@dataclass
class _CuItemWithSoldermaskLayers(_SingleOrMultiLayer):
    def __post_init__(self):
        super().__post_init__()

        if not self.layers:
            return

        # only copper and mask layers
        assert all(
            layer.endswith(".Cu") or layer.endswith(".Mask") for layer in self.layers
        )

        # single copper layer
        assert len([layer for layer in self.layers if layer.endswith(".Cu")]) == 1

        # max one soldermask layer
        assert len([layer for layer in self.layers if layer.endswith(".Mask")]) <= 1

        # copper and mask on the same side
        assert not ("F.Cu" in self.layers and "B.Mask" in self.layers)
        assert not ("B.Cu" in self.layers and "F.Mask" in self.layers)

        # no mask layer when track is on internal layer
        if any(layer.startswith("In") for layer in self.layers):
            assert not any(layer.endswith(".Mask") for layer in self.layers)


@dataclass_json(undefined=Undefined.INCLUDE)
@dataclass(kw_only=True)
class C_kicad_drc_report_file(JSON_File):
    """
    Represents the structure of a KiCad DRC report file (JSON format).
    Based on an example DRC report.
    """

    class C_Severity(StrEnum):
        INFO = auto()
        EXCLUSION = auto()
        ACTION = auto()
        WARNING = auto()
        ERROR = auto()
        DEBUG = auto()

    @dataclass_json(undefined=Undefined.INCLUDE)
    @dataclass
    class C_Position:
        x: float
        y: float
        unknown: CatchAll = None

    @dataclass_json(undefined=Undefined.INCLUDE)
    @dataclass
    class C_Item:
        description: str
        pos: "C_kicad_drc_report_file.C_Position"
        uuid: UUID
        unknown: CatchAll = None

    @dataclass_json(undefined=Undefined.INCLUDE)
    @dataclass
    class C_Violation:
        class C_Type(StrEnum):
            """
            Extracted from pcbnew/drc/drc_item.cpp
            """

            unconnected_items = auto()
            shorting_items = auto()
            items_not_allowed = auto()
            text_on_edge_cuts = auto()
            clearance = auto()
            creepage = auto()
            tracks_crossing = auto()
            copper_edge_clearance = auto()
            zones_intersect = auto()
            isolated_copper = auto()
            starved_thermal = auto()
            via_dangling = auto()
            track_dangling = auto()
            hole_clearance = auto()
            hole_to_hole = auto()
            holes_co_located = auto()
            connection_width = auto()
            track_width = auto()
            track_angle = auto()
            track_segment_length = auto()
            annular_width = auto()
            drill_out_of_range = auto()
            via_diameter = auto()
            padstack = auto()
            padstack_invalid = auto()
            microvia_drill_out_of_range = auto()
            courtyards_overlap = auto()
            missing_courtyard = auto()
            malformed_courtyard = auto()
            pth_inside_courtyard = auto()
            npth_inside_courtyard = auto()
            item_on_disabled_layer = auto()
            invalid_outline = auto()
            duplicate_footprints = auto()
            missing_footprint = auto()
            extra_footprint = auto()
            net_conflict = auto()
            footprint_symbol_mismatch = auto()
            footprint_filters_mismatch = auto()
            lib_footprint_issues = auto()
            lib_footprint_mismatch = auto()
            unresolved_variable = auto()
            assertion_failure = auto()
            generic_warning = auto()
            generic_error = auto()
            copper_sliver = auto()
            solder_mask_bridge = auto()
            silk_over_copper = auto()
            silk_edge_clearance = auto()
            silk_overlap = auto()
            text_height = auto()
            text_thickness = auto()
            length_out_of_range = auto()
            skew_out_of_range = auto()
            too_many_vias = auto()
            diff_pair_gap_out_of_range = auto()
            diff_pair_uncoupled_length_too_long = auto()
            footprint = auto()
            footprint_type_mismatch = auto()
            through_hole_pad_without_hole = auto()
            mirrored_text_on_front_layer = auto()
            nonmirrored_text_on_back_layer = auto()

        description: str
        items: list["C_kicad_drc_report_file.C_Item"]
        severity: "C_kicad_drc_report_file.C_Severity"
        type: C_Type
        # excluded: bool = False
        unknown: CatchAll = None

    # https://schemas.kicad.org/drc.v1.json
    schema: Optional[str] = field(metadata=config(field_name="$schema"), default=None)
    date: str  # ISO8601
    kicad_version: str  # Major.Minor.Patch
    source: str
    coordinate_units: str  # mm, in, mil, ..

    violations: list[C_Violation] = field(default_factory=list)
    unconnected_items: list[C_Violation] = field(default_factory=list)
    schematic_parity: list[C_Violation] = field(default_factory=list)
    unknown: CatchAll = None


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

    def __rich_repr__(self):
        yield "**kwargs", "..."


@dataclass
class C_text_layer:
    class E_knockout(SymEnum):
        knockout = auto()

    layer: str = field(**sexp_field(positional=True))
    knockout: Optional[E_knockout] = field(**sexp_field(positional=True), default=None)


class E_fill(SymEnum):
    yes = auto()
    no = auto()
    none = auto()
    solid = auto()


@dataclass(kw_only=True)
class C_shape(_SingleOrMultiLayer):
    solder_mask_margin: float | None = None
    stroke: C_stroke | None = None
    fill: E_fill | None = None
    locked: Optional[bool] = None
    uuid: UUID | None = field(**sexp_field(order=100), default_factory=gen_uuid)


# gr_vector
# gr_line
# fp_line
@dataclass(kw_only=True)
class C_line(C_shape):
    start: C_xy = field(**sexp_field(order=-2))
    end: C_xy = field(**sexp_field(order=-1))


# gr_circle
# fp_circle
@dataclass(kw_only=True)
class C_circle(C_shape):
    center: C_xy = field(**sexp_field(order=-2))
    end: C_xy = field(**sexp_field(order=-1))


# gr_arc
# fp_arc
@dataclass(kw_only=True)
class C_arc(C_shape):
    start: C_xy = field(**sexp_field(order=-3))
    mid: C_xy = field(**sexp_field(order=-2))
    end: C_xy = field(**sexp_field(order=-1))


# gr_curve
# fp_curve
@dataclass(kw_only=True)
class C_curve(C_shape):
    pts: C_pts = field(**sexp_field(order=-1))


# gr_bbox
# gr_rect
# fp_rect
@dataclass(kw_only=True)
class C_rect(C_shape):
    start: C_xy = field(**sexp_field(order=-2))
    end: C_xy = field(**sexp_field(order=-1))


# gr_poly
# fp_poly
@dataclass(kw_only=True)
class C_polygon(C_shape):
    pts: C_pts = field(**sexp_field(order=-1))
    uuid: UUID | None = None

    def __post_init__(self):
        assert len(self.pts.xys) > 0 or len(self.pts.arcs) > 0, (
            "Polygon must have at least one point or arc"
        )


@dataclass(kw_only=True)
class C_render_cache:
    text: str = field(**sexp_field(positional=True), default="")
    rotation: float = field(**sexp_field(positional=True), default=0)
    polygons: list[C_polygon] = field(
        **sexp_field(multidict=True), default_factory=list
    )
    # TODO: KiCad:parseRenderCache


@dataclass(kw_only=True)
class C_text:
    text: str = field(**sexp_field(positional=True))
    at: C_xyr
    layer: C_text_layer
    uuid: UUID = field(default_factory=gen_uuid)
    effects: C_effects
    render_cache: C_render_cache | None = None


@dataclass(kw_only=True)
class C_fp_text:  # TODO: Inherit from C_text maybe ?
    class E_type(SymEnum):
        user = auto()
        reference = auto()
        value = auto()

    @dataclass(kw_only=True)
    class C_fp_text_effects(C_effects):
        # driven by the outer hide in C_fp_text
        hide: bool | None = None

    type: E_type = field(**sexp_field(positional=True))
    text: str = field(**sexp_field(positional=True))
    at: C_xyr
    layer: C_text_layer
    hide: bool | None = None
    uuid: UUID = field(default_factory=gen_uuid)
    effects: C_fp_text_effects
    unlocked: bool | None = field(default=False)


@dataclass(kw_only=True)
class C_teardrop:
    enabled: bool = False
    allow_two_segments: bool = False
    prefer_zone_connections: bool = True
    best_length_ratio: float
    max_length: float
    best_width_ratio: float
    max_width: float
    curved_edges: bool
    filter_ratio: float


@dataclass(kw_only=True)
class C_image:
    at: C_xy
    layer: str
    scale: float = 1.0
    data: C_data | None = None
    uuid: UUID = field(default_factory=gen_uuid)


@dataclass(kw_only=True)
class C_text_box:
    @dataclass
    class C_margins:
        left: int = field(**sexp_field(positional=True))
        top: int = field(**sexp_field(positional=True))
        right: int = field(**sexp_field(positional=True))
        bottom: int = field(**sexp_field(positional=True))

    @dataclass
    class C_span:
        cols: int = field(**sexp_field(positional=True))
        rows: int = field(**sexp_field(positional=True))

    text: str = field(**sexp_field(positional=True))
    locked: bool = False
    start: C_xy | None = None
    end: C_xy | None = None
    pts: C_pts | None = None
    angle: float | None = None
    stroke: C_stroke | None = None
    border: bool | None = None
    margins: C_margins | None = None
    layer: str
    span: Optional[C_span] = None
    effects: C_effects  # TODO: KiCad:parseEDA_TEXT
    render_cache: C_render_cache | None = None
    uuid: UUID = field(default_factory=gen_uuid)

    def __post_init__(self):
        if (self.end is None or self.start is None) and self.pts is None:
            raise ValueError("Either start + end or pts must be specified")


@dataclass(kw_only=True)
class C_table:
    @dataclass
    class C_cells:
        @dataclass
        class C_table_cell(C_text_box):
            pass

        table_cells: list[C_table_cell] = field(
            **sexp_field(multidict=True), default_factory=list
        )

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

    column_count: int
    locked: Optional[bool] = None
    layer: str
    column_widths: list[float]
    row_heights: list[float]
    cells: C_cells
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
        override_value: str | int | None = None
        suppress_zeroes: bool = False

        def __post_init__(self):
            if self.units < 0 or self.units > 4:
                raise ValueError(f"units must be between 0 and 4, got {self.units}")
            if self.units_format < 0 or self.units_format > 3:
                raise ValueError(
                    f"units_format must be between 0 and 3, got {self.units_format}"
                )

    @dataclass
    class C_style:
        class E_arrow_direction(SymEnum):
            inward = auto()
            outward = auto()

        thickness: float | None = None
        arrow_length: float | None = None
        arrow_direction: E_arrow_direction = E_arrow_direction.outward
        text_position_mode: int | None = None
        extension_height: float | None = None
        extension_offset: float | None = None
        keep_text_aligned: bool = True
        text_frame: int | None = None

    @dataclass
    class C_xypts:
        xys: list[C_xy] = field(**sexp_field(multidict=True), default_factory=list)

    class E_type(SymEnum):
        aligned = auto()
        orthogonal = auto()
        leader = auto()
        center = auto()
        radial = auto()

    type: E_type
    layer: str
    uuid: UUID = field(default_factory=gen_uuid)
    pts: C_xypts
    height: float
    orientation: float | None = None
    leader_length: float | None = None
    format: C_format | None = None
    style: C_style | None = None
    gr_text: C_text


@dataclass(kw_only=True)
class C_embedded_file:
    class C_type(SymEnum):
        other = auto()
        model = auto()
        font = auto()
        datasheet = auto()
        worksheet = auto()

    name: str
    type: C_type
    data: C_data | None = None
    """
    base64 encoded data
    """
    checksum: str | None = None  # MD5 hash of the file content

    @staticmethod
    def make_checksum(data: bytes) -> None:
        # from kicad:libs/kimath/include/mmh3_hash.h
        # FIXME
        # import mmh3

        # SEED = 0xABBA2345
        # return mmh3.mmh3_x64_128_digest(data, SEED).hex().upper()
        return None


@dataclass
class C_embedded_files:
    # are_fonts_embedded: bool = False
    files: dict[str, C_embedded_file] = field(
        default_factory=dict, **sexp_field(multidict=True, key=lambda x: x.name)
    )


@dataclass(kw_only=True)
class C_group:
    name: str | None = field(**sexp_field(positional=True), default=None)
    uuid: UUID = field(default_factory=gen_uuid)
    locked: bool | None = None
    members: list[UUID] = field(default_factory=list)


@dataclass
class C_net:
    number: int = field(**sexp_field(positional=True))
    name: str | None = field(**sexp_field(positional=True))


@dataclass(kw_only=True)
class C_footprint(HasPropertiesMixin):
    class E_attr(SymEnum):
        smd = auto()
        dnp = auto()
        board_only = auto()
        through_hole = auto()
        exclude_from_pos_files = auto()
        exclude_from_bom = auto()
        allow_missing_courtyard = auto()

    @dataclass(kw_only=True)
    class C_property(C_property_base):
        name: str = field(**sexp_field(positional=True))
        value: str = field(**sexp_field(positional=True))
        at: C_xyr
        layer: C_text_layer
        hide: bool = False
        uuid: UUID = field(default_factory=gen_uuid)
        effects: C_fp_text.C_fp_text_effects

    @dataclass
    class C_footprint_polygon(C_polygon):
        uuid: UUID | None = field(default_factory=gen_uuid)

    @dataclass(kw_only=True)
    class C_rect_delta:
        width: float
        height: float

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
            trapezoid = auto()
            chamfered_rect = auto()

        @dataclass
        class C_options:
            class E_clearance(SymEnum):
                outline = auto()
                convexhull = auto()

            class E_anchor(SymEnum):
                rect = auto()
                circle = auto()

            clearance: E_clearance | None = None
            anchor: E_anchor | None = None

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
            none = "none"

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
                    rect = auto()
                    roundrect = auto()
                    oval = auto()
                    trapezoid = auto()
                    custom = auto()

                class E_zone_connection(IntEnum):
                    INHERITED = -1
                    NONE = 0
                    THERMAL = 1
                    FULL = 2
                    THT_THERMAL = 3

                class E_chamfer(SymEnum):
                    top_left = "chamfer_top_left"
                    top_right = "chamfer_top_right"
                    bottom_left = "chamfer_bottom_left"
                    bottom_right = "chamfer_bottom_right"

                shape: E_shape
                size: C_wh | None = None
                offset: C_xy | None = None
                rect_delta: C_wh | None = None
                roundrect_rratio: float | None = None
                chamfer_ratio: float | None = None
                chamfer: list[E_chamfer] | None = None
                thermal_bridge_width: float | None = None
                thermal_gap: float | None = None
                thermal_bridge_angle: float | None = None
                zone_connect: E_zone_connection | None = None
                clearance: float | None = None
                tenting: "C_footprint.C_pad.C_tenting | None" = None
                options: "C_footprint.C_pad.C_options | None" = None
                primitives: list[C_shape] | None = None

            mode: E_mode
            layers: list[C_layer] = field(**sexp_field(multidict=True))

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
        at: C_xyr
        size: C_wh
        rect_delta: Optional[C_rect_delta] = None
        drill: Optional[C_drill] = None
        layers: list[str]
        die_length: Optional[float] = None
        solder_mask_margin: Optional[float] = None
        solder_paste_margin: Optional[float] = None
        solder_paste_margin_ratio: Optional[float] = None
        clearance: Optional[float] = None
        teardrops: Optional[C_teardrop] = None
        zone_connect: Optional[C_padstack.C_layer.E_zone_connection] = None
        thermal_bridge_width: Optional[float] = None
        thermal_bridge_angle: Optional[float] = None
        thermal_gap: Optional[float] = None
        roundrect_rratio: Optional[float] = None
        chamfer_ratio: Optional[float] = None
        chamfer: Optional[E_chamfer] = None
        properties: Optional[E_property] = None
        net: C_net | None = None
        options: Optional[C_options] = None
        padstack: Optional[C_padstack] = None  # see parsePadstack
        # TODO: primitives: gr_line, gr_arc, gr_circle, gr_curve, gr_rect, gr_bbox or
        # gr_poly
        remove_unused_layers: bool | None = None
        keep_end_layers: bool | None = None
        tenting: Optional[C_tenting] = None
        zone_layer_connections: Optional[list[str]] = None
        uuid: UUID = field(default_factory=gen_uuid)
        unknown: CatchAll = None

    class E_embedded_fonts(SymEnum):
        yes = auto()
        no = auto()

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
    embedded_fonts: E_embedded_fonts | None = None
    embedded_files: C_embedded_files | None = None
    component_classes: list[str] | None = None
    models: list[C_model] = field(**sexp_field(multidict=True), default_factory=list)

    @property
    def base_name(self) -> str:
        return self.name.split(":", 1)[-1]

    @override
    def add_property(self, name: str, value: str):
        self.propertys[name] = C_footprint.C_property(
            name=name,
            value=value,
            at=C_xyr(x=0, y=0, r=0),
            layer=C_text_layer("User.9"),
            effects=C_fp_text.C_fp_text_effects(
                font=C_fp_text.C_fp_text_effects.C_font(
                    size=C_wh(w=0.125, h=0.125),
                    thickness=0.01875,
                    unresolved_font_name=None,
                ),
                justifys=[],
                hide=True,
            ),
        )

    def __rich_repr__(self):
        yield "name", self.name
        yield "**kwargs", "..."


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
            class E_type(StrEnum):
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
                layerselection: Symbol = Symbol("0x00010fc_ffffffff")
                plot_on_all_layers_selection: Symbol = Symbol("0x0000000_00000000")
                disableapertmacros: bool = False
                usegerberextensions: bool = False
                usegerberattributes: bool = True
                usegerberadvancedattributes: bool = True
                creategerberjobfile: bool = True
                dashed_line_dash_ratio: float = 12.0
                dashed_line_gap_ratio: float = 3.0
                svgprecision: int = 4
                plotframeref: bool = False
                viasonmask: bool | None = None
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
                plot_black_and_white: bool = field(default=True)
                plotinvisibletext: bool = field(default=False)
                sketchpadsonfab: bool = field(default=False)
                plotreference: bool = field(default=True)
                plotvalue: bool = field(default=True)
                plotpadnumbers: bool = field(default=False)
                hidednponfab: bool = field(default=False)
                sketchdnponfab: bool = field(default=True)
                crossoutdnponfab: bool = field(default=True)
                plotfptext: bool = field(default=True)
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

        @dataclass(kw_only=True)
        class C_pcb_footprint(C_footprint):
            @dataclass(kw_only=True)
            class C_pad_no_net(C_footprint.C_pad):
                net: C_net | None = None

            uuid: UUID = field(**sexp_field(order=-15))
            at: C_xyr = field(**sexp_field(order=-10))
            pads: list[C_pad_no_net] = field(
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
                    name: str
                    size: C_xy | None = None
                    thermal_gap: float | None = None
                    thermal_bridge_width: float | None = None
                    thermal_bridge_angle: float | None = None
                    zone_connect: int | None = None

                mode: E_mode = field(**sexp_field(positional=True))
                layers: list[C_layer] = field(default_factory=list)

            @dataclass
            class C_tenting:
                front: bool = False
                back: bool = False

            # blind: bool = False
            # micro: bool = False
            at: C_xy
            size: float
            drill: float
            layers: list[str] = field(default_factory=list)
            net: int

            # Legacy options replaced by padstack structure:
            remove_unused_layers: bool | None = None
            keep_end_layers: bool | None = None
            zone_layer_connections: list[str] | None = None

            padstack: C_padstack | None = None
            teardrops: C_teardrop | None = None
            tenting: C_tenting | None = None
            free: bool | None = None
            locked: bool | None = None
            uuid: UUID = field(default_factory=gen_uuid)
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

            @dataclass
            class C_placement:
                class E_rule_area_placement_source_type(SymEnum):
                    sheetname = auto()
                    component_class = auto()

                source_type: E_rule_area_placement_source_type | None = None
                source: str | None = None
                enabled: bool = True

            @dataclass(kw_only=True)
            class C_filled_polygon:
                layer: str
                # FIXME: decode (island), a bracketed positional
                # We're currently relying on the CatchAll to re-serialise it
                pts: C_pts
                unknown: CatchAll = None

            @dataclass
            class C_attr:
                @dataclass
                class C_teardrop:
                    class E_type(SymEnum):
                        padvia = auto()
                        track_end = auto()

                    type: E_type

            net: int
            net_name: str
            layers: list[str] | None = None
            # NOTE: if zones is both front and back Cu layer then layer="F&B.Cu"
            # else layer="F.Cu" "B.Cu" "In1.Cu" ...
            uuid: UUID
            name: Optional[str] = None
            # locked: Optional[bool] = None #TODO: legacy -> delete?
            hatch: C_hatch
            priority: Optional[int] = None
            attr: C_attr | None = None
            connect_pads: C_connect_pads
            min_thickness: float
            filled_areas_thickness: bool
            fill: C_fill
            keepout: Optional[C_keepout] = None
            polygon: C_polygon
            filled_polygon: list[C_filled_polygon] = field(
                **sexp_field(multidict=True), default_factory=list
            )
            placement: C_placement | None = None
            unknown: CatchAll = None

        @dataclass(kw_only=True)
        class C_segment(_CuItemWithSoldermaskLayers):
            start: C_xy = field(**sexp_field(order=-3))
            end: C_xy = field(**sexp_field(order=-2))
            width: float = field(**sexp_field(order=-1))
            net: int
            uuid: UUID
            solder_mask_margin: float | None = None
            locked: bool | None = None

        @dataclass(kw_only=True)
        class C_arc_segment(_CuItemWithSoldermaskLayers):
            start: C_xy
            mid: C_xy
            end: C_xy
            width: float
            net: int
            uuid: UUID
            solder_mask_margin: float | None = None
            locked: bool | None = None

        @dataclass
        class C_generated:
            uuid: UUID
            type: str
            name: str
            layer: str
            members: list[UUID]
            locked: bool | None = None
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
            default_factory=lambda: [C_net(number=0, name="")],
        )
        footprints: list[C_pcb_footprint] = field(
            **sexp_field(multidict=True), default_factory=list
        )
        vias: list[C_via] = field(**sexp_field(multidict=True), default_factory=list)
        zones: list[C_zone] = field(**sexp_field(multidict=True), default_factory=list)
        embedded_fonts: bool | None = None
        embedded_files: C_embedded_files | None = None
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
        images: list[C_image] = field(
            **sexp_field(multidict=True), default_factory=list
        )
        gr_texts: list[C_text] = field(
            **sexp_field(multidict=True), default_factory=list
        )
        gr_text_boxs: list[C_text_box] = field(
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
        generateds: list[C_generated] = field(
            **sexp_field(multidict=True), default_factory=list
        )
        targets: list[C_target] = field(
            **sexp_field(multidict=True), default_factory=list
        )

        unknown: CatchAll = None

        def __rich_repr__(self):
            yield "**kwargs", "..."

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
        descr: Optional[str] = field(default=None, **sexp_field(order=-1))
        tags: Optional[list[str]] = field(default=None, **sexp_field(order=-1))
        version: int = field(**sexp_field(order=-1), default=KICAD_PCB_VERSION)
        generator: str = field(**sexp_field(order=-1), default="faebryk")
        generator_version: str = field(**sexp_field(order=-1), default="latest")
        tedit: Optional[str] = field(default=None, **sexp_field(order=-1))
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
            uri: Path
            options: str
            descr: str

        version: int | None = field(default=None, **sexp_field())
        libs: dict[str, C_lib] = field(
            **sexp_field(multidict=True, key=lambda x: x.name), default_factory=dict
        )

    fp_lib_table: C_fp_lib_table

    @classmethod
    def skeleton(cls, version: int = 7) -> "C_kicad_fp_lib_table_file":
        return cls(cls.C_fp_lib_table(version=version, libs={}))


@dataclass
class C_kicad_model_file:
    """
    Wrapper around step file
    """

    # TODO: consider finding a step file lib

    _raw: bytes

    def __post_init__(self):
        if not self._raw.startswith(b"ISO-10303-21"):
            raise ValueError("Invalid STEP file format")

    @property
    def header(self) -> str:
        # Extract header section between HEADER; and ENDSEC; using regex

        # ISO 10303-21:2016-03, section 5.2:
        # The set of LATIN_CODEPOINT character is equivalent to the basic alphabet
        # in the first and second editions of ISO 10303-21. The UTF-8 representation of
        # code points U+0020 to U+007E is the same as the ISO/IEC 8859-1 characters
        # G(02/00) to G(07/14) that defined the basic alphabet in earlier editions.
        # Use of HIGH_CODEPOINT characters within the exchange structure can be avoided
        # when compatibility with previous editions of ISO 10303-21 is desired.

        # Read till DATA; token ignore any invalid UTF-8 characters that may occur
        # Currently only used to extract filename, so not critical to drop characters
        non_data = first(lazy_split(self._raw, b"DATA;")).decode(
            "utf-8", errors="ignore"
        )

        pattern = r"HEADER;(.*?)ENDSEC;"
        match = re.search(pattern, non_data, re.DOTALL)
        if not match:
            raise ValueError("No HEADER section found in STEP file")
        return match.group(1)

    @property
    def filename(self) -> str:
        # find line with "FILE_NAME"
        # ghetto parse first arg
        header = self.header
        match = re.search(r"FILE_NAME.*?'(.*?)'\s*,", header, re.DOTALL)
        if not match:
            raise ValueError("No FILE_NAME section found in STEP file")
        return match.group(1)

    @classmethod
    def loads(cls, path_or_content: Path | bytes) -> Self:
        if isinstance(path_or_content, Path):
            content = path_or_content.read_bytes()
        else:
            content = path_or_content

        return cls(_raw=content)

    def dumps(self, path: Path | None = None) -> bytes:
        if path is not None:
            path.write_bytes(self._raw)
        return self._raw


if RICH_PRINT:
    # TODO ugly
    del C_kicad_pcb_file.C_kicad_pcb.__rich_repr__
    del C_kicad_project_file.__rich_repr__
    del C_footprint.__rich_repr__
