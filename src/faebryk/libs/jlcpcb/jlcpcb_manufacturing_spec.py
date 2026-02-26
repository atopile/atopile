"""JLCPCB PCB and PCBA manufacturing capabilities.

Source: https://jlcpcb.com/capabilities/pcb-capabilities
"""

from dataclasses import dataclass, field
from enum import Enum

# ===================================================================
# Enums
# ===================================================================


class PCBMaterial(Enum):
    FR4 = "FR-4"
    ALUMINUM_CORE = "Aluminum-Core"
    COPPER_CORE = "Copper-Core"
    RF = "RF PCB"


class SurfaceFinish(Enum):
    HASL_LEADED = "HASL (leaded)"
    HASL_LEAD_FREE = "HASL (lead-free)"
    ENIG = "ENIG"
    OSP = "OSP"


class SoldermaskColor(Enum):
    GREEN = "Green"
    PURPLE = "Purple"
    RED = "Red"
    YELLOW = "Yellow"
    BLUE = "Blue"
    WHITE = "White"
    BLACK = "Black"


class DeliveryFormat(Enum):
    SINGLE_PCB = "Single PCB"
    PANEL_MOUSE_BITES = "Panel with mouse bites"
    PANEL_V_CUT = "Panel with V-cut"


class FPCDielectricType(Enum):
    PI_25UM = "25µm"
    PI_50UM = "50µm"
    TRANSPARENT = "Transparent"


class FPCCoverlayColor(Enum):
    YELLOW = "Yellow"
    BLACK = "Black"
    WHITE = "White"


class StiffenerMaterial(Enum):
    PI = "PI"
    FR4 = "FR4"
    STAINLESS_STEEL = "Stainless Steel"


# ===================================================================
# PCB Specifications
# ===================================================================


@dataclass(frozen=True)
class MaxDimensions:
    """Maximum PCB dimensions per material type."""

    fr4_mm: tuple[float, float] = (670, 600)
    fr4_thin_mm: tuple[float, float] = (500, 600)  # thickness < 0.8mm
    fr4_2layer_mm: tuple[float, float] = (1020, 600)
    rogers_ptfe_mm: tuple[float, float] = (590, 438)
    aluminum_mm: tuple[float, float] = (602, 506)
    copper_mm: tuple[float, float] = (480, 286)


@dataclass(frozen=True)
class MinDimensions:
    """Minimum PCB dimensions."""

    regular_mm: tuple[float, float] = (3, 3)
    castellated_mm: tuple[float, float] = (10, 10)
    plated_edges_mm: tuple[float, float] = (10, 10)
    min_thickness_mm: float = 0.6  # for min dimension to apply


@dataclass(frozen=True)
class DimensionTolerance:
    """Board outline dimension tolerances."""

    cnc_precision_mm: float = 0.1
    cnc_regular_mm: float = 0.2
    v_score_mm: float = 0.4


@dataclass(frozen=True)
class ThicknessTolerance:
    """Board thickness tolerances."""

    above_1mm_pct: float = 10  # ±10%
    below_1mm_mm: float = 0.1  # ±0.1mm


@dataclass(frozen=True)
class TraceWidthSpacing:
    """Minimum trace width and spacing for a given copper weight."""

    copper_weight_oz: float
    min_width_mm: float
    min_spacing_mm: float
    layer_note: str = ""  # e.g. "2-layer" or "multilayer"


@dataclass(frozen=True)
class CopperWeightOptions:
    """Available copper weight options."""

    outer_2layer_oz: tuple[float, ...] = (1.0, 2.0, 2.5, 3.5, 4.5)
    outer_multilayer_oz: tuple[float, ...] = (1.0, 2.0)
    inner_oz: tuple[float, ...] = (0.5, 1.0, 2.0)
    inner_default_oz: float = 0.5


# ===================================================================
# Drilling
# ===================================================================


