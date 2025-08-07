# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from enum import Enum, StrEnum, auto

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.libs.library import L
from faebryk.libs.units import P

logger = logging.getLogger(__name__)


class Fuse(Module):
    class FuseType(Enum):
        NON_RESETTABLE = auto()
        RESETTABLE = auto()

    class ResponseType(Enum):
        SLOW = auto()
        FAST = auto()

    terminals = L.list_field(2, F.Electrical)
    
    fuse_type = L.p_field(
        domain=L.Domains.ENUM(FuseType),
    )
    response_type = L.p_field(
        domain=L.Domains.ENUM(ResponseType),
    )

    rated_trip_current = L.p_field(
        units=P.A,
        likely_constrained=True,
        domain=L.Domains.Numbers.REAL(),
        soft_set=L.Range(100 * P.mA, 100 * P.A),
    )

    rated_hold_current = L.p_field(
        units=P.A,
        likely_constrained=True,
        domain=L.Domains.Numbers.REAL(),
        soft_set=L.Range(100 * P.mA, 100 * P.A),
    )

    rated_voltage = L.p_field(
        units=P.V,
        likely_constrained=True,
        soft_set=L.Range(10 * P.V, 100 * P.V),
        tolerance_guess=10 * P.percent,
    )

    rated_power_dissipation = L.p_field(
        units=P.W,
        likely_constrained=True,
        soft_set=L.Range(0.1 * P.mW, 10 * P.W),
        tolerance_guess=10 * P.percent,
    )

    @L.rt_field
    def pickable(self):
        return F.is_pickable_by_type(
            endpoint=F.is_pickable_by_type.Endpoint.FUSES,
            params=[
                self.fuse_type,
                self.response_type,
                self.rated_trip_current,
                self.rated_hold_current,
                self.rated_voltage,
                self.rated_power_dissipation,
            ],
        )
    attach_to_footprint: F.can_attach_to_footprint_symmetrically

    def __init__(self, fuse_type: FuseType):
        super().__init__()
        self.fuse_type = fuse_type

    @L.rt_field
    def can_bridge(self):
        return F.can_bridge_defined(self.terminals[0], self.terminals[1])

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.F
    )

    usage_example = L.f_field(F.has_usage_example)(
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
    )

    class Package(StrEnum):
        _01005 = "PACKAGE"

    package = L.p_field(domain=L.Domains.ENUM(Package))
