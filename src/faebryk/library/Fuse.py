# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import StrEnum

import faebryk.core.node as fabll
import faebryk.library._F as F

logger = logging.getLogger(__name__)


class Fuse(fabll.Node):
    # ----------------------------------------
    #                 enums
    # ----------------------------------------
    class FuseType(StrEnum):
        NON_RESETTABLE = "NON_RESETTABLE"
        RESETTABLE = "RESETTABLE"

    class ResponseType(StrEnum):
        SLOW = "SLOW"
        FAST = "FAST"

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------
    unnamed = [F.Electrical.MakeChild() for _ in range(2)]

    fuse_type = F.Parameters.EnumParameter.MakeChild(enum_t=FuseType)
    response_type = F.Parameters.EnumParameter.MakeChild(enum_t=ResponseType)
    trip_current = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Ampere)

    # ----------------------------------------
    #                 traits
    # ----------------------------------------
    _is_module = fabll.Traits.MakeEdge(fabll.is_module.MakeChild())

    _can_attatch_to_footprint = fabll.Traits.MakeEdge(
        F.Footprints.can_attach_to_footprint.MakeChild()
    )

    for e in unnamed:
        e.add_dependant(fabll.Traits.MakeEdge(F.Lead.is_lead.MakeChild(), [e]))

    _can_bridge = fabll.Traits.MakeEdge(
        F.can_bridge.MakeChild(in_=unnamed[0], out_=unnamed[1])
    )

    designator_prefix = fabll.Traits.MakeEdge(
        F.has_designator_prefix.MakeChild(F.has_designator_prefix.Prefix.F)
    )

    S = F.has_simple_value_representation.Spec
    _simple_repr = fabll.Traits.MakeEdge(
        F.has_simple_value_representation.MakeChild(
            S(trip_current, prefix="It"),
        )
    )

    usage_example = fabll.Traits.MakeEdge(
        F.has_usage_example.MakeChild(
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
    )
