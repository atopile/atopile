# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod

from faebryk.core.core import NodeTrait
from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer
from faebryk.exporters.pcb.routing.util import Route


# TODO remove transformer from here
class has_pcb_routing_strategy(NodeTrait):
    @abstractmethod
    def calculate(self, transformer: PCB_Transformer) -> list[Route]: ...

    def __init__(self) -> None:
        super().__init__()
        self.priority = 0.0

    def __repr__(self) -> str:
        return f"{type(self).__name__}(prio={self.priority})"
