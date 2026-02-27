import logging
import re
from dataclasses import dataclass, field
from enum import StrEnum, auto
from os import PathLike
from pathlib import Path
from typing import (
    Any,
    Optional,
    Self,
)

from dataclasses_json import (
    CatchAll,
    DataClassJsonMixin,
    Undefined,
    config,
    dataclass_json,
)
from more_itertools import first

from faebryk.libs.util import ConfigFlag, lazy_split

logger = logging.getLogger(__name__)

RICH_PRINT = ConfigFlag("FF_RICH_PRINT")
UUID = str


class JSON_File(DataClassJsonMixin):
    @classmethod
    def loads(cls, path: Path | str) -> "Self":
        if isinstance(path, Path):
            text = path.read_text(encoding="utf-8")
        else:
            text = path
        return cls.from_json(text)

    def dumps(self, path: PathLike | None = None):
        path = Path(path) if path else None
        text = self.to_json(indent=4)  # type: ignore
        if path:
            path.write_text(text, encoding="utf-8")
        return text


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
                    suppress_zeroes: bool = True
                    text_position: int = 0
                    units_format: int = 0
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
                    drill: float = 0.8
                    height: float = 1.27
                    width: float = 2.54
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
                    forty_five_degree_only: Optional[bool] = field(
                        metadata=config(field_name="45_degree_only"), default=None
                    )
                    unknown: CatchAll = None

                zones: C_zones = field(default_factory=C_zones)
                unknown: CatchAll = None

            defaults: C_defaults = field(default_factory=C_defaults)

            @dataclass_json(undefined=Undefined.INCLUDE)
            @dataclass
            class C_diff_pair_dimensions:
                gap: float = 0.0
                via_gap: float = 0.0
                width: float = 0.0
                unknown: CatchAll = None

            diff_pair_dimensions: list[C_diff_pair_dimensions] = field(
                default_factory=list
            )

            # Elements are either strings or [marker_string, comment_string] pairs
            drc_exclusions: list[str] = field(default_factory=list)

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
                creepage: str = "error"
                diff_pair_gap_out_of_range: str = "error"
                diff_pair_uncoupled_length_too_long: str = "error"
                drill_out_of_range: str = "error"
                duplicate_footprints: str = "warning"
                extra_footprint: str = "warning"
                footprint: str = "error"
                footprint_filters_mismatch: str = "ignore"
                footprint_symbol_mismatch: str = "warning"
                footprint_type_mismatch: str = "ignore"
                hole_clearance: str = "error"
                hole_near_hole: Optional[str] = None
                hole_to_hole: str = "warning"
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
                mirrored_text_on_front_layer: str = "warning"
                missing_courtyard: str = "ignore"
                missing_footprint: str = "warning"
                net_conflict: str = "warning"
                nonmirrored_text_on_back_layer: str = "warning"
                npth_inside_courtyard: str = "ignore"
                overlapping_pads: Optional[str] = None
                padstack: str = "warning"
                padstack_invalid: Optional[str] = None
                pth_inside_courtyard: str = "ignore"
                shorting_items: str = "error"
                silk_edge_clearance: str = "warning"
                silk_over_copper: str = "warning"
                silk_overlap: str = "warning"
                skew_out_of_range: str = "error"
                solder_mask_bridge: str = "error"
                starved_thermal: str = "error"
                text_height: str = "warning"
                text_on_edge_cuts: str = "error"
                text_thickness: str = "warning"
                through_hole_pad_without_hole: str = "error"
                too_many_vias: str = "error"
                track_angle: str = "error"
                track_dangling: str = "warning"
                track_segment_length: str = "error"
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
                allow_blind_buried_vias: Optional[bool] = None
                allow_microvias: Optional[bool] = None
                max_error: float = 0.005
                min_clearance: float = 0.0
                min_connection: float = 0.0
                min_copper_edge_clearance: float = 0.5
                min_groove_width: float = 0.0
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
                # legacy field names (pre-v9)
                td_onpadsmd: Optional[bool] = None
                td_onviapad: Optional[bool] = None
                # current field names
                td_onpthpad: bool = True
                td_onsmdpad: bool = True
                td_onvia: bool = True
                td_onroundshapesonly: bool = False
                td_ontrackend: bool = False
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
                diameter: float = 0.0
                drill: float = 0.0
                unknown: CatchAll = None

            via_dimensions: list[C_via_dimensions] = field(default_factory=list)
            zones_allow_external_fillets: bool = False
            zones_use_no_outline: Optional[bool] = None
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
        class C_layer_pair:
            top_layer: Optional[int] = field(
                metadata=config(field_name="topLayer"), default=None
            )
            bottom_layer: Optional[int] = field(
                metadata=config(field_name="bottomLayer"), default=None
            )
            enabled: Optional[bool] = None
            name: Optional[str] = None
            unknown: CatchAll = None

        layer_pairs: list[C_layer_pair] = field(default_factory=list)

        @dataclass_json(undefined=Undefined.INCLUDE)
        @dataclass
        class C_layer_preset:
            name: str = ""
            active_layer: Optional[int] = field(
                metadata=config(field_name="activeLayer"), default=None
            )
            flip_board: Optional[bool] = field(
                metadata=config(field_name="flipBoard"), default=None
            )
            layers: list[int] = field(default_factory=list)
            render_layers: list[str] = field(
                metadata=config(field_name="renderLayers"), default_factory=list
            )
            unknown: CatchAll = None

        layer_presets: list[C_layer_preset] = field(default_factory=list)

        @dataclass_json(undefined=Undefined.INCLUDE)
        @dataclass
        class C_3d_viewport:
            name: str = ""
            xx: float = 0.0
            xy: float = 0.0
            xz: float = 0.0
            xw: float = 0.0
            yx: float = 0.0
            yy: float = 0.0
            yz: float = 0.0
            yw: float = 0.0
            zx: float = 0.0
            zy: float = 0.0
            zz: float = 0.0
            zw: float = 0.0
            wx: float = 0.0
            wy: float = 0.0
            wz: float = 0.0
            ww: float = 0.0
            unknown: CatchAll = None

        three_d_viewports: list[C_3d_viewport] = field(
            metadata=config(field_name="3dviewports"), default_factory=list
        )

        @dataclass_json(undefined=Undefined.INCLUDE)
        @dataclass
        class C_viewports:
            name: str = ""
            x: float = 0.0
            y: float = 0.0
            zoom: float = 1.0
            unknown: CatchAll = None

        viewports: list[C_viewports] = field(default_factory=list)
        unknown: CatchAll = None

    board: C_board = field(default_factory=C_board)

    # Each element is a [uuid, title] pair
    boards: list[list[str]] = field(default_factory=list)

    @dataclass_json(undefined=Undefined.INCLUDE)
    @dataclass
    class C_cvpcb:
        equivalence_files: list[str] = field(default_factory=list)
        unknown: CatchAll = None

    cvpcb: C_cvpcb = field(default_factory=C_cvpcb)

    @dataclass_json(undefined=Undefined.INCLUDE)
    @dataclass
    class C_libraries:
        pinned_footprint_libs: list[str] = field(default_factory=list)
        pinned_symbol_libs: list[str] = field(default_factory=list)
        pinned_design_block_libs: Optional[list[str]] = None
        unknown: CatchAll = None

    libraries: C_libraries = field(default_factory=C_libraries)

    @dataclass_json(undefined=Undefined.INCLUDE)
    @dataclass
    class C_meta:
        filename: str = "example.kicad_pro"
        version: int = 3
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
            priority: int = 2147483647
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
            version: int = 4
            unknown: CatchAll = None

        meta: C_meta = field(default_factory=C_meta)
        net_colors: Optional[Any] = None
        netclass_assignments: Optional[Any] = None

        @dataclass_json(undefined=Undefined.INCLUDE)
        @dataclass
        class C_netclass_pattern:
            netclass: str = ""
            pattern: str = ""
            unknown: CatchAll = None

        netclass_patterns: list[C_netclass_pattern] = field(default_factory=list)
        unknown: CatchAll = None

    net_settings: C_net_settings = field(default_factory=C_net_settings)

    @dataclass_json(undefined=Undefined.INCLUDE)
    @dataclass
    class C_schematic:
        @dataclass_json(undefined=Undefined.INCLUDE)
        @dataclass
        class C_drawing:
            dashed_lines_dash_length_ratio: float = 12.0
            dashed_lines_gap_length_ratio: float = 3.0
            default_bus_thickness: float = 12.0
            default_junction_size: float = 40.0
            default_line_thickness: float = 6.0
            default_text_size: float = 50.0
            default_wire_thickness: float = 6.0
            field_names: list[str] = field(default_factory=list)
            intersheets_ref_own_page: bool = False
            intersheets_ref_prefix: str = ""
            intersheets_ref_short: bool = False
            intersheets_ref_show: bool = False
            intersheets_ref_suffix: str = ""
            junction_size_choice: int = 3
            label_size_ratio: float = 0.25
            operating_point_overlay_i_precision: int = 3
            operating_point_overlay_i_range: str = "~A"
            operating_point_overlay_v_precision: int = 3
            operating_point_overlay_v_range: str = "~V"
            overbar_offset_ratio: float = 1.23
            pin_symbol_size: float = 0.0
            text_offset_ratio: float = 0.08
            unknown: CatchAll = None

        @dataclass_json(undefined=Undefined.INCLUDE)
        @dataclass
        class C_bom_field:
            group_by: bool = False
            label: str = ""
            name: str = ""
            show: bool = True
            unknown: CatchAll = None

        @dataclass_json(undefined=Undefined.INCLUDE)
        @dataclass
        class C_bom_settings:
            exclude_dnp: bool = False
            fields_ordered: list["C_kicad_project_file.C_schematic.C_bom_field"] = (
                field(default_factory=list)
            )
            filter_string: str = ""
            group_symbols: bool = True
            include_excluded_from_bom: Optional[bool] = None
            name: str = "Grouped By Value"
            sort_asc: bool = True
            sort_field: str = "Reference"
            unknown: CatchAll = None

        @dataclass_json(undefined=Undefined.INCLUDE)
        @dataclass
        class C_bom_fmt_settings:
            field_delimiter: str = ","
            keep_line_breaks: bool = False
            keep_tabs: bool = False
            name: str = "CSV"
            ref_delimiter: str = ","
            ref_range_delimiter: str = ""
            string_delimiter: str = '"'
            unknown: CatchAll = None

        @dataclass_json(undefined=Undefined.INCLUDE)
        @dataclass
        class C_ngspice:
            fix_include_paths: Optional[bool] = None
            fix_passive_vals: Optional[bool] = None
            meta: Optional[dict[str, int]] = None
            model_mode: Optional[int] = None
            workbook_filename: str = ""
            unknown: CatchAll = None

        @dataclass_json(undefined=Undefined.INCLUDE)
        @dataclass
        class C_meta:
            version: int = 1
            unknown: CatchAll = None

        annotate_start_num: Optional[int] = None
        bom_export_filename: Optional[str] = None
        bom_fmt_presets: Optional[list[C_bom_fmt_settings]] = None
        bom_fmt_settings: Optional[C_bom_fmt_settings] = None
        bom_presets: Optional[list[C_bom_settings]] = None
        bom_settings: Optional[C_bom_settings] = None
        connection_grid_size: Optional[float] = None
        drawing: Optional[C_drawing] = None
        legacy_lib_dir: str = ""
        legacy_lib_list: list[str] = field(default_factory=list)
        meta: Optional[C_meta] = None
        net_format_name: Optional[str] = None
        ngspice: Optional[C_ngspice] = None
        page_layout_descr_file: Optional[str] = None
        plot_directory: Optional[str] = None
        space_save_all_events: Optional[bool] = None
        spice_adjust_passive_values: Optional[bool] = None
        spice_current_sheet_as_root: Optional[bool] = None
        spice_external_command: Optional[str] = None
        spice_model_current_sheet_as_root: Optional[bool] = None
        spice_save_all_currents: Optional[bool] = None
        spice_save_all_dissipations: Optional[bool] = None
        spice_save_all_voltages: Optional[bool] = None
        subpart_first_id: Optional[int] = None
        subpart_id_separator: Optional[int] = None
        unknown: CatchAll = None

    schematic: C_schematic = field(default_factory=C_schematic)

    @dataclass_json(undefined=Undefined.INCLUDE)
    @dataclass
    class C_erc:
        @dataclass_json(undefined=Undefined.INCLUDE)
        @dataclass
        class C_rule_severities:
            bus_definition_conflict: str = "error"
            bus_entry_needed: str = "error"
            bus_label_syntax: Optional[str] = None
            bus_to_bus_conflict: str = "error"
            bus_to_net_conflict: str = "error"
            conflicting_netclasses: str = "error"
            different_unit_footprint: str = "error"
            different_unit_net: str = "error"
            duplicate_reference: str = "error"
            duplicate_sheet_names: str = "error"
            endpoint_off_grid: str = "warning"
            extra_units: str = "error"
            footprint_filter: Optional[str] = None
            footprint_link_issues: Optional[str] = None
            four_way_junction: Optional[str] = None
            global_label_dangling: str = "warning"
            hier_label_mismatch: str = "error"
            label_dangling: str = "error"
            label_multiple_wires: Optional[str] = None
            lib_symbol_issues: str = "warning"
            lib_symbol_mismatch: Optional[str] = None
            missing_bidi_pin: str = "warning"
            missing_input_pin: str = "warning"
            missing_power_pin: Optional[str] = None
            missing_unit: str = "warning"
            multiple_net_names: str = "warning"
            net_not_bus_member: str = "warning"
            no_connect_connected: str = "warning"
            no_connect_dangling: str = "warning"
            pin_not_connected: str = "error"
            pin_not_driven: str = "error"
            pin_to_pin: str = "warning"
            power_pin_not_driven: str = "error"
            same_local_global_label: Optional[str] = None
            similar_label_and_power: Optional[str] = None
            similar_labels: str = "warning"
            similar_power: Optional[str] = None
            simulation_model_issue: str = "ignore"
            single_global_label: Optional[str] = None
            unannotated: str = "error"
            unconnected_wire_endpoint: Optional[str] = None
            unit_value_mismatch: str = "error"
            unresolved_variable: str = "error"
            wire_dangling: Optional[str] = None
            unknown: CatchAll = None

        @dataclass_json(undefined=Undefined.INCLUDE)
        @dataclass
        class C_meta:
            version: int = 0
            unknown: CatchAll = None

        erc_exclusions: list[str] = field(default_factory=list)
        meta: C_meta = field(default_factory=C_meta)
        pin_map: list[list[int]] = field(default_factory=list)
        rule_severities: Optional[C_rule_severities] = None
        unknown: CatchAll = None

    erc: Optional[C_erc] = None

    # Each element is a [uuid, title] pair
    sheets: list[list[str]] = field(default_factory=list)

    text_variables: dict[str, str] = field(default_factory=dict)
    unknown: CatchAll = None

    def __rich_repr__(self):
        yield "**kwargs", "..."


@dataclass_json(undefined=Undefined.INCLUDE)
@dataclass(kw_only=True)
class C_kicad_config_common(JSON_File, DataClassJsonMixin):
    @dataclass_json(undefined=Undefined.INCLUDE)
    @dataclass(kw_only=True)
    class C_kicad_config_common_api(DataClassJsonMixin):
        enable_server: bool
        interpreter_path: str
        unknown: CatchAll = None

    api: C_kicad_config_common_api
    unknown: CatchAll = None


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
    # del C_kicad_pcb_file.C_kicad_pcb.__rich_repr__
    # del C_footprint.__rich_repr__
    del C_kicad_project_file.__rich_repr__
