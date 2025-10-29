# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from abc import abstractmethod
from typing import TYPE_CHECKING

import faebryk.core.node as fabll

if TYPE_CHECKING:
    from faebryk.exporters.pcb.kicad.transformer import PCB_Transformer
    from faebryk.exporters.pcb.routing.util import Route


# TODO remove transformer from here
class has_pcb_routing_strategy(fabll.Node):
    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()

    @abstractmethod
    def calculate(self, transformer: "PCB_Transformer") -> list["Route"]: ...

    def __preinit__(self):
        self.priority = 0.0

    def __repr__(self) -> str:
        return f"{type(self).__name__}(prio={self.priority})"