@dataclass(frozen=True)
class DrillSpec:
    """Drilling capabilities."""

    # Drill diameter range
    min_drill_1layer_mm: float = 0.3
    max_drill_mm: float = 6.3
    min_drill_2plus_layer_mm: float = 0.15
    min_drill_aluminum_mm: float = 0.65
    min_drill_copper_core_mm: float = 1.0

    # Hole tolerances
    plated_tolerance_plus_mm: float = 0.13
    plated_tolerance_minus_mm: float = 0.08
    press_fit_tolerance_mm: float = (
        0.05  # ±0.05, holes 0.55-1.025mm, multilayer ENIG only
    )
    non_plated_tolerance_mm: float = 0.2  # ±0.2

    # Plating
    avg_hole_plating_thickness_um: float = 18

    # Via
    min_via_hole_mm: float = 0.15
    min_via_diameter_mm: float = 0.25
    preferred_min_via_hole_mm: float = 0.2
    min_via_annular_ring_mm: float = (
        0.1  # diameter should be 0.1mm larger, 0.15mm preferred
    )

    # 1-layer specific
    min_via_hole_1layer_mm: float = 0.3  # NPTH only
    min_via_diameter_1layer_mm: float = 0.5

    # Non-plated holes
    min_npth_mm: float = 0.5

    # Slots
    min_plated_slot_mm: float = 0.5
    min_non_plated_slot_mm: float = 1.0

    # Spacing
    via_hole_to_hole_spacing_mm: float = 0.2
    pad_hole_to_hole_spacing_mm: float = 0.45

    # Castellated holes
    min_castellated_hole_mm: float = 0.5
    castellated_hole_to_edge_mm: float = 1.0
    castellated_hole_to_hole_mm: float = 0.5
    castellated_min_pcb_size_mm: tuple[float, float] = (10, 10)
    castellated_min_thickness_mm: float = 0.6

    # Plated edges
    plated_edges_min_pcb_size_mm: tuple[float, float] = (10, 10)
    plated_edges_min_thickness_mm: float = 0.6

    # Blind/buried vias
    blind_buried_vias_supported: bool = False

    # Blind slot
    blind_slot_min_width_mm: float = 1.0
    blind_slot_min_depth_mm: float = 0.2
    blind_slot_min_annular_width_mm: float = 0.3
    blind_slot_min_safety_distance_mm: float = 0.2
    blind_slot_min_remaining_thickness_mm: float = 0.2
    blind_slot_min_board_thickness_mm: float = 0.8

    # Rectangular holes
    rectangular_holes_supported: bool = False


# ===================================================================
# Traces
# ===================================================================


@dataclass(frozen=True)
class TraceSpec:
    """Trace and clearance capabilities."""

    # Trace width/spacing by copper weight
    trace_rules: tuple[TraceWidthSpacing, ...] = (
        # 1 oz
        TraceWidthSpacing(1.0, 0.10, 0.10, "1-2 layer"),
        TraceWidthSpacing(1.0, 0.09, 0.09, "multilayer (3.5/3.5 mil, 3 mil in BGA)"),
        # 2 oz
        TraceWidthSpacing(2.0, 0.16, 0.16, "2-layer"),
        TraceWidthSpacing(2.0, 0.16, 0.20, "multilayer"),
        # 2.5 oz
        TraceWidthSpacing(2.5, 0.20, 0.20, "2-layer"),
        # 3.5 oz
        TraceWidthSpacing(3.5, 0.25, 0.25, "2-layer"),
        # 4.5 oz
        TraceWidthSpacing(4.5, 0.30, 0.30, "2-layer"),
    )

    # Tolerances
    trace_width_tolerance_pct: float = 20  # ±20%

    # Annular rings
    pth_annular_ring_min_mm: float = 0.20
    pth_annular_ring_2layer_1oz_recommended_mm: float = 0.25
    pth_annular_ring_2layer_1oz_absolute_min_mm: float = 0.18
    pth_annular_ring_2layer_2oz_mm: float = 0.254
    pth_annular_ring_multilayer_1oz_recommended_mm: float = 0.20
    pth_annular_ring_multilayer_1oz_absolute_min_mm: float = 0.15
    pth_annular_ring_multilayer_2oz_mm: float = 0.254
    npth_pad_annular_ring_min_mm: float = 0.45

    # BGA
    bga_min_pad_diameter_mm: float = 0.25
    bga_pad_to_trace_clearance_mm: float = 0.1
    bga_pad_to_trace_clearance_multilayer_mm: float = 0.09

    # Trace coils
    trace_coil_min_width_with_mask_mm: float = 0.15
    trace_coil_min_spacing_with_mask_mm: float = 0.15
    trace_coil_min_width_no_mask_mm: float = 0.25
    trace_coil_min_spacing_no_mask_mm: float = 0.25

    # Grid
    hatched_grid_min_width_mm: float = 0.25
    hatched_grid_min_spacing_mm: float = 0.25

    # Clearances
    same_net_track_spacing_mm: float = 0.25
    inner_via_to_copper_clearance_mm: float = 0.2
    inner_pth_to_copper_clearance_mm: float = 0.3
    pad_to_track_clearance_mm: float = 0.1
    pad_to_track_clearance_bga_mm: float = 0.09
    smd_pad_to_pad_clearance_mm: float = 0.15
    via_hole_to_track_mm: float = 0.2
    pth_to_track_mm: float = 0.28
    pth_to_track_recommended_mm: float = 0.35
    npth_to_track_mm: float = 0.2


