# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum, auto

from faebryk.core.core import Module
from faebryk.library.can_bridge_defined import can_bridge_defined
from faebryk.library.Electrical import Electrical
from faebryk.library.has_designator_prefix_defined import has_designator_prefix_defined
from faebryk.library.has_pin_association_heuristic_lookup_table import (
    has_pin_association_heuristic_lookup_table,
)
from faebryk.library.TBD import TBD


class MOSFET(Module):
    class ChannelType(Enum):
        N_CHANNEL = auto()
        P_CHANNEL = auto()

    class SaturationType(Enum):
        ENHANCEMENT = auto()
        DEPLETION = auto()

    def __init__(self):
        super().__init__()

        class _PARAMs(Module.PARAMS()):
            channel_type = TBD[MOSFET.ChannelType]()
            saturation_type = TBD[MOSFET.SaturationType]()
            gate_source_threshold_voltage = TBD[float]()
            max_drain_source_voltage = TBD[float]()
            max_continuous_drain_current = TBD[float]()
            on_resistance = TBD[float]()

        self.PARAMs = _PARAMs(self)

        class _IFs(Module.IFS()):
            source = Electrical()
            gate = Electrical()
            drain = Electrical()

        self.IFs = _IFs(self)

        self.add_trait(has_designator_prefix_defined("Q"))
        # TODO pretty confusing
        self.add_trait(can_bridge_defined(in_if=self.IFs.source, out_if=self.IFs.drain))

        self.add_trait(
            has_pin_association_heuristic_lookup_table(
                mapping={
                    self.IFs.source: ["S", "Source"],
                    self.IFs.gate: ["G", "Gate"],
                    self.IFs.drain: ["D", "Drain"],
                },
                accept_prefix=False,
                case_sensitive=False,
            )
        )
