# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.module import Module


class can_bridge_by_name(F.can_bridge.impl()):
    def __init__(self, input_name: str = "input", output_name: str = "output"):
        super().__init__()
        self._input_name = input_name
        self._output_name = output_name

    def get_in(self):
        return self.get_obj(Module)[self._input_name]

    def get_out(self):
        return self.get_obj(Module)[self._output_name]