# ===================================================================
# Soldermask
# ===================================================================


@dataclass(frozen=True)
class SoldermaskSpec:
    """Soldermask capabilities."""

    # Expansion
    expansion_ratio: str = "1:1"  # pad size : soldermask opening
    opening_to_trace_clearance_mm: float = 0.09

    # Bridge
    bridge_1oz_green_red_yellow_blue_purple_mm: float = 0.10
    bridge_1oz_black_white_mm: float = 0.13
    bridge_2oz_mm: float = 0.20

    # Plugged vias
    plugged_via_max_diameter_mm: float = 0.5
    plugged_via_clearance_to_opening_mm: float = 0.35

    # Via-in-pad
    via_in_pad_fill: tuple[str, ...] = (
        "Epoxy Filled & Capped",
        "Copper paste Filled & Capped",
    )
    via_in_pad_diameter_range_mm: tuple[float, float] = (0.15, 0.5)
    via_in_pad_default_6plus_layers: bool = True

    # Dielectric
    dielectric_constant_er: float = 3.8
    min_ink_thickness_um: float = 10

    # Colors
    colors: tuple[SoldermaskColor, ...] = (
        SoldermaskColor.GREEN,
        SoldermaskColor.PURPLE,
        SoldermaskColor.RED,
        SoldermaskColor.YELLOW,
        SoldermaskColor.BLUE,
        SoldermaskColor.WHITE,
        SoldermaskColor.BLACK,
    )


# ===================================================================
# Legend (Silkscreen)
# ===================================================================


@dataclass(frozen=True)
class LegendSpec:
    """Silkscreen / legend capabilities."""

    min_line_width_mm: float = 0.153  # 6 mil
    min_text_height_mm: float = 1.0  # 40 mil
    width_to_height_ratio: str = "1:6"
    hollow_carved_width_to_height_ratio: str = "1:6"
    pad_to_silkscreen_mm: float = 0.15


# ===================================================================
# Outline
# ===================================================================


@dataclass(frozen=True)
class RoutedOutlineSpec:
    """Routed board outline capabilities."""

    copper_clearance_from_edge_mm: float = 0.2
    copper_clearance_from_slot_mm: float = 0.2
    dimension_tolerance_regular_mm: float = 0.2
    dimension_tolerance_precision_mm: float = 0.1
    precision_min_dimension_mm: tuple[float, float] = (50, 50)
    precision_min_tooling_holes: int = 3
    precision_tooling_hole_min_diameter_mm: float = 1.5
    aluminum_copper_min_slot_width_mm: float = 1.6


@dataclass(frozen=True)
class VCutSpec:
    """V-cut capabilities."""

    copper_clearance_from_edge_mm: float = 0.4
    dimension_tolerance_mm: float = 0.4
    min_pcb_thickness_mm: float = 0.6
    min_panel_size_mm: tuple[float, float] = (70, 70)
    max_panel_size_mm: tuple[float, float] = (475, 475)
    groove_angle_deg: float = 25


@dataclass(frozen=True)
class MouseBiteSpec:
    """Mouse bite panelization capabilities."""

    copper_clearance_from_edge_mm: float = 0.2
    dimension_tolerance_regular_mm: float = 0.2
    dimension_tolerance_precision_mm: float = 0.1
    board_spacing_mm: tuple[float, ...] = (1.6, 2.0)
    min_tooling_edge_width_mm: float = 3.0
    smt_tooling_edge_width_mm: float = 5.0
    smt_tooling_hole_diameter_mm: float = 2.0
    smt_fiducial_diameter_mm: float = 1.0
    smt_fiducial_center_to_edge_mm: float = 3.85
    recommended_mouse_bite_diameter_mm: tuple[float, float] = (0.5, 0.8)
    recommended_mouse_bite_spacing_mm: tuple[float, float] = (0.2, 0.3)
    min_breakaway_tab_width_mm: float = 4.0
    min_breakaway_tab_with_bites_width_mm: float = 5.0


