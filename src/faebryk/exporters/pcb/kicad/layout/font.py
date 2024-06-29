# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from faebryk.core.core import Node
from faebryk.exporters.pcb.kicad.layout.layout import Layout

logger = logging.getLogger(__name__)


class FontLayout(Layout):
    def apply(self, node: Node):
        raise NotImplementedError()
