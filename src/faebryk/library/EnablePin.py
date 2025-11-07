# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class EnablePin(fabll.Node):
    enable = F.ElectricLogic.MakeChild()

    def _handle_optional(self, needed: bool):
        if not needed:
            self.enable.set(True)

    def set(self, value: bool):
        self.add(F.is_optional_defined(not value, self._handle_optional))
        self.enable.set(value)

    def set_weak(self, value: bool, owner: fabll.Node):
        return self.enable.set_weak(value, owner=owner)

    _single_electric_reference = fabll.ChildField(F.has_single_electric_reference)

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