@dataclass(frozen=True)
class PanelSpec:
    """General panelization capabilities."""

    min_board_spacing_mm: float = 2.0
    min_circular_pcb_size_mm: tuple[float, float] = (20, 20)


@dataclass(frozen=True)
class OutlineSpec:
    """All outline / panelization capabilities."""

    routed: RoutedOutlineSpec = field(default_factory=RoutedOutlineSpec)
    v_cut: VCutSpec = field(default_factory=VCutSpec)
    mouse_bite: MouseBiteSpec = field(default_factory=MouseBiteSpec)
    panel: PanelSpec = field(default_factory=PanelSpec)


# ===================================================================
# PCB Spec (combined)
# ===================================================================


@dataclass(frozen=True)
class PCBSpec:
    """Complete JLCPCB rigid PCB manufacturing capabilities."""

    # General
    layer_count_min: int = 1
    layer_count_max: int = 32
    impedance_controlled_layers: tuple[int, ...] = (
        4,
        6,
        8,
        10,
        12,
        14,
        16,
        18,
        20,
        22,
        24,
        26,
        28,
        30,
        32,
    )
    impedance_tolerance_pct: float = 10  # ±10%

    # Materials
    materials: tuple[PCBMaterial, ...] = (
        PCBMaterial.FR4,
        PCBMaterial.ALUMINUM_CORE,
        PCBMaterial.COPPER_CORE,
        PCBMaterial.RF,
    )
    fr4_er_2layer: float = 4.5

    # Dimensions
    max_dimensions: MaxDimensions = field(default_factory=MaxDimensions)
    min_dimensions: MinDimensions = field(default_factory=MinDimensions)
    dimension_tolerance: DimensionTolerance = field(default_factory=DimensionTolerance)

    # Thickness
    thickness_range_mm: tuple[float, float] = (0.4, 4.5)
    fr4_thicknesses_mm: tuple[float, ...] = (0.4, 0.6, 0.8, 1.0, 1.2, 1.6, 2.0)
    fr4_thick_12plus_layers_mm: tuple[float, ...] = (2.5, 3.0, 3.2, 3.5, 4.0, 4.5)
    thickness_tolerance: ThicknessTolerance = field(default_factory=ThicknessTolerance)

    # Copper
    copper: CopperWeightOptions = field(default_factory=CopperWeightOptions)

    # Surface finish
    surface_finishes: tuple[SurfaceFinish, ...] = (
        SurfaceFinish.HASL_LEADED,
        SurfaceFinish.HASL_LEAD_FREE,
        SurfaceFinish.ENIG,
        SurfaceFinish.OSP,
    )

    # Sub-specs
    drilling: DrillSpec = field(default_factory=DrillSpec)
    traces: TraceSpec = field(default_factory=TraceSpec)
    soldermask: SoldermaskSpec = field(default_factory=SoldermaskSpec)
    legend: LegendSpec = field(default_factory=LegendSpec)
    outline: OutlineSpec = field(default_factory=OutlineSpec)


# ===================================================================
# Flexible PCB
# ===================================================================


@dataclass(frozen=True)
class FPCStackup:
    """A single FPC stackup option."""

    layers: int
    dielectric: FPCDielectricType
    dielectric_thickness_um: float
    finished_thicknesses_mm: tuple[float, ...]
    description: str = ""


@dataclass(frozen=True)
class FPCCoverlayThickness:
    """Coverlay thickness for a given dielectric type."""

    dielectric: FPCDielectricType
    pi_thickness_um: float
    adhesive_thickness_um: float
    copper_weight_note: str = ""


@dataclass(frozen=True)
class FPCStiffener:
    """Stiffener option for FPC."""

    material: StiffenerMaterial
    thicknesses_mm: tuple[float, ...]
    description: str = ""


