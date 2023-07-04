# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum

from faebryk.core.core import Module
from faebryk.library.can_bridge_defined import can_bridge_defined
from faebryk.library.Electrical import Electrical
from faebryk.library.has_defined_type_description import has_defined_type_description


class MOSFET(Module):
    class ChannelType(Enum):
        N_CHANNEL = 1
        P_CHANNEL = 2

    class SaturationType(Enum):
        ENHANCEMENT = 1
        DEPLETION = 2

    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        self._setup_traits()
        return self

    def __init__(
        self, channel_type: ChannelType, saturation_type: SaturationType
    ) -> None:
        super().__init__()

        self.channel_type = channel_type
        self.saturation_type = saturation_type

        self._setup_interfaces()
        self._setup_interfaces()

    def _setup_traits(self):
        self.add_trait(has_defined_type_description("MOSFET"))

    def _setup_interfaces(self):
        class _IFs(super().IFS()):
            source = Electrical()
            gate = Electrical()
            drain = Electrical()

        self.IFs = _IFs(self)
        # TODO pretty confusing
        self.add_trait(can_bridge_defined(in_if=self.IFs.source, out_if=self.IFs.drain))
