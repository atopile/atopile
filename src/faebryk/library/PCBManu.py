# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import IntEnum, auto
from typing import Self

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.ISO3166 import ISO3166_1_A3

logger = logging.getLogger(__name__)


class is_pcb_layer(fabll.Node):
    """
    Printed circuit board layer
    """

    is_trait = fabll.ImplementsTrait.MakeChild().put_on_type()

    def get_layer(self) -> PCBLayer:
        return fabll.Traits(self).get_obj_raw().cast(PCBLayer)


class PCBLayer(fabll.Node):
    """
    Printed circuit board layer
    """

    is_layer = fabll.Traits.MakeEdge(is_pcb_layer.MakeChild())

    class LayerType(IntEnum):
        """
        Layer type in the PCB stackup
        """

        COPPER = auto()
        CORE = auto()
        SUBSTRATE = auto()
        SOLDER_MASK = auto()
        SILK_SCREEN = auto()
        PASTE = auto()

    class Material(IntEnum):
        """
        Material of the layer
        """

        LPSM = auto()
        """
        Liquid Photoimageable Solder Mask.
        """
        FR4 = auto()
        """
        Flame retardant epoxy glass fiber.
        """
        ALUMINIUM = auto()
        """
        Aluminium.
        """
        COPPER = auto()
        """
        Copper.
        """
        POLYAMIDE = auto()
        """
        Polyamide. Also known as Kapton.
        """
        PET = auto()
        """
        Polyethylene.
        """
        PTFE = auto()
        """
        Polytetrafluoroethylene. Also known as Teflon.
        """
        ALUMINIUM_OXIDE = auto()
        """
        Ceramic.
        """

    thickness = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Meter)
    relative_permittivity = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Dimensionless
    )
    """εr (epsilon-r). Also known as dissipation/dielectric constant."""
    loss_tangent = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Dimensionless)
    """tan(δ) (tan delta). Also known as dissipation factor."""
    # material = F.Collections.Pointer.MakeChild()
    layer_type = F.Parameters.EnumParameter.MakeChild(enum_t=LayerType)
    material = F.Parameters.EnumParameter.MakeChild(enum_t=Material)

    def get_thickness(self) -> float:
        """
        Thickness in meters.
        """
        return self.thickness.get().force_extract_superset().get_single()


class is_pcb_stackup(fabll.Node):
    """
    Trait for discovering PCB stackup instances (including .ato subtypes)
    """

    is_trait = fabll.ImplementsTrait.MakeChild().put_on_type()

    def get_stackup(self) -> fabll.Node:
        return fabll.Traits(self).get_obj_raw()

    def get_layers(self) -> list[PCBLayer]:
        stackup = self.get_stackup()
        return stackup.get_children(direct_only=True, types=PCBLayer)


class is_pcb(fabll.Node):
    """
    Mark as PCB
    """

    is_trait = fabll.ImplementsTrait.MakeChild().put_on_type()


class is_company(fabll.Node):
    """
    Mark as company
    """

    is_trait = fabll.ImplementsTrait.MakeChild().put_on_type()

    company_name = F.Parameters.StringParameter.MakeChild()
    country = F.Parameters.EnumParameter.MakeChild(enum_t=ISO3166_1_A3)
    website = F.Parameters.StringParameter.MakeChild()

    @classmethod
    def MakeChild(
        cls, name: str, country: ISO3166_1_A3 | str, website: str
    ) -> fabll._ChildField[Self]:
        if isinstance(country, str):
            country = ISO3166_1_A3[country]
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.Strings.MakeChild_SetSuperset([out, cls.company_name], name)
        )
        out.add_dependant(
            F.Literals.AbstractEnums.MakeChild_SetSuperset([out, cls.country], country)
        )
        out.add_dependant(
            F.Literals.Strings.MakeChild_SetSuperset([out, cls.website], website)
        )
        return out

    def get_company_name(self) -> str:
        return self.company_name.get().extract_singleton()

    def get_country_code(self) -> ISO3166_1_A3 | None:
        """
        ISO 3166-1 alpha-3 country code.
        """
        return self.country.get().try_extract_singleton_typed(enum_type=ISO3166_1_A3)

    def get_website(self) -> str:
        return self.website.get().extract_singleton()