@dataclass(frozen=True)
class FPCSpec:
    """JLCPCB flexible PCB capabilities."""

    layer_counts: tuple[int, ...] = (1, 2, 4)
    rigid_flex_supported: bool = False

    # Stack-ups
    stackups: tuple[FPCStackup, ...] = (
        FPCStackup(1, FPCDielectricType.PI_25UM, 25, (0.07, 0.11)),
        FPCStackup(2, FPCDielectricType.PI_25UM, 25, (0.11, 0.12, 0.2)),
        FPCStackup(1, FPCDielectricType.PI_50UM, 50, (0.12,), "Tear-resistant"),
        FPCStackup(
            2,
            FPCDielectricType.PI_50UM,
            50,
            (0.19,),
            "Tear-resistant, impedance-controlled",
        ),
        FPCStackup(1, FPCDielectricType.TRANSPARENT, 36, (0.14,), "PET substrate"),
        FPCStackup(2, FPCDielectricType.TRANSPARENT, 36, (0.24,), "PET substrate"),
    )

    # Dimensions
    max_dimensions_mm: tuple[float, float] = (234, 490)
    max_dimensions_absolute_mm: tuple[float, float] = (250, 500)  # with handling edges
    min_dimensions_panelized_mm: tuple[float, float] = (20, 20)

    # Thickness
    thickness_tolerance_mm: float = 0.05  # ±0.05

    # Copper
    outer_copper_1layer_oz: tuple[float, ...] = (0.5, 1.0)  # 18µm, 35µm
    outer_copper_2layer_oz: tuple[float, ...] = (0.33, 0.5, 1.0)  # 12µm, 18µm, 35µm

    # Surface finish
    surface_finish: str = "ENIG"
    enig_thickness_options: tuple[str, ...] = ('1u"', '2u"')

    # Holes
    hole_diameter_range_mm: tuple[float, float] = (0.15, 6.5)
    hole_diameter_tolerance_mm: float = 0.08  # ±0.08
    min_plated_slot_mm: float = 0.5
    castellated_hole_min_diameter_mm: float = 0.3
    castellated_hole_to_edge_mm: float = 0.5
    castellated_hole_to_hole_mm: float = 0.4

    # Via
    min_via_hole_regular_mm: float = 0.15
    min_via_diameter_regular_mm: float = 0.35
    min_via_hole_extreme_mm: float = 0.10
    min_via_diameter_extreme_mm: float = 0.30
    recommended_via_hole_mm: float = 0.3
    recommended_via_diameter_mm: float = 0.55

    # Traces
    trace_width_tolerance_pct: float = 20  # ±20%
    pth_annular_ring_recommended_mm: float = 0.25
    pth_annular_ring_absolute_min_mm: float = 0.18
    pad_to_trace_clearance_via_mm: float = 0.1
    pad_to_trace_clearance_exposed_mm: float = 0.15
    npth_to_copper_clearance_mm: float = 0.2
    bga_min_pad_diameter_mm: float = 0.25
    bga_pad_to_trace_clearance_mm: float = 0.2

    # Coverlay
    coverlay_colors: tuple[FPCCoverlayColor, ...] = (
        FPCCoverlayColor.YELLOW,
        FPCCoverlayColor.BLACK,
        FPCCoverlayColor.WHITE,
    )
    coverlay_expansion_one_side_mm: float = 0.1
    coverlay_opening_to_trace_clearance_mm: float = 0.15
    min_solder_bridge_width_mm: float = 0.5

    # Coverlay thickness
    coverlay_thicknesses: tuple[FPCCoverlayThickness, ...] = (
        FPCCoverlayThickness(
            FPCDielectricType.PI_25UM, 12.5, 15, "on 1/3oz or 0.5oz copper"
        ),
        FPCCoverlayThickness(FPCDielectricType.PI_25UM, 25, 25, "on 1oz copper"),
        FPCCoverlayThickness(FPCDielectricType.PI_50UM, 50, 50),
        FPCCoverlayThickness(FPCDielectricType.TRANSPARENT, 25, 25, "PET substrate"),
    )

    # Silkscreen
    silkscreen_min_char_height_mm: float = 1.0
    silkscreen_min_line_width_mm: float = 0.15
    silkscreen_char_to_pad_clearance_mm: float = 0.15

    # Outline
    copper_to_board_edge_mm: float = 0.3
    copper_to_slot_mm: float = 0.3
    outline_tolerance_mm: float = 0.1
    outline_tolerance_precision_mm: float = 0.05
    gold_finger_to_edge_clearance_mm: float = 0.2

    # Panel
    panel_board_spacing_mm: float = 2.0
    panel_board_spacing_metal_stiffener_mm: float = 3.0
    panel_handling_edge_width_mm: float = 5.0
    panel_max_size_mm: tuple[float, float] = (234, 490)
    panel_support_tab_width_mm: tuple[float, float] = (0.7, 1.0)

    # Stiffeners
    stiffeners: tuple[FPCStiffener, ...] = (
        FPCStiffener(
            StiffenerMaterial.PI,
            (0.1, 0.15, 0.2, 0.225, 0.25),
            "Gold finger connectors",
        ),
        FPCStiffener(StiffenerMaterial.FR4, (0.1, 0.2), "Low-end, prone to chipping"),
        FPCStiffener(
            StiffenerMaterial.STAINLESS_STEEL,
            (0.1, 0.2, 0.3),
            "Excellent flatness, slightly magnetic",
        ),
    )

    # 3M tape
    tape_3m9077_thickness_mm: float = 0.05  # heat-resistant
    tape_3m468_thickness_mm: float = 0.13  # not heat-resistant
    em_shielding_film_thickness_um: float = 18

    # Impedance
    core_polyimide_er: float = 3.3
    coverlay_er: float = 2.9
    core_polyimide_thickness_um: float = 25
    impedance_control_supported: bool = False


