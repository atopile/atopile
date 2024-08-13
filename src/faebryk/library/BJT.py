# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum, auto

from faebryk.core.core import Module, Parameter
from faebryk.library.can_bridge_defined import can_bridge_defined
from faebryk.library.Electrical import Electrical
from faebryk.library.has_designator_prefix_defined import (
    has_designator_prefix_defined,
)
from faebryk.library.has_pin_association_heuristic_lookup_table import (
    has_pin_association_heuristic_lookup_table,
)
from faebryk.library.TBD import TBD


class BJT(Module):
    class DopingType(Enum):
        NPN = auto()
        PNP = auto()

    # TODO use this, here is more info: https://en.wikipedia.org/wiki/Bipolar_junction_transistor#Regions_of_operation
    class OperationRegion(Enum):
        ACTIVE = auto()
        INVERTED = auto()
        SATURATION = auto()
        CUT_OFF = auto()

    def __init__(
        self,
        doping_type: Parameter[DopingType],
        operation_region: Parameter[OperationRegion],
    ):
        super().__init__()

        class _PARAMs(super().PARAMS()):
            doping_type = TBD[self.DopingType]()
            operation_region = TBD[self.OperationRegion]()

        self.PARAMs = _PARAMs(self)
        self.PARAMs.doping_type.merge(doping_type)
        self.PARAMs.operation_region.merge(operation_region)

        class _IFs(super().IFS()):
            emitter = Electrical()
            base = Electrical()
            collector = Electrical()

        self.IFs = _IFs(self)

        self.add_trait(has_designator_prefix_defined("Q"))
        self.add_trait(can_bridge_defined(self.IFs.collector, self.IFs.emitter))
        self.add_trait(
            has_pin_association_heuristic_lookup_table(
                mapping={
                    self.IFs.emitter: ["E", "Emitter"],
                    self.IFs.base: ["B", "Base"],
                    self.IFs.collector: ["C", "Collector"],
                },
                accept_prefix=False,
                case_sensitive=False,
            )
        )
