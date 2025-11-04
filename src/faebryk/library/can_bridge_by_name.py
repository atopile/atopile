# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll


class can_bridge_by_name(fabll.Node):
    """
    Only keeping for ato v1 compatibility.
    """

    def __init__(self, input_name: str = "input", output_name: str = "output"):
        # super().__init__()
        self._input_name = input_name
        self._output_name = output_name

    def get_in(self):
        return self.get_obj(fabll.Module)[self._input_name]

    def get_out(self):
        return self.get_obj(fabll.Module)[self._output_name]
