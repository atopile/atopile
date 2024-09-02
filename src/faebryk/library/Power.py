# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.moduleinterface import ModuleInterface


class Power(ModuleInterface):
    class PowerSourcesShortedError(Exception): ...

    class is_power_source(ModuleInterface.TraitT): ...

    class is_power_source_defined(is_power_source.impl()): ...

    def make_source(self):
        self.add(self.is_power_source_defined())
        return self

    def _on_connect(self, other: "Power"):
        if self.has_trait(self.is_power_source) and other.has_trait(
            self.is_power_source
        ):
            raise self.PowerSourcesShortedError(self, other)
