import logging
import re
from dataclasses import dataclass, field
from enum import StrEnum, auto
from os import PathLike
from pathlib import Path
from typing import (
    Any,
    Callable,
    Iterable,
    Optional,
    Protocol,
    Self,
    cast,
    overload,
)

from dataclasses_json import (
    CatchAll,
    DataClassJsonMixin,
    Undefined,
    config,
    dataclass_json,
)
from more_itertools import first

from faebryk.libs.checksum import Checksum
from faebryk.libs.util import ConfigFlag, compare_dataclasses, find, find_or, lazy_split

logger = logging.getLogger(__name__)

RICH_PRINT = ConfigFlag("FF_RICH_PRINT")

# TODO find complete examples of the fileformats, maybe in the kicad repo


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


UUID = str


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
            uuid: str
            title: str

        sheet: list[C_sheet] = field(default_factory=list)

    sheets: list[C_sheets] = field(default_factory=list)

    @dataclass_json(undefined=Undefined.INCLUDE)
    @dataclass
    class C_text_variables:
        unknown: CatchAll = None

    text_variables: dict = field(default_factory=dict)
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

# zig shims


class Named(Protocol):
    name: str


# namespace
class kicad:
    from faebryk.core.zig import (
        footprint,  # noqa: E402, F401
        footprint_v5,  # noqa: E402, F401
        fp_lib_table,  # noqa: E402, F401
        netlist,  # noqa: E402, F401
        pcb,  # noqa: E402
        schematic,  # noqa: E402, F401
        symbol,  # noqa: E402, F401
        symbol_v6,  # noqa: E402, F401
    )

    class project:
        ProjectFile = C_kicad_project_file

    class drc:
        DrcFile = C_kicad_drc_report_file

    class model:
        ModelFile = C_kicad_model_file

    class config:
        ConfigFile = C_kicad_config_common

    type types = (
        pcb.PcbFile
        | footprint.FootprintFile
        | fp_lib_table.FpLibTableFile
        | netlist.NetlistFile
        | symbol.SymbolFile
        | schematic.SchematicFile
        | C_kicad_drc_report_file
        | C_kicad_model_file
        | C_kicad_project_file
        | C_kicad_config_common
        | footprint_v5.FootprintFile
        | symbol_v6.SymbolFile
    )

    @staticmethod
    def type_to_module(t: type[types] | types):
        def instance_or_subclass(_t: type | object, target: type):
            return _t is target or type(_t) is target

        if instance_or_subclass(t, kicad.pcb.PcbFile):
            return kicad.pcb
        elif instance_or_subclass(t, kicad.footprint.FootprintFile):
            return kicad.footprint
        elif instance_or_subclass(t, kicad.fp_lib_table.FpLibTableFile):
            return kicad.fp_lib_table
        elif instance_or_subclass(t, kicad.netlist.NetlistFile):
            return kicad.netlist
        elif instance_or_subclass(t, kicad.symbol.SymbolFile):
            return kicad.symbol
        elif instance_or_subclass(t, kicad.schematic.SchematicFile):
            return kicad.schematic
        elif instance_or_subclass(t, kicad.footprint_v5.FootprintFile):
            return kicad.footprint_v5
        elif instance_or_subclass(t, kicad.symbol_v6.SymbolFile):
            return kicad.symbol_v6
        elif instance_or_subclass(t, kicad.drc.DrcFile):
            return kicad.drc.DrcFile
        # TODO need to switch to bytes instead of str in sexp load
        # elif instance_or_subclass(t, kicad.model.ModelFile):
        #    return kicad.model.ModelFile
        elif instance_or_subclass(t, kicad.project.ProjectFile):
            return kicad.project.ProjectFile
        elif instance_or_subclass(t, kicad.config.ConfigFile):
            return kicad.config.ConfigFile

        raise ValueError(f"Unsupported type: {t} ({type(t)})")

    @staticmethod
    def loads[T: kicad.types](t: type[T], path_or_sexpstring: Path | str) -> T:
        """
        Attention: object returned is shared, so be careful with mutations!
        """
        path = None
        if isinstance(path_or_sexpstring, Path):
            path = path_or_sexpstring
            if not hasattr(kicad.loads, "cache"):
                kicad.loads.cache = {}
            if path in kicad.loads.cache:
                out = kicad.loads.cache[path]
                assert isinstance(out, t)
                return out
            data = path.read_text(encoding="utf-8")
        else:
            data = path_or_sexpstring

        out = cast(T, kicad.type_to_module(t).loads(data))
        if path:
            kicad.loads.cache[path] = out
        return out

    @staticmethod
    def dumps(obj: types, path: Path | None = None):
        raw = kicad.type_to_module(obj).dumps(
            obj,  # type: ignore
        )

        # TODO should live in zig
        # some files have trailing newlines, some don't
        if isinstance(obj, kicad.footprint.FootprintFile):
            if raw.endswith("\n"):
                raw = raw[: -len("\n")]

        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(raw, encoding="utf-8")
        return raw

    @staticmethod
    def gen_uuid(mark: str = ""):
        import uuid

        # format: d864cebe-263c-4d3f-bbd6-bb51c6d2a608
        value = uuid.uuid4().hex

        suffix = mark.encode().hex()
        if suffix:
            value = value[: -len(suffix)] + suffix

        DASH_IDX = [8, 12, 16, 20]
        formatted = value
        for i, idx in enumerate(DASH_IDX):
            formatted = formatted[: idx + i] + "-" + formatted[idx + i :]

        return UUID(formatted)

    @staticmethod
    def fp_get_base_name(fp: footprint.Footprint | pcb.Footprint) -> str:
        return fp.name.split(":")[-1]

    @staticmethod
    def get[T: Named](obj: Iterable[T], name: str) -> T:
        return find(obj, lambda o: o.name == name)

    @staticmethod
    def try_get[T: Named](
        obj: Iterable[T], name: str, default: T | None = None
    ) -> T | None:
        return find_or(obj, lambda o: o.name == name, default=cast(T, default))

    @staticmethod
    def set[T: Named](
        parent,
        field: str,
        container: list[T],
        value: T,
        index: int | None = None,
        preserve_uuid: bool = True,
    ) -> T:
        uuid = None
        if index is None:
            index = next(
                (i for i, o in enumerate(container) if o.name == value.name), -1
            )
            if index != -1:
                uuid = getattr(container[index], "uuid", None)
        kicad.filter(parent, field, container, lambda o: o.name != value.name)

        if preserve_uuid and hasattr(value, "uuid") and uuid:
            setattr(value, "uuid", uuid)

        return kicad.insert(parent, field, container, value, index=index)

    @staticmethod
    def insert[T](parent, field: str, container: list[T], *value: T, index=-1) -> T:
        obj = getattr(parent, field)
        for i, val in enumerate(value):
            obj.insert(index + i, val)

        return obj[index]

    @staticmethod
    def filter[T](
        parent, field: str, container: list[T], predicate: Callable[[T], bool]
    ):
        obj = getattr(parent, field)

        # Iterate backwards to avoid index shifting issues
        for i in range(len(obj) - 1, -1, -1):
            if not predicate(obj[i]):
                obj.pop(i)

        return obj

    @staticmethod
    def delete[T: Named](parent, field: str, container: list[T], name: str):
        kicad.filter(parent, field, container, lambda o: o.name != name)

    @staticmethod
    def clear_and_set[T](parent, field: str, container: list[T], values: list[T]):
        obj = getattr(parent, field)

        obj.clear()
        for val in values:
            obj.append(val)

    class geo:
        @staticmethod
        def rotate(obj: "kicad.pcb.Xy", center: "kicad.pcb.Xy", angle: float):
            import math

            angle = -angle  # rotate kicad style counter-clockwise

            # Translate point to origin
            translated_x = obj.x - center.x
            translated_y = obj.y - center.y

            # Convert angle to radians
            angle = math.radians(angle)

            # Rotate
            rotated_x = translated_x * math.cos(angle) - translated_y * math.sin(angle)
            rotated_y = translated_x * math.sin(angle) + translated_y * math.cos(angle)

            # Translate back
            new_x = rotated_x + center.x
            new_y = rotated_y + center.y

            return kicad.pcb.Xy(x=new_x, y=new_y)

        @overload
        @staticmethod
        def add(obj: "kicad.pcb.Xy", *other: "kicad.pcb.Xy") -> "kicad.pcb.Xy": ...

        @overload
        @staticmethod
        def add(
            obj: "kicad.pcb.Xyr", *other: "kicad.pcb.Xyr | kicad.pcb.Xy"
        ) -> "kicad.pcb.Xyr": ...

        @staticmethod
        def add(obj, *other):
            x = obj.x
            y = obj.y
            r = getattr(obj, "r", None) or 0
            for o in other:
                x += o.x
                y += o.y
                r += getattr(o, "r", None) or 0
            if hasattr(obj, "r"):
                return kicad.pcb.Xyr(x=x, y=y, r=r)
            else:
                return kicad.pcb.Xy(x=x, y=y)

        @overload
        @staticmethod
        def sub(obj: "kicad.pcb.Xy", *other: "kicad.pcb.Xy") -> "kicad.pcb.Xy": ...

        @overload
        @staticmethod
        def sub(
            obj: "kicad.pcb.Xyr", *other: "kicad.pcb.Xyr | kicad.pcb.Xy"
        ) -> "kicad.pcb.Xyr": ...

        @staticmethod
        def sub(obj, *other):
            x = obj.x
            y = obj.y
            r = getattr(obj, "r", None) or 0
            for o in other:
                x -= o.x
                y -= o.y
                r -= getattr(o, "r", None) or 0
            if hasattr(obj, "r"):
                return kicad.pcb.Xy(x=x, y=y)
            else:
                return kicad.pcb.Xyr(x=x, y=y, r=r)

        @staticmethod
        def neg(obj: "kicad.pcb.Xy") -> "kicad.pcb.Xy":
            return kicad.pcb.Xy(x=-obj.x, y=-obj.y)

        @staticmethod
        def get_layers(obj):
            if obj.layer is not None:
                return [obj.layer]
            if obj.layers is not None:
                return obj.layers
            return []

        @staticmethod
        def apply_to_layers(obj, func: Callable[[str], str]):
            if hasattr(obj, "layer") and obj.layer is not None:
                if isinstance(obj.layer, str):
                    obj.layer = func(obj.layer)
                elif hasattr(obj.layer, "layer"):
                    obj.layer.layer = func(obj.layer.layer)
            if hasattr(obj, "layers") and obj.layers is not None:
                obj.layers = [func(layer) for layer in obj.layers]

    @staticmethod
    @overload
    def convert(
        old: "kicad.footprint_v5.FootprintFile",
    ) -> "kicad.footprint.FootprintFile": ...

    @staticmethod
    @overload
    def convert(
        old: "kicad.symbol_v6.SymbolFile",
    ) -> "kicad.symbol.SymbolFile": ...

    @staticmethod
    def convert(old: Any) -> Any:
        old = kicad.copy(old)
        if isinstance(old, kicad.footprint_v5.FootprintFile):

            def _calc_arc_midpoint(arc: kicad.footprint_v5.Arc):
                start = arc.end
                center = arc.start

                mid = kicad.geo.rotate(start, center, -arc.angle / 2.0)
                end = kicad.geo.rotate(start, center, -arc.angle)

                return {"start": start, "mid": mid, "end": end}

            for k in old.footprint.fp_texts:
                if (name := k.type.capitalize()) in ("Reference", "Value"):
                    Property.set_property(
                        old.footprint,
                        kicad.pcb.Property(
                            name=name,
                            value=k.text,
                            at=k.at,
                            layer=k.layer.layer,
                            uuid=k.uuid or kicad.gen_uuid(),
                            hide=k.hide,
                            effects=k.effects,
                            unlocked=None,
                        ),
                        index=0 if name == "Reference" else 1,
                    )
            texts = [
                t
                for t in old.footprint.fp_texts
                if t.type
                not in (
                    kicad.pcb.E_fp_text_type.REFERENCE,
                    kicad.pcb.E_fp_text_type.VALUE,
                )
            ]
            for t in old.footprint.fp_texts:
                if t.type == kicad.pcb.E_fp_text_type.REFERENCE:
                    # already added it as property
                    continue
                    texts.append(
                        kicad.pcb.FpText(
                            type=kicad.pcb.E_fp_text_type.USER,
                            text=t.text.replace("REF**", "${REFERENCE}"),
                            at=t.at,
                            layer=t.layer,
                            uuid=t.uuid or kicad.gen_uuid(),
                            effects=t.effects,
                            hide=t.hide,
                        )
                    )
                elif not t.uuid:
                    t.uuid = kicad.gen_uuid()

            for p in old.footprint.pads:
                if p.uuid:
                    continue
                p.uuid = kicad.gen_uuid()

            if old.footprint.layer not in [None, "F.Cu"]:
                raise ValueError(
                    f"Invalid library footprint: layer must be F.Cu, got"
                    f" {old.footprint.layer}"
                )

            return kicad.footprint.FootprintFile(
                footprint=kicad.footprint.Footprint(
                    name=old.footprint.name,
                    layer=old.footprint.layer,
                    uuid=old.footprint.uuid or kicad.gen_uuid(),
                    path=old.footprint.path,
                    propertys=old.footprint.propertys,
                    fp_texts=texts,
                    attr=old.footprint.attr,
                    fp_lines=[
                        kicad.pcb.Line(
                            start=line.start,
                            end=line.end,
                            layer=line.layer,
                            layers=[line.layer],
                            solder_mask_margin=None,
                            stroke=kicad.pcb.Stroke(width=line.width, type="solid"),
                            fill=None,
                            locked=False,
                            uuid=kicad.gen_uuid(),
                        )
                        for line in old.footprint.fp_lines
                    ],
                    fp_arcs=[
                        kicad.pcb.Arc(
                            **_calc_arc_midpoint(arc),
                            layer=arc.layer,
                            layers=[],
                            solder_mask_margin=None,
                            stroke=kicad.pcb.Stroke(width=arc.width, type="solid"),
                            fill=None,
                            locked=False,
                            uuid=kicad.gen_uuid(),
                        )
                        for arc in old.footprint.fp_arcs
                    ],
                    fp_circles=[
                        kicad.pcb.Circle(
                            center=circle.center,
                            end=circle.end,
                            layer=circle.layer,
                            layers=[],
                            solder_mask_margin=None,
                            stroke=kicad.pcb.Stroke(width=circle.width, type="solid"),
                            fill=None,
                            locked=False,
                            uuid=kicad.gen_uuid(),
                        )
                        for circle in old.footprint.fp_circles
                    ],
                    fp_rects=[
                        kicad.pcb.Rect(
                            start=rect.start,
                            end=rect.end,
                            layer=rect.layer,
                            layers=[],
                            solder_mask_margin=None,
                            stroke=kicad.pcb.Stroke(width=rect.width, type="solid"),
                            fill=None,
                            locked=False,
                            uuid=kicad.gen_uuid(),
                        )
                        for rect in old.footprint.fp_rects
                    ],
                    fp_poly=old.footprint.fp_poly,
                    pads=old.footprint.pads,
                    models=[
                        kicad.pcb.Model(
                            path=old.footprint.model.path,
                            offset=old.footprint.model.offset
                            or old.footprint.model.at
                            or kicad.pcb.ModelXyz(xyz=kicad.pcb.Xyz(x=0, y=0, z=0)),
                            scale=old.footprint.model.scale,
                            rotate=old.footprint.model.rotate,
                        )
                    ]
                    if old.footprint.model
                    else [],
                    description=old.footprint.description,
                    tags=old.footprint.tags,
                    version=20241229,
                    generator="faebryk_convert",
                    generator_version="v5",
                    tedit=old.footprint.tedit,
                    embedded_fonts=False,
                )
            )
        elif isinstance(old, kicad.symbol_v6.SymbolFile):
            return kicad.symbol.SymbolFile(
                kicad_sym=kicad.symbol.SymbolLib(
                    version=20241229,
                    generator="faebryk_convert",
                    symbols=[
                        kicad.schematic.Symbol(
                            name=symbol.name,
                            power=symbol.power,
                            propertys=symbol.propertys,
                            pin_numbers=symbol.pin_numbers,
                            pin_names=symbol.pin_names,
                            in_bom=symbol.in_bom,
                            on_board=symbol.on_board,
                            symbols=[
                                kicad.schematic.SymbolUnit(
                                    name=sym.name,
                                    polylines=sym.polylines,
                                    circles=[
                                        kicad.schematic.Circle(
                                            center=circle.center,
                                            end=kicad.pcb.Xy(
                                                x=circle.center.x + circle.radius,
                                                y=circle.center.y,
                                            ),
                                            stroke=circle.stroke,
                                            fill=circle.fill,
                                        )
                                        for circle in sym.circles
                                    ],
                                    rectangles=sym.rectangles,
                                    arcs=sym.arcs,
                                    pins=sym.pins,
                                )
                                for sym in symbol.symbols
                            ],
                            convert=symbol.convert,
                        )
                        for symbol in old.kicad_sym.symbols
                    ],
                )
            )
        raise ValueError(f"Unsupported type: {type(old)}")

    @staticmethod
    def compare_without_uuid(old: Any, new: Any):
        return compare_dataclasses(
            before=old,
            after=new,
            skip_keys=("uuid",),
            require_dataclass_type_match=False,
            float_precision=2,
        )

    class KicadStruct(Protocol):
        @staticmethod
        def __field_names__() -> list[str]: ...

    type Primitive = str | list | int | float | bool | tuple | None

    @staticmethod
    def copy[T: KicadStruct | Primitive](old: T) -> T:
        if old is None:
            return old
        if isinstance(old, (str, int, float, bool, tuple)):
            return old
        # Accept both Python lists and pyzig MutableList wrappers
        # pyzig exposes lists as a C-extension type named 'pyzig.MutableList'
        if isinstance(old, list) or (
            type(old).__name__ == "MutableList"
            and type(old).__module__ in ("pyzig", "pyzig_local")
        ):
            return [kicad.copy(item) for item in old]  # type: ignore
        t = type(old)
        copied = {
            name: kicad.copy(getattr(old, name)) for name in old.__field_names__()
        }
        return t(**copied)

    @staticmethod
    def decompress(data: list[str]) -> bytes:
        from base64 import b64decode

        import zstd

        merged = "".join(str(v) for v in data)
        assert merged.startswith("|") and merged.endswith("|")
        return zstd.decompress(b64decode(merged[1:-1]))

    @staticmethod
    def compress(data: bytes) -> list[str]:
        from base64 import b64encode

        import zstd

        # from kicad:common/embedded_files.cpp
        b64 = b64encode(zstd.compress(data)).decode()
        CHUNK_LEN = 76
        # chunk string to 76 characters
        chunks = [b64[i : i + CHUNK_LEN] for i in range(0, len(b64), CHUNK_LEN)]
        chunks[0] = "|" + chunks[0]
        chunks[-1] = chunks[-1] + "|"
        return chunks


