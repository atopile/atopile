# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.moduleinterface import ModuleInterface


class Power(ModuleInterface):
    class is_power_source(ModuleInterface.TraitT): ...

    class is_power_sink(ModuleInterface.TraitT): ...

    def make_source(self):
        self.add(self.is_power_source.impl()())
        return self

    def make_sink(self):
        self.add(self.is_power_sink.impl()())
        return self
