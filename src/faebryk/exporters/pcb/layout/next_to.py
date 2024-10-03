# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.node import Node
from faebryk.exporters.pcb.layout.heuristic_decoupling import Params, place_next_to
from faebryk.exporters.pcb.layout.layout import Layout

logger = logging.getLogger(__name__)


class LayoutNextTo(Layout):
    Parameters = Params

    def __init__(self, target: F.Electrical, params: Params | None = None):
        super().__init__()
        self._params = params or Params()
        self._target = target

    def apply(self, *node: Node):
        # Remove nodes that have a position defined
        node = tuple(
            n
            for n in node
            if not n.has_trait(F.has_pcb_position) and n.has_trait(F.has_footprint)
        )

        for n in node:
            # TODO: why the assert?
            assert isinstance(n, Module)
            place_next_to(self._target, n, route=True, params=self._params)
