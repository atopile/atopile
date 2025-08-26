# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L


class EnablePin(ModuleInterface):
    enable: F.ElectricLogic

    def _handle_optional(self, needed: bool):
        if not needed:
            self.enable.set(True)

    def set(self, value: bool):
        self.add(F.is_optional_defined(not value, self._handle_optional))
        self.enable.set(value)

    def set_weak(self, value: bool, owner: Module):
        return self.enable.set_weak(value, owner=owner)

    @L.rt_field
    def has_single_electric_reference(self):
        return F.has_single_electric_reference_defined(self.enable.reference)

    @L.rt_field
    def is_optional(self):
        return F.is_optional_defined(False, self._handle_optional)

    def make_required(self):
        self.add(F.is_optional_defined(True, self._handle_optional))

    def get_enable_signal(self):
        self.make_required()
        return self.enable.line

    def __postinit__(self, *args, **kwargs):
        super().__postinit__(*args, **kwargs)
        self.enable.line.add(
            F.has_net_name("ENABLE", level=F.has_net_name.Level.SUGGESTED)
        )