class has_trace_specification(fabll.Node):
    """
    Trace and clearance manufacturing capabilities.
    """

    is_trait = fabll.ImplementsTrait.MakeChild().put_on_type()

    # Trace width/spacing
    trace_width = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Meter)
    trace_spacing = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Meter)
    trace_width_tolerance = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Percent
    )

    # Annular ring widths (radial distance from hole edge to pad edge)
    pth_annular_ring_width = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Meter)
    npth_annular_ring_width = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Meter
    )

    # BGA
    bga_pad_diameter = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Meter)
    bga_pad_to_trace_clearance = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Meter
    )

    # Clearances
    pad_to_track_clearance = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Meter)
    via_to_track_clearance = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Meter)
    pth_to_track_clearance = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Meter)


class has_drill_specification(fabll.Node):
    """
    Drilling manufacturing capabilities.
    """

    is_trait = fabll.ImplementsTrait.MakeChild().put_on_type()

    # Drill hole diameter
    drill_diameter = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Meter)

    # Hole diameter tolerances
    plated_hole_diameter_tolerance = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Meter
    )
    non_plated_hole_diameter_tolerance = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Meter
    )

    # Via
    via_hole_diameter = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Meter)
    via_pad_diameter = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Meter)
    via_annular_ring_width = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Meter)

    # Non-plated hole diameter
    npth_diameter = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Meter)

    # Slot widths
    plated_slot_width = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Meter)
    non_plated_slot_width = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Meter)

    # Spacing (edge-to-edge)
    hole_to_hole_clearance = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Meter)

    # Castellated hole diameter
    castellated_hole_diameter = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Meter
    )
    castellated_hole_to_edge_clearance = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Meter
    )
    castellated_hole_to_hole_clearance = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Meter
    )

    # Plating thickness
    hole_plating_thickness = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Meter)


class has_soldermask_specification(fabll.Node):
    """
    Soldermask manufacturing capabilities.
    """

    is_trait = fabll.ImplementsTrait.MakeChild().put_on_type()

    bridge_width = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Meter)
    opening_to_trace_clearance = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Meter
    )
    plugged_via_diameter = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Meter)
    ink_thickness = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Meter)


class has_legend_specification(fabll.Node):
    """
    Silkscreen / legend manufacturing capabilities.
    """

    is_trait = fabll.ImplementsTrait.MakeChild().put_on_type()

    line_width = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Meter)
    text_height = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Meter)
    pad_to_silkscreen_clearance = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Meter
    )


class has_outline_specification(fabll.Node):
    """
    Board outline manufacturing capabilities.
    """

    is_trait = fabll.ImplementsTrait.MakeChild().put_on_type()

    copper_to_board_edge_clearance = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Meter
    )
    copper_to_slot_clearance = F.Parameters.NumericParameter.MakeChild(
        unit=F.Units.Meter
    )
    dimension_tolerance = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Meter)


class is_pcb_manufacturer(fabll.Node):
    """
    PCB fabrication house
    """

    is_trait = fabll.ImplementsTrait.MakeChild().put_on_type()


class has_pcb_manufacturing_specification(fabll.Node):
    is_trait = fabll.ImplementsTrait.MakeChild().put_on_type()

    trace_specification = fabll.Traits.MakeEdge(has_trace_specification.MakeChild())
    drill_specification = fabll.Traits.MakeEdge(has_drill_specification.MakeChild())
    soldermask_specification = fabll.Traits.MakeEdge(
        has_soldermask_specification.MakeChild()
    )
    legend_specification = fabll.Traits.MakeEdge(has_legend_specification.MakeChild())
    outline_specification = fabll.Traits.MakeEdge(has_outline_specification.MakeChild())
