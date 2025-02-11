# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.node import Node
from faebryk.exporters.pcb.layout.heuristic_decoupling import Params, place_next_to
from faebryk.exporters.pcb.layout.layout import Layout
from faebryk.libs.util import not_none

logger = logging.getLogger(__name__)


class LayoutHeuristicElectricalClosenessPullResistors(Layout):
    Parameters = Params

    def __init__(self, params: Params | None = None):
        super().__init__()
        self._params = params or Params()

    def apply(self, *node: Node):
        # Remove nodes that have a position defined
        node = tuple(
            n
            for n in node
            if not n.has_trait(F.has_pcb_position) and n.has_trait(F.has_footprint)
        )

        for n in node:
            assert isinstance(n, F.Resistor)
            logic = not_none(n.get_parent_of_type(F.ElectricLogic))

            place_next_to(logic.line, n, route=True, params=self._params)

    @staticmethod
    def find_module_candidates(node: Node):
        return Module.get_children_modules(
            node,
            direct_only=False,
            types=F.Resistor,
            f_filter=lambda c: c.get_parent_of_type(F.ElectricLogic) is not None,
        )

    @classmethod
    def add_to_all_suitable_modules(cls, node: Node, params: Params | None = None):
        layout = cls(params)
        candidates = cls.find_module_candidates(node)
        for c in candidates:
            logger.debug(f"Adding {cls.__name__} to {c}")
            c.add(F.has_pcb_layout_defined(layout))
        return candidates
