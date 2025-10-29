# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.core.node as fabll
from faebryk.exporters.pcb.layout.layout import Layout


class has_pcb_layout_defined(fabll.Node):
    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()

    def __init__(self, layout: Layout) -> None:
        super().__init__()
        self.layout = layout

    def apply(self):
        node = self.obj
        return self.layout.apply(node)
