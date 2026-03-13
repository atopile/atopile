"""JLCPCB impedance calculator material data.

Source: https://jlcpcb.com/help/article/User-Guide-to-the-JLCPCB-Impedance-Calculator
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CopperSpec:
    """Copper foil specification."""

    weight_oz: float
    thickness_mm: float
    position: str  # "external" or "internal"


@dataclass(frozen=True)
class SolderMaskSpec:
    """Solder mask properties."""

    base_thickness_mil: float
    over_copper_thickness_mil: float
    between_traces_thickness_mil: float
    er: float
    """εr (relative permittivity). Also known as dissipation/dielectric constant. """


@dataclass(frozen=True)
class CoreSpec:
    """Core laminate dielectric properties at a given thickness."""

    thickness_mm: float
    er: float
    """εr (relative permittivity). Also known as dissipation/dielectric constant. """


@dataclass(frozen=True)
class PrepregSpec:
    """Prepreg dielectric properties."""

    type_name: str
    resin_content_pct: int
    nominal_thickness_mil: float
    er: float
    """εr (relative permittivity). Also known as dissipation/dielectric constant. """


@dataclass(frozen=True)
class LaminateMaterial:
    """A PCB laminate material system with its core and prepreg options."""

    name: str
    manufacturer: str
    layer_count_min: int
    layer_count_max: int | None  # None = unbounded
    cores: tuple[CoreSpec, ...]
    prepregs: tuple[PrepregSpec, ...]


@dataclass(frozen=True)
class TraceGeometry:
    """Manufacturing trace geometry rules."""

    top_width_offset_mil: float
    """top_width = base_width + this (negative = narrower)"""


@dataclass(frozen=True)
class ImpedanceRange:
    """Supported impedance target ranges."""

    single_ended_min_ohm: int
    single_ended_max_ohm: int
    differential_min_ohm: int
    differential_max_ohm: int


# ---------------------------------------------------------------------------
# Copper foil specs
# ---------------------------------------------------------------------------

COPPER_SPECS = (
    CopperSpec(weight_oz=1.0, thickness_mm=0.0406, position="external"),  # 1.6 mil
    CopperSpec(weight_oz=0.5, thickness_mm=0.0152, position="internal"),  # 0.6 mil
    CopperSpec(weight_oz=1.0, thickness_mm=0.0305, position="internal"),  # 1.2 mil
)

# ---------------------------------------------------------------------------
# Solder mask
# ---------------------------------------------------------------------------

SOLDER_MASK = SolderMaskSpec(
    base_thickness_mil=1.2,
    over_copper_thickness_mil=0.6,
    between_traces_thickness_mil=1.2,
    er=3.8,
)

# ---------------------------------------------------------------------------
# Trace geometry
# ---------------------------------------------------------------------------

TRACE_GEOMETRY = TraceGeometry(
    top_width_offset_mil=-0.7,
)

# ---------------------------------------------------------------------------
# Impedance ranges
# ---------------------------------------------------------------------------

IMPEDANCE_RANGE = ImpedanceRange(
    single_ended_min_ohm=20,
    single_ended_max_ohm=90,
    differential_min_ohm=50,
    differential_max_ohm=150,
)

# ---------------------------------------------------------------------------
# Nan Ya Plastics NP-155F  (4- to 8-layer boards)
# ---------------------------------------------------------------------------

NP_155F = LaminateMaterial(
    name="NP-155F",
    manufacturer="Nan Ya Plastics",
    layer_count_min=4,
    layer_count_max=8,
    cores=(
        CoreSpec(thickness_mm=0.08, er=3.99),
        CoreSpec(thickness_mm=0.10, er=4.36),
        CoreSpec(thickness_mm=0.13, er=4.17),
        CoreSpec(thickness_mm=0.15, er=4.36),
        CoreSpec(thickness_mm=0.20, er=4.36),
        CoreSpec(thickness_mm=0.25, er=4.23),
        CoreSpec(thickness_mm=0.30, er=4.41),
        CoreSpec(thickness_mm=0.35, er=4.36),
        CoreSpec(thickness_mm=0.40, er=4.36),
        CoreSpec(thickness_mm=0.45, er=4.36),
        CoreSpec(thickness_mm=0.50, er=4.48),
        CoreSpec(thickness_mm=0.55, er=4.41),
        CoreSpec(thickness_mm=0.60, er=4.36),
        CoreSpec(thickness_mm=0.65, er=4.36),
        CoreSpec(thickness_mm=0.70, er=4.53),
    ),
    prepregs=(
        PrepregSpec(
            type_name="7628", resin_content_pct=49, nominal_thickness_mil=8.6, er=4.4
        ),
        PrepregSpec(
            type_name="3313", resin_content_pct=57, nominal_thickness_mil=4.2, er=4.1
        ),
        PrepregSpec(
            type_name="1080", resin_content_pct=67, nominal_thickness_mil=3.3, er=3.91
        ),
        PrepregSpec(
            type_name="2116", resin_content_pct=54, nominal_thickness_mil=4.9, er=4.16
        ),
    ),
)

# ---------------------------------------------------------------------------
# SYTECH (Shengyi) S1000-2M  (10+ layer boards)
# ---------------------------------------------------------------------------

S1000_2M = LaminateMaterial(
    name="S1000-2M",
    manufacturer="SYTECH (Shengyi)",
    layer_count_min=10,
    layer_count_max=None,
    cores=(
        CoreSpec(thickness_mm=0.075, er=4.14),
        CoreSpec(thickness_mm=0.10, er=4.11),
        CoreSpec(thickness_mm=0.13, er=4.03),
        CoreSpec(thickness_mm=0.15, er=4.35),
        CoreSpec(thickness_mm=0.20, er=4.42),
        CoreSpec(thickness_mm=0.25, er=4.29),
        CoreSpec(thickness_mm=0.30, er=4.56),
    ),
    prepregs=(
        PrepregSpec(
            type_name="106", resin_content_pct=72, nominal_thickness_mil=1.97, er=3.92
        ),
        PrepregSpec(
            type_name="1080", resin_content_pct=69, nominal_thickness_mil=3.31, er=3.99
        ),
        PrepregSpec(
            type_name="2313", resin_content_pct=58, nominal_thickness_mil=4.09, er=4.31
        ),
        PrepregSpec(
            type_name="2116", resin_content_pct=57, nominal_thickness_mil=5.00, er=4.29
        ),
    ),
)

# ---------------------------------------------------------------------------
# All materials indexed by layer count
# ---------------------------------------------------------------------------

ALL_MATERIALS = (NP_155F, S1000_2M)


def material_for_layer_count(layer_count: int) -> LaminateMaterial | None:
    """Return the laminate material used by JLCPCB for a given layer count."""
    for mat in ALL_MATERIALS:
        if layer_count >= mat.layer_count_min and (
            mat.layer_count_max is None or layer_count <= mat.layer_count_max
        ):
            return mat
    return None
