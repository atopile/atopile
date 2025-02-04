# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F


class PFET(F.MOSFET):
    def __preinit__(self) -> None:
        self.channel_type.alias_is(F.MOSFET.ChannelType.P_CHANNEL)