# ===================================================================
# PCBA (Assembly)
# ===================================================================


@dataclass(frozen=True)
class PCBAAssemblyTier:
    """Capabilities for an assembly tier (Economic or Standard)."""

    name: str
    assembly_sides: str  # "single" or "single & double"
    layer_counts: tuple[int, ...]
    thickness_range_mm: tuple[float, float] | None  # None = no limit
    single_pcb_size_range_mm: tuple[
        tuple[float, float], tuple[float, float]
    ]  # (min, max)
    panel_size_range_mm: tuple[tuple[float, float], tuple[float, float]]
    order_volume_range: tuple[int, int]
    delivery_formats: tuple[DeliveryFormat, ...]
    stackup_note: str
    gold_fingers_supported: bool
    castellated_holes_supported: bool
    edge_plating_supported: bool
    edge_rails_required: bool
    fiducials_required: bool
    min_package: str  # e.g. "0402", "0201"
    min_ic_pin_spacing_mm: float
    min_bga_spacing_mm: float
    reflow_temp_c: float
    reflow_temp_tolerance_c: float
    reflow_temp_adjustable: bool
    spi_inspection: bool
    aoi_inspection: bool
    visual_inspection: bool
    xray_inspection: str  # e.g. "Yes (BGA only)"
    build_time_days: str  # e.g. "1-3" or "≥4"


@dataclass(frozen=True)
class EconomicPCBAOption:
    """A specific PCB configuration available for Economic PCBA."""

    layers: int
    thickness_mm: float
    colors: tuple[SoldermaskColor, ...]
    surface_finishes: tuple[SurfaceFinish, ...]
    qty_range: tuple[int, int]


