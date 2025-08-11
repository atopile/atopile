# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum, StrEnum, auto

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.node import rt_field
from faebryk.libs.library import L


class BJT(Module):
    class DopingType(Enum):
        NPN = auto()
        PNP = auto()

    class OperationRegion(Enum):
        ACTIVE = auto()
        INVERTED = auto()
        SATURATION = auto()
        CUT_OFF = auto()

    doping_type = L.p_field(domain=L.Domains.ENUM(DopingType))

    # TODO: Deprecated operation_region -> nothing
    operation_region = L.p_field(domain=L.Domains.ENUM(OperationRegion))

    emitter: F.Electrical
    base: F.Electrical
    collector: F.Electrical

    designator_prefix = L.f_field(F.has_designator_prefix)(
        F.has_designator_prefix.Prefix.Q
    )

    @L.rt_field
    def pickable(self):
        return F.is_pickable_by_type(
            endpoint=F.is_pickable_by_type.Endpoint.BJTS,
            params=[self.doping_type, self.package],
        )

    def __init__(self, doping_type: DopingType):
        super().__init__()
        self.doping_type = doping_type

    @rt_field
    def can_bridge(self):
        # if self.doping_type == self.DopingType.NPN:
        return F.can_bridge_defined(self.collector, self.emitter)
        # elif self.doping_type == self.DopingType.PNP:
        # return F.can_bridge_defined(self.emitter, self.collector)
        # else:
        # raise ValueError(f"Invalid doping type: {self.doping_type}")

    @rt_field
    def pin_association_heuristic(self):
        return F.has_pin_association_heuristic_lookup_table(
            mapping={
                self.emitter: ["E", "Emitter"],
                self.base: ["B", "Base"],
                self.collector: ["C", "Collector"],
            },
            accept_prefix=False,
            case_sensitive=False,
        )

    usage_example = L.f_field(F.has_usage_example)(
        example="""
        import BJT, Resistor, ElectricPower

        bjt = new BJT<doping_type="NPN">
        bjt.mpn = "C373737

        # Use as amplifier with bias resistors
        base_resistor = new Resistor
        collector_resistor = new Resistor
        power_supply = new ElectricPower

        # Basic amplifier configuration
        power_supply.hv ~> collector_resistor ~> bjt.collector
        bjt.emitter ~ power_supply.lv
        input_signal ~> base_resistor ~> bjt.base
        output_signal ~ bjt.collector
        """,
        language=F.has_usage_example.Language.ato,
    )

    class Package(StrEnum):
        _01005 = "STRING"

    package = L.p_field(domain=L.Domains.ENUM(Package))