class Property:
    class _Property(Protocol):
        name: str
        value: str
        at: kicad.pcb.Xyr

        # def __init__(self, name: str, value: str): ...

    class _PropertyHolder(Protocol):  # [T: _Property](kicad.KicadStruct):
        propertys: list  # [T]

    class PropertyNotSet(Exception):
        pass

    class checksum:
        @staticmethod
        def _hashable(obj: "Property._PropertyHolder", remove_uuid: bool = True):
            # TODO: only used by ato part for verifying user didnt accidentally modify
            # will fix later when we care about that
            raise NotImplementedError("Not implemented")
            copy = kicad.copy(obj)

            Property.checksum.delete_checksum(copy)
            # TODO: this doesn't work atm
            # out = kicad.dumps(copy)
            out = repr(copy)

            if remove_uuid:
                out = re.sub(r"\(uuid \"[^\"]*\"\)", "", out)

            return out

        @staticmethod
        def set_checksum(
            obj: "Property._PropertyHolder", p_type: type["Property._Property"]
        ):
            Property.checksum.delete_checksum(obj)

            attrs = {
                "name": "checksum",
                "value": Checksum.build(Property.checksum._hashable(obj)),
                "at": kicad.pcb.Xyr(x=0, y=0, r=0),
                "hide": True,
            }
            if p_type is kicad.pcb.Property:
                attrs["layer"] = "F.Cu"
            Property.set_property(
                obj,
                p_type(**attrs),
            )

        @staticmethod
        def verify_checksum(obj: "Property._PropertyHolder"):
            checksum_stated = Property.checksum.get_checksum(obj)
            try:
                Checksum.verify(checksum_stated, Property.checksum._hashable(obj))
            except Checksum.Mismatch:
                # legacy
                Checksum.verify(
                    checksum_stated, Property.checksum._hashable(obj, remove_uuid=False)
                )

        @staticmethod
        def delete_checksum(obj: "Property._PropertyHolder"):
            Property.delete_property(obj, "checksum")

        @staticmethod
        def get_checksum(obj: "Property._PropertyHolder") -> str:
            return Property.get_property(obj.propertys, "checksum")

    @staticmethod
    def get_property_obj[T: _Property](obj: Iterable[T], name: str) -> T:
        for prop in obj:
            if prop.name == name:
                return prop
        raise Property.PropertyNotSet(f"Property `{name}` not set")

    @staticmethod
    def get_property(obj: Iterable[_Property], name: str) -> str:
        out = Property.try_get_property(obj, name)
        if out is None:
            raise Property.PropertyNotSet(f"Property `{name}` not set")
        return out

    @staticmethod
    def delete_property[T: _Property](parent: _PropertyHolder, name: str):
        kicad.delete(parent, "propertys", parent.propertys, name)

    @staticmethod
    def set_property[T: _Property](
        parent: _PropertyHolder, prop: T, index: int | None = None
    ) -> T:
        for p in parent.propertys:
            if p.name == prop.name:
                p.value = prop.value
                return p

        return kicad.set(parent, "propertys", parent.propertys, prop, index=index)

    @staticmethod
    def try_get_property(obj: Iterable[_Property], name: str) -> str | None:
        for prop in obj:
            if prop.name == name:
                return prop.value
        return None

    @staticmethod
    def property_dict(obj: Iterable[_Property]) -> dict[str, str]:
        return {prop.name: prop.value for prop in obj}
