# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.exporters.pcb.layout.layout import Layout
from faebryk.library.has_pcb_layout import has_pcb_layout


class has_pcb_layout_defined(has_pcb_layout.impl()):
    def __init__(self, layout: Layout) -> None:
        super().__init__()
        self.layout = layout

    def apply(self):
        node = self.get_obj()
        return self.layout.apply(node)
