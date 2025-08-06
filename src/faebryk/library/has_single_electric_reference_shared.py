# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface


class has_single_electric_reference_shared(F.has_single_electric_reference.impl()):
    lazy: F.is_lazy

    def __init__(self, gnd_only: bool = False):
        super().__init__()
        self.gnd_only = gnd_only

    def on_obj_set(self):
        super().on_obj_set()

        if not isinstance(self.obj, (Module, ModuleInterface)):
            raise TypeError(
                f"has_single_electric_reference_shared can only be used on "
                f"modules or module interfaces, got {self.obj}"
            )

        F.ElectricSignal.connect_all_module_references(self.obj, gnd_only=self.gnd_only)
