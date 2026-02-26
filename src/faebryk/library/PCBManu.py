# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import IntEnum, auto

import faebryk.core.node as fabll
import faebryk.library._F as F

logger = logging.getLogger(__name__)


# ============================================================
#  PCBLayer — single layer in a PCB stackup
# ============================================================
class PCBLayer(fabll.Node):
    class LayerType(IntEnum):
        COPPER = auto()
        CORE = auto()
        SUBSTRATE = auto()
        SOLDER_MASK = auto()
        SILK_SCREEN = auto()
        PASTE = auto()

    class Material(IntEnum):
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

    layer_type = F.Parameters.EnumParameter.MakeChild(enum_t=LayerType)
    thickness = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Meter)
    material = F.Parameters.EnumParameter.MakeChild(enum_t=Material)
    epsilon_r = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Dimensionless)
    loss_tangent = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Dimensionless)
    color = F.Parameters.StringParameter.MakeChild()


# ============================================================
#  PCBoard — base type for PCB definitions
# ============================================================
class PCBoard(fabll.Node):
    pass


# ============================================================
#  PCBManufacturer — PCB fabrication house
# ============================================================
class PCBManufacturer(fabll.Node):
    name_ = F.Parameters.StringParameter.MakeChild()
    country = F.Parameters.StringParameter.MakeChild()
    website = F.Parameters.StringParameter.MakeChild()


# ============================================================
#  Manufacturer — generic manufacturer entity
# ============================================================
class Manufacturer(fabll.Node):
    name_ = F.Parameters.StringParameter.MakeChild()
    country = F.Parameters.StringParameter.MakeChild()
    website = F.Parameters.StringParameter.MakeChild()
