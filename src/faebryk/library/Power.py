# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll


class Power(fabll.Node):
    class is_power_source(fabll.Node): ...

    class is_power_sink(fabll.Node): ...

    def make_source(self):
        self.add(self.is_power_source.impl()())
        return self

    def make_sink(self):
        self.add(self.is_power_sink.impl()())
        return self
