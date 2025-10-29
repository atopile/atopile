# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import Enum, auto

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class Fuse(fabll.Node):
    class FuseType(Enum):
        NON_RESETTABLE = auto()
        RESETTABLE = auto()

    class ResponseType(Enum):
        SLOW = auto()
        FAST = auto()

    unnamed = [F.Electrical.MakeChild() for _ in range(2)]
    fuse_type = fabll.Parameter.MakeChild_Enum(enum_t=FuseType)
    response_type = fabll.Parameter.MakeChild_Enum(enum_t=ResponseType)
    trip_current = fabll.Parameter.MakeChild_Numeric(unit=fabll.Units.Ampere)

    attach_to_footprint = F.can_attach_to_footprint_symmetrically.MakeChild()

    _can_bridge = F.can_bridge.MakeChild(in_=unnamed[0], out_=unnamed[1])

    designator_prefix = F.has_designator_prefix.MakeChild(
        F.has_designator_prefix.Prefix.F
    ).put_on_type()

    usage_example = F.has_usage_example.MakeChild(
        example="""
        import Fuse, ElectricPower

        fuse = new Fuse
        fuse.trip_current = 2A +/- 10%
        fuse.fuse_type = Fuse.FuseType.NON_RESETTABLE
        fuse.response_type = Fuse.ResponseType.FAST
        fuse.package = "1206"

        # Connect fuse in series with power supply
        power_input = new ElectricPower
        protected_power = new ElectricPower

        # Fuse protects the circuit from overcurrent
        power_input.hv ~> fuse ~> protected_power.hv
        power_input.lv ~ protected_power.lv

        # For resettable fuse (PTC)
        ptc_fuse = new Fuse
        ptc_fuse.trip_current = 500mA +/- 20%
        ptc_fuse.fuse_type = Fuse.FuseType.RESETTABLE
        ptc_fuse.response_type = Fuse.ResponseType.SLOW

        # Common applications: USB power protection, battery protection
        """,
        language=F.has_usage_example.Language.ato,
    ).put_on_type()