@dataclass(frozen=True)
class PCBASpec:
    """JLCPCB PCB assembly capabilities."""

    economic: PCBAAssemblyTier = field(
        default_factory=lambda: PCBAAssemblyTier(
            name="Economic",
            assembly_sides="single",
            layer_counts=(2, 4, 6),
            thickness_range_mm=(0.8, 1.6),
            single_pcb_size_range_mm=((10, 10), (470, 500)),
            panel_size_range_mm=((10, 10), (250, 250)),
            order_volume_range=(2, 50),
            delivery_formats=(
                DeliveryFormat.SINGLE_PCB,
                DeliveryFormat.PANEL_MOUSE_BITES,
            ),
            stackup_note="Standard stack-up only",
            gold_fingers_supported=False,
            castellated_holes_supported=False,
            edge_plating_supported=False,
            edge_rails_required=False,
            fiducials_required=False,
            min_package="0402",
            min_ic_pin_spacing_mm=0.4,
            min_bga_spacing_mm=0.5,
            reflow_temp_c=255,
            reflow_temp_tolerance_c=5,
            reflow_temp_adjustable=False,
            spi_inspection=False,
            aoi_inspection=True,
            visual_inspection=True,
            xray_inspection="Yes (BGA only)",
            build_time_days="1-3",
        )
    )

    standard: PCBAAssemblyTier = field(
        default_factory=lambda: PCBAAssemblyTier(
            name="Standard",
            assembly_sides="single & double",
            layer_counts=tuple(range(1, 33)),
            thickness_range_mm=None,
            single_pcb_size_range_mm=((70, 70), (460, 500)),
            panel_size_range_mm=((70, 70), (250, 250)),
            order_volume_range=(2, 80000),
            delivery_formats=(
                DeliveryFormat.SINGLE_PCB,
                DeliveryFormat.PANEL_MOUSE_BITES,
                DeliveryFormat.PANEL_V_CUT,
            ),
            stackup_note="All stack-ups",
            gold_fingers_supported=True,
            castellated_holes_supported=True,
            edge_plating_supported=True,
            edge_rails_required=True,
            fiducials_required=True,
            min_package="0201",
            min_ic_pin_spacing_mm=0.35,
            min_bga_spacing_mm=0.35,
            reflow_temp_c=240,
            reflow_temp_tolerance_c=5,
            reflow_temp_adjustable=True,
            spi_inspection=True,
            aoi_inspection=True,
            visual_inspection=True,
            xray_inspection="Yes (BGA only)",
            build_time_days="≥4",
        )
    )

    economic_pcb_options: tuple[EconomicPCBAOption, ...] = (
        # 2-layer
        EconomicPCBAOption(
            2,
            0.8,
            (SoldermaskColor.GREEN,),
            (SurfaceFinish.HASL_LEADED, SurfaceFinish.HASL_LEAD_FREE),
            (2, 30),
        ),
        EconomicPCBAOption(
            2,
            1.0,
            (SoldermaskColor.GREEN, SoldermaskColor.BLACK),
            (SurfaceFinish.HASL_LEADED, SurfaceFinish.HASL_LEAD_FREE),
            (2, 30),
        ),
        EconomicPCBAOption(
            2,
            1.2,
            (SoldermaskColor.GREEN, SoldermaskColor.BLACK),
            (SurfaceFinish.HASL_LEADED, SurfaceFinish.HASL_LEAD_FREE),
            (2, 30),
        ),
        EconomicPCBAOption(
            2,
            1.6,
            (SoldermaskColor.GREEN,),
            (
                SurfaceFinish.HASL_LEADED,
                SurfaceFinish.HASL_LEAD_FREE,
                SurfaceFinish.ENIG,
            ),
            (2, 50),
        ),
        EconomicPCBAOption(
            2,
            1.6,
            (SoldermaskColor.BLACK,),
            (SurfaceFinish.HASL_LEADED, SurfaceFinish.HASL_LEAD_FREE),
            (2, 50),
        ),
        EconomicPCBAOption(
            2,
            1.6,
            (
                SoldermaskColor.BLUE,
                SoldermaskColor.RED,
                SoldermaskColor.WHITE,
                SoldermaskColor.PURPLE,
            ),
            (SurfaceFinish.HASL_LEADED, SurfaceFinish.HASL_LEAD_FREE),
            (5, 30),
        ),
        # 4-layer
        EconomicPCBAOption(
            4,
            1.0,
            (SoldermaskColor.GREEN,),
            (SurfaceFinish.HASL_LEADED, SurfaceFinish.HASL_LEAD_FREE),
            (2, 30),
        ),
        EconomicPCBAOption(
            4,
            1.2,
            (SoldermaskColor.GREEN,),
            (SurfaceFinish.HASL_LEADED, SurfaceFinish.HASL_LEAD_FREE),
            (2, 50),
        ),
        EconomicPCBAOption(
            4,
            1.6,
            (SoldermaskColor.GREEN,),
            (
                SurfaceFinish.HASL_LEADED,
                SurfaceFinish.HASL_LEAD_FREE,
                SurfaceFinish.ENIG,
            ),
            (2, 50),
        ),
        # 6-layer
        EconomicPCBAOption(
            6, 1.6, (SoldermaskColor.GREEN,), (SurfaceFinish.ENIG,), (2, 30)
        ),
    )


# ===================================================================
# Top-level singleton
# ===================================================================


JLCPCB_PCB_SPEC = PCBSpec()
JLCPCB_FPC_SPEC = FPCSpec()
JLCPCB_PCBA_SPEC = PCBASpec()
